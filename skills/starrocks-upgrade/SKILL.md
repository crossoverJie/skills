---
name: starrocks-upgrade
description: >
  StarRocks upgrade comparison tool. Compares two local branches of a StarRocks
  repository via commit log diff. Scans for incompatibilities including config
  changes, type system changes, and materialized view compatibility issues.
  Requires local StarRocks source code.
license: Apache-2.0
metadata:
  author: crossoverJie
  version: "2.0"
triggers:
  - starrocks upgrade
  - starrocks 版本对比
  - starrocks release note
  - starrocks 升级
---

# StarRocks Upgrade Skill

Compares two local branches of a StarRocks repository to identify upgrade risks.
Scans for config changes, type system changes, and materialized view compatibility issues.

**Requires local StarRocks source code.** This tool operates entirely on local git history — no network calls needed (except optional `--fetch-prs`).

## Prerequisites

- **Python 3** (standard library only)
- **git** (for branch diff)
- **gh** (GitHub CLI, authenticated — only needed for `--fetch-prs`)
- **StarRocks 官方文档**（本地仓库内）：`docs/zh/` 目录，生成升级报告时必须参考以下文档：
  - `docs/zh/deployment/upgrade.md` — 升级流程（升级顺序、兼容性配置、注意事项）
  - `docs/zh/deployment/deployment_prerequisites.md` — 部署先决条件（JDK 版本等）
  - `docs/zh/release_notes/` — 各版本 Release Notes

## Usage

### Recommended workflow

Switch to the target branch, then compare against production:

```bash
cd ~/starrocks && git checkout 3.5.17-cj-0604
python3 skills/starrocks-upgrade/starrocks_upgrade.py --against 3.3.16-cj-0708
```

### Explicit branch specification (both required)

```bash
python3 skills/starrocks-upgrade/starrocks_upgrade.py --branch-a <base> --branch-b <target>
```

### With full PR details from GitHub (slow when there are many PRs)

```bash
python3 skills/starrocks-upgrade/starrocks_upgrade.py --against <base> --fetch-prs
```

### What the tool does

1. `git log branchA..branchB` to find commits only in B (batch, single call)
2. `git log branchB..branchA` to find commits only in A (batch, single call)
3. Extract PR numbers from commit messages (commit subject already contains PR title)
4. Categorize commits by type (feat/fix/refactor/perf/etc.)
5. Scan for incompatibility patterns (config, type system, MV)
6. Cross-reference with local release notes from the target branch
7. Optionally fetch full PR details from GitHub with `--fetch-prs` (body, labels, files)

### Options

- `--output <dir>`: Output directory (default: `./upgrade-report`)
- `--repo <path>`: Path to StarRocks repo (default: current directory)

## Output Structure

```
upgrade-report/
├── prs/                        # Individual PR details (only with --fetch-prs)
│   ├── 73237.json
│   └── ...
├── commits/                    # Commit details
│   ├── only-in-3.5.17-cj-0604.json
│   └── only-in-3.3.16-cj-0708.json
├── categories/                 # Categorized commits
│   ├── feat-in-3.5.17-cj-0604.json
│   ├── fix-in-3.5.17-cj-0604.json
│   └── ...
├── pr-diff.json                # PR number diff
├── incompatibilities.json      # Config/type/MV incompatibility scan results
├── release-notes-cross-ref.json # Release notes cross-reference
└── summary.json                # Overall summary
```

## Generating the Upgrade Report

After the script collects data, the agent should:

1. **Read `summary.json`** to understand the overall scope
2. **Read `incompatibilities.json`** for config changes, type system changes, and MV compatibility findings
3. **Read `pr-diff.json`** to see which PRs are only in each branch
4. **Read each PR JSON in `prs/`** (if `--fetch-prs` was used) for detailed impact analysis
5. **Read official upgrade documentation** from the StarRocks repo:
   - `docs/zh/deployment/upgrade.md` — 获取正确的升级流程（升级顺序、兼容性配置步骤）
   - `docs/zh/deployment/deployment_prerequisites.md` — 获取目标版本的先决条件（JDK 版本等）
   - 将官方文档中的升级步骤整合到报告的 Upgrade Checklist 中，确保升级顺序和操作步骤与官方文档一致
6. **Generate `upgrade-report.md`** with the following structure:

### Report Structure

```markdown
# StarRocks Upgrade Report: <branch-a> -> <branch-b>

## Summary
- Generated: <date>
- Commits only in <branch-b>: N
- Commits only in <branch-a>: N
- PRs only in <branch-b>: N
- PRs only in <branch-a>: N
- Common PRs: N

## Materialized View (MV) Compatibility — CRITICAL
> We use MVs extensively. This section must be reviewed first.

- **MV-related commits**: List commits touching MV code with PR numbers
- **MV refresh logic changes**: What changed and impact on existing MVs
- **MV rewrite behavior changes**: Whether query rewrite rules changed
- **Base table schema changes**: Alter table / schema change impacts on MVs
- **Action required**: Re-create MVs? Full refresh needed? No action required?

## Breaking Changes / Incompatible Changes
List PRs that introduce breaking changes or behavior incompatibilities.
For each: PR number, title, impact description, migration steps.

## New Features
List new features added in the target version.

## Bug Fixes
List bug fixes relevant to the user's deployment.

## Configuration Changes
List changes to configuration defaults, new config options, removed options.

## Upgrade Checklist
- [ ] Step 1: ...
- [ ] Step 2: ...

## Missing from <branch-b> (only in <branch-a>)
List commits that exist in A but not B — these may need to be cherry-picked
or are intentionally excluded customizations.

## Detailed Commit Analysis
For key commits:
### <commit subject>
- **What it does**: ...
- **Impact**: ...
- **Action needed**: ...
```

### Analysis Guidelines

When analyzing PRs, focus on:

1. **Breaking changes**: Look for keywords like "breaking", "incompatible", "remove", "deprecate",
   "rename", "default change", "behavior change" in PR titles and bodies
2. **Materialized View (MV) compatibility** (CRITICAL): We rely heavily on materialized views.
   Any changes to MV refresh, rewriting, partitioning, or schema must be flagged. Check PR titles
   and bodies for keywords like "materialized view", "MV", "rollup", "refresh", "rewrite",
   "partition" combined with "change", "fix", "refactor". Changes to MV-related files are
   high-risk — see MV Compatibility section below.
3. **Compatibility**: Check if new features require specific dependencies, hardware, or config
4. **Risk assessment**: Large PRs touching core components (FE optimizer, BE storage engine,
   query execution) carry higher risk than small bug fixes

### Materialized View Compatibility Check (CRITICAL)

**We use materialized views extensively. Any upgrade that breaks or alters MV behavior is a blocker.**

The tool automatically scans for MV-related code changes between branches. Key areas:

- **MV metadata and schema**: `MaterializedView.java`, `MaterializedViewMeta.java`, partition scheme classes
- **MV refresh**: `MVRefresh*.java`, `MaterializedViewRefresh*.java`, `TaskRun.java` (refresh task logic)
- **MV query rewriting**: `MaterializedViewRewriter.java`, `Optimizer` classes that handle MV rewrite
- **MV partition handling**: partition pruning, partition range computation for incremental refresh
- **Schema change on MV base tables**: `SchemaChangeJob`, alter table logic that may invalidate MVs
- **Rollup/index changes**: `RollupJob`, `AlterJob` classes

When the scan finds MV-related changes:
1. **Check if existing MVs need re-creation** — does the change alter storage format or metadata?
2. **Check if MV rewrite behavior changes** — queries that were rewritten may stop being rewritten
3. **Check if refresh logic changes** — incremental refresh may break, full refresh may be needed
4. **Check partition handling** — partition evolution on base tables may break MV partition alignment
5. **Document rollback steps** — if MVs break, what's the rollback procedure?

**In the upgrade report, MV compatibility findings MUST appear in a dedicated section at the top, NOT buried in general findings.**

### Handling Large PR Counts

If there are too many PRs to analyze individually:
- Prioritize PRs with labels like "behavior-change", "incompatible", "major"
- Focus on PRs touching the same components as the user's customizations
- Group small bug fixes by subsystem (optimizer, storage, connector, etc.)

## Error Handling

- If `gh` is not authenticated: remind user to run `gh auth login` (only needed for `--fetch-prs`)
- If the repo is not detected: guide user to use `--repo`
- If a PR fetch fails: note it in the report and continue with remaining PRs
