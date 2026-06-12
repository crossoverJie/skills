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
# Incompatibility scanning
# ---------------------------------------------------------------------------

def scan_config_changes(repo_path, branch_a, branch_b):
    """Scan Config.java for default value changes between branches.

    Returns list of dicts with changed config details.
    """
    config_path = "fe/fe-core/src/main/java/com/starrocks/common/Config.java"

    def extract_configs(ref):
        content = run_cmd(["git", "show", f"{ref}:{config_path}"], cwd=repo_path, check=False)
        if not content:
            return {}
        configs = {}
        for m in re.finditer(r'public\s+static\s+(\S+)\s+(\w+)\s*=\s*(.+?);', content):
            type_, name, value = m.group(1), m.group(2), m.group(3).strip()
            configs[name] = {"type": type_, "value": value}
        return configs

    old_configs = extract_configs(branch_a)
    new_configs = extract_configs(branch_b)
    if not old_configs or not new_configs:
        return []

    changes = []
    for name in sorted(set(old_configs.keys()) & set(new_configs.keys())):
        if old_configs[name]["value"] != new_configs[name]["value"]:
            changes.append({
                "type": "config_changed",
                "name": name,
                "config_type": old_configs[name]["type"],
                "old_value": old_configs[name]["value"],
                "new_value": new_configs[name]["value"],
                "file": config_path,
            })

    trivial = {"0", "0L", "0L;", '""', "null", "{}"}
    for name in sorted(set(new_configs.keys()) - set(old_configs.keys())):
        val = new_configs[name]["value"].rstrip(";").rstrip("L").rstrip("f").rstrip("d")
        if val not in trivial and val != "0":
            changes.append({
                "type": "config_added",
                "name": name,
                "config_type": new_configs[name]["type"],
                "default_value": new_configs[name]["value"],
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

    Returns dict with categorized findings.
    """
    print(f"\n[INFO] Scanning for incompatibility patterns...", flush=True)

    config_changes = scan_config_changes(repo_path, branch_a, branch_b)
    print(f"[INFO] Config changes: {len(config_changes)}", flush=True)

    type_changes = scan_type_system_changes(repo_path, branch_a, branch_b)
    print(f"[INFO] Type system changes: {len(type_changes)}", flush=True)

    mv_changes = scan_mv_changes(repo_path, branch_a, branch_b)
    print(f"[INFO] MV file changes: {mv_changes['summary']['total_mv_files_changed']}", flush=True)
    print(f"[INFO] MV high-risk changes: {mv_changes['summary']['high_risk_mv_changes']}", flush=True)
    print(f"[INFO] MV refresh logic changes: {mv_changes['summary']['refresh_logic_changes']}", flush=True)
    print(f"[INFO] MV rewrite logic changes: {mv_changes['summary']['rewrite_logic_changes']}", flush=True)

    high_risk_configs = []
    medium_risk_configs = []
    low_risk_configs = []

    high_risk_names = {
        "mysql_server_version", "transform_type_prefer_string_for_varchar",
        "max_varchar_length", "enable_load_volume_from_conf",
        "enable_alter_struct_column", "enable_rollback_default_warehouse",
    }

    for change in config_changes:
        if change["type"] == "config_changed":
            name = change["name"]
            if name in high_risk_names:
                change["risk"] = "high"
                high_risk_configs.append(change)
            elif change["new_value"] in ("true", "false") and change["old_value"] in ("true", "false"):
                change["risk"] = "medium"
                medium_risk_configs.append(change)
            else:
                change["risk"] = "low"
                low_risk_configs.append(change)
        elif change["type"] == "config_added":
            name = change["name"]
            if name in high_risk_names:
                change["risk"] = "high"
                high_risk_configs.append(change)
            else:
                change["risk"] = "low"
                low_risk_configs.append(change)

    result = {
        "config_changes": config_changes,
        "type_system_changes": type_changes,
        "mv_changes": mv_changes,
        "summary": {
            "total_config_changes": len(config_changes),
            "high_risk_configs": len(high_risk_configs),
            "medium_risk_configs": len(medium_risk_configs),
            "low_risk_configs": len(low_risk_configs),
            "type_system_changes": len(type_changes),
            "mv_files_changed": mv_changes["summary"]["total_mv_files_changed"],
            "mv_high_risk": mv_changes["summary"]["high_risk_mv_changes"],
            "mv_refresh_changes": mv_changes["summary"]["refresh_logic_changes"],
            "mv_rewrite_changes": mv_changes["summary"]["rewrite_logic_changes"],
        },
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
# Main orchestration
# ---------------------------------------------------------------------------

def run_branch_compare_mode(repo_path, branch_a, branch_b, output_dir, fetch_prs=False):
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
    print(f"[INFO] Incompatibilities found: {inc_summary['high_risk_configs']} high-risk config changes, "
          f"{inc_summary['type_system_changes']} type system changes")

    if incompatibilities["high_risk"]:
        print(f"\n[WARN] High-risk incompatibilities detected:")
        for item in incompatibilities["high_risk"]:
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
        "release_notes": rn_summary,
        "incompatibilities": incompatibilities["summary"],
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

    run_branch_compare_mode(repo_path, branch_a, branch_b, output_dir, args.fetch_prs)


if __name__ == "__main__":
    main()
