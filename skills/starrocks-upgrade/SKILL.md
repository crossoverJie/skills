---
name: starrocks-upgrade
description: >
  StarRocks upgrade comparison tool. Compares two local branches of a StarRocks
  repository via commit log diff. Comprehensive compatibility scanning covers
  config changes, session/system variables, BE config, protocol changes, parser
  changes, auth changes, storage format changes, charset/collation, type system
  changes, and materialized view compatibility. Unified impact model assesses
  data, behavior, operational, and rolling-upgrade impacts.
  Requires local StarRocks source code.
license: Apache-2.0
metadata:
  author: crossoverJie
  version: "3.2"
triggers:
  - starrocks upgrade
  - starrocks 版本对比
  - starrocks release note
  - starrocks 升级
---

# StarRocks Upgrade Skill

Compares two local branches of a StarRocks repository to identify upgrade risks.
Runs 11 scanners for comprehensive compatibility checking with unified impact assessment.

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
5. Run 11 compatibility scanners (see below)
6. Classify all findings by risk level (critical/high/medium/low) with unified impact model
7. Cross-reference with local release notes from the target branch
8. Optionally fetch full PR details from GitHub with `--fetch-prs` (body, labels, files)

### Compatibility Scanners

The tool runs 11 scanners to detect upgrade risks:

| Scanner | What it scans | Impact focus |
|---------|--------------|--------------|
| `config` | FE `Config.java` default value changes | Operational |
| `session_variables` | `SessionVariable.java` session var defaults | Behavior |
| `system_variables` | `GlobalVariable.java` system var defaults | Behavior |
| `be_config` | BE `config.h` default value changes | Operational, Data |
| `protocol` | `.thrift` / `.proto` IDL changes (removed fields, enum changes) | Rolling upgrade |
| `parser` | SQL parser grammar/token changes | Behavior |
| `auth` | Authentication and privilege manager changes | Operational |
| `storage_format` | BE storage format, tablet metadata, encoding | Data, Rolling upgrade |
| `charset_collation` | Charset and collation behavior changes | Data, Behavior |
| `type_system` | Type conversion, varchar handling, schema changes | Data |
| `mv` | Materialized view refresh, rewrite, partition, schema | Data, Behavior |

### Unified Impact Model

Each finding includes an impact assessment across four dimensions:

- **Data**: Affects existing data (storage format, encoding, charset)
- **Behavior**: Changes query results for the same SQL
- **Operational**: Requires config changes, restarts, or object re-creation
- **Rolling Upgrade**: Breaks mixed-version cluster during rolling upgrade

Risk levels: `critical` > `high` > `medium` > `low`. Critical findings are always flagged prominently.

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
├── incompatibilities.json      # All scanner results (config, session vars, BE config, protocol, parser, auth, storage, charset, type system, MV)
├── release-notes-cross-ref.json # Release notes cross-reference
└── summary.json                # Overall summary with scanner counts and impact breakdown
```

## Generating the Upgrade Report

After the script collects data, the agent should:

1. **Read `summary.json`** to understand the overall scope, scanner counts, and impact breakdown
2. **Read `incompatibilities.json`** for all scanner findings, categorized by scanner and risk level
3. **Read `pr-diff.json`** to see which PRs are only in each branch
4. **Read each PR JSON in `prs/`** (if `--fetch-prs` was used) for detailed impact analysis
5. **Read official upgrade documentation** from the StarRocks repo:
   - `docs/zh/deployment/upgrade.md` — 获取正确的升级流程（升级顺序、兼容性配置步骤）
   - `docs/zh/deployment/deployment_prerequisites.md` — 获取目标版本的先决条件（JDK 版本等）
   - 将官方文档中的升级步骤整合到报告的 Upgrade Checklist 中，确保升级顺序和操作步骤与官方文档一致
6. **Deep impact analysis** — see Parallelization Strategy below
7. **Generate `upgrade-report.md`** with the following structure:

### Parallelization Strategy

Deep impact analysis is the most time-consuming step. Each HIGH/CRITICAL finding requires
grep across the codebase, tracing call chains, and understanding data flow — this is
**embarrassingly parallel** since findings are independent of each other.

**Use multiple subagents to analyze findings in parallel.** The workflow:

```
Phase 1: Collect (single agent)
  - Run the Python script
  - Read summary.json, incompatibilities.json
  - Identify all HIGH/CRITICAL findings

Phase 2: Deep Analysis (parallel subagents)
  - Spawn one subagent per HIGH/CRITICAL finding (or batch related findings)
  - Each subagent gets:
    * The finding details (config name, file, old/new value, risk)
    * Access to the StarRocks repo for grep/read
    * Instructions to produce: callers, data flow, dependent modules,
      blast radius, edge cases, rollback feasibility
  - Subagents return structured analysis results

Phase 3: Synthesize (single agent)
  - Merge all subagent results into the final report
  - Read official upgrade docs for the Upgrade Checklist
  - Generate upgrade-report.md
```

**Subagent prompt template** for each finding:

```
Analyze this StarRocks upgrade finding for the report:

Finding: <name> changed from <old> to <new>
File: <file path>
Risk: HIGH
Impact: data=<bool>, behavior=<bool>, operational=<bool>, rolling_upgrade=<bool>

Your task:
1. grep the repo for all DIRECT usages of this config/function/variable
2. **CRITICAL — trace INDIRECT call paths**: For each direct caller, ask "who calls THIS caller?"
   and recurse 2-3 levels up. Also check these system lifecycle entry points:
   - `AlterJobMgr.java` (MV re-activation: re-parses MV CREATE SQL via Analyzer.analyze())
   - `GlobalStateMgr.transferToLeader()` (FE leader transfer: triggers MV re-activation, storage volume creation)
   - `TaskRun.java` (MV refresh execution)
   - `StorageEngine.open()` (BE startup: loads tablets)
   - `GlobalStateMgr.loadImage()` (metadata reload)
   Use grep for `Analyzer.analyze`, `parse.*createMvSql`, `getMvColumnItems` to find indirect paths.
3. Trace the call chain: who calls this code, what does it affect
4. Identify dependent modules
5. Assess blast radius (how many features/paths affected)
6. Consider edge cases during rolling upgrade (mixed FE/BE versions)
7. Evaluate rollback feasibility

Repo path: <path>
Branch: <branch name>

Return your analysis in this format:
- Direct callers: <list>
- Indirect callers (via system lifecycle flows): <list>
- Data flow: <description>
- Dependent modules: <list>
- Blast radius: <description>
- Edge cases: <list>
- Rollback: <description>
- Reproduction: step-by-step instructions to reproduce on a test cluster, including:
  1. Preconditions (which version, what objects to create)
  2. The action that triggers the issue (upgrade, restart, DDL, etc.)
  3. How to observe the issue (error message, MV status, query result)
  4. How to verify the fix (config change, restart, expected result)
```

**Batching strategy**: If there are more than 10 HIGH/CRITICAL findings, batch related findings
(e.g., all BE config removals in one subagent, all MV changes in another) to keep subagent
count manageable. Aim for 3-8 parallel subagents.

**Medium/Low findings** do NOT need subagents — the main agent can summarize them in a table
directly from the scanner output.

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
- Scanners run: N/11
- Total findings: N (critical: N, high: N, medium: N, low: N)
- Impact breakdown: data=N, behavior=N, operational=N, rolling-upgrade=N

## Compatibility Impact Summary
> Review this section FIRST. It consolidates findings from all 11 scanners
> grouped by impact dimension.

### Data Impact (existing data may be affected)
> Storage format changes, encoding changes, charset/collation changes.

**HIGH/CRITICAL findings** — each MUST use this format:

#### [HIGH] <config/variable/feature name>: <old> -> <new>
- **Scanner**: <scanner name>
- **File**: <file path>
- **What changed**: <one-line summary of the actual code change>
- **Callers**: <list all call sites found by grep — file:method, count>
- **Data flow**: <what reads/writes the changed data; end-to-end path when the value flips>
- **Dependent modules**: <subsystems that depend on this behavior>
- **Blast radius**: <how many features/query paths/ops procedures are affected>
- **Edge cases**: <mixed-version state, rolling upgrade scenarios>
- **Rollback**: <can it be rolled back? one-way migration?>
- **Reproduction**: step-by-step instructions to reproduce the issue on a test cluster, so the user can verify before production upgrade. Include:
  1. Preconditions (which version, what objects to create)
  2. The action that triggers the issue (upgrade, restart, DDL, etc.)
  3. How to observe the issue (error message, MV status, query result)
  4. How to verify the fix (config change, restart, expected result)

**Medium/Low findings** — one-line table:

| Finding | File | Old | New | Risk | Reasoning |
|---------|------|-----|-----|------|-----------|

### Behavior Impact (same SQL may return different results)
> Session variable default changes, parser changes, MV rewrite changes.

**HIGH/CRITICAL findings** — same deep format as Data Impact:

#### [HIGH] <variable/parser rule name>: <old> -> <new>
- **Scanner**: <scanner name>
- **File**: <file path>
- **What changed**: <one-line summary>
- **Callers**: <all code paths that read this variable / use this grammar rule>
- **Data flow**: <how the variable/rule propagates through query execution>
- **Dependent modules**: <optimizer, executor, planner, etc.>
- **Blast radius**: <which query patterns are affected>
- **Edge cases**: <session-level vs global; what if user explicitly SET this variable?>
- **Rollback**: <SET GLOBAL to old value? restart required?>
- **Reproduction**: step-by-step instructions to reproduce on a test cluster (see Data Impact template above for format)

**Medium/Low findings** — one-line table:

| Finding | File | Old | New | Risk | Reasoning |
|---------|------|-----|-----|------|-----------|

### Operational Impact (requires config/ops changes)
> FE/BE config default changes, auth/privilege changes.

**HIGH/CRITICAL findings** — same deep format:

#### [HIGH] <config name>: <old> -> <new>
- **Scanner**: <scanner name>
- **File**: <file path>
- **What changed**: <one-line summary>
- **Callers**: <all code paths gated by this config>
- **Data flow**: <what feature does this config control? end-to-end>
- **Dependent modules**: <which subsystems read this config>
- **Blast radius**: <how many operational procedures change>
- **Edge cases**: <config is mutable? can it be changed at runtime? what about fe.conf vs SQL?>
- **Rollback**: <set in fe.conf and restart? ADMIN SET FRONTEND CONFIG?>
- **Reproduction**: step-by-step instructions to reproduce on a test cluster (see Data Impact template above for format)

**Medium/Low findings** — one-line table:

| Finding | File | Old | New | Risk | Reasoning |
|---------|------|-----|-----|------|-----------|

### Rolling Upgrade Impact (mixed-version cluster may break)
> Protocol/IDL changes, storage format version changes.

**HIGH/CRITICAL findings** — same deep format:

#### [HIGH] <protocol/field name>: <change description>
- **Scanner**: <scanner name>
- **File**: <file path>
- **What changed**: <field removed? enum value added? required field added?>
- **Callers**: <FE code that serializes, BE code that deserializes>
- **Data flow**: <request path: FE -> Thrift -> BE; response path: BE -> Thrift -> FE>
- **Dependent modules**: <RPC handlers, result receivers>
- **Blast radius**: <which RPC calls are affected>
- **Edge cases**: <old FE + new BE: does old FE ignore new field? new FE + old BE: does old BE reject new field?>
- **Rollback**: <is the protocol change backward-compatible? can both versions coexist?>
- **Reproduction**: step-by-step instructions to reproduce on a test cluster (see Data Impact template above for format)

**Medium/Low findings** — one-line table:

| Finding | File | Old | New | Risk | Reasoning |
|---------|------|-----|-----|------|-----------|

## Materialized View (MV) Compatibility — CRITICAL
> We use MVs extensively. This section must be reviewed first.

- **MV-related commits**: List commits touching MV code with PR numbers
- **MV refresh logic changes**: What changed and impact on existing MVs
- **MV rewrite behavior changes**: Whether query rewrite rules changed
- **Base table schema changes**: Alter table / schema change impacts on MVs
- **Action required**: Re-create MVs? Full refresh needed? No action required?

## Configuration Changes (FE & BE)
List changes to configuration defaults, new config options, removed options.
Include both FE Config.java and BE config.h changes.

## Session & System Variable Changes
List changes to session variable and system variable defaults.
Highlight variables that affect query behavior (sql_mode, query_timeout, etc.).

## Protocol & Parser Changes
List Thrift/Protobuf IDL changes and SQL parser grammar changes.
Flag any breaking changes to FE-BE communication or SQL syntax.

## Storage Format & Charset Changes
List changes to storage format, encoding, compression, charset, collation.
Flag changes that affect existing data readability.

## Breaking Changes / Incompatible Changes
List PRs that introduce breaking changes or behavior incompatibilities.
For each: PR number, title, impact description, migration steps.

## New Features
List new features added in the target version.

## Bug Fixes
List bug fixes relevant to the user's deployment.

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
3. **Data impact**: Prioritize findings where `impact.data == true` — these affect existing data
   (storage format, encoding, charset changes). Data-impacting changes are potential blockers.
4. **Behavior impact**: Prioritize findings where `impact.behavior == true` — these change query
   results for the same SQL (session variable defaults, parser changes, MV rewrite changes).
5. **Rolling upgrade impact**: Prioritize findings where `impact.rolling_upgrade == true` — these
   break mixed-version clusters (protocol changes, storage format version bumps).
6. **Risk assessment**: Large PRs touching core components (FE optimizer, BE storage engine,
   query execution) carry higher risk than small bug fixes

### Deep Impact Analysis (REQUIRED for high-risk findings)

**For every high-risk finding, do NOT stop at the changed lines.** Surface-level pattern matching
(keyword scan, default-value diff) catches obvious breaks but misses cascading effects. Each
high-risk change MUST be analyzed in its full context before the report is written.

1. **Trace callers**: `grep -r` for the changed function / config / variable across the entire
   codebase. Identify every call site, every reader, every writer. A function rename that looks
   harmless breaks every caller.
   **CRITICAL — also trace INDIRECT call paths**: A config may not be directly referenced by
   system lifecycle code, but is reached indirectly through intermediate calls. For example,
   `AlterJobMgr.java` doesn't reference `transform_type_prefer_string_for_varchar`, but it
   calls `Analyzer.analyze()` -> `MaterializedViewAnalyzer` -> `transformTableColumnType()`
   which reads the config. To catch these:
   - For each direct caller, ask "who calls THIS caller?" and recurse 2-3 levels up.
   - Search for the **entry point flows** listed in the "System Lifecycle Flows" section below
     that may indirectly trigger the changed code.
   - Use `grep -rn "Analyzer.analyze\|parse.*createMvSql\|getMvColumnItems"` to find indirect
     paths through the analyzer framework.
2. **Map data flow**: understand what reads and writes the changed data structure. If a config
   controls a code path, trace that path end-to-end — what feature does it gate? What happens
   when the gate flips?
3. **Identify dependent modules**: which subsystems depend on the changed behavior? A change
   to `MaterializedView.java` may affect the optimizer, the scheduler, the privilege system,
   and the metadata subsystem — not just the MV module itself.
4. **Assess blast radius**: how many features / query paths / operational procedures are
   affected? A config change that touches 1 call site is low risk; one that gates behavior
   across 50 code paths is high risk even if the diff is small.
5. **Consider edge cases and mixed-version state**: what happens when the old code path is
   still used during a rolling upgrade? What if a query hits a BE node that hasn't been
   upgraded yet? What if metadata is written by the new FE but read by the old BE?
6. **Evaluate rollback feasibility**: can this change be rolled back cleanly? Are there
   one-way metadata migrations that prevent downgrade?

**How to apply this in practice:**

For each high-risk finding (config change, scanner hit, MV change, type system change):

```
## [HIGH] enable_alter_struct_column: false -> true

### What changed
Config default flipped; ALTER TABLE ... MODIFY COLUMN now allows struct type changes.

### Deep impact analysis
- **Callers**: grep finds 12 call sites in AlterJobExecutor, SchemaChangeHandler, ColumnTypeAnalyzer
- **Data flow**: gates the validation in `checkTypeCompatibility()` — with old=false, struct
  columns reject ALTER; with new=true, they pass through to the schema change pipeline
- **Dependent modules**: SchemaChangeJob, MaterializedViewHandler (rollup rebuilds),
  InformationSchemaProvider (column metadata)
- **Blast radius**: affects any user with struct columns who runs ALTER TABLE; MVs built on
  struct-column tables may trigger unexpected rebuilds
- **Edge cases**: during rolling upgrade, old FE rejects ALTER that new FE would allow —
  job submitted to new FE but executed on old FE may fail mid-flight
- **Rollback**: set `enable_alter_struct_column=false` in fe.conf before restart; no
  one-way migration
```

**The report MUST include this depth for every HIGH and CRITICAL finding.** Medium and low
findings get a one-line impact summary, but high/critical findings that only show the diff
without context analysis are incomplete.

### System Lifecycle Flows (MUST CHECK for high-risk config/type changes)

**Config and type changes can be triggered INDIRECTLY by system lifecycle events, not just
by direct code references.** When analyzing high-risk config changes, column type changes,
or schema-affecting changes, ALWAYS check these lifecycle flows:

| Lifecycle Flow | Entry Point | What it does | Why it matters |
|---|---|---|---|
| **MV re-activation** | `AlterJobMgr.java:265-267` | Re-parses MV CREATE SQL, calls `Analyzer.analyze()`, compares new schema with existing | Any config that affects `AnalyzerUtils.transformTableColumnType()` or column type inference will cause existing MVs to fail schema compatibility check on FE restart |
| **MV refresh** | `TaskRun.java` / `PartitionBasedMvRefreshProcessor.java` | Executes MV refresh SQL | Config changes affecting query execution or insert behavior may break refresh |
| **FE leader transfer** | `GlobalStateMgr.transferToLeader()` | Reloads metadata, re-activates MVs, creates builtin storage volumes | Triggers MV re-activation, storage volume creation, and other initialization flows |
| **BE startup** | `StorageEngine.open()` | Loads tablets, applies txn logs | Config changes affecting storage format or tablet loading may cause startup failures |
| **Metadata reload** | `GlobalStateMgr.loadImage()` | Deserializes metadata from image | Schema/field type changes may break deserialization of existing metadata |

**How to apply**: For each high-risk config change that affects column types, schema, or type
resolution (e.g., `transform_type_prefer_string_for_varchar`, `enable_alter_struct_column`):
1. Check if `AlterJobMgr.java` re-parses any SQL that would be affected
2. Check if `GlobalStateMgr.transferToLeader()` triggers any flow that reads this config
3. Check if metadata deserialization depends on the changed behavior

### K8s Rolling Upgrade Considerations

**StarRocks on K8s performs rolling upgrades by restarting pods one by one.** Each pod restart
triggers the full lifecycle flow for that component. This means ANY issue triggered by a
restart — not just version incompatibility — becomes a blocker during rolling upgrade.

**Common K8s restart-triggered issues to check:**

| Scenario | What happens | How to detect |
|---|---|---|
| **FE pod restart -> MV re-activation failure** | FE restarts, re-parses all MV creation SQL, schema check fails for VARCHAR/CHAR MVs | Config changes affecting `transformTableColumnType()` or column type inference |
| **FE pod restart -> leader transfer** | Old leader pod dies, new leader calls `transferToLeader()`, triggers MV re-activation + storage volume creation | Config changes affecting `createBuiltinStorageVolume()` or MV metadata |
| **BE pod restart -> tablet load failure** | BE restarts, `StorageEngine.open()` loads tablets, config changes cause load failures | Config changes affecting tablet metadata format or storage engine initialization |
| **FE pod restart -> metadata load failure** | FE restarts, `loadImage()` deserializes metadata, schema changes break deserialization | `@SerializedName` field type changes, new required fields |
| **Mixed-version pods during rolling upgrade** | Old FE pod + new FE pod coexist, behavior differs | Config default changes that affect DDL, DML, or auth behavior |
| **Pod restart -> config file mismatch** | New binary reads old `fe.conf`/`be.conf`, removed configs cause warnings or errors | Removed config entries in conf files |

**For each high-risk finding, ask: "If this component pod restarts, will it break?"**

This is especially critical for:
- Config changes that affect column type resolution (MV re-activation on FE restart)
- Config changes that affect storage volume creation (leader transfer on FE restart)
- Config changes that affect tablet loading (BE restart)
- Removed configs that may still be in the user's `fe.conf`/`be.conf`

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
5. **Check MV re-activation compatibility** — FE restart triggers MV re-activation in `AlterJobMgr.java:265-267`.
   This flow re-parses the MV's CREATE SQL via `Analyzer.analyze()`. ANY config that affects
   `AnalyzerUtils.transformTableColumnType()` or column type inference will cause existing MVs
   to fail the schema compatibility check (`Column.isSchemaCompatible` at line 284) if the
   re-parsed column types differ from the stored column types. Common triggers:
   - Config changes to `transform_type_prefer_string_for_varchar`
   - Changes to `MaterializedViewAnalyzer` column type inference logic
   - Changes to `CreateMaterializedViewStmt` column derivation logic
   - Changes to `ScalarType.getOlapMaxVarcharLength()`
   To check: grep for `transformTableColumnType` callers, then trace each caller back to
   `AlterJobMgr.java` or `GlobalStateMgr.transferToLeader()`.
6. **Document rollback steps** — if MVs break, what's the rollback procedure?

**In the upgrade report, MV compatibility findings MUST appear in a dedicated section at the top, NOT buried in general findings.**

### Additional Scanner Areas

Beyond config and MV, the tool scans these areas for compatibility risks:

**Session & System Variables** (`SessionVariable.java`, `GlobalVariable.java`):
- Default value changes to session variables (e.g., `sql_mode`, `query_timeout`, `pipeline_dop`)
- These silently alter query behavior without user awareness
- High-risk: variables that control MV rewrite, parallelism, timeout, isolation level

**BE Configuration** (`be/src/common/config.h`):
- Default value changes to BE config macros (DEFINE_Int32, DEFINE_Bool, etc.)
- Affects compaction, memory limits, tablet version limits, storage paths
- High-risk: `max_tablet_version_count`, `mem_limit`, `chunk_reserved_bytes_limit`

**Protocol Changes** (`.thrift`, `.proto` files):
- Removed fields, new required fields, enum value changes
- Breaks FE-BE communication during rolling upgrades
- Any removed field or enum value is automatically critical risk

**SQL Parser Changes** (`StarRocksParser.g4`, `StarRocksLex.jflex`, `AstBuilder.java`):
- Grammar rule changes, token additions/removals, reserved word changes
- May break existing SQL queries or change parsing behavior

**Storage Format** (`segment_format*.h`, `tablet_meta*.h`, `rowset/segment*.cpp`):
- Version bumps, format changes, encoding/compression default changes
- Critical risk: may make existing tablets unreadable after upgrade

**Charset & Collation** (`Collation*.java`, `Charset*.java`):
- Changes to string comparison behavior, default charset, collation rules
- Affects data interpretation and query results

**Auth & Privilege** (`AuthenticationManager.java`, `PrivilegeManager.java`):
- Changes to authentication plugins, privilege model, role management
- May require re-configuring user permissions after upgrade

### Handling Large PR Counts

If there are too many PRs to analyze individually:
- Prioritize PRs with labels like "behavior-change", "incompatible", "major"
- Focus on PRs touching the same components as the user's customizations
- Group small bug fixes by subsystem (optimizer, storage, connector, etc.)

## Error Handling

- If `gh` is not authenticated: remind user to run `gh auth login` (only needed for `--fetch-prs`)
- If the repo is not detected: guide user to use `--repo`
- If a PR fetch fails: note it in the report and continue with remaining PRs
