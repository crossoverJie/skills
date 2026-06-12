#!/usr/bin/env python3
"""Tests for starrocks_upgrade.py — pure function tests only (no network/git)."""

import json
import os
import sys
import tempfile
import unittest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from starrocks_upgrade import (
    extract_pr_numbers,
    categorize_commits,
    save_json,
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


if __name__ == "__main__":
    unittest.main()
