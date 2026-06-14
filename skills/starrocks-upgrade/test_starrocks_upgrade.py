#!/usr/bin/env python3
"""Tests for starrocks_upgrade.py — pure function tests only (no network/git)."""

import json
import os
import re
import sys
import tempfile
import unittest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from starrocks_upgrade import (
    extract_pr_numbers,
    categorize_commits,
    save_json,
    _extract_fields_from_content,
    _diff_field_sets,
    _is_high_risk_name,
    _classify_config_risk,
    _assess_impact,
    _diff_changed_lines,
    _parse_config_java,
    _parse_session_variable_java,
    classify_commit_tier,
    _matches_path,
    _matches_file_pattern,
    parse_conf_content,
    _normalize_conf_value,
    check_config_conflicts,
    HIGH_RISK_CONFIG_NAMES,
    HIGH_RISK_SESSION_VAR_NAMES,
)


class TestExtractPrNumbers(unittest.TestCase):
    def test_single_pr(self):
        self.assertEqual(extract_pr_numbers("Fix something #73237"), [73237])

    def test_multiple_prs(self):
        result = extract_pr_numbers("Hive Connector #73237 #73569")
        self.assertEqual(result, [73237, 73569])

    def test_no_prs(self):
        self.assertEqual(extract_pr_numbers("No PRs here"), [])

    def test_empty_text(self):
        self.assertEqual(extract_pr_numbers(""), [])
        self.assertEqual(extract_pr_numbers(None), [])

    def test_dedup(self):
        result = extract_pr_numbers("#12345 and #12345 again")
        self.assertEqual(result, [12345])

    def test_ignores_short_numbers(self):
        # Only 3-7 digit numbers are valid PR refs
        self.assertEqual(extract_pr_numbers("#12"), [])
        # 8+ digits: regex matches first 7, which is acceptable for real PRs
        self.assertEqual(extract_pr_numbers("#12345678"), [1234567])


class TestFileIO(unittest.TestCase):
    def test_save_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = save_json({"key": "value"}, os.path.join(tmpdir, "sub", "test.json"))
            self.assertTrue(os.path.exists(path))
            with open(path) as f:
                data = json.load(f)
            self.assertEqual(data["key"], "value")


class TestCategorizeCommits(unittest.TestCase):
    def test_feat_and_fix(self):
        commits = [
            {"message": "feat: add new connector", "hash": "abc123"},
            {"message": "fix: resolve null pointer", "hash": "def456"},
            {"message": "feat(scanner): native avro support", "hash": "ghi789"},
            {"message": "random commit message", "hash": "jkl012"},
        ]
        result = categorize_commits(commits)
        self.assertEqual(len(result["feat"]), 2)
        self.assertEqual(len(result["fix"]), 1)
        self.assertEqual(len(result["other"]), 1)
        self.assertEqual(len(result["refactor"]), 0)

    def test_perf_and_refactor(self):
        commits = [
            {"message": "perf: optimize hash join", "hash": "aaa"},
            {"message": "refactor: extract common utils", "hash": "bbb"},
        ]
        result = categorize_commits(commits)
        self.assertEqual(len(result["perf"]), 1)
        self.assertEqual(len(result["refactor"]), 1)

    def test_empty_commits(self):
        result = categorize_commits([])
        for cat_list in result.values():
            self.assertEqual(len(cat_list), 0)

    def test_breaking_change_marker(self):
        commits = [
            {"message": "feat!: breaking change", "hash": "aaa"},
            {"message": "fix(core)!: also breaking", "hash": "bbb"},
        ]
        result = categorize_commits(commits)
        self.assertEqual(len(result["feat"]), 1)
        self.assertEqual(len(result["fix"]), 1)

    def test_commit_with_subject_field(self):
        """categorize_commits should also work with 'subject' key."""
        commits = [
            {"subject": "feat: new feature", "hash": "aaa"},
            {"subject": "unconventional message", "hash": "bbb"},
        ]
        result = categorize_commits(commits)
        self.assertEqual(len(result["feat"]), 1)
        self.assertEqual(len(result["other"]), 1)


class TestExtractFieldsFromContent(unittest.TestCase):
    def test_basic_extraction(self):
        content = 'public static int query_timeout = 300;\npublic static boolean enable_profile = false;'
        regex = re.compile(r'public\s+(?:static\s+)?(\w+)\s+(\w+)\s*=\s*(.+?);')
        result = _extract_fields_from_content(content, regex)
        self.assertIn("query_timeout", result)
        self.assertEqual(result["query_timeout"]["type"], "int")
        self.assertEqual(result["query_timeout"]["value"], "300")
        self.assertIn("enable_profile", result)
        self.assertEqual(result["enable_profile"]["value"], "false")

    def test_empty_content(self):
        regex = re.compile(r'public\s+(?:static\s+)?(\w+)\s+(\w+)\s*=\s*(.+?);')
        result = _extract_fields_from_content("", regex)
        self.assertEqual(result, {})

    def test_none_content(self):
        regex = re.compile(r'public\s+(?:static\s+)?(\w+)\s+(\w+)\s*=\s*(.+?);')
        result = _extract_fields_from_content(None, regex)
        self.assertEqual(result, {})

    def test_be_config_macros(self):
        content = 'CONF_Int32(max_tablet_version_count, "500");\nCONF_Bool(enable_profile, "false");'
        regex = re.compile(r'CONF_(m?\w+)\((\w+),\s*"([^"]*)"\)')
        result = _extract_fields_from_content(content, regex)
        self.assertIn("max_tablet_version_count", result)
        self.assertEqual(result["max_tablet_version_count"]["type"], "Int32")
        self.assertEqual(result["max_tablet_version_count"]["value"], "500")
        self.assertIn("enable_profile", result)
        self.assertEqual(result["enable_profile"]["type"], "Bool")
        self.assertEqual(result["enable_profile"]["value"], "false")


class TestDiffFieldSets(unittest.TestCase):
    def test_changed_values(self):
        old = {"timeout": {"type": "int", "value": "300"}, "enabled": {"type": "bool", "value": "true"}}
        new = {"timeout": {"type": "int", "value": "600"}, "enabled": {"type": "bool", "value": "true"}}
        added, removed, changed = _diff_field_sets(old, new)
        self.assertEqual(len(changed), 1)
        self.assertEqual(changed[0]["name"], "timeout")
        self.assertEqual(changed[0]["old_value"], "300")
        self.assertEqual(changed[0]["new_value"], "600")
        self.assertEqual(len(added), 0)
        self.assertEqual(len(removed), 0)

    def test_added_nontrivial(self):
        old = {"a": {"type": "int", "value": "1"}}
        new = {"a": {"type": "int", "value": "1"}, "b": {"type": "int", "value": "42"}}
        added, removed, changed = _diff_field_sets(old, new)
        self.assertEqual(len(added), 1)
        self.assertEqual(added[0]["name"], "b")

    def test_added_trivial_skipped(self):
        old = {"a": {"type": "int", "value": "1"}}
        new = {"a": {"type": "int", "value": "1"}, "b": {"type": "int", "value": "0"}}
        added, removed, changed = _diff_field_sets(old, new)
        self.assertEqual(len(added), 0)

    def test_removed(self):
        old = {"a": {"type": "int", "value": "1"}, "b": {"type": "int", "value": "2"}}
        new = {"a": {"type": "int", "value": "1"}}
        added, removed, changed = _diff_field_sets(old, new)
        self.assertEqual(len(removed), 1)
        self.assertEqual(removed[0]["name"], "b")

    def test_empty_sets(self):
        added, removed, changed = _diff_field_sets({}, {})
        self.assertEqual(len(added), 0)
        self.assertEqual(len(removed), 0)
        self.assertEqual(len(changed), 0)


class TestIsHighRiskName(unittest.TestCase):
    def test_exact_match(self):
        self.assertTrue(_is_high_risk_name("mysql_server_version", HIGH_RISK_CONFIG_NAMES))

    def test_no_match(self):
        self.assertFalse(_is_high_risk_name("some_random_config", HIGH_RISK_CONFIG_NAMES))

    def test_session_var_match(self):
        self.assertTrue(_is_high_risk_name("enable_materialized_view_rewrite", HIGH_RISK_SESSION_VAR_NAMES))


class TestClassifyConfigRisk(unittest.TestCase):
    def test_high_risk_config(self):
        risk = _classify_config_risk("mysql_server_version", "config_changed", "5.7.26", "8.0.32")
        self.assertEqual(risk, "high")

    def test_medium_risk_bool_toggle(self):
        risk = _classify_config_risk("some_toggle", "config_changed", "true", "false")
        self.assertEqual(risk, "medium")

    def test_low_risk_default(self):
        risk = _classify_config_risk("unknown_config", "config_changed", "100", "200")
        self.assertEqual(risk, "low")

    def test_high_risk_session_var(self):
        risk = _classify_config_risk("query_timeout", "session_var_changed", "300", "600")
        self.assertEqual(risk, "high")


class TestAssessImpact(unittest.TestCase):
    def test_data_impact(self):
        impact = _assess_impact("max_varchar_length")
        self.assertTrue(impact["data"])

    def test_behavior_impact(self):
        impact = _assess_impact("sql_mode")
        self.assertTrue(impact["behavior"])

    def test_no_impact(self):
        impact = _assess_impact("some_random_setting")
        self.assertFalse(impact["data"])
        self.assertFalse(impact["behavior"])
        self.assertFalse(impact["operational"])

    def test_rolling_upgrade_impact(self):
        impact = _assess_impact("some_field", "protocol_field_removed")
        self.assertTrue(impact["rolling_upgrade"])


class TestDiffChangedLines(unittest.TestCase):
    def test_basic_diff(self):
        diff = "--- a/file.java\n+++ b/file.java\n@@ -1,3 +1,3 @@\n-old line\n+new line\n context"
        added, removed = _diff_changed_lines(diff)
        self.assertEqual(added, ["new line"])
        self.assertEqual(removed, ["old line"])

    def test_empty_diff(self):
        added, removed = _diff_changed_lines("")
        self.assertEqual(added, [])
        self.assertEqual(removed, [])

    def test_only_additions(self):
        diff = "+added line 1\n+added line 2"
        added, removed = _diff_changed_lines(diff)
        self.assertEqual(len(added), 2)
        self.assertEqual(len(removed), 0)


class TestParseConfigJava(unittest.TestCase):
    def test_basic_field(self):
        content = '    @ConfField\n    public static int timeout = 300;'
        result = _parse_config_java(content)
        self.assertIn("timeout", result)
        self.assertEqual(result["timeout"]["type"], "int")
        self.assertEqual(result["timeout"]["value"], "300")
        self.assertIsNone(result["timeout"]["mutable"])
        self.assertFalse(result["timeout"]["deprecated"])

    def test_mutable_annotation(self):
        content = '    @ConfField(mutable = true)\n    public static boolean enable = true;'
        result = _parse_config_java(content)
        self.assertTrue(result["enable"]["mutable"])

    def test_mutable_false(self):
        content = '    @ConfField(mutable = false)\n    public static boolean fixed = true;'
        result = _parse_config_java(content)
        self.assertFalse(result["fixed"]["mutable"])

    def test_comment_annotation(self):
        content = '    @ConfField(comment = "Max connections")\n    public static int max_conn = 100;'
        result = _parse_config_java(content)
        self.assertEqual(result["max_conn"]["comment"], "Max connections")

    def test_mutable_and_comment(self):
        content = '    @ConfField(mutable = true, comment = "Enable feature")\n    public static boolean feature = true;'
        result = _parse_config_java(content)
        self.assertTrue(result["feature"]["mutable"])
        self.assertEqual(result["feature"]["comment"], "Enable feature")

    def test_deprecated(self):
        content = '    @Deprecated\n    @ConfField(mutable = true)\n    public static int old_val = 1;'
        result = _parse_config_java(content)
        self.assertTrue(result["old_val"]["deprecated"])
        self.assertTrue(result["old_val"]["mutable"])

    def test_inline_comment(self):
        content = '    @ConfField\n    public static int log_size = 1024; // 1 GB'
        result = _parse_config_java(content)
        self.assertEqual(result["log_size"]["value"], "1024")

    def test_complex_value(self):
        content = '    @ConfField\n    public static String dir = StarRocksFE.HOME + "/log";'
        result = _parse_config_java(content)
        self.assertEqual(result["dir"]["value"], 'StarRocksFE.HOME + "/log"')

    def test_empty_content(self):
        self.assertEqual(_parse_config_java(""), {})
        self.assertEqual(_parse_config_java(None), {})


class TestParseSessionVariableJava(unittest.TestCase):
    def test_basic_var(self):
        content = '    @VarAttr(name = QUERY_TIMEOUT)\n    public int queryTimeout = 300;'
        result = _parse_session_variable_java(content)
        self.assertIn("queryTimeout", result)
        self.assertEqual(result["queryTimeout"]["var_name"], "QUERY_TIMEOUT")
        self.assertEqual(result["queryTimeout"]["value"], "300")

    def test_var_with_flag(self):
        content = '    @VarAttr(name = ENABLE_SPILL, flag = VariableMgr.INVISIBLE)\n    public boolean enableSpill = false;'
        result = _parse_session_variable_java(content)
        self.assertEqual(result["enableSpill"]["flag"], "VariableMgr.INVISIBLE")

    def test_empty_content(self):
        self.assertEqual(_parse_session_variable_java(""), {})
        self.assertEqual(_parse_session_variable_java(None), {})

    def test_private_field(self):
        content = '    @VarAttr(name = QUERY_TIMEOUT)\n    private int queryTimeout = 300;'
        result = _parse_session_variable_java(content)
        self.assertIn("queryTimeout", result)
        self.assertEqual(result["queryTimeout"]["value"], "300")
        self.assertEqual(result["queryTimeout"]["var_name"], "QUERY_TIMEOUT")

    def test_private_static_field(self):
        content = '    @VarAttr(name = ENABLE_SPILL)\n    private static boolean enableSpill = false;'
        result = _parse_session_variable_java(content)
        self.assertIn("enableSpill", result)
        self.assertEqual(result["enableSpill"]["value"], "false")

    def test_annotation_does_not_leak(self):
        """@VarAttr annotation on one field should not leak to the next field."""
        content = (
            '    @VarAttr(name = FIELD_A)\n'
            '    public int fieldA = 100;\n'
            '\n'
            '    // some comment\n'
            '    public int fieldB = 200;'
        )
        result = _parse_session_variable_java(content)
        self.assertIn("fieldA", result)
        self.assertEqual(result["fieldA"]["var_name"], "FIELD_A")
        self.assertIn("fieldB", result)
        self.assertIsNone(result["fieldB"]["var_name"])

    def test_inline_comment_stripped(self):
        content = '    public int queryTimeout = 300; // timeout in seconds'
        result = _parse_session_variable_java(content)
        self.assertIn("queryTimeout", result)
        self.assertEqual(result["queryTimeout"]["value"], "300")


class TestMatchesPath(unittest.TestCase):
    def test_exact_prefix_match(self):
        self.assertTrue(_matches_path(
            "fe/fe-core/src/main/java/com/starrocks/sql/optimizer/Optimizer.java",
            ["fe/fe-core/src/main/java/com/starrocks/sql/optimizer/"],
        ))

    def test_no_match(self):
        self.assertFalse(_matches_path(
            "fe/fe-core/src/test/java/com/starrocks/sql/SomeTest.java",
            ["fe/fe-core/src/main/java/com/starrocks/sql/optimizer/"],
        ))

    def test_mid_path_match(self):
        self.assertTrue(_matches_path(
            "be/src/runtime/some_file.cpp",
            ["be/src/runtime/"],
        ))

    def test_empty_path_list(self):
        self.assertFalse(_matches_path("any/path", []))


class TestMatchesFilePattern(unittest.TestCase):
    def test_exact_name(self):
        self.assertTrue(_matches_file_pattern(
            "fe/.../MaterializedView.java",
            ["MaterializedView.java"],
        ))

    def test_glob_pattern(self):
        self.assertTrue(_matches_file_pattern(
            "fe/.../MaterializedViewRefreshProcessor.java",
            ["MaterializedViewRefresh*.java"],
        ))

    def test_no_match(self):
        self.assertFalse(_matches_file_pattern(
            "fe/.../SomeOtherFile.java",
            ["MaterializedView.java"],
        ))

    def test_empty_pattern_list(self):
        self.assertFalse(_matches_file_pattern("any/File.java", []))


class TestClassifyCommitTier(unittest.TestCase):
    def test_high_tier_optimizer_path(self):
        commit = {"subject": "fix: optimizer null handling"}
        files = ["fe/fe-core/src/main/java/com/starrocks/sql/optimizer/Rule.java"]
        tier, reason = classify_commit_tier(commit, files)
        self.assertEqual(tier, "HIGH")
        self.assertIn("core path", reason)

    def test_high_tier_critical_file(self):
        commit = {"subject": "refactor: ScalarType comparison logic"}
        files = ["fe/fe-core/src/main/java/com/starrocks/catalog/ScalarType.java"]
        tier, reason = classify_commit_tier(commit, files)
        self.assertEqual(tier, "HIGH")
        self.assertIn("critical file", reason)

    def test_high_tier_mv_file(self):
        commit = {"subject": "feat: MV rewrite improvement"}
        files = ["fe/fe-core/src/main/java/com/starrocks/catalog/MaterializedView.java"]
        tier, reason = classify_commit_tier(commit, files)
        self.assertEqual(tier, "HIGH")

    def test_high_tier_be_storage(self):
        commit = {"subject": "fix: tablet load failure on restart"}
        files = ["be/src/storage/tablet.cpp"]
        tier, reason = classify_commit_tier(commit, files)
        self.assertEqual(tier, "HIGH")
        self.assertIn("core path", reason)

    def test_high_tier_protocol(self):
        commit = {"subject": "feat: add new thrift field"}
        files = ["gensrc/thrift/StarRocksExternalService.thrift"]
        tier, reason = classify_commit_tier(commit, files)
        self.assertEqual(tier, "HIGH")

    def test_medium_tier_connector(self):
        commit = {"subject": "feat: hive connector improvement"}
        files = ["fe/fe-core/src/main/java/com/starrocks/connector/hive/HiveConnector.java"]
        tier, reason = classify_commit_tier(commit, files)
        self.assertEqual(tier, "MEDIUM")
        self.assertIn("business path", reason)

    def test_medium_tier_feat_with_source(self):
        commit = {"subject": "feat: add new string function"}
        files = ["fe/fe-core/src/main/java/com/starrocks/sql/SomeNewFunction.java"]
        tier, reason = classify_commit_tier(commit, files)
        self.assertEqual(tier, "MEDIUM")
        self.assertIn("feat/fix with source code changes", reason)

    def test_low_tier_infra_change(self):
        commit = {"subject": "update dependency version"}
        files = ["pom.xml"]
        tier, _ = classify_commit_tier(commit, files)
        self.assertEqual(tier, "LOW")

    def test_skip_tier_chore_prefix(self):
        commit = {"subject": "chore: update CI pipeline"}
        files = [".github/workflows/ci.yml"]
        tier, reason = classify_commit_tier(commit, files)
        self.assertEqual(tier, "SKIP")
        self.assertIn("commit type", reason)

    def test_skip_tier_build_prefix(self):
        commit = {"subject": "build: fix compilation error"}
        files = ["Makefile"]
        tier, reason = classify_commit_tier(commit, files)
        self.assertEqual(tier, "SKIP")

    def test_skip_tier_ci_prefix(self):
        commit = {"subject": "ci: add new test job"}
        files = ["ci/run-tests.sh"]
        tier, reason = classify_commit_tier(commit, files)
        self.assertEqual(tier, "SKIP")

    def test_skip_tier_all_test_files(self):
        commit = {"subject": "test: add unit tests for optimizer"}
        files = [
            "fe/fe-core/src/test/java/com/starrocks/sql/optimizer/OptimizerTest.java",
            "fe/fe-core/src/test/java/com/starrocks/sql/optimizer/RuleTest.java",
        ]
        tier, reason = classify_commit_tier(commit, files)
        self.assertEqual(tier, "SKIP")
        self.assertIn("skip paths", reason)

    def test_high_tier_overrides_test_files(self):
        """If a commit touches both core and test files, it's HIGH."""
        commit = {"subject": "fix: optimizer edge case + test"}
        files = [
            "fe/fe-core/src/main/java/com/starrocks/sql/optimizer/Rule.java",
            "fe/fe-core/src/test/java/com/starrocks/sql/optimizer/RuleTest.java",
        ]
        tier, reason = classify_commit_tier(commit, files)
        self.assertEqual(tier, "HIGH")

    def test_empty_changed_files(self):
        """With no file info, feat commit defaults to LOW (no source file evidence)."""
        commit = {"subject": "feat: some new feature"}
        tier, _ = classify_commit_tier(commit, [])
        self.assertEqual(tier, "LOW")

    def test_fix_in_catalog_path_is_high(self):
        """catalog/ is in HIGH_TIER_PATHS — changes to catalog code are always HIGH."""
        commit = {"subject": "fix: catalog metadata race condition"}
        files = ["fe/fe-core/src/main/java/com/starrocks/catalog/CatalogMgr.java"]
        tier, _ = classify_commit_tier(commit, files)
        self.assertEqual(tier, "HIGH")

    def test_fix_in_scheduler_path_is_medium(self):
        commit = {"subject": "fix: scheduler task retry logic"}
        files = ["fe/fe-core/src/main/java/com/starrocks/scheduler/TaskRun.java"]
        tier, reason = classify_commit_tier(commit, files)
        self.assertEqual(tier, "MEDIUM")
        self.assertIn("business path", reason)

    def test_high_tier_global_state_mgr(self):
        commit = {"subject": "refactor: leader transfer flow"}
        files = ["fe/fe-core/src/main/java/com/starrocks/server/GlobalStateMgr.java"]
        tier, _ = classify_commit_tier(commit, files)
        self.assertEqual(tier, "HIGH")

    def test_revert_prefix_is_skip(self):
        commit = {"subject": "revert: rollback previous change"}
        files = ["fe/fe-core/src/main/java/com/starrocks/sql/optimizer/Rule.java"]
        tier, reason = classify_commit_tier(commit, files)
        self.assertEqual(tier, "SKIP")
        self.assertIn("commit type", reason)

    def test_multiple_high_reasons(self):
        """Commit touching both high-tier path and critical file."""
        commit = {"subject": "fix: MV schema check in optimizer"}
        files = [
            "fe/fe-core/src/main/java/com/starrocks/sql/optimizer/MVRule.java",
            "fe/fe-core/src/main/java/com/starrocks/catalog/MaterializedView.java",
        ]
        tier, reason = classify_commit_tier(commit, files)
        self.assertEqual(tier, "HIGH")
        self.assertIn("core path", reason)
        self.assertIn("critical file", reason)


class TestParseConfContent(unittest.TestCase):
    def test_basic_key_value(self):
        content = "mysql_server_version = 5.1.0\nmetadata_failure_recovery = false"
        result = parse_conf_content(content)
        self.assertEqual(result["mysql_server_version"], "5.1.0")
        self.assertEqual(result["metadata_failure_recovery"], "false")

    def test_comments_ignored(self):
        content = "# This is a comment\nkey = value"
        result = parse_conf_content(content)
        self.assertEqual(result, {"key": "value"})

    def test_empty_lines_ignored(self):
        content = "key1 = val1\n\n\nkey2 = val2"
        result = parse_conf_content(content)
        self.assertEqual(len(result), 2)

    def test_value_with_equals(self):
        content = 'JAVA_OPTS = "-Xmx8192m -XX:+UseG1GC"'
        result = parse_conf_content(content)
        self.assertEqual(result["JAVA_OPTS"], '"-Xmx8192m -XX:+UseG1GC"')

    def test_no_spaces_around_equals(self):
        content = "key=val"
        result = parse_conf_content(content)
        self.assertEqual(result["key"], "val")

    def test_empty_content(self):
        self.assertEqual(parse_conf_content(""), {})
        self.assertEqual(parse_conf_content(None), {})

    def test_line_without_equals_skipped(self):
        content = "no_equals_here\nkey = value"
        result = parse_conf_content(content)
        self.assertEqual(len(result), 1)
        self.assertIn("key", result)

    def test_empty_key_skipped(self):
        content = " = value_only\nkey = value"
        result = parse_conf_content(content)
        self.assertEqual(len(result), 1)
        self.assertIn("key", result)


class TestNormalizeConfValue(unittest.TestCase):
    def test_strip_semicolon(self):
        self.assertEqual(_normalize_conf_value("300;"), "300")

    def test_strip_java_long_suffix(self):
        self.assertEqual(_normalize_conf_value("1024L;"), "1024")

    def test_strip_java_float_suffix(self):
        self.assertEqual(_normalize_conf_value("0.8f;"), "0.8")

    def test_strip_double_quotes(self):
        self.assertEqual(_normalize_conf_value('"5.1.0"'), "5.1.0")

    def test_strip_single_quotes(self):
        self.assertEqual(_normalize_conf_value("'5.1.0'"), "5.1.0")

    def test_empty_value(self):
        self.assertEqual(_normalize_conf_value(""), "")
        self.assertEqual(_normalize_conf_value(None), "")

    def test_no_stripping_needed(self):
        self.assertEqual(_normalize_conf_value("false"), "false")

    def test_boolean_value(self):
        self.assertEqual(_normalize_conf_value("true"), "true")


class TestCheckConfigConflicts(unittest.TestCase):
    def _make_profile(self, fe_conf_raw="", be_conf_raw="", deployment="k8s", mvs=120):
        return {
            "cluster": {
                "name": "test-cluster",
                "deployment": deployment,
                "scale": {
                    "fe_nodes": 3,
                    "be_nodes": 12,
                    "tables": 800,
                    "mvs": mvs,
                    "has_async_mv": True,
                    "has_sync_mv": True,
                },
            },
            "fe_conf_parsed": parse_conf_content(fe_conf_raw),
            "be_conf_parsed": parse_conf_content(be_conf_raw),
        }

    def test_none_profile_returns_none(self):
        result = check_config_conflicts(None, {"config_changes": []})
        self.assertIsNone(result)

    def test_removed_config_in_fe_conf(self):
        profile = self._make_profile(fe_conf_raw="removed_config = some_value")
        incompat = {
            "config_changes": [{
                "type": "config_removed",
                "name": "removed_config",
                "file": "fe/fe-core/src/main/java/com/starrocks/common/Config.java",
                "old_value": "some_value",
            }],
            "scanner_findings": [],
            "mv_changes": {"summary": {"total_mv_files_changed": 0}},
        }
        result = check_config_conflicts(profile, incompat)
        self.assertIsNotNone(result)
        high_conflicts = [c for c in result["config_conflicts"] if c["risk"] == "high"]
        self.assertEqual(len(high_conflicts), 1)
        self.assertEqual(high_conflicts[0]["type"], "removed_config_in_conf")
        self.assertEqual(high_conflicts[0]["config_name"], "removed_config")

    def test_removed_config_not_in_conf(self):
        profile = self._make_profile(fe_conf_raw="other_config = value")
        incompat = {
            "config_changes": [{
                "type": "config_removed",
                "name": "removed_config",
                "file": "fe/fe-core/src/main/java/com/starrocks/common/Config.java",
                "old_value": "some_value",
            }],
            "scanner_findings": [],
            "mv_changes": {"summary": {"total_mv_files_changed": 0}},
        }
        result = check_config_conflicts(profile, incompat)
        high_conflicts = [c for c in result["config_conflicts"] if c["risk"] == "high"]
        self.assertEqual(len(high_conflicts), 0)

    def test_changed_config_using_old_default(self):
        profile = self._make_profile(fe_conf_raw="some_config = false")
        incompat = {
            "config_changes": [{
                "type": "config_changed",
                "name": "some_config",
                "file": "fe/fe-core/src/main/java/com/starrocks/common/Config.java",
                "old_value": "false",
                "new_value": "true",
                "risk": "medium",
            }],
            "scanner_findings": [],
            "mv_changes": {"summary": {"total_mv_files_changed": 0}},
        }
        result = check_config_conflicts(profile, incompat)
        medium_conflicts = [c for c in result["config_conflicts"] if c["risk"] == "medium"]
        self.assertTrue(any(c["type"] == "config_changed_using_old_default" for c in medium_conflicts))

    def test_changed_config_custom_override(self):
        profile = self._make_profile(fe_conf_raw="some_config = 50")
        incompat = {
            "config_changes": [{
                "type": "config_changed",
                "name": "some_config",
                "file": "fe/fe-core/src/main/java/com/starrocks/common/Config.java",
                "old_value": "10",
                "new_value": "20",
                "risk": "low",
            }],
            "scanner_findings": [],
            "mv_changes": {"summary": {"total_mv_files_changed": 0}},
        }
        result = check_config_conflicts(profile, incompat)
        custom_overrides = [c for c in result["config_conflicts"]
                           if c["type"] == "config_changed_custom_override"]
        self.assertEqual(len(custom_overrides), 1)
        self.assertEqual(custom_overrides[0]["risk"], "low")

    def test_changed_config_no_override_high_risk(self):
        profile = self._make_profile(fe_conf_raw="other_config = value")
        incompat = {
            "config_changes": [{
                "type": "config_changed",
                "name": "high_risk_config",
                "file": "fe/fe-core/src/main/java/com/starrocks/common/Config.java",
                "old_value": "false",
                "new_value": "true",
                "risk": "high",
            }],
            "scanner_findings": [],
            "mv_changes": {"summary": {"total_mv_files_changed": 0}},
        }
        result = check_config_conflicts(profile, incompat)
        no_override = [c for c in result["config_conflicts"]
                       if c["type"] == "config_changed_no_override"]
        self.assertEqual(len(no_override), 1)
        self.assertEqual(no_override[0]["risk"], "high")

    def test_be_config_removed_in_be_conf(self):
        profile = self._make_profile(be_conf_raw="old_be_config = 500")
        incompat = {
            "config_changes": [],
            "scanner_findings": [{
                "type": "be_config_removed",
                "name": "old_be_config",
                "file": "be/src/common/config.h",
            }],
            "mv_changes": {"summary": {"total_mv_files_changed": 0}},
        }
        result = check_config_conflicts(profile, incompat)
        high_conflicts = [c for c in result["config_conflicts"] if c["risk"] == "high"]
        self.assertEqual(len(high_conflicts), 1)
        self.assertEqual(high_conflicts[0]["conf_source"], "be_conf")

    def test_k8s_deployment_risk_with_mv_changes(self):
        profile = self._make_profile(deployment="k8s", mvs=50)
        incompat = {
            "config_changes": [],
            "scanner_findings": [],
            "mv_changes": {"summary": {"total_mv_files_changed": 3}},
        }
        result = check_config_conflicts(profile, incompat)
        self.assertTrue(len(result["deployment_risks"]) > 0)
        self.assertIn("MV", result["deployment_risks"][0]["risk"])

    def test_k8s_deployment_risk_with_protocol_changes(self):
        profile = self._make_profile(deployment="k8s")
        incompat = {
            "config_changes": [],
            "scanner_findings": [{
                "type": "protocol_field_removed",
                "file": "gensrc/thrift/StarRocks.thrift",
            }],
            "mv_changes": {"summary": {"total_mv_files_changed": 0}},
        }
        result = check_config_conflicts(profile, incompat)
        protocol_risks = [r for r in result["deployment_risks"] if "Protocol" in r["risk"]]
        self.assertTrue(len(protocol_risks) > 0)

    def test_vm_deployment_risk_with_protocol_changes(self):
        profile = self._make_profile(deployment="vm")
        incompat = {
            "config_changes": [],
            "scanner_findings": [{
                "type": "protocol_field_removed",
                "file": "gensrc/thrift/StarRocks.thrift",
            }],
            "mv_changes": {"summary": {"total_mv_files_changed": 0}},
        }
        result = check_config_conflicts(profile, incompat)
        protocol_risks = [r for r in result["deployment_risks"] if "Protocol" in r["risk"]]
        self.assertTrue(len(protocol_risks) > 0)

    def test_scale_assessment_mv_risk(self):
        profile = self._make_profile(mvs=120)
        incompat = {
            "config_changes": [],
            "scanner_findings": [],
            "mv_changes": {"summary": {"total_mv_files_changed": 0}},
        }
        result = check_config_conflicts(profile, incompat)
        self.assertIn("mv_risk", result["scale_assessment"])
        self.assertEqual(result["scale_assessment"]["mv_risk"]["level"], "high")

    def test_scale_assessment_low_mv_risk(self):
        profile = self._make_profile(mvs=5)
        incompat = {
            "config_changes": [],
            "scanner_findings": [],
            "mv_changes": {"summary": {"total_mv_files_changed": 0}},
        }
        result = check_config_conflicts(profile, incompat)
        self.assertEqual(result["scale_assessment"]["mv_risk"]["level"], "low")

    def test_conflict_summary(self):
        profile = self._make_profile(fe_conf_raw="removed_a = 1\nchanged_b = false")
        incompat = {
            "config_changes": [
                {
                    "type": "config_removed",
                    "name": "removed_a",
                    "file": "fe/fe-core/src/main/java/com/starrocks/common/Config.java",
                    "old_value": "1",
                },
                {
                    "type": "config_changed",
                    "name": "changed_b",
                    "file": "fe/fe-core/src/main/java/com/starrocks/common/Config.java",
                    "old_value": "false",
                    "new_value": "true",
                    "risk": "medium",
                },
            ],
            "scanner_findings": [],
            "mv_changes": {"summary": {"total_mv_files_changed": 0}},
        }
        result = check_config_conflicts(profile, incompat)
        self.assertEqual(result["conflict_summary"]["high_risk"], 1)
        self.assertEqual(result["conflict_summary"]["medium_risk"], 1)


if __name__ == "__main__":
    unittest.main()
