#!/usr/bin/env python3
"""StarRocks Upgrade Comparison Tool.

Compares two local branches of a StarRocks repository via commit log diff.
Scans for incompatibility patterns including config changes, type system
changes, and materialized view compatibility issues.

Requires: git, gh (GitHub CLI, authenticated — for --fetch-prs only)
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime

GITHUB_OWNER = "StarRocks"
GITHUB_REPO = "starrocks"


# ---------------------------------------------------------------------------
# Shell helpers
# ---------------------------------------------------------------------------

def run_cmd(cmd, cwd=None, check=True, timeout=60):
    """Run a command and return its stdout. Returns None on failure if check=False."""
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout
        )
        if check and result.returncode != 0:
            print(f"[WARN] Command failed: {' '.join(cmd)}", file=sys.stderr)
            if result.stderr:
                print(f"  stderr: {result.stderr.strip()}", file=sys.stderr)
            return None
        return result.stdout.strip() if result.returncode == 0 else None
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"[WARN] Command error: {e}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# PR extraction and fetching
# ---------------------------------------------------------------------------

PR_PATTERN = re.compile(r"#(\d{3,7})")


def extract_pr_numbers(text):
    """Extract unique PR numbers from text (e.g., #73237)."""
    if not text:
        return []
    return sorted(set(int(m) for m in PR_PATTERN.findall(text)))


def fetch_pr_details(pr_number):
    """Fetch PR details via gh CLI. Returns dict or None."""
    output = run_cmd(
        [
            "gh", "pr", "view", str(pr_number),
            "--repo", f"{GITHUB_OWNER}/{GITHUB_REPO}",
            "--json", "number,title,body,labels,files,url,state,mergedAt",
        ],
        check=False,
    )
    if output:
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            pass

    # PR might be an issue, try gh issue view
    output = run_cmd(
        [
            "gh", "issue", "view", str(pr_number),
            "--repo", f"{GITHUB_OWNER}/{GITHUB_REPO}",
            "--json", "number,title,body,labels,url,state,closedAt",
        ],
        check=False,
    )
    if output:
        try:
            data = json.loads(output)
            data["type"] = "issue"
            return data
        except json.JSONDecodeError:
            pass

    return None


# ---------------------------------------------------------------------------
# Git local repo helpers
# ---------------------------------------------------------------------------

def get_current_branch(repo_path):
    """Get the current git branch name."""
    return run_cmd(["git", "branch", "--show-current"], cwd=repo_path, check=False)


# Format: each field separated by \x01 (SOH), records separated by \x02 (STX)
_GIT_SEP = "\x01"   # field separator
_GIT_REC = "\x02"   # record separator
GIT_LOG_FORMAT = f"%H{_GIT_SEP}%an{_GIT_SEP}%ad{_GIT_SEP}%s{_GIT_SEP}%b{_GIT_REC}"


def get_branch_diff_commits(repo_path, branch_a, branch_b):
    """Get commits in branch_b that are not in branch_a, and vice versa.

    Uses a single git log call per direction with full commit details.
    Returns (only_in_b, only_in_a) — each is a list of commit dicts.
    """
    print(f"[INFO] Fetching commit log for {branch_a}..{branch_b} ...", flush=True)
    output_b = run_cmd(
        ["git", "log", f"--format={GIT_LOG_FORMAT}", "--no-merges",
         f"{branch_a}..{branch_b}"],
        cwd=repo_path, check=False, timeout=300,
    )
    print(f"[INFO] Fetching commit log for {branch_b}..{branch_a} ...", flush=True)
    output_a = run_cmd(
        ["git", "log", f"--format={GIT_LOG_FORMAT}", "--no-merges",
         f"{branch_b}..{branch_a}"],
        cwd=repo_path, check=False, timeout=300,
    )

    def parse_commits(output):
        if not output:
            return []
        commits = []
        records = output.split(_GIT_REC)
        for record in records:
            if not record.strip():
                continue
            fields = record.split(_GIT_SEP)
            if len(fields) < 5:
                continue
            hash_val = fields[0].strip()
            author = fields[1].strip()
            date = fields[2].strip()
            subject = fields[3].strip()
            body = fields[4].strip()

            if not hash_val:
                continue

            full_text = subject + " " + body
            commits.append({
                "hash": hash_val,
                "author": author,
                "date": date,
                "subject": subject,
                "body": body,
                "pr_numbers": extract_pr_numbers(full_text),
            })
        return commits

    return parse_commits(output_b), parse_commits(output_a)


def categorize_commits(commits):
    """Categorize commits by type based on conventional commit prefixes.

    Returns dict with categories as keys and commit lists as values.
    """
    categories = {
        "feat": [],
        "fix": [],
        "refactor": [],
        "perf": [],
        "test": [],
        "docs": [],
        "chore": [],
        "other": [],
    }

    prefix_pattern = re.compile(r"^(\w+)(?:\(.*?\))?(!)?:\s")

    for commit in commits:
        msg = commit.get("message", commit.get("subject", ""))
        match = prefix_pattern.match(msg)
        if match:
            prefix = match.group(1).lower()
            if prefix in categories:
                categories[prefix].append(commit)
            else:
                categories["other"].append(commit)
        else:
            categories["other"].append(commit)

    return categories


# ---------------------------------------------------------------------------
# Release notes cross-reference (reads from local branch)
# ---------------------------------------------------------------------------

def read_local_release_notes(repo_path, branch=None):
    """Read all release note files from a local StarRocks repo.

    If branch is specified, reads from that branch via git show (not working tree).
    Returns list of dicts: {filename, path, content}
    """
    release_dir = "docs/zh/release_notes"

    if branch:
        output = run_cmd(
            ["git", "ls-tree", "-r", "--name-only", branch, release_dir],
            cwd=repo_path, check=False, timeout=30,
        )
        if not output:
            return []
        filenames = [os.path.basename(f) for f in output.strip().split("\n") if f.endswith(".md")]
    else:
        local_dir = os.path.join(repo_path, release_dir)
        if not os.path.isdir(local_dir):
            return []
        filenames = sorted(os.listdir(local_dir))

    results = []
    for filename in filenames:
        if not filename.startswith("release-") or not filename.endswith(".md"):
            continue

        if branch:
            content = run_cmd(
                ["git", "show", f"{branch}:{release_dir}/{filename}"],
                cwd=repo_path, check=False, timeout=30,
            )
        else:
            filepath = os.path.join(repo_path, release_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
            except (IOError, UnicodeDecodeError):
                continue

        if content:
            results.append({
                "filename": filename,
                "path": f"{release_dir}/{filename}",
                "content": content,
            })

    return results


def extract_all_versions_with_prs(content):
    """Extract all version sections and their PR numbers from release notes.

    Returns list of dicts: {version, pr_numbers, section_preview}
    """
    if not content:
        return []

    lines = content.split("\n")
    version_heading = re.compile(r"^#+\s+(\d+\.\d+\.\d+)\s*(.*)")
    results = []
    current_version = None
    current_lines = []

    for line in lines:
        match = version_heading.match(line)
        if match:
            if current_version:
                section_text = "\n".join(current_lines)
                results.append({
                    "version": current_version,
                    "pr_numbers": extract_pr_numbers(section_text),
                    "section_preview": section_text[:500],
                })
            current_version = match.group(1)
            current_lines = [line]
        elif current_version:
            current_lines.append(line)

    if current_version:
        section_text = "\n".join(current_lines)
        results.append({
            "version": current_version,
            "pr_numbers": extract_pr_numbers(section_text),
            "section_preview": section_text[:500],
        })

    return results


def cross_reference_release_notes(repo_path, commit_pr_numbers, branch=None):
    """Cross-reference local release notes with PR numbers found in commits.

    If branch is specified, reads release notes from that branch (not working tree).
    Returns dict with cross-reference results.
    """
    rn_files = read_local_release_notes(repo_path, branch=branch)
    if not rn_files:
        return None

    all_rn_prs = set()
    versions_info = []

    for rn_file in rn_files:
        versions = extract_all_versions_with_prs(rn_file["content"])
        for ver in versions:
            all_rn_prs.update(ver["pr_numbers"])
            versions_info.append({
                "file": rn_file["filename"],
                "version": ver["version"],
                "pr_count": len(ver["pr_numbers"]),
                "pr_numbers": ver["pr_numbers"],
                "preview": ver["section_preview"],
            })

    commit_pr_set = set(commit_pr_numbers)

    return {
        "files_read": [f["filename"] for f in rn_files],
        "total_versions": len(versions_info),
        "total_rn_prs": len(all_rn_prs),
        "versions": versions_info,
        "rn_pr_in_commits": sorted(all_rn_prs & commit_pr_set),
        "rn_pr_not_in_commits": sorted(all_rn_prs - commit_pr_set),
        "commit_prs_not_in_rn": sorted(commit_pr_set - all_rn_prs),
    }


# ---------------------------------------------------------------------------
# Materialized View change scanning
# ---------------------------------------------------------------------------

MV_FILE_PATTERNS = [
    "MaterializedView.java",
    "MaterializedViewMeta.java",
    "MaterializedViewRefresh*.java",
    "MVRefresh*.java",
    "MaterializedViewRewriter.java",
    "MVPartitionScheme.java",
    "MVEmitStrategy.java",
    "TaskRun.java",
    "SchemaChangeJob.java",
    "AlterJob.java",
    "RollupJob.java",
    "MaterializedView*.java",
]

MV_KEYWORDS = [
    "materialized view",
    "MaterializedView",
    "MVRefresh",
    "refresh",
    "rewrite",
    "partition scheme",
    "incremental refresh",
    "partition pruning",
    "rollup",
    "mv partition",
    "MV_TABLE",
    "MVPartition",
    "async_materialized_view",
    "mvRewrite",
    "MV_REWRITE",
    "REFRESH_MV",
]


def scan_mv_changes(repo_path, branch_a, branch_b):
    """Scan for materialized view related code changes between branches.

    Returns dict with:
    - mv_file_changes: list of files changed that match MV patterns
    - mv_diff_findings: list of diffs containing MV keyword changes
    - summary: counts and risk assessment
    """
    findings = []
    changed_mv_files = []

    for pattern in MV_FILE_PATTERNS:
        output = run_cmd(
            ["git", "diff", "--name-only", f"{branch_a}..{branch_b}", "--",
             f"**/{pattern}"],
            cwd=repo_path, check=False, timeout=60,
        )
        if not output:
            continue
        for filepath in output.strip().split("\n"):
            if not filepath:
                continue
            if filepath not in changed_mv_files:
                changed_mv_files.append(filepath)

    for filepath in changed_mv_files:
        diff = run_cmd(
            ["git", "diff", f"{branch_a}..{branch_b}", "--", filepath],
            cwd=repo_path, check=False, timeout=30,
        )
        if not diff:
            continue

        diff_lower = diff.lower()
        matched_keywords = [kw for kw in MV_KEYWORDS if kw.lower() in diff_lower]

        change_type = "other"
        if any(kw.lower() in diff_lower for kw in ["refresh", "MVRefresh", "REFRESH_MV"]):
            change_type = "refresh_logic"
        elif any(kw.lower() in diff_lower for kw in ["rewrite", "mvRewrite", "MV_REWRITE"]):
            change_type = "rewrite_logic"
        elif any(kw.lower() in diff_lower for kw in ["partition scheme", "MVPartition", "partition pruning"]):
            change_type = "partition_handling"
        elif any(kw.lower() in diff_lower for kw in ["schema", "column", "alter", "SchemaChange"]):
            change_type = "schema_change"

        changed_lines = []
        for line in diff.split("\n"):
            if line.startswith("+") and not line.startswith("+++"):
                changed_lines.append(line[1:].strip())
            elif line.startswith("-") and not line.startswith("---"):
                changed_lines.append(line[1:].strip())

        risk = "high" if matched_keywords else "low"
        if change_type in ("refresh_logic", "rewrite_logic"):
            risk = "high"
        elif change_type == "partition_handling":
            risk = "medium"

        findings.append({
            "file": filepath,
            "change_type": change_type,
            "matched_keywords": matched_keywords,
            "risk": risk,
            "diff_preview": "\n".join(changed_lines[:30]),
        })

    high_risk = [f for f in findings if f["risk"] == "high"]
    medium_risk = [f for f in findings if f["risk"] == "medium"]

    return {
        "mv_file_changes": changed_mv_files,
        "mv_diff_findings": findings,
        "summary": {
            "total_mv_files_changed": len(changed_mv_files),
            "high_risk_mv_changes": len(high_risk),
            "medium_risk_mv_changes": len(medium_risk),
            "refresh_logic_changes": len([f for f in findings if f["change_type"] == "refresh_logic"]),
            "rewrite_logic_changes": len([f for f in findings if f["change_type"] == "rewrite_logic"]),
            "partition_handling_changes": len([f for f in findings if f["change_type"] == "partition_handling"]),
            "schema_change_on_mv": len([f for f in findings if f["change_type"] == "schema_change"]),
        },
        "high_risk": high_risk,
    }


# ---------------------------------------------------------------------------
# Scanner helpers
# ---------------------------------------------------------------------------

def _extract_fields_from_content(content, regex):
    """Extract field definitions from content using regex. Returns dict of {name: {type, value}}."""
    if not content:
        return {}
    fields = {}
    for m in re.finditer(regex, content):
        type_ = m.group(1)
        name = m.group(2)
        value = m.group(3).strip()
        fields[name] = {"type": type_, "value": value}
    return fields


def _diff_field_sets(old_fields, new_fields, trivial_values=None):
    """Compare two field dicts and return (added, removed, changed) lists.

    Each item in the returned lists is a dict with keys: name, type, old_value, new_value.
    """
    if trivial_values is None:
        trivial_values = {"0", "0L", "0f", "0d", '""', "null", "{}"}

    added = []
    removed = []
    changed = []

    for name in sorted(set(old_fields.keys()) & set(new_fields.keys())):
        if old_fields[name]["value"] != new_fields[name]["value"]:
            changed.append({
                "name": name,
                "type": old_fields[name]["type"],
                "old_value": old_fields[name]["value"],
                "new_value": new_fields[name]["value"],
            })

    for name in sorted(set(new_fields.keys()) - set(old_fields.keys())):
        val = new_fields[name]["value"].rstrip(";").rstrip("L").rstrip("f").rstrip("d")
        if val not in trivial_values and val != "0":
            added.append({
                "name": name,
                "type": new_fields[name]["type"],
                "new_value": new_fields[name]["value"],
            })

    for name in sorted(set(old_fields.keys()) - set(new_fields.keys())):
        removed.append({
            "name": name,
            "type": old_fields[name]["type"],
            "old_value": old_fields[name]["value"],
        })

    return added, removed, changed


HIGH_RISK_CONFIG_NAMES = {
    "mysql_server_version", "transform_type_prefer_string_for_varchar",
    "max_varchar_length", "enable_load_volume_from_conf",
    "enable_alter_struct_column", "enable_rollback_default_warehouse",
}

HIGH_RISK_SESSION_VAR_NAMES = {
    "enable_materialized_view_rewrite", "query_timeout", "sql_mode",
    "pipeline_dop", "parallel_fragment_exec_instance_num",
    "prefer_compute_node", "enable_profile", "wait_timeout",
    "net_read_timeout", "new_planner_optimize_timeout",
    "enable_replication_starlet", "transaction_isolation",
}

HIGH_RISK_BE_CONFIG_NAMES = {
    "max_tablet_version_count", "base_compaction_check_interval_seconds",
    "storage_root_path", "mem_limit", "chunk_reserved_bytes_limit",
    "max_runnings_transactions_per_txn_map", "tablet_meta_shutdown_grace_time_s",
    "primary_key_limit_size", "update_cache_expire_sec",
    "tablet_max_versions", "l0_max_mem_usage",
}

DATA_IMPACT_CONFIG_NAMES = {
    "max_varchar_length", "transform_type_prefer_string_for_varchar",
    "enable_alter_struct_column", "max_tablet_version_count",
    "primary_key_limit_size", "chunk_reserved_bytes_limit",
}

BEHAVIOR_IMPACT_CONFIG_NAMES = {
    "enable_materialized_view_rewrite", "sql_mode", "query_timeout",
    "mysql_server_version", "pipeline_dop",
    "parallel_fragment_exec_instance_num", "prefer_compute_node",
}


def _is_high_risk_name(name, high_risk_set):
    """Check if a config name is in the high-risk set or is a substring match."""
    if name in high_risk_set:
        return True
    for risk_name in high_risk_set:
        if risk_name in name or name in risk_name:
            return True
    return False


def _assess_impact(name, change_type="config_changed"):
    """Assess compatibility impact for a config/variable change."""
    return {
        "data": _is_high_risk_name(name, DATA_IMPACT_CONFIG_NAMES),
        "behavior": _is_high_risk_name(name, BEHAVIOR_IMPACT_CONFIG_NAMES),
        "operational": _is_high_risk_name(name, HIGH_RISK_CONFIG_NAMES | HIGH_RISK_SESSION_VAR_NAMES | HIGH_RISK_BE_CONFIG_NAMES),
        "rolling_upgrade": change_type in ("protocol_field_removed", "storage_format_changed"),
    }


def _classify_config_risk(name, change_type, old_value=None, new_value=None):
    """Classify risk level for a config change."""
    if _is_high_risk_name(name, HIGH_RISK_CONFIG_NAMES | HIGH_RISK_SESSION_VAR_NAMES | HIGH_RISK_BE_CONFIG_NAMES):
        return "high"
    if old_value is not None and new_value is not None:
        if old_value in ("true", "false") and new_value in ("true", "false"):
            return "medium"
    return "low"


def _diff_changed_lines(diff):
    """Extract added/removed lines from a git diff."""
    added = []
    removed = []
    for line in diff.split("\n"):
        if line.startswith("+") and not line.startswith("+++"):
            added.append(line[1:].strip())
        elif line.startswith("-") and not line.startswith("---"):
            removed.append(line[1:].strip())
    return added, removed


# ---------------------------------------------------------------------------
# Commit tier classification
# ---------------------------------------------------------------------------

HIGH_TIER_PATHS = [
    # FE core
    "fe/fe-core/src/main/java/com/starrocks/sql/optimizer/",
    "fe/fe-core/src/main/java/com/starrocks/planner/",
    "fe/fe-core/src/main/java/com/starrocks/execution/",
    "fe/fe-core/src/main/java/com/starrocks/catalog/",
    "fe/fe-core/src/main/java/com/starrocks/analysis/",
    "fe/fe-core/src/main/java/com/starrocks/sql/ast/",
    "fe/fe-core/src/main/java/com/starrocks/qe/",
    "fe/fe-core/src/main/java/com/starrocks/service/",
    "fe/fe-core/src/main/java/com/starrocks/transaction/",
    "fe/fe-core/src/main/java/com/starrocks/load/",
    "fe/fe-core/src/main/java/com/starrocks/alter/",
    "fe/fe-core/src/main/java/com/starrocks/persist/",
    # BE core
    "be/src/runtime/",
    "be/src/storage/",
    "be/src/service/",
    "be/src/http/",
    "be/src/agent/",
    # Protocol/IDL
    "gensrc/proto/",
    "gensrc/thrift/",
    # MV (exact file names)
]

HIGH_TIER_FILE_PATTERNS = [
    "MaterializedView.java",
    "MaterializedViewMeta.java",
    "MaterializedViewRefresh*.java",
    "MVRefresh*.java",
    "MaterializedViewRewriter.java",
    "MaterializedViewHandler.java",
    "Column.java",
    "ScalarType.java",
    "Type.java",
    "SchemaChangeJob.java",
    "AlterJob.java",
    "AlterJobMgr.java",
    "GlobalStateMgr.java",
    "StorageEngine.java",
]

MEDIUM_TIER_PATHS = [
    "fe/fe-core/src/main/java/com/starrocks/connector/",
    "fe/fe-core/src/main/java/com/starrocks/authentication/",
    "fe/fe-core/src/main/java/com/starrocks/privilege/",
    "fe/fe-core/src/main/java/com/starrocks/sql/parser/",
    "fe/fe-core/src/main/java/com/starrocks/catalog/",
    "fe/fe-core/src/main/java/com/starrocks/scheduler/",
    "fe/fe-core/src/main/java/com/starrocks/monitor/",
    "fe/fe-core/src/main/java/com/starrocks/common/",
    "be/src/util/",
    "be/src/exprs/",
    "be/src/column/",
    "be/src/http/",
    "be/src/gutil/",
    "be/src/connector/",
]

SKIP_TIER_PATHS = [
    "fe/fe-core/src/test/",
    "be/src/test/",
    "testlibs/",
    "docs/",
    ".github/",
    "community/",
    "contrib/",
]

SKIP_TIER_PREFIXES = [
    "build",
    "chore",
    "ci",
    "style",
    "revert",
]


def _matches_path(filepath, path_list):
    """Check if filepath matches any prefix in path_list."""
    for p in path_list:
        if filepath.startswith(p) or f"/{p}" in filepath:
            return True
    return False


def _matches_file_pattern(filepath, pattern_list):
    """Check if filepath's basename matches any glob pattern in pattern_list."""
    import fnmatch
    basename = os.path.basename(filepath)
    for p in pattern_list:
        if fnmatch.fnmatch(basename, p):
            return True
    return False


def classify_commit_tier(commit, changed_files=None):
    """Classify a commit into a risk tier based on changed file paths and commit type.

    Returns (tier, tier_reason) where tier is HIGH/MEDIUM/LOW/SKIP.
    """
    if changed_files is None:
        changed_files = []

    subject = commit.get("subject", "")

    # Check SKIP first — test/docs/build commits
    prefix_pattern = re.compile(r"^(\w+)(?:\(.*?\))?(!)?:\s")
    match = prefix_pattern.match(subject)
    prefix = match.group(1).lower() if match else ""

    if prefix in SKIP_TIER_PREFIXES:
        return "SKIP", f"commit type: {prefix}"

    # If all changed files are in skip paths, skip the commit
    if changed_files and all(_matches_path(f, SKIP_TIER_PATHS) for f in changed_files):
        non_test = [f for f in changed_files if not _matches_path(f, SKIP_TIER_PATHS)]
        if not non_test:
            return "SKIP", "all changed files in skip paths (test/docs/build)"

    # Check HIGH tier
    high_reasons = []
    for filepath in changed_files:
        if _matches_path(filepath, HIGH_TIER_PATHS):
            matched = [p for p in HIGH_TIER_PATHS if filepath.startswith(p) or f"/{p}" in filepath]
            high_reasons.append(f"core path: {matched[0]}")
        if _matches_file_pattern(filepath, HIGH_TIER_FILE_PATTERNS):
            high_reasons.append(f"critical file: {os.path.basename(filepath)}")

    if high_reasons:
        return "HIGH", "; ".join(set(high_reasons))

    # Check MEDIUM tier
    medium_reasons = []
    for filepath in changed_files:
        if _matches_path(filepath, MEDIUM_TIER_PATHS):
            matched = [p for p in MEDIUM_TIER_PATHS if filepath.startswith(p) or f"/{p}" in filepath]
            medium_reasons.append(f"business path: {matched[0]}")

    # feat/fix in any Java/C++ file is at least MEDIUM
    if prefix in ("feat", "fix") and changed_files:
        has_source = any(f.endswith((".java", ".cpp", ".h", ".py", ".scala")) for f in changed_files)
        if has_source:
            medium_reasons.append(f"feat/fix with source code changes")

    if medium_reasons:
        return "MEDIUM", "; ".join(set(medium_reasons))

    return "LOW", "non-core or infrastructure change"


def get_commit_changed_files(repo_path, commit_hash):
    """Get the list of files changed by a commit via git show --stat."""
    output = run_cmd(
        ["git", "show", "--stat", "--format=", commit_hash],
        cwd=repo_path, check=False, timeout=30,
    )
    if not output:
        return []

    files = []
    for line in output.strip().split("\n"):
        line = line.strip()
        if not line or "file changed" in line or "files changed" in line:
            continue
        parts = line.split("|")
        if len(parts) >= 2:
            filepath = parts[0].strip()
            if filepath:
                files.append(filepath)
    return files


def get_commit_diff(repo_path, commit_hash, max_lines=2000):
    """Get the full diff for a commit, truncated at max_lines."""
    output = run_cmd(
        ["git", "show", "--format=", commit_hash],
        cwd=repo_path, check=False, timeout=30,
    )
    if not output:
        return None

    lines = output.split("\n")
    if len(lines) > max_lines:
        return "\n".join(lines[:max_lines]) + f"\n... (truncated, {len(lines)} total lines)"
    return output


def classify_and_save_commits(repo_path, commits, output_dir, branch_label, skip_diff=False, diff_stat_only=False):
    """Classify commits into tiers and save per-commit metadata and diffs.

    Returns dict with tier statistics and list of commit meta dicts.
    """
    tier_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "SKIP": 0}
    commit_metas = []
    detail_dir = os.path.join(output_dir, "commits", "detail")

    for i, commit in enumerate(commits):
        hash_val = commit["hash"]
        print(f"[INFO] Classifying commit {i+1}/{len(commits)}: {hash_val[:8]} {commit['subject'][:60]}...",
              end="", flush=True)

        changed_files = get_commit_changed_files(repo_path, hash_val)
        tier, tier_reason = classify_commit_tier(commit, changed_files)
        tier_counts[tier] += 1

        meta = {
            "hash": hash_val,
            "subject": commit["subject"],
            "author": commit.get("author", ""),
            "date": commit.get("date", ""),
            "pr_numbers": commit.get("pr_numbers", []),
            "tier": tier,
            "tier_reason": tier_reason,
            "changed_files": changed_files,
        }

        # Save diff for HIGH/MEDIUM commits
        if tier in ("HIGH", "MEDIUM") and not skip_diff:
            if not diff_stat_only:
                diff_content = get_commit_diff(repo_path, hash_val)
                if diff_content:
                    diff_path = os.path.join(detail_dir, f"{hash_val}-diff.txt")
                    os.makedirs(detail_dir, exist_ok=True)
                    with open(diff_path, "w", encoding="utf-8") as f:
                        f.write(diff_content)
                    meta["diff_file"] = f"detail/{hash_val}-diff.txt"

        commit_metas.append(meta)
        print(f" [{tier}]")

    # Save all commit metas
    meta_path = os.path.join(output_dir, "commits", f"tiered-{branch_label}.json")
    os.makedirs(os.path.dirname(meta_path), exist_ok=True)
    save_json(commit_metas, meta_path)

    return {
        "tier_counts": tier_counts,
        "commit_metas": commit_metas,
        "high_medium_commits": [m for m in commit_metas if m["tier"] in ("HIGH", "MEDIUM")],
        "meta_file": f"commits/tiered-{branch_label}.json",
    }


def _scan_files_diff(repo_path, branch_a, branch_b, file_patterns):
    """Find changed files matching patterns and return their diffs.

    Returns list of (filepath, diff_text) tuples.
    """
    changed_files = []
    for pattern in file_patterns:
        output = run_cmd(
            ["git", "diff", "--name-only", f"{branch_a}..{branch_b}", "--", f"**/{pattern}"],
            cwd=repo_path, check=False, timeout=60,
        )
        if not output:
            continue
        for filepath in output.strip().split("\n"):
            if filepath and filepath not in [f for f, _ in changed_files]:
                changed_files.append(filepath)

    results = []
    for filepath in changed_files:
        diff = run_cmd(
            ["git", "diff", f"{branch_a}..{branch_b}", "--", filepath],
            cwd=repo_path, check=False, timeout=30,
        )
        if diff:
            results.append((filepath, diff))
    return results


# ---------------------------------------------------------------------------
# Additional scanners (Session Variable, System Variable, BE Config, etc.)
# ---------------------------------------------------------------------------

def _parse_session_variable_java(content):
    """Parse SessionVariable.java content with @VarAttr annotation metadata.

    Uses a line-by-line state machine to capture:
    - Field type, name, default value
    - @VarAttr annotation: var_name (SQL variable name), flag (INVISIBLE, etc.)

    Returns dict of {field_name: {type, value, var_name, flag}}
    """
    if not content:
        return {}

    vars_ = {}
    lines = content.split("\n")
    in_annotation = False
    annotation_text = ""

    for line in lines:
        stripped = line.strip()

        # Track @VarAttr annotation (may span multiple lines if '(' without ')')
        if "@VarAttr" in stripped:
            annotation_text = stripped
            if "(" in stripped and ")" not in stripped:
                in_annotation = True
            else:
                in_annotation = False
            continue

        if in_annotation:
            annotation_text += " " + stripped
            if ")" in stripped:
                in_annotation = False
            continue

        # Match field declaration — handle any access modifier (public/private/protected/static/final)
        m = re.match(r'\s*(?:(?:public|private|protected)\s+)?(?:(?:static|final)\s+)*(\w+)\s+(\w+)\s*=\s*(.+)', stripped)
        if m:
            type_, name, value_raw = m.group(1), m.group(2), m.group(3).strip()
            # Strip inline comments first, then semicolons and whitespace
            value = re.sub(r'//.*$', '', value_raw).strip().rstrip(";").strip()

            var_name = None
            flag = None
            if annotation_text:
                name_m = re.search(r'name\s*=\s*(\w+)', annotation_text)
                if name_m:
                    var_name = name_m.group(1)
                flag_m = re.search(r'flag\s*=\s*(\w+(?:\.\w+)*)', annotation_text)
                if flag_m:
                    flag = flag_m.group(1)

            vars_[name] = {
                "type": type_,
                "value": value,
                "var_name": var_name,
                "flag": flag,
            }
            annotation_text = ""
        elif not stripped.startswith("//") and stripped and not stripped.startswith("@"):
            # Non-comment, non-annotation, non-field line — reset annotation to prevent leakage
            annotation_text = ""

    return vars_


def scan_session_variables(repo_path, branch_a, branch_b):
    """Scan SessionVariable.java for default value changes between branches.

    Captures @VarAttr metadata (var_name, flag).
    Returns list of dicts with changed session variable details.
    """
    config_path = "fe/fe-core/src/main/java/com/starrocks/qe/SessionVariable.java"

    def extract(ref):
        content = run_cmd(["git", "show", f"{ref}:{config_path}"], cwd=repo_path, check=False)
        return _parse_session_variable_java(content) if content else {}

    old_vars = extract(branch_a)
    new_vars = extract(branch_b)
    if not old_vars or not new_vars:
        return []

    added, removed, changed = _diff_field_sets(old_vars, new_vars)
    findings = []

    for item in changed:
        risk = _classify_config_risk(item["name"], "session_var_changed", item["old_value"], item["new_value"])
        finding = {
            "type": "session_var_changed",
            "name": item["name"],
            "config_type": item["type"],
            "old_value": item["old_value"],
            "new_value": item["new_value"],
            "risk": risk,
            "impact": _assess_impact(item["name"]),
            "file": config_path,
        }
        # Attach @VarAttr metadata if available
        new_meta = new_vars.get(item["name"], {})
        if new_meta.get("var_name"):
            finding["var_name"] = new_meta["var_name"]
        if new_meta.get("flag"):
            finding["flag"] = new_meta["flag"]
        findings.append(finding)

    for item in added:
        risk = _classify_config_risk(item["name"], "session_var_added")
        finding = {
            "type": "session_var_added",
            "name": item["name"],
            "config_type": item["type"],
            "default_value": item["new_value"],
            "risk": risk,
            "impact": _assess_impact(item["name"]),
            "file": config_path,
        }
        new_meta = new_vars.get(item["name"], {})
        if new_meta.get("var_name"):
            finding["var_name"] = new_meta["var_name"]
        if new_meta.get("flag"):
            finding["flag"] = new_meta["flag"]
        findings.append(finding)

    for item in removed:
        findings.append({
            "type": "session_var_removed",
            "name": item["name"],
            "config_type": item["type"],
            "old_value": item["old_value"],
            "risk": "high",
            "impact": _assess_impact(item["name"]),
            "file": config_path,
        })

    return findings


def scan_system_variables(repo_path, branch_a, branch_b):
    """Scan GlobalVariable.java for system variable default changes."""
    config_paths = [
        "fe/fe-core/src/main/java/com/starrocks/qe/GlobalVariable.java",
        "fe/fe-core/src/main/java/com/starrocks/qe/SysVariable.java",
    ]
    field_regex = re.compile(r'public\s+(?:static\s+)?(\w+)\s+(\w+)\s*=\s*(.+?);')
    findings = []

    for config_path in config_paths:
        def extract(ref):
            content = run_cmd(["git", "show", f"{ref}:{config_path}"], cwd=repo_path, check=False)
            return _extract_fields_from_content(content, field_regex) if content else {}

        old_vars = extract(branch_a)
        new_vars = extract(branch_b)
        if not old_vars or not new_vars:
            continue

        _, _, changed = _diff_field_sets(old_vars, new_vars)
        for item in changed:
            risk = _classify_config_risk(item["name"], "system_var_changed", item["old_value"], item["new_value"])
            findings.append({
                "type": "system_var_changed",
                "name": item["name"],
                "config_type": item["type"],
                "old_value": item["old_value"],
                "new_value": item["new_value"],
                "risk": risk,
                "impact": _assess_impact(item["name"]),
                "file": config_path,
            })

    return findings


def _parse_be_config_h(content):
    """Parse BE config.h CONF_* macros.

    StarRocks BE uses macros like:
        CONF_Int32(name, "default")
        CONF_Bool(name, "default")
        CONF_String(name, "default")
        CONF_mInt32(name, "default")  // mutable
        CONF_mBool(name, "default")   // mutable

    Returns dict of {name: {type, value, mutable}}
    """
    if not content:
        return {}
    configs = {}
    # Match CONF_* macros: CONF_Type(name, "default_value")
    for m in re.finditer(r'CONF_(m?\w+)\((\w+),\s*"([^"]*)"\)', content):
        macro_type, name, value = m.group(1), m.group(2), m.group(3)
        mutable = macro_type.startswith("m")
        configs[name] = {"type": macro_type, "value": value, "mutable": mutable}
    return configs


def scan_be_config(repo_path, branch_a, branch_b):
    """Scan BE config.h for default value changes between branches.

    StarRocks BE uses CONF_* macros (CONF_Int32, CONF_Bool, CONF_String, etc.)
    with CONF_m* prefix for mutable configs.
    """
    config_path = "be/src/common/config.h"

    def extract(ref):
        content = run_cmd(["git", "show", f"{ref}:{config_path}"], cwd=repo_path, check=False)
        return _parse_be_config_h(content) if content else {}

    old_configs = extract(branch_a)
    new_configs = extract(branch_b)
    if not old_configs or not new_configs:
        return []

    added, removed, changed = _diff_field_sets(old_configs, new_configs)
    findings = []

    for item in changed:
        risk = _classify_config_risk(item["name"], "be_config_changed", item["old_value"], item["new_value"])
        finding = {
            "type": "be_config_changed",
            "name": item["name"],
            "config_type": item["type"],
            "old_value": item["old_value"],
            "new_value": item["new_value"],
            "risk": risk,
            "impact": _assess_impact(item["name"]),
            "file": config_path,
        }
        new_meta = new_configs.get(item["name"], {})
        if "mutable" in new_meta:
            finding["mutable"] = new_meta["mutable"]
        findings.append(finding)

    for item in added:
        risk = _classify_config_risk(item["name"], "be_config_added")
        finding = {
            "type": "be_config_added",
            "name": item["name"],
            "config_type": item["type"],
            "default_value": item["new_value"],
            "risk": risk,
            "impact": _assess_impact(item["name"]),
            "file": config_path,
        }
        new_meta = new_configs.get(item["name"], {})
        if "mutable" in new_meta:
            finding["mutable"] = new_meta["mutable"]
        findings.append(finding)

    for item in removed:
        findings.append({
            "type": "be_config_removed",
            "name": item["name"],
            "config_type": item["type"],
            "old_value": item["old_value"],
            "risk": "high",
            "impact": _assess_impact(item["name"]),
            "file": config_path,
        })

    return findings


def scan_protocol_changes(repo_path, branch_a, branch_b):
    """Scan Thrift/Protobuf IDL files for protocol-breaking changes.

    Detects removed fields, new required fields, enum value changes, and
    service/method removals that break FE-BE communication or rolling upgrades.
    """
    file_patterns = ["*.thrift", "*.proto"]
    protocol_keywords = {"struct", "enum", "service", "message", "rpc", "required", "optional", "removed"}

    findings = []
    for filepath, diff in _scan_files_diff(repo_path, branch_a, branch_b, file_patterns):
        added_lines, removed_lines = _diff_changed_lines(diff)

        # Detect removed enum values
        removed_enum = [l for l in removed_lines if re.match(r'\s*\d+\s*[:=]', l.strip())]
        added_enum = [l for l in added_lines if re.match(r'\s*\d+\s*[:=]', l.strip())]
        if removed_enum and not added_enum:
            findings.append({
                "type": "protocol_field_removed",
                "file": filepath,
                "detail": f"{len(removed_enum)} enum value(s) removed",
                "diff_preview": "\n".join(removed_enum[:10]),
                "risk": "critical",
                "impact": {"data": False, "behavior": True, "operational": False, "rolling_upgrade": True},
            })

        # Detect removed struct/message fields (lines with field IDs that were deleted)
        removed_fields = [l for l in removed_lines if re.search(r':\s*\w+', l) and any(kw in l.lower() for kw in protocol_keywords)]
        if removed_fields:
            findings.append({
                "type": "protocol_field_removed",
                "file": filepath,
                "detail": f"{len(removed_fields)} field(s) removed from struct/message",
                "diff_preview": "\n".join(removed_fields[:10]),
                "risk": "critical",
                "impact": {"data": False, "behavior": True, "operational": False, "rolling_upgrade": True},
            })

        # Detect new required fields
        new_required = [l for l in added_lines if "required" in l.lower()]
        if new_required:
            findings.append({
                "type": "protocol_required_field_added",
                "file": filepath,
                "detail": f"{len(new_required)} new required field(s) added",
                "diff_preview": "\n".join(new_required[:10]),
                "risk": "high",
                "impact": {"data": False, "behavior": True, "operational": False, "rolling_upgrade": True},
            })

    return findings


def scan_parser_changes(repo_path, branch_a, branch_b):
    """Scan SQL parser files for syntax changes.

    Detects changes to grammar rules, token definitions, and AST building
    that could affect SQL compatibility.
    """
    file_patterns = [
        "StarRocksParser.g4", "StarRocksLex.jflex",
        "SqlParser.java", "AstBuilder.java",
    ]
    parser_keywords = {"ALTER", "DROP", "CREATE", "UNSUPPORTED", "DEPRECATED", "reserved", "syntax", "nonReserved"}

    findings = []
    for filepath, diff in _scan_files_diff(repo_path, branch_a, branch_b, file_patterns):
        added_lines, removed_lines = _diff_changed_lines(diff)

        matched_keywords = set()
        for line in added_lines + removed_lines:
            for kw in parser_keywords:
                if kw in line:
                    matched_keywords.add(kw)

        if matched_keywords:
            findings.append({
                "type": "parser_change",
                "file": filepath,
                "keywords": sorted(matched_keywords),
                "lines_changed": len(added_lines) + len(removed_lines),
                "diff_preview": "\n".join((added_lines + removed_lines)[:20]),
                "risk": "medium",
                "impact": {"data": False, "behavior": True, "operational": False, "rolling_upgrade": False},
            })

    return findings


def scan_auth_changes(repo_path, branch_a, branch_b):
    """Scan authentication and privilege management files for changes."""
    file_patterns = [
        "AuthenticationManager.java", "PrivilegeManager.java",
        "AuthorizationMgr.java", "AccessController*.java",
    ]
    auth_keywords = {"GRANT", "REVOKE", "privilege", "authentication", "plugin", "role", "user", "password", "LDAP", "OIDC"}

    findings = []
    for filepath, diff in _scan_files_diff(repo_path, branch_a, branch_b, file_patterns):
        added_lines, removed_lines = _diff_changed_lines(diff)

        matched_keywords = set()
        for line in added_lines + removed_lines:
            for kw in auth_keywords:
                if kw.lower() in line.lower():
                    matched_keywords.add(kw)

        if matched_keywords:
            findings.append({
                "type": "auth_change",
                "file": filepath,
                "keywords": sorted(matched_keywords),
                "lines_changed": len(added_lines) + len(removed_lines),
                "diff_preview": "\n".join((added_lines + removed_lines)[:20]),
                "risk": "medium",
                "impact": {"data": False, "behavior": False, "operational": True, "rolling_upgrade": False},
            })

    return findings


def scan_storage_format(repo_path, branch_a, branch_b):
    """Scan BE storage format files for data format changes.

    Detects changes to segment format, tablet metadata, page format, encoding,
    and compression that could affect existing data readability.
    """
    file_patterns = [
        "segment_format*.h", "tablet_meta*.h", "rowset/segment*.cpp",
        "column/ordinal_page*.cpp", "storage_types.h",
    ]
    format_keywords = {"VERSION", "FORMAT", "PAGE_SIZE", "CHUNK_SIZE", "ENCODING", "COMPRESSION", "DEFAULT_COMPRESSION", "TABLET_FORMAT_VERSION", "ROWSET_VERSION"}

    findings = []
    for filepath, diff in _scan_files_diff(repo_path, branch_a, branch_b, file_patterns):
        added_lines, removed_lines = _diff_changed_lines(diff)

        matched_keywords = set()
        for line in added_lines + removed_lines:
            for kw in format_keywords:
                if kw in line:
                    matched_keywords.add(kw)

        if matched_keywords:
            findings.append({
                "type": "storage_format_changed",
                "file": filepath,
                "keywords": sorted(matched_keywords),
                "lines_changed": len(added_lines) + len(removed_lines),
                "diff_preview": "\n".join((added_lines + removed_lines)[:20]),
                "risk": "critical",
                "impact": {"data": True, "behavior": True, "operational": True, "rolling_upgrade": True},
            })

    return findings


def scan_charset_collation(repo_path, branch_a, branch_b):
    """Scan charset and collation files for string comparison behavior changes."""
    file_patterns = [
        "Collation*.java", "charset*.java", "Charset*.java",
    ]
    charset_keywords = {"utf8mb4", "utf8", "collation", "gmb", "binary", "CI", "CS", "unicode", "general_ci", "0900"}

    findings = []
    for filepath, diff in _scan_files_diff(repo_path, branch_a, branch_b, file_patterns):
        added_lines, removed_lines = _diff_changed_lines(diff)

        matched_keywords = set()
        for line in added_lines + removed_lines:
            for kw in charset_keywords:
                if kw.lower() in line.lower():
                    matched_keywords.add(kw)

        if matched_keywords:
            findings.append({
                "type": "charset_collation_change",
                "file": filepath,
                "keywords": sorted(matched_keywords),
                "lines_changed": len(added_lines) + len(removed_lines),
                "diff_preview": "\n".join((added_lines + removed_lines)[:20]),
                "risk": "medium",
                "impact": {"data": True, "behavior": True, "operational": False, "rolling_upgrade": False},
            })

    return findings


# ---------------------------------------------------------------------------
# Unified scanner registry
# ---------------------------------------------------------------------------

_SCANNERS = [
    ("session_variables", scan_session_variables),
    ("system_variables", scan_system_variables),
    ("be_config", scan_be_config),
    ("protocol", scan_protocol_changes),
    ("parser", scan_parser_changes),
    ("auth", scan_auth_changes),
    ("storage_format", scan_storage_format),
    ("charset_collation", scan_charset_collation),
]


# ---------------------------------------------------------------------------
# Incompatibility scanning
# ---------------------------------------------------------------------------

def _parse_config_java(content):
    """Parse Config.java content with @ConfField annotation metadata.

    Uses a line-by-line state machine to capture:
    - Field type, name, default value
    - @ConfField annotation: mutable flag, comment
    - @Deprecated annotation
    - Multi-line field declarations

    Returns dict of {name: {type, value, mutable, comment, deprecated}}
    """
    if not content:
        return {}

    configs = {}
    lines = content.split("\n")
    in_annotation = False
    annotation_text = ""
    deprecated = False

    for line in lines:
        stripped = line.strip()

        # Track @Deprecated
        if stripped == "@Deprecated":
            deprecated = True
            continue

        # Track @ConfField annotation (may span multiple lines if it has '(' but no ')')
        if "@ConfField" in stripped:
            annotation_text = stripped
            if "(" in stripped and ")" not in stripped:
                # Multi-line annotation: @ConfField(mutable = true,\n  comment = "...")
                in_annotation = True
            else:
                # Complete annotation: @ConfField or @ConfField(mutable = true)
                in_annotation = False
            continue

        if in_annotation:
            annotation_text += " " + stripped
            if ")" in stripped:
                in_annotation = False
            continue

        # Match field declaration — capture value up to semicolon (handles inline comments)
        m = re.match(r'\s*public\s+static\s+(\S+)\s+(\w+)\s*=\s*(.+?);', stripped)
        if m:
            type_, name, value_raw = m.group(1), m.group(2), m.group(3).strip()
            # Multi-line values (no ';' on this line) — rare (1 case in 744 fields), skip
            if ";" not in line and not value_raw:
                continue
            value = value_raw.strip()

            # Parse annotation metadata
            mutable = None
            comment = None
            if annotation_text:
                mutable_m = re.search(r'mutable\s*=\s*(true|false)', annotation_text)
                if mutable_m:
                    mutable = mutable_m.group(1) == "true"
                comment_m = re.search(r'comment\s*=\s*"([^"]*)"', annotation_text)
                if comment_m:
                    comment = comment_m.group(1)

            configs[name] = {
                "type": type_,
                "value": value,
                "mutable": mutable,
                "comment": comment,
                "deprecated": deprecated,
            }

            # Reset state
            annotation_text = ""
            deprecated = False
        elif not stripped.startswith("//") and stripped and not stripped.startswith("@"):
            # Non-comment, non-annotation, non-field line — reset state to prevent leakage
            annotation_text = ""
            if deprecated:
                deprecated = False

    return configs


def scan_config_changes(repo_path, branch_a, branch_b):
    """Scan Config.java for default value changes between branches.

    Captures @ConfField annotation metadata (mutable, comment) and @Deprecated.
    Returns list of dicts with changed config details including annotation info.
    """
    config_path = "fe/fe-core/src/main/java/com/starrocks/common/Config.java"

    def extract_configs(ref):
        content = run_cmd(["git", "show", f"{ref}:{config_path}"], cwd=repo_path, check=False)
        return _parse_config_java(content) if content else {}

    old_configs = extract_configs(branch_a)
    new_configs = extract_configs(branch_b)
    if not old_configs or not new_configs:
        return []

    changes = []

    # Changed configs
    for name in sorted(set(old_configs.keys()) & set(new_configs.keys())):
        old = old_configs[name]
        new = new_configs[name]
        if old["value"] != new["value"]:
            change = {
                "type": "config_changed",
                "name": name,
                "config_type": old["type"],
                "old_value": old["value"],
                "new_value": new["value"],
                "file": config_path,
            }
            # Attach annotation metadata from new version
            if new["mutable"] is not None:
                change["mutable"] = new["mutable"]
            if new["comment"]:
                change["comment"] = new["comment"]
            if old["deprecated"] or new["deprecated"]:
                change["deprecated"] = True
            changes.append(change)

        # Detect annotation changes (mutable flag changed)
        if old["mutable"] != new["mutable"] and old["mutable"] is not None and new["mutable"] is not None:
            changes.append({
                "type": "config_mutability_changed",
                "name": name,
                "config_type": old["type"],
                "old_mutable": old["mutable"],
                "new_mutable": new["mutable"],
                "file": config_path,
            })

    # Added configs
    trivial = {"0", "0L", "0L;", '""', "null", "{}"}
    for name in sorted(set(new_configs.keys()) - set(old_configs.keys())):
        val = new_configs[name]["value"].rstrip(";").rstrip("L").rstrip("f").rstrip("d")
        if val not in trivial and val != "0":
            change = {
                "type": "config_added",
                "name": name,
                "config_type": new_configs[name]["type"],
                "default_value": new_configs[name]["value"],
                "file": config_path,
            }
            if new_configs[name]["mutable"] is not None:
                change["mutable"] = new_configs[name]["mutable"]
            if new_configs[name]["comment"]:
                change["comment"] = new_configs[name]["comment"]
            changes.append(change)

    # Removed configs (high risk — may break existing configurations)
    for name in sorted(set(old_configs.keys()) - set(new_configs.keys())):
        changes.append({
            "type": "config_removed",
            "name": name,
            "config_type": old_configs[name]["type"],
            "old_value": old_configs[name]["value"],
            "deprecated": old_configs[name]["deprecated"],
            "file": config_path,
        })

    return changes


def scan_type_system_changes(repo_path, branch_a, branch_b):
    """Scan for type system and schema-related changes.

    Detects changes to type conversion, varchar handling, column comparison logic.
    """
    patterns = [
        {
            "name": "varchar_type_handling",
            "files": ["ColumnRefOperator.java", "Type.java", "ScalarType.java"],
            "keywords": ["varchar", "string", "CHAR", "STRING", "isStringType"],
        },
        {
            "name": "column_comparison",
            "files": ["ColumnRefOperator.java"],
            "keywords": ["equals", "compareTo", "isCompatible"],
        },
        {
            "name": "schema_change",
            "files": ["SchemaChangeJob", "MaterializedView", "MVPartitionScheme"],
            "keywords": ["schema", "column", "compatible", "incompatible"],
        },
    ]

    findings = []
    for pattern in patterns:
        for file_pattern in pattern["files"]:
            output = run_cmd(
                ["git", "diff", "--name-only", f"{branch_a}..{branch_b}", "--",
                 f"**/{file_pattern}"],
                cwd=repo_path, check=False, timeout=60,
            )
            if not output:
                continue
            for filepath in output.strip().split("\n"):
                if not filepath:
                    continue
                diff = run_cmd(
                    ["git", "diff", f"{branch_a}..{branch_b}", "--", filepath],
                    cwd=repo_path, check=False, timeout=30,
                )
                if not diff:
                    continue
                diff_lower = diff.lower()
                matched_keywords = [kw for kw in pattern["keywords"] if kw.lower() in diff_lower]
                if matched_keywords:
                    changed_lines = []
                    for line in diff.split("\n"):
                        if line.startswith("+") and not line.startswith("+++"):
                            changed_lines.append(line[1:].strip())
                        elif line.startswith("-") and not line.startswith("---"):
                            changed_lines.append(line[1:].strip())
                    findings.append({
                        "type": "type_system_change",
                        "pattern": pattern["name"],
                        "file": filepath,
                        "keywords": matched_keywords,
                        "diff_preview": "\n".join(changed_lines[:20]),
                    })

    return findings


def scan_incompatibilities(repo_path, branch_a, branch_b):
    """Scan the diff between branches for known incompatibility patterns.

    Runs all registered scanners and classifies findings by risk level.
    Returns dict with categorized findings and unified impact assessment.
    """
    print(f"\n[INFO] Scanning for incompatibility patterns...", flush=True)

    # Run the original scanners (config, type_system, mv)
    config_changes = scan_config_changes(repo_path, branch_a, branch_b)
    print(f"[INFO] Config changes: {len(config_changes)}", flush=True)

    type_changes = scan_type_system_changes(repo_path, branch_a, branch_b)
    print(f"[INFO] Type system changes: {len(type_changes)}", flush=True)

    mv_changes = scan_mv_changes(repo_path, branch_a, branch_b)
    print(f"[INFO] MV file changes: {mv_changes['summary']['total_mv_files_changed']}", flush=True)
    print(f"[INFO] MV high-risk changes: {mv_changes['summary']['high_risk_mv_changes']}", flush=True)

    # Classify config changes using unified risk model
    high_risk_configs = []
    medium_risk_configs = []
    low_risk_configs = []

    for change in config_changes:
        if change["type"] == "config_changed":
            name = change["name"]
            risk = _classify_config_risk(name, "config_changed", change.get("old_value"), change.get("new_value"))
            # Immutable config default changes are higher risk (require restart, can't be changed at runtime)
            if change.get("mutable") is False and risk == "low":
                risk = "medium"
            change["risk"] = risk
            change["impact"] = _assess_impact(name)
        elif change["type"] == "config_added":
            name = change["name"]
            risk = _classify_config_risk(name, "config_added")
            change["risk"] = risk
            change["impact"] = _assess_impact(name)
        elif change["type"] == "config_removed":
            # Removed configs are always high risk — may break existing fe.conf
            risk = "high"
            change["risk"] = risk
            change["impact"] = _assess_impact(change["name"])
        elif change["type"] == "config_mutability_changed":
            risk = "medium"
            change["risk"] = risk
            change["impact"] = {"data": False, "behavior": False, "operational": True, "rolling_upgrade": False}
        else:
            risk = change.get("risk", "low")

        if risk == "high":
            high_risk_configs.append(change)
        elif risk == "medium":
            medium_risk_configs.append(change)
        else:
            low_risk_configs.append(change)

    # Run all additional scanners
    scanner_results = {}
    scanner_findings = []
    scanners_skipped = []
    scanners_run = []

    for scanner_name, scanner_fn in _SCANNERS:
        print(f"[INFO] Running scanner: {scanner_name}...", flush=True)
        try:
            findings = scanner_fn(repo_path, branch_a, branch_b)
            if findings:
                scanner_results[scanner_name] = findings
                scanner_findings.extend(findings)
                scanners_run.append(scanner_name)
                print(f"[INFO]   {scanner_name}: {len(findings)} finding(s)", flush=True)
            else:
                scanner_results[scanner_name] = []
                scanners_run.append(scanner_name)
                print(f"[INFO]   {scanner_name}: 0 findings", flush=True)
        except Exception as e:
            scanners_skipped.append({"name": scanner_name, "reason": str(e)})
            scanner_results[scanner_name] = []
            print(f"[WARN]   {scanner_name}: skipped ({e})", flush=True)

    # Classify scanner findings by risk
    for finding in scanner_findings:
        risk = finding.get("risk", "low")
        if risk == "critical":
            high_risk_configs.append(finding)
        elif risk == "high":
            high_risk_configs.append(finding)
        elif risk == "medium":
            medium_risk_configs.append(finding)
        else:
            low_risk_configs.append(finding)

    # Build unified summary
    summary = {
        "total_config_changes": len(config_changes),
        "high_risk_configs": len(high_risk_configs),
        "medium_risk_configs": len(medium_risk_configs),
        "low_risk_configs": len(low_risk_configs),
        "type_system_changes": len(type_changes),
        "mv_files_changed": mv_changes["summary"]["total_mv_files_changed"],
        "mv_high_risk": mv_changes["summary"]["high_risk_mv_changes"],
        "mv_refresh_changes": mv_changes["summary"]["refresh_logic_changes"],
        "mv_rewrite_changes": mv_changes["summary"]["rewrite_logic_changes"],
        "total_scanner_findings": len(scanner_findings),
        "scanners_run": scanners_run,
        "scanners_skipped": [s["name"] for s in scanners_skipped],
        "findings_by_scanner": {name: len(finds) for name, finds in scanner_results.items() if finds},
        "findings_by_risk": {
            "critical": len([f for f in scanner_findings if f.get("risk") == "critical"]),
            "high": len([f for f in scanner_findings if f.get("risk") == "high"]),
            "medium": len([f for f in scanner_findings if f.get("risk") == "medium"]),
            "low": len([f for f in scanner_findings if f.get("risk") == "low"]),
        },
        "findings_by_impact": {
            "data": len([f for f in scanner_findings if f.get("impact", {}).get("data")]),
            "behavior": len([f for f in scanner_findings if f.get("impact", {}).get("behavior")]),
            "operational": len([f for f in scanner_findings if f.get("impact", {}).get("operational")]),
            "rolling_upgrade": len([f for f in scanner_findings if f.get("impact", {}).get("rolling_upgrade")]),
        },
    }

    result = {
        "config_changes": config_changes,
        "type_system_changes": type_changes,
        "mv_changes": mv_changes,
        "scanner_findings": scanner_findings,
        "scanner_results": scanner_results,
        "summary": summary,
        "high_risk": high_risk_configs + [
            tc for tc in type_changes
            if tc["pattern"] in ("varchar_type_handling", "column_comparison")
        ] + mv_changes["high_risk"],
    }

    return result


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def save_json(data, filepath):
    """Save data as JSON."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filepath


# ---------------------------------------------------------------------------
# Cluster profile and config conflict detection
# ---------------------------------------------------------------------------

def parse_conf_content(content):
    """Parse fe.conf or be.conf content into a dict of {key: value}.

    Handles: # comments, empty lines, KEY = VALUE / KEY=VALUE, quoted values,
    values containing = signs (e.g. JAVA_OPTS = "-Xmx8192m").
    """
    if not content:
        return {}
    result = {}
    for line in content.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        idx = line.index("=")
        key = line[:idx].strip()
        value = line[idx + 1:].strip()
        if key:
            result[key] = value
    return result


def _normalize_conf_value(value):
    """Normalize a config value for comparison.

    Strips quotes, semicolons, Java type suffixes (L/f/d), and whitespace.
    """
    if not value:
        return ""
    v = value.strip()
    v = v.rstrip(";").strip()
    v = v.rstrip("L").rstrip("f").rstrip("d").rstrip()
    if len(v) >= 2 and ((v[0] == '"' and v[-1] == '"') or (v[0] == "'" and v[-1] == "'")):
        v = v[1:-1]
    return v.strip()


def load_cluster_profile(path):
    """Load cluster profile from YAML file.

    Returns dict with cluster info and parsed fe_conf/be_conf.
    Returns None if file doesn't exist or pyyaml is not available.
    """
    if not os.path.isfile(path):
        print(f"[INFO] Cluster profile not found at {path}", file=sys.stderr)
        return None

    try:
        import yaml
    except ImportError:
        print(f"[WARN] PyYAML not installed — cluster profile loading skipped. "
              f"Install with: pip install pyyaml", file=sys.stderr)
        return None

    with open(path, "r", encoding="utf-8") as f:
        profile = yaml.safe_load(f)

    if not profile or not isinstance(profile, dict):
        print(f"[WARN] Cluster profile is empty or invalid", file=sys.stderr)
        return None

    fe_conf_raw = profile.get("fe_conf", "") or ""
    be_conf_raw = profile.get("be_conf", "") or ""

    profile["fe_conf_parsed"] = parse_conf_content(fe_conf_raw)
    profile["be_conf_parsed"] = parse_conf_content(be_conf_raw)

    cluster = profile.get("cluster", {})
    name = cluster.get("name", "unknown")
    deployment = cluster.get("deployment", "vm")
    scale = cluster.get("scale", {})
    print(f"[INFO] Cluster profile loaded: {name}, deployment={deployment}, "
          f"fe_conf={len(profile['fe_conf_parsed'])} items, "
          f"be_conf={len(profile['be_conf_parsed'])} items"
          + (f", scale: {scale.get('tables', '?')} tables, {scale.get('mvs', '?')} MVs"
             if scale else ""))

    return profile


def check_config_conflicts(profile, incompatibilities):
    """Check user's fe.conf/be.conf against scanner findings.

    Returns dict with config conflicts, deployment risks, and scale assessment.
    """
    if not profile:
        return None

    fe_conf = profile.get("fe_conf_parsed", {})
    be_conf = profile.get("be_conf_parsed", {})
    cluster = profile.get("cluster", {})
    deployment = cluster.get("deployment", "vm")
    scale = cluster.get("scale", {})

    conflicts = []

    config_changes = incompatibilities.get("config_changes", [])
    scanner_findings = incompatibilities.get("scanner_findings", [])

    all_findings = list(config_changes) + list(scanner_findings)

    for change in all_findings:
        name = change.get("name", "")
        change_type = change.get("type", "")
        file_path = change.get("file", "")
        is_fe = "Config.java" in file_path or "SessionVariable" in file_path or "GlobalVariable" in file_path
        is_be = "config.h" in file_path

        user_conf = fe_conf if is_fe else (be_conf if is_be else None)
        conf_label = "fe_conf" if is_fe else ("be_conf" if is_be else None)

        if not user_conf or not conf_label:
            continue

        # Removed configs that exist in user's conf
        if change_type in ("config_removed", "be_config_removed",
                           "session_var_removed", "system_var_removed"):
            if name in user_conf:
                conflicts.append({
                    "type": "removed_config_in_conf",
                    "config_name": name,
                    "conf_source": conf_label,
                    "current_value": user_conf[name],
                    "risk": "high",
                    "recommendation": (f"Remove '{name}' from your conf — this config no longer exists "
                                       f"and may cause startup warnings/errors"),
                })

        # Default value changed
        elif change_type in ("config_changed", "be_config_changed",
                             "session_var_changed", "system_var_changed"):
            old_default = _normalize_conf_value(change.get("old_value", ""))
            new_default = _normalize_conf_value(change.get("new_value", ""))

            if name in user_conf:
                current_value = _normalize_conf_value(user_conf[name])

                if current_value == old_default:
                    conflicts.append({
                        "type": "config_changed_using_old_default",
                        "config_name": name,
                        "conf_source": conf_label,
                        "old_default": change.get("old_value", ""),
                        "new_default": change.get("new_value", ""),
                        "current_in_conf": user_conf[name],
                        "risk": "medium",
                        "recommendation": (f"'{name}' in your conf matches the old default. "
                                           f"Decide whether to adopt the new default or keep your override."),
                    })
                else:
                    conflicts.append({
                        "type": "config_changed_custom_override",
                        "config_name": name,
                        "conf_source": conf_label,
                        "old_default": change.get("old_value", ""),
                        "new_default": change.get("new_value", ""),
                        "current_in_conf": user_conf[name],
                        "risk": "low",
                        "recommendation": (f"'{name}' has a custom value in your conf — "
                                           f"your override takes precedence."),
                    })
            else:
                change_risk = change.get("risk", "low")
                if change_risk in ("high", "critical"):
                    conflicts.append({
                        "type": "config_changed_no_override",
                        "config_name": name,
                        "conf_source": conf_label,
                        "old_default": change.get("old_value", ""),
                        "new_default": change.get("new_value", ""),
                        "current_in_conf": None,
                        "risk": change_risk,
                        "recommendation": (f"'{name}' default changes and you don't override it. "
                                           f"Add it to your conf if you need the old behavior."),
                    })

    # Deployment-specific risks
    deployment_risks = []
    mv_summary = incompatibilities.get("mv_changes", {}).get("summary", {})
    mv_files_changed = mv_summary.get("total_mv_files_changed", 0)

    if deployment == "k8s":
        if mv_files_changed > 0:
            deployment_risks.append({
                "deployment": "k8s",
                "risk": "FE pod restart triggers MV re-activation; MV code changes detected",
                "detail": ("K8s rolling upgrade restarts FE pods one by one. Each restart triggers "
                           "AlterJobMgr.java MV re-activation which re-parses MV CREATE SQL. "
                           "MV code changes may cause schema compatibility check failures."),
                "severity": "high",
            })

        protocol_findings = [f for f in scanner_findings
                             if f.get("type") in ("protocol_field_removed", "protocol_required_field_added")]
        if protocol_findings:
            deployment_risks.append({
                "deployment": "k8s",
                "risk": "Protocol changes — mixed-version pods may fail",
                "detail": ("Rolling upgrade creates mixed-version clusters. Protocol changes "
                           "can cause FE-BE communication failures between old and new pods."),
                "severity": "critical",
            })

        restart_sensitive = [c for c in conflicts
                             if c["risk"] == "high" and c["type"] == "removed_config_in_conf"]
        if restart_sensitive:
            deployment_risks.append({
                "deployment": "k8s",
                "risk": (f"{len(restart_sensitive)} removed config(s) in your conf "
                         f"will cause issues on pod restart"),
                "detail": "Removed configs in fe.conf/be.conf may cause startup errors when pods restart.",
                "severity": "high",
            })

    elif deployment == "vm":
        protocol_findings = [f for f in scanner_findings
                             if f.get("type") in ("protocol_field_removed", "protocol_required_field_added")]
        if protocol_findings:
            deployment_risks.append({
                "deployment": "vm",
                "risk": "Protocol changes — upgrade all BE first, then FE",
                "detail": ("VM deployments should follow the correct upgrade order: upgrade all BE nodes first, "
                           "then FE nodes. Protocol changes require careful version ordering."),
                "severity": "high",
            })

    # Scale-aware assessment
    scale_assessment = {}
    mv_count = scale.get("mvs", 0)
    table_count = scale.get("tables", 0)
    has_async_mv = scale.get("has_async_mv", False)
    has_sync_mv = scale.get("has_sync_mv", False)

    if mv_count > 0:
        mv_risk_level = "high" if mv_count > 50 else ("medium" if mv_count > 10 else "low")
        scale_assessment["mv_risk"] = {
            "level": mv_risk_level,
            "mv_count": mv_count,
            "has_async_mv": has_async_mv,
            "has_sync_mv": has_sync_mv,
            "reason": (f"Cluster has {mv_count} MVs — "
                       f"{'any MV compatibility issue affects significant workload' if mv_count > 50 else 'moderate MV exposure'}"),
        }

    if table_count > 0:
        scale_assessment["data_risk"] = {
            "table_count": table_count,
            "reason": f"Cluster has {table_count} tables — storage format changes affect data accessibility",
        }

    return {
        "profile_loaded": True,
        "cluster": cluster,
        "config_conflicts": conflicts,
        "deployment_risks": deployment_risks,
        "scale_assessment": scale_assessment,
        "conflict_summary": {
            "total_conflicts": len(conflicts),
            "high_risk": len([c for c in conflicts if c["risk"] == "high"]),
            "medium_risk": len([c for c in conflicts if c["risk"] == "medium"]),
            "low_risk": len([c for c in conflicts if c["risk"] == "low"]),
            "deployment_risks": len(deployment_risks),
        },
    }


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

def run_branch_compare_mode(repo_path, branch_a, branch_b, output_dir, fetch_prs=False,
                            skip_diff_detail=False, diff_stat_only=False,
                            cluster_profile_path=None):
    """Run in branch compare mode: diff two local branches via commit log.

    No GitHub release notes are fetched — comparison is purely based on
    git commit history between the two branches. PR details are only fetched
    when --fetch-prs is specified (commit messages already contain PR titles).
    """
    print(f"[INFO] Running in BRANCH COMPARE mode")
    print(f"[INFO] Repo path: {repo_path}")
    print(f"[INFO] Branch A (base): {branch_a}")
    print(f"[INFO] Branch B (target): {branch_b}")

    # Verify branches exist
    for branch in [branch_a, branch_b]:
        output = run_cmd(
            ["git", "rev-parse", "--verify", branch],
            cwd=repo_path, check=False,
        )
        if not output:
            print(f"[ERROR] Branch/ref '{branch}' not found in repository", file=sys.stderr)
            sys.exit(1)

    # Get diff commits (batch, with full details)
    only_in_b, only_in_a = get_branch_diff_commits(repo_path, branch_a, branch_b)
    print(f"[INFO] Commits in {branch_b} but not in {branch_a}: {len(only_in_b)}")
    print(f"[INFO] Commits in {branch_a} but not in {branch_b}: {len(only_in_a)}")

    # Extract PR numbers
    pr_numbers_b = set()
    for c in only_in_b:
        pr_numbers_b.update(c.get("pr_numbers", []))

    pr_numbers_a = set()
    for c in only_in_a:
        pr_numbers_a.update(c.get("pr_numbers", []))

    print(f"[INFO] PR numbers in {branch_b} (new): {len(pr_numbers_b)}")
    print(f"[INFO] PR numbers in {branch_a} (old): {len(pr_numbers_a)}")

    # Categorize commits
    categories_b = categorize_commits(only_in_b)
    categories_a = categorize_commits(only_in_a)

    # Classify commits into risk tiers and save per-commit diffs
    print(f"\n[INFO] Classifying commits into risk tiers...")
    tier_result_b = classify_and_save_commits(
        repo_path, only_in_b, output_dir,
        branch_b.replace('/', '_'), skip_diff=skip_diff_detail, diff_stat_only=diff_stat_only,
    )
    print(f"[INFO] Tier distribution ({branch_b}): "
          f"HIGH={tier_result_b['tier_counts']['HIGH']}, "
          f"MEDIUM={tier_result_b['tier_counts']['MEDIUM']}, "
          f"LOW={tier_result_b['tier_counts']['LOW']}, "
          f"SKIP={tier_result_b['tier_counts']['SKIP']}")

    tier_result_a = classify_and_save_commits(
        repo_path, only_in_a, output_dir,
        branch_a.replace('/', '_'), skip_diff=skip_diff_detail, diff_stat_only=diff_stat_only,
    )
    print(f"[INFO] Tier distribution ({branch_a}): "
          f"HIGH={tier_result_a['tier_counts']['HIGH']}, "
          f"MEDIUM={tier_result_a['tier_counts']['MEDIUM']}, "
          f"LOW={tier_result_a['tier_counts']['LOW']}, "
          f"SKIP={tier_result_a['tier_counts']['SKIP']}")

    # Optionally fetch PR details from GitHub
    pr_details = {}
    if fetch_prs:
        all_pr_numbers = pr_numbers_b | pr_numbers_a
        if all_pr_numbers:
            print(f"\n[INFO] Fetching PR details from GitHub ({len(all_pr_numbers)} PRs)...")
            for i, pr_num in enumerate(sorted(all_pr_numbers)):
                print(f"[INFO] Fetching PR #{pr_num} ({i+1}/{len(all_pr_numbers)})...",
                      end="", flush=True)
                detail = fetch_pr_details(pr_num)
                if detail:
                    pr_details[pr_num] = detail
                    save_json(detail, os.path.join(output_dir, "prs", f"{pr_num}.json"))
                    print(f" OK - {detail.get('title', '')[:60]}")
                else:
                    print(f" SKIPPED")

    # Save commit data
    save_json(only_in_b, os.path.join(output_dir, "commits", f"only-in-{branch_b.replace('/', '_')}.json"))
    save_json(only_in_a, os.path.join(output_dir, "commits", f"only-in-{branch_a.replace('/', '_')}.json"))

    # Save categorized commits
    for cat, cat_commits in categories_b.items():
        if cat_commits:
            save_json(
                cat_commits,
                os.path.join(output_dir, "categories", f"{cat}-in-{branch_b.replace('/', '_')}.json"),
            )

    # Save PR list
    save_json({
        "in_branch_b": sorted(pr_numbers_b),
        "in_branch_a": sorted(pr_numbers_a),
        "only_in_b": sorted(pr_numbers_b - pr_numbers_a),
        "only_in_a": sorted(pr_numbers_a - pr_numbers_b),
        "common": sorted(pr_numbers_a & pr_numbers_b),
    }, os.path.join(output_dir, "pr-diff.json"))

    # Scan for incompatibility patterns in the diff
    incompatibilities = scan_incompatibilities(repo_path, branch_a, branch_b)
    save_json(incompatibilities, os.path.join(output_dir, "incompatibilities.json"))
    inc_summary = incompatibilities["summary"]
    print(f"[INFO] Incompatibilities found: {inc_summary['high_risk_configs']} high-risk, "
          f"{inc_summary['medium_risk_configs']} medium-risk, "
          f"{inc_summary['low_risk_configs']} low-risk")
    print(f"[INFO] Scanner findings: {inc_summary.get('total_scanner_findings', 0)} across "
          f"{len(inc_summary.get('scanners_run', []))} scanner(s)")

    # Load cluster profile and check config conflicts
    profile = None
    config_conflict_result = None
    if cluster_profile_path:
        print(f"\n[INFO] Loading cluster profile from {cluster_profile_path}...", flush=True)
        profile = load_cluster_profile(cluster_profile_path)
        if profile:
            config_conflict_result = check_config_conflicts(profile, incompatibilities)
            save_json(config_conflict_result,
                      os.path.join(output_dir, "cluster-config-conflicts.json"))
            cs = config_conflict_result["conflict_summary"]
            print(f"[INFO] Config conflicts: {cs['high_risk']} high, "
                  f"{cs['medium_risk']} medium, {cs['low_risk']} low")
            if config_conflict_result["deployment_risks"]:
                print(f"[INFO] Deployment-specific risks: {len(config_conflict_result['deployment_risks'])}")
        else:
            print(f"[INFO] No cluster profile loaded — skipping config conflict detection")

    # Print scanner findings grouped by risk level
    scanner_findings = incompatibilities.get("scanner_findings", [])
    if scanner_findings:
        critical_findings = [f for f in scanner_findings if f.get("risk") == "critical"]
        high_findings = [f for f in scanner_findings if f.get("risk") == "high"]
        medium_findings = [f for f in scanner_findings if f.get("risk") == "medium"]

        if critical_findings:
            print(f"\n[CRITICAL] {len(critical_findings)} critical compatibility finding(s):")
            for item in critical_findings:
                impact = item.get("impact", {})
                impact_tags = []
                if impact.get("data"): impact_tags.append("DATA")
                if impact.get("behavior"): impact_tags.append("BEHAVIOR")
                if impact.get("operational"): impact_tags.append("OPS")
                if impact.get("rolling_upgrade"): impact_tags.append("ROLLING-UPGRADE")
                tag_str = f" [{', '.join(impact_tags)}]" if impact_tags else ""
                print(f"  [{item['type'].upper()}] {item.get('name', item.get('file', ''))}{tag_str}")
                if item.get("old_value") and item.get("new_value"):
                    print(f"    {item['old_value']} -> {item['new_value']}")
                elif item.get("detail"):
                    print(f"    {item['detail']}")

        if high_findings:
            print(f"\n[HIGH] {len(high_findings)} high-risk finding(s):")
            for item in high_findings:
                impact = item.get("impact", {})
                impact_tags = []
                if impact.get("data"): impact_tags.append("DATA")
                if impact.get("behavior"): impact_tags.append("BEHAVIOR")
                if impact.get("operational"): impact_tags.append("OPS")
                if impact.get("rolling_upgrade"): impact_tags.append("ROLLING-UPGRADE")
                tag_str = f" [{', '.join(impact_tags)}]" if impact_tags else ""
                print(f"  [{item['type'].upper()}] {item.get('name', item.get('file', ''))}{tag_str}")
                if item.get("old_value") and item.get("new_value"):
                    print(f"    {item['old_value']} -> {item['new_value']}")
                elif item.get("detail"):
                    print(f"    {item['detail']}")

        if medium_findings:
            print(f"\n[MEDIUM] {len(medium_findings)} medium-risk finding(s)")
            for item in medium_findings[:5]:
                print(f"  [{item['type'].upper()}] {item.get('name', item.get('file', ''))}")
            if len(medium_findings) > 5:
                print(f"  ... and {len(medium_findings) - 5} more")

    # Print impact summary
    impact_summary = inc_summary.get("findings_by_impact", {})
    if any(v > 0 for v in impact_summary.values()):
        print(f"\n[IMPACT SUMMARY]")
        if impact_summary.get("data"): print(f"  Data impact: {impact_summary['data']} finding(s) may affect existing data")
        if impact_summary.get("behavior"): print(f"  Behavior impact: {impact_summary['behavior']} finding(s) may change query results")
        if impact_summary.get("operational"): print(f"  Operational impact: {impact_summary['operational']} finding(s) require config/ops changes")
        if impact_summary.get("rolling_upgrade"): print(f"  Rolling upgrade impact: {impact_summary['rolling_upgrade']} finding(s) may break mixed-version clusters")

    # Print skipped scanners
    skipped = inc_summary.get("scanners_skipped", [])
    if skipped:
        print(f"\n[WARN] Scanners skipped: {', '.join(skipped)}")

    # Legacy high-risk items (config, type system)
    legacy_high_risk = [
        item for item in incompatibilities["high_risk"]
        if item.get("type") in ("config_changed", "config_added", "type_system_change")
    ]
    if legacy_high_risk:
        print(f"\n[WARN] Additional high-risk incompatibilities:")
        for item in legacy_high_risk:
            if item.get("type") in ("config_changed", "config_added"):
                if item["type"] == "config_changed":
                    print(f"  [CONFIG] {item['name']}: {item['old_value']} -> {item['new_value']}")
                else:
                    print(f"  [CONFIG] {item['name']}: (new, default {item['default_value']})")
            elif item.get("type") == "type_system_change":
                print(f"  [TYPE]   {item['pattern']}: {item['file']} ({', '.join(item['keywords'])})")

    # MV compatibility warnings — always shown prominently
    mv = incompatibilities["mv_changes"]
    if mv["summary"]["total_mv_files_changed"] > 0:
        print(f"\n{'='*60}")
        print(f"[MV COMPATIBILITY] Materialized view code changes detected!")
        print(f"  Files changed: {mv['summary']['total_mv_files_changed']}")
        print(f"  High-risk changes: {mv['summary']['high_risk_mv_changes']}")
        print(f"  Medium-risk changes: {mv['summary']['medium_risk_mv_changes']}")
        print(f"  Refresh logic changes: {mv['summary']['refresh_logic_changes']}")
        print(f"  Rewrite logic changes: {mv['summary']['rewrite_logic_changes']}")
        print(f"  Partition handling changes: {mv['summary']['partition_handling_changes']}")
        print(f"  Schema changes on MV: {mv['summary']['schema_change_on_mv']}")
        if mv["high_risk"]:
            print(f"\n  [MV HIGH-RISK] The following files have high-risk MV changes:")
            for item in mv["high_risk"]:
                print(f"    [{item['change_type'].upper()}] {item['file']}")
                if item["matched_keywords"]:
                    print(f"      Keywords: {', '.join(item['matched_keywords'][:5])}")
        print(f"\n  ** ACTION REQUIRED: Review MV compatibility before upgrading! **")
        print(f"  ** Existing MVs may need re-creation or full refresh. **")
        print(f"{'='*60}")
    else:
        print(f"\n[INFO] No materialized view code changes detected.")

    # Cross-reference with local release notes (from target branch)
    all_commit_prs = pr_numbers_b | pr_numbers_a
    print(f"\n[INFO] Reading local release notes from branch '{branch_b}'...", flush=True)
    rn_cross_ref = cross_reference_release_notes(repo_path, all_commit_prs, branch=branch_b)
    rn_summary = None
    if rn_cross_ref:
        save_json(rn_cross_ref, os.path.join(output_dir, "release-notes-cross-ref.json"))
        rn_summary = {
            "files_read": rn_cross_ref["files_read"],
            "total_versions": rn_cross_ref["total_versions"],
            "total_rn_prs": rn_cross_ref["total_rn_prs"],
            "rn_pr_in_commits": len(rn_cross_ref["rn_pr_in_commits"]),
            "rn_pr_not_in_commits": len(rn_cross_ref["rn_pr_not_in_commits"]),
            "commit_prs_not_in_rn": len(rn_cross_ref["commit_prs_not_in_rn"]),
        }
        print(f"[INFO] Release notes: {rn_cross_ref['total_versions']} versions, "
              f"{rn_cross_ref['total_rn_prs']} PRs referenced")
        print(f"[INFO] RN PRs found in commits: {len(rn_cross_ref['rn_pr_in_commits'])}")
        print(f"[INFO] RN PRs NOT in commits: {len(rn_cross_ref['rn_pr_not_in_commits'])}")
        print(f"[INFO] Commit PRs NOT in any RN: {len(rn_cross_ref['commit_prs_not_in_rn'])}")
    else:
        print(f"[INFO] No local release notes found in repo")

    # Summary
    summary = {
        "mode": "branch-compare",
        "repo_path": os.path.abspath(repo_path),
        "branch_a": branch_a,
        "branch_b": branch_b,
        "commits_in_b_not_a": len(only_in_b),
        "commits_in_a_not_b": len(only_in_a),
        "pr_numbers_in_b": sorted(pr_numbers_b),
        "pr_numbers_in_a": sorted(pr_numbers_a),
        "pr_only_in_b": sorted(pr_numbers_b - pr_numbers_a),
        "pr_only_in_a": sorted(pr_numbers_a - pr_numbers_b),
        "pr_common": sorted(pr_numbers_a & pr_numbers_b),
        "categories_in_b": {k: len(v) for k, v in categories_b.items() if v},
        "commit_tier_summary": {
            "branch_b": tier_result_b["tier_counts"],
            "branch_a": tier_result_a["tier_counts"],
            "high_medium_commits_in_b": len(tier_result_b["high_medium_commits"]),
            "high_medium_commits_in_a": len(tier_result_a["high_medium_commits"]),
            "tiered_meta_files": [tier_result_b["meta_file"], tier_result_a["meta_file"]],
        },
        "release_notes": rn_summary,
        "incompatibilities": incompatibilities["summary"],
        "cluster_profile": {
            "loaded": profile is not None,
            "cluster_name": cluster.get("name") if profile else None,
            "deployment": cluster.get("deployment") if profile else None,
            "config_conflicts": config_conflict_result["conflict_summary"] if config_conflict_result else None,
            "deployment_risks_count": len(config_conflict_result["deployment_risks"]) if config_conflict_result else 0,
            "scale_assessment": config_conflict_result["scale_assessment"] if config_conflict_result else None,
        } if profile else None,
        "fetch_prs": fetch_prs,
        "pr_details_fetched": len(pr_details),
        "collected_at": datetime.now().isoformat(),
    }
    save_json(summary, os.path.join(output_dir, "summary.json"))

    print(f"\n{'='*60}")
    print(f"[DONE] Branch comparison complete!")
    print(f"  {branch_b} only: {len(only_in_b)} commits, {len(pr_numbers_b)} PRs")
    print(f"  {branch_a} only: {len(only_in_a)} commits, {len(pr_numbers_a)} PRs")
    print(f"  Common PRs: {len(pr_numbers_a & pr_numbers_b)}")
    print(f"  Output directory: {output_dir}")

    return summary


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="StarRocks Upgrade Comparison Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Typical workflow: switch to target branch, then compare against production
  cd ~/starrocks && git checkout 3.5.17-cj-0604
  python3 starrocks_upgrade.py --against 3.3.16-cj-0708

  # Same but with explicit repo path
  python3 starrocks_upgrade.py --repo ~/starrocks --against 3.3.16-cj-0708

  # Explicit branch-a/branch-b (both required)
  python3 starrocks_upgrade.py --branch-a 3.3.16-cj-0708 --branch-b 3.5.17-cj-0604

  # With full PR details from GitHub (slow for many PRs)
  python3 starrocks_upgrade.py --against 3.3.16-cj-0708 --fetch-prs

  # Quick mode: skip per-commit diff generation for faster run
  python3 starrocks_upgrade.py --against 3.3.16-cj-0708 --skip-diff-detail

  # Preview mode: only save diff stat per commit, not full diffs
  python3 starrocks_upgrade.py --against 3.3.16-cj-0708 --diff-stat-only
        """,
    )
    parser.add_argument(
        "--against",
        help="Compare current branch against this base branch (branch compare mode shortcut)"
    )
    parser.add_argument(
        "--branch-a",
        help="Base branch for comparison (branch compare mode)"
    )
    parser.add_argument(
        "--branch-b",
        help="Target branch for comparison (branch compare mode, default: current branch)"
    )
    parser.add_argument(
        "--fetch-prs", action="store_true",
        help="Fetch PR details from GitHub (slow for many PRs)"
    )
    parser.add_argument(
        "--repo",
        help="Path to StarRocks repo (default: current directory)"
    )
    parser.add_argument(
        "--output", default="./upgrade-report",
        help="Output directory (default: ./upgrade-report)"
    )
    parser.add_argument(
        "--skip-diff-detail", action="store_true",
        help="Skip per-commit diff generation (faster, but no commit-level diff analysis possible)"
    )
    parser.add_argument(
        "--diff-stat-only", action="store_true",
        help="Only save --stat per commit, not full diff (quick preview mode)"
    )
    parser.add_argument(
        "--cluster-profile",
        help="Path to cluster profile YAML (cluster config, fe.conf/be.conf, scale info)"
    )

    args = parser.parse_args()

    has_branch_ab = args.branch_a and args.branch_b
    has_against = args.against is not None

    if has_against and has_branch_ab:
        parser.error("--against cannot be used with --branch-a/--branch-b")

    if not has_against and not has_branch_ab:
        parser.error("One of --against or --branch-a/--branch-b is required")

    if (args.branch_a and not args.branch_b) or (args.branch_b and not args.branch_a):
        parser.error("Both --branch-a and --branch-b are required")

    # Resolve output directory
    output_dir = os.path.abspath(args.output)
    os.makedirs(output_dir, exist_ok=True)
    print(f"[INFO] Output directory: {output_dir}")

    # Resolve repo path
    repo_path = os.path.abspath(args.repo) if args.repo else os.getcwd()
    if not os.path.isdir(os.path.join(repo_path, ".git")):
        print("[ERROR] Not a git repository. Use --repo to specify the StarRocks repo path.",
              file=sys.stderr)
        sys.exit(1)

    if has_against:
        current_branch = get_current_branch(repo_path)
        if not current_branch:
            print("[ERROR] Could not detect current git branch.", file=sys.stderr)
            sys.exit(1)
        branch_a = args.against
        branch_b = current_branch
        print(f"[INFO] Current branch (target): {branch_b}")
        print(f"[INFO] Comparing against (base): {branch_a}")
    else:
        branch_a = args.branch_a
        branch_b = args.branch_b

    run_branch_compare_mode(
        repo_path, branch_a, branch_b, output_dir, args.fetch_prs,
        skip_diff_detail=args.skip_diff_detail, diff_stat_only=args.diff_stat_only,
        cluster_profile_path=args.cluster_profile,
    )


if __name__ == "__main__":
    main()
