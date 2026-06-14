---
name: starrocks-upgrade
description: >
  StarRocks upgrade comparison tool. Compares two local branches of a StarRocks
  repository via commit log diff. Per-commit diff analysis with risk tier classification
  (HIGH/MEDIUM/LOW/SKIP) for comprehensive impact assessment beyond scanner coverage.
  11 compatibility scanners cover config changes, session/system variables, BE config,
  protocol changes, parser changes, auth changes, storage format changes, charset/collation,
  type system changes, and materialized view compatibility. Unified impact model assesses
  data, behavior, operational, and rolling-upgrade impacts. Four-phase parallel analysis
  with subagent-driven deep investigation for all HIGH/CRITICAL findings.
  Requires local StarRocks source code.
license: Apache-2.0
metadata:
  author: crossoverJie
  version: "4.0"
triggers:
  - starrocks upgrade
  - starrocks 版本对比
  - starrocks release note
  - starrocks 升级
---

# StarRocks Upgrade Skill

Compares two local branches of a StarRocks repository to identify upgrade risks.
Four-phase analysis: data collection, per-commit diff analysis, deep impact investigation,
and report synthesis. Runs 11 scanners + per-commit diff tier classification for
comprehensive compatibility checking with unified impact assessment.

**Requires local StarRocks source code.** This tool operates entirely on local git history — no network calls needed (except optional `--fetch-prs`).

## Prerequisites

- **Python 3** (standard library only)
- **git** (for branch diff)
- **gh** (GitHub CLI, authenticated — only needed for `--fetch-prs`)
- **PyYAML** (optional — only needed for `--cluster-profile`)
- **StarRocks 官方文档**（本地仓库内）：`docs/zh/` 目录，生成升级报告时必须参考以下文档：
  - `docs/zh/deployment/upgrade.md` — 升级流程（升级顺序、兼容性配置、注意事项）
  - `docs/zh/deployment/deployment_prerequisites.md` — 部署先决条件（JDK 版本等）
  - `docs/zh/release_notes/` — 各版本 Release Notes

## Cluster Profile (Optional but Highly Recommended)

The cluster profile provides your production environment context so the analysis can
produce **cluster-specific risk assessment** instead of generic findings.

**What the profile enables:**
- **Config conflict detection**: Find removed/changed configs that exist in your fe.conf/be.conf
- **Deployment-aware guidance**: K8s rolling restart triggers MV re-activation and leader transfer;
  VM deployments follow a different upgrade order
- **Scale-aware risk**: A cluster with 120 MVs faces higher MV-compatibility risk than one with 5
- **Targeted upgrade checklist**: Only includes items relevant to your configuration

### Profile Collection Flow

When the user triggers this skill, the agent should:

1. **Check if `cluster-profile.yaml` exists** in `skills/starrocks-upgrade/`
2. **If it exists**: Show a brief summary and ask if anything needs updating
3. **If it doesn't exist**: Proactively ask the user for the following information through conversation

### What to Collect

Ask the user for these items (one by one or let them paste all at once):

1. **Cluster name and deployment method**: K8s / VM / mixed?
   - K8s: rolling upgrade restarts pods → triggers MV re-activation, leader transfer
   - VM: manual restart order → different upgrade sequence guidance

2. **fe.conf content**: Paste the full fe.conf from production FE node
   - Used to: detect removed/invalid configs, check if overrides conflict with new defaults,
     generate targeted checklist items

3. **be.conf content**: Paste the full be.conf from production BE node
   - Same purpose as fe.conf but for BE side

4. **Cluster scale** (optional but helps prioritize):
   - How many FE/BE nodes?
   - Roughly how many tables and MVs?
   - Using async MV, sync MV (rollup), or both?

### How the Agent Assembles the YAML

After collecting info through conversation, the agent creates `skills/starrocks-upgrade/cluster-profile.yaml`:

```yaml
cluster:
  name: prod-cn-east
  deployment: k8s               # k8s | vm | mixed
  scale:
    fe_nodes: 3
    be_nodes: 12
    tables: 800
    mvs: 120
    has_async_mv: true
    has_sync_mv: true

fe_conf: |
  LOG_DIR = ${STARROCKS_HOME}/log
  DATE = %Y%m%d-%H%M%S
  mysql_server_version = 5.1.0
  metadata_failure_recovery = false
  ...

be_conf: |
  LOG_DIR = ${STARROCKS_HOME}/log
  sys_log_level = INFO
  storage_root_path = /data/starrocks/storage
  mem_limit = 0.8
  max_tablet_version_count = 5000
  ...
```

**Agent behavior:**
- If the user pastes conf content directly, parse it into the YAML `fe_conf:` / `be_conf:` block literals
- If the user says "skip" or "I don't have it", proceed without profile
  (analysis still works but won't have cluster-specific risk assessment)
- Save the assembled profile to `skills/starrocks-upgrade/cluster-profile.yaml`
  so it persists across sessions
- When loading an existing profile, show a brief summary and ask if anything needs updating

### Example Conversation

```
User: 我想做 StarRocks 升级分析，从 3.3.16-cj-0708 升级到 3.5.17-cj-0604

Agent: 好的，我先检查集群配置信息...
       没有找到 cluster-profile.yaml，我需要了解一些集群信息：

       1. 集群名称和部署方式是什么？(K8s / VM / 混合)
       2. 能否贴一下生产环境的 fe.conf 内容？
       3. 能否贴一下生产环境的 be.conf 内容？
       4. 集群规模：多少 FE/BE 节点？大约多少表和 MV？是否使用异步 MV / 同步 rollup？

       你可以一次性提供所有信息，也可以逐项告诉我。

User: 集群名 prod-cn-east，K8s 部署，3 FE 12 BE，大概 800 张表 120 个 MV，
      有异步 MV 也有同步 rollup。
      fe.conf: (粘贴完整内容)
      be.conf: (粘贴完整内容)

Agent: [自动解析并保存 cluster-profile.yaml]
       已保存集群配置 profile：
       - 部署方式: K8s
       - FE 配置: 25 项
       - BE 配置: 18 项
       - 规模: 800 表, 120 MV
       开始升级分析...
```

### Config Conflict Detection Logic

When a cluster profile is provided, the tool automatically:

| Scenario | What happens | Risk |
|----------|-------------|------|
| Config removed + exists in your conf | Will cause startup warning/error | HIGH |
| Config default changed + you use old default | You'll get the new default after upgrade | MEDIUM |
| Config default changed + you have custom override | Your override takes precedence | LOW |
| Config default changed (high-risk) + not in your conf | You'll get the new default | HIGH/CRITICAL |

This means: if you already override a config, default value changes are low risk.
But if you rely on the default and it flips, that's a real risk the tool will flag.

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

### With cluster profile for config conflict detection

```bash
python3 skills/starrocks-upgrade/starrocks_upgrade.py --against <base> --cluster-profile skills/starrocks-upgrade/cluster-profile.yaml
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
- `--skip-diff-detail`: Skip per-commit diff generation (faster, but no commit-level diff analysis possible)
- `--diff-stat-only`: Only save `--stat` per commit, not full diffs (quick preview mode)
- `--cluster-profile <path>`: Path to cluster profile YAML for config conflict detection

## Output Structure

```
upgrade-report/
├── prs/                        # Individual PR details (only with --fetch-prs)
│   ├── 73237.json
│   └── ...
├── commits/                    # Commit details
│   ├── only-in-3.5.17-cj-0604.json
│   ├── only-in-3.3.16-cj-0708.json
│   ├── tiered-3.5.17-cj-0604.json   # Per-commit tier metadata (HIGH/MEDIUM/LOW/SKIP)
│   ├── tiered-3.3.16-cj-0708.json   # Per-commit tier metadata
│   └── detail/                      # Per-commit diff files (HIGH/MEDIUM only)
│       ├── abc123-diff.txt
│       └── ...
├── categories/                 # Categorized commits
│   ├── feat-in-3.5.17-cj-0604.json
│   ├── fix-in-3.5.17-cj-0604.json
│   └── ...
├── pr-diff.json                # PR number diff
├── incompatibilities.json      # All scanner results (config, session vars, BE config, protocol, parser, auth, storage, charset, type system, MV)
├── cluster-config-conflicts.json # Config conflict detection results (only with --cluster-profile)
├── release-notes-cross-ref.json # Release notes cross-reference
└── summary.json                # Overall summary with scanner counts, impact breakdown, and tier counts
```

## Generating the Upgrade Report

After the script collects data, the agent should follow a **four-phase analysis**:

### Phase 1: Collect (single agent)

1. **Run the Python script** — collects commits, scanner results, tier classifications
2. **Read `summary.json`** to understand overall scope, scanner counts, impact breakdown, and tier distribution
3. **Read `incompatibilities.json`** for all scanner findings, categorized by scanner and risk level
4. **Read `pr-diff.json`** to see which PRs are only in each branch
5. **Read `commits/tiered-*.json`** to get the per-commit tier metadata and identify HIGH/MEDIUM commits
6. **Read each PR JSON in `prs/`** (if `--fetch-prs` was used) for detailed impact analysis
7. **Read `cluster-config-conflicts.json`** (if `--cluster-profile` was used) for config conflict detection
   results, deployment-specific risks, and scale assessment
8. **Read official upgrade documentation** from the StarRocks repo:
   - `docs/zh/deployment/upgrade.md` — 获取正确的升级流程（升级顺序、兼容性配置步骤）
   - `docs/zh/deployment/deployment_prerequisites.md` — 获取目标版本的先决条件（JDK 版本等）
9. **Identify all findings requiring deep analysis**:
   - Scanner HIGH/CRITICAL findings
   - Cluster config conflicts (HIGH risk: removed configs in your conf)
   - Deployment-specific risks (K8s: pod restart triggers; VM: upgrade order)
   - HIGH tier commits with diffs
   - MEDIUM tier commits that may have compatibility impact

### Phase 2: Commit Diff Analysis (parallel subagents)

This phase analyzes **per-commit diffs** for HIGH and MEDIUM tier commits. This is critical
because the 11 scanners only cover specific file patterns — changes to core modules like the
optimizer, executor, or catalog may introduce incompatibilities that scanners miss.

**Group commits by module for subagent batching:**

```
Subagent A: Optimizer/Planner commits (5-8 commits per subagent)
Subagent B: Storage engine commits (5-8 commits)
Subagent C: Protocol/RPC commits (5-8 commits)
Subagent D: MV/refresh/rewrite commits (5-8 commits)
Subagent E: Catalog/metadata commits (5-8 commits)
Subagent F: Other MEDIUM tier commits (10-15 commits, summary analysis)
...

Target: 3-8 parallel subagents
```

**Subagent prompt template for commit diff analysis:**

```
你是 StarRocks 升级兼容性分析师。分析以下 commit 的 diff，判断升级风险。

## 升级上下文
- 源分支: {branch_a}
- 目标分支: {branch_b}
- 你的负责模块: {module_name}

## 待分析 Commit 列表

### Commit 1: {subject}
- Hash: {hash}
- PR: #{pr_number}
- Tier: HIGH
- Tier reason: {tier_reason}
- Changed files: {file_list}

Diff:
{diff_content}

---

### Commit 2: ...

## 分析要求

对每个 commit，输出以下结构化结果：

1. **compatibility_impact**: 是否存在不兼容变更？[YES/NO]
2. **impact_type**: [API_BREAKING | BEHAVIOR_CHANGE | DATA_FORMAT | CONFIG_REQUIRED |
   ROLLING_UPGRADE_RISK | ERROR_MESSAGE_CHANGE | DEPRECATION | NONE]
3. **severity**: [CRITICAL | HIGH | MEDIUM | LOW]
4. **summary**: 一句话描述变更及其风险
5. **incompatible_detail**:
   - 哪个接口/行为/数据格式发生了变化
   - 升级后旧版本客户端/旧数据会怎样
   - 是否在混合版本集群中会出问题
6. **error_scenario**: 如果存在不兼容，升级后可能出现的具体报错（包含错误信息原文）
7. **reproduction**: 复现步骤，格式：
   - Precondition: 在哪个版本、创建什么对象
   - Action: 执行什么操作（升级/重启/DDL/DML）
   - Expected result: 升级前的行为
   - Actual result: 升级后的行为/报错
   - Verify fix: 如何验证修复（配置回退/重启/预期结果）
8. **affected_callers**: 受影响的调用方（需要 grep 确认的关键调用点）
9. **rollback**: 能否回滚？是否单向迁移？

## 评估原则
- 宁可误报也不漏报：不确定是否兼容的，标记为 HIGH
- 关注间接影响：一个方法签名变化可能导致所有调用方失败
- 重点关注：类型系统变更、null 处理变化、默认值翻转、异常类型变化、
  序列化格式变化、SQL 语义变化
- 任何删除的 public 方法/类 = CRITICAL
- 任何修改了方法签名但未保持向后兼容 = HIGH
- 任何修改了错误信息的格式 = MEDIUM（可能破坏监控告警）
- 关注 K8s 重启场景：FE/BE pod 重启是否会触发问题？
  - MV re-activation via AlterJobMgr.java
  - FE leader transfer via GlobalStateMgr.transferToLeader()
  - BE startup via StorageEngine.open()
  - Metadata reload via GlobalStateMgr.loadImage()
```

**Subagent output format (JSON):**

```json
{
  "module": "optimizer",
  "commits_analyzed": 6,
  "findings": [
    {
      "commit_hash": "abc123",
      "subject": "fix: handle null in varchar type comparison",
      "pr_number": 73237,
      "compatibility_impact": "YES",
      "impact_type": "BEHAVIOR_CHANGE",
      "severity": "HIGH",
      "summary": "ScalarType.isTypeCompatible() 对 VARCHAR(NULL) 的判断逻辑改变，可能导致 MV re-activation 时 schema check 失败",
      "incompatible_detail": "旧版本允许 VARCHAR(10) 和 VARCHAR(NULL) 互为兼容类型，新版本不再允许。FE 重启时 MV re-activation 会调用 Column.isSchemaCompatible()，如果 MV 定义含 VARCHAR 列，schema check 失败导致 MV 变为 inactive",
      "error_scenario": "FE 重启后报错：MV 'mv_orders' is inactive: schema is not compatible, column 'order_name' type VARCHAR(65533) != VARCHAR(200)",
      "reproduction": {
        "precondition": "在 3.3 版本创建含 VARCHAR 列的 MV",
        "action": "升级 FE 到目标版本并重启",
        "expected_result": "MV 保持 active，查询可正常 rewrite",
        "actual_result": "MV 变为 inactive，查询不再被 rewrite，返回基表全量扫描结果",
        "verify_fix": "SET GLOBAL transform_type_prefer_string_for_varchar = false; 重启 FE; MV 恢复 active"
      },
      "affected_callers": [
        "Column.isSchemaCompatible()",
        "AlterJobMgr.reActivateMV()",
        "AnalyzerUtils.transformTableColumnType()"
      ],
      "rollback": "可回滚，通过 SET GLOBAL 恢复旧行为"
    }
  ]
}
```

**Batching strategy**: If there are more than 10 HIGH/CRITICAL findings, batch related findings
(e.g., all optimizer changes in one subagent, all MV changes in another) to keep subagent
count manageable. Aim for 3-8 parallel subagents.

**LOW tier commits** do NOT need subagents — the main agent can summarize them in a table
directly from the tiered metadata. **SKIP tier commits** are listed by count only.

### Phase 3: Deep Impact Analysis (parallel subagents)

Deep impact analysis traces call chains, data flow, and blast radius for CRITICAL/HIGH findings.
Input sources include BOTH Phase 2 commit findings AND Phase 1 scanner findings.

**Use multiple subagents to analyze findings in parallel.** The workflow:

```
Phase 3: Deep Analysis (parallel subagents)
  - Spawn one subagent per HIGH/CRITICAL finding (or batch related findings)
  - Each subagent gets:
    * The finding details (config name, file, old/new value, risk, source)
    * Source: [Scanner] or [Commit Diff Analysis]
    * Access to the StarRocks repo for grep/read
    * Instructions to produce: callers, data flow, dependent modules,
      blast radius, edge cases, rollback feasibility, reproduction steps
  - Subagents return structured analysis results
```

**Subagent prompt template** for each finding:

```
Analyze this StarRocks upgrade finding for the report:

Finding: <name> changed from <old> to <new>
File: <file path>
Risk: HIGH
Source: [Scanner] / [Commit Diff Analysis - commit <hash>]
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

**Medium/Low findings** do NOT need subagents — the main agent can summarize them in a table
directly from the scanner output or tiered metadata.

### Phase 4: Synthesize (single agent)

1. **Merge all subagent results** from Phase 2 (commit diff) and Phase 3 (deep analysis)
2. **Read official upgrade docs** for the Upgrade Checklist
3. **Generate `upgrade-report.md`** with the following structure

### Report Structure

```markdown
# StarRocks Upgrade Report: <branch-a> -> <branch-b>

## ⚠️ INCOMPATIBLE CHANGES — MUST READ FIRST
> 以下变更会在升级后导致功能异常或报错，必须提前处理。

### [CRITICAL] <变更描述>
- **来源**: Commit <hash> (<subject>) / Scanner <name>
- **影响**: <具体报错信息或行为变化>
- **触发条件**: <什么时候会触发这个问题>
- **复现步骤**:
  1. Precondition: ...
  2. Action: ...
  3. Expected: ...
  4. Actual: ...
- **处理建议**: <升级前/升级后需要做什么>
- **回滚方案**: ...

### [HIGH] <变更描述>
- 同上格式

---

## ⚠️ CLUSTER CONFIG CONFLICTS — 你的集群配置是否有冲突
> 仅当提供了 cluster profile 时显示此节。以下配置在你的 fe.conf/be.conf 中
> 与新版本存在冲突，必须在升级前处理。

### Removed Configs in Your Conf (HIGH)
> 这些配置已从新版本中移除，但你的 conf 文件中仍然存在。
> 升级后可能导致启动报错或警告。

| Config | Conf Source | Current Value | Recommendation |
|--------|------------|---------------|----------------|

### Default Value Changes — You Use the Old Default (MEDIUM)
> 这些配置的默认值已变，你的 conf 中的值恰好是旧默认值。
> 需要决定是否采纳新默认值。

| Config | Conf Source | Old Default | New Default | Your Value | Recommendation |
|--------|------------|-------------|-------------|------------|----------------|

### Default Value Changes — No Override (HIGH)
> 这些高风险配置的默认值已变，你的 conf 中没有覆盖。
> 升级后将自动采用新默认值，可能影响行为。

| Config | Conf Source | Old Default | New Default | Recommendation |
|--------|------------|-------------|-------------|----------------|

### Default Value Changes — Custom Override (LOW)
> 这些配置的默认值已变，但你已有自定义覆盖值，不受影响。

| Config | Conf Source | Old Default | New Default | Your Value |
|--------|------------|-------------|-------------|------------|

### Deployment-Specific Risks
> 基于你的部署方式（K8s/VM）的特定风险提示。

### Scale Assessment
> 基于集群规模的风险评级。

---

## ⚠️ ERROR SCENARIOS — 升级后可能出现的报错
> 按触发时机分类，便于按升级阶段排查

### 升级过程中（rolling upgrade）
| 报错信息 | 触发条件 | 严重程度 | 来源 commit/Scanner | 处理方式 |
|---------|---------|---------|-------------------|---------|

### FE 重启后
| 报错信息 | 触发条件 | 严重程度 | 来源 commit/Scanner | 处理方式 |
|---------|---------|---------|-------------------|---------|

### BE 重启后
| 报错信息 | 触发条件 | 严重程度 | 来源 commit/Scanner | 处理方式 |
|---------|---------|---------|-------------------|---------|

### 日常查询/DDL
| 报错信息 | 触发条件 | 严重程度 | 来源 commit/Scanner | 处理方式 |
|---------|---------|---------|-------------------|---------|

---

## Summary
- Generated: <date>
- Commits only in <branch-b>: N (HIGH: N, MEDIUM: N, LOW: N, SKIP: N)
- Commits only in <branch-a>: N (HIGH: N, MEDIUM: N, LOW: N, SKIP: N)
- PRs only in <branch-b>: N
- PRs only in <branch-a>: N
- Common PRs: N
- Scanners run: N/11
- Total findings: N (critical: N, high: N, medium: N, low: N)
- Impact breakdown: data=N, behavior=N, operational=N, rolling-upgrade=N
- Commit diff analysis: N HIGH/MEDIUM commits analyzed in Phase 2

## Compatibility Impact Summary
> Review this section AFTER the INCOMPATIBLE CHANGES section above.
> This consolidates findings from all 11 scanners AND commit diff analysis,
> grouped by impact dimension.

### Data Impact (existing data may be affected)
> Storage format changes, encoding changes, charset/collation changes.

**HIGH/CRITICAL findings** — each MUST use this format:

#### [HIGH] <config/variable/feature name>: <old> -> <new>
- **Source**: <Scanner name> / <Commit Diff Analysis - commit <hash>>
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

## Commit-Level Diff Analysis (Phase 2 Results)
> Per-commit diff analysis results from Phase 2 subagents.

### HIGH Tier Commits
#### <subject> (<hash>)
- **Tier**: HIGH — <tier_reason>
- **PR**: #<number>
- **兼容性影响**: YES/NO
- **影响类型**: API_BREAKING / BEHAVIOR_CHANGE / DATA_FORMAT / ...
- **严重程度**: CRITICAL / HIGH / MEDIUM / LOW
- **详细分析**: <incompatible_detail>
- **可能的报错**: <error_scenario>
- **复现步骤**:
  1. Precondition: ...
  2. Action: ...
  3. Expected: ...
  4. Actual: ...
  5. Verify fix: ...
- **受影响调用方**: <affected_callers>
- **回滚方案**: <rollback>

### MEDIUM Tier Commits
| Commit | Subject | 影响类型 | 风险 | 摘要 |
|--------|---------|---------|------|------|

### Skipped Commits (LOW/SKIP tier)
| Count | Category | Reason |
|-------|----------|--------|
| 42 | test | 纯测试变更，无兼容性风险 |
| 18 | docs | 文档变更 |
```

### Analysis Guidelines

When analyzing PRs and commit diffs, focus on:

1. **Breaking changes**: Look for keywords like "breaking", "incompatible", "remove", "deprecate",
   "rename", "default change", "behavior change" in PR titles and bodies. **Also read the actual
   diff** — keyword scanning in commit messages catches obvious breaks but misses silent
   behavior changes (null handling, default value flips, error message format changes).
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
7. **Error scenarios**: Every incompatible finding MUST include the specific error message the
   user would see, and the exact conditions to trigger it. This is non-negotiable — the report
   must help the user search for errors in logs.
8. **Reproduction is mandatory**: No finding is complete without reproduction steps. If you
   cannot determine reproduction steps, explicitly state "Reproduction steps unavailable —
   requires manual testing with <specific scenario>".

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
