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


if __name__ == "__main__":
    unittest.main()
