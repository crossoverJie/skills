"""Unit tests for agent-notifier notify.py."""

import json
import os
import subprocess
import sys
import unittest
from unittest.mock import patch, MagicMock

# Ensure the module is importable
sys.path.insert(0, os.path.dirname(__file__))
import notify


class TestGetGitRepoName(unittest.TestCase):
    """Tests for _get_git_repo_name()."""

    @patch("notify.subprocess.run")
    def test_returns_repo_basename(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="/Users/dev/my-project\n"
        )
        self.assertEqual(notify._get_git_repo_name("/Users/dev/my-project"), "my-project")

    @patch("notify.subprocess.run")
    def test_returns_empty_on_non_git_dir(self, mock_run):
        mock_run.return_value = MagicMock(returncode=128, stdout="")
        self.assertEqual(notify._get_git_repo_name("/tmp"), "")

    @patch("notify.subprocess.run", side_effect=FileNotFoundError)
    def test_returns_empty_when_git_not_installed(self, mock_run):
        self.assertEqual(notify._get_git_repo_name("/tmp"), "")

    @patch("notify.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="git", timeout=3))
    def test_returns_empty_on_timeout(self, mock_run):
        self.assertEqual(notify._get_git_repo_name("/tmp"), "")


class TestDetectProjectContext(unittest.TestCase):
    """Tests for _detect_project_context()."""

    @patch("notify._get_git_repo_name", return_value="my-repo")
    def test_uses_cwd_from_payload(self, mock_git):
        result = notify._detect_project_context(
            {"cwd": "/Users/dev/my-repo"}, "copilot_cli"
        )
        self.assertEqual(result, "my-repo")
        mock_git.assert_called_once_with("/Users/dev/my-repo")

    @patch("notify._get_git_repo_name", return_value="workspace")
    @patch("os.getcwd", return_value="/home/user/workspace")
    def test_falls_back_to_os_getcwd(self, mock_getcwd, mock_git):
        result = notify._detect_project_context({}, "claude_code")
        self.assertEqual(result, "workspace")
        mock_getcwd.assert_called_once()

    @patch("notify._get_git_repo_name", return_value="")
    @patch("os.getcwd", return_value="/home/user/plain-dir")
    def test_falls_back_to_basename_when_not_git(self, mock_getcwd, mock_git):
        result = notify._detect_project_context({}, "claude_code")
        self.assertEqual(result, "plain-dir")

    @patch("notify._get_git_repo_name", return_value="")
    def test_uses_payload_cwd_basename_when_not_git(self, mock_git):
        result = notify._detect_project_context(
            {"cwd": "/Users/dev/my-folder"}, "copilot_cli"
        )
        self.assertEqual(result, "my-folder")

    def test_returns_empty_on_non_dict_data(self):
        with patch("os.getcwd", return_value="/home/user/proj"), \
             patch("notify._get_git_repo_name", return_value="proj"):
            result = notify._detect_project_context("not a dict", "unknown")
            self.assertEqual(result, "proj")


class TestFormatBody(unittest.TestCase):
    """Tests for _format_body()."""

    def test_with_project(self):
        event = {"message": "Task completed", "event": "idle", "project": "my-app"}
        self.assertEqual(notify._format_body(event), "[my-app] Task completed")

    def test_without_project(self):
        event = {"message": "Task completed", "event": "idle"}
        self.assertEqual(notify._format_body(event), "Task completed")

    def test_empty_project(self):
        event = {"message": "Task completed", "event": "idle", "project": ""}
        self.assertEqual(notify._format_body(event), "Task completed")

    def test_falls_back_to_event_when_no_message(self):
        event = {"message": "", "event": "idle_prompt", "project": "proj"}
        self.assertEqual(notify._format_body(event), "[proj] idle_prompt")


class TestFormatTitle(unittest.TestCase):
    """Tests for _format_title()."""

    def test_known_platform(self):
        event = {"platform": "claude_code"}
        self.assertEqual(notify._format_title(event), "Agent Notifier — Claude Code")

    def test_opencode_platform(self):
        event = {"platform": "opencode"}
        self.assertEqual(notify._format_title(event), "Agent Notifier — OpenCode")

    def test_unknown_platform(self):
        event = {"platform": "unknown"}
        self.assertEqual(notify._format_title(event), "Agent Notifier — AI Agent")


class TestParseInput(unittest.TestCase):
    """Integration tests for parse_input() — project field presence."""

    @patch("notify._detect_project_context", return_value="skills")
    @patch("notify._read_stdin", return_value='{"notification_type":"idle_prompt"}')
    def test_claude_code_has_project(self, mock_stdin, mock_ctx):
        result = notify.parse_input()
        self.assertEqual(result["platform"], "claude_code")
        self.assertEqual(result["project"], "skills")
        self.assertIn("project", result)

    @patch("notify._detect_project_context", return_value="my-project")
    @patch("notify._read_stdin", return_value='{"reason":"complete","cwd":"/dev/my-project"}')
    def test_copilot_session_end_has_project(self, mock_stdin, mock_ctx):
        result = notify.parse_input()
        self.assertEqual(result["platform"], "copilot_cli")
        self.assertEqual(result["event"], "sessionEnd")
        self.assertEqual(result["project"], "my-project")

    @patch("notify._detect_project_context", return_value="repo")
    @patch("notify._read_stdin", return_value='{"toolName":"bash","toolResult":{"resultType":"success"}}')
    def test_copilot_post_tool_use_has_project(self, mock_stdin, mock_ctx):
        result = notify.parse_input()
        self.assertEqual(result["platform"], "copilot_cli")
        self.assertEqual(result["event"], "postToolUse")
        self.assertEqual(result["project"], "repo")

    @patch("notify._detect_project_context", return_value="repo")
    @patch("notify._read_stdin", return_value='{"source":"terminal"}')
    def test_copilot_session_start_has_project(self, mock_stdin, mock_ctx):
        result = notify.parse_input()
        self.assertEqual(result["platform"], "copilot_cli")
        self.assertEqual(result["event"], "sessionStart")
        self.assertEqual(result["project"], "repo")

    @patch("notify._detect_project_context", return_value="cur-proj")
    @patch("notify._read_stdin", return_value='{"hook_event_name":"stop","status":"completed","agent":"cursor"}')
    def test_cursor_has_project(self, mock_stdin, mock_ctx):
        result = notify.parse_input()
        self.assertEqual(result["platform"], "cursor")
        self.assertEqual(result["project"], "cur-proj")

    @patch("notify._detect_project_context", return_value="codex-proj")
    @patch("notify._read_stdin", return_value='{"type":"agent-turn-complete","message":"Done"}')
    def test_codex_has_project(self, mock_stdin, mock_ctx):
        result = notify.parse_input()
        self.assertEqual(result["platform"], "codex")
        self.assertEqual(result["project"], "codex-proj")

    @patch("notify._detect_project_context", return_value="oc-proj")
    @patch("notify._read_stdin", return_value='{"platform":"opencode","event_type":"session.idle","message":"Session completed"}')
    def test_opencode_session_idle(self, mock_stdin, mock_ctx):
        result = notify.parse_input()
        self.assertEqual(result["platform"], "opencode")
        self.assertEqual(result["event"], "session.idle")
        self.assertEqual(result["message"], "✅ Session completed — waiting for your input")
        self.assertEqual(result["project"], "oc-proj")

    @patch("notify._detect_project_context", return_value="proj")
    @patch("notify._read_stdin", return_value="")
    def test_empty_stdin_has_project(self, mock_stdin, mock_ctx):
        # sys.argv has no extra args
        with patch.object(sys, "argv", ["notify.py"]):
            result = notify.parse_input()
            self.assertEqual(result["platform"], "unknown")
            self.assertIn("project", result)

    @patch("notify._detect_project_context", return_value="proj")
    @patch("notify._read_stdin", return_value="")
    def test_aider_argv_has_project(self, mock_stdin, mock_ctx):
        with patch.object(sys, "argv", ["notify.py", "Task", "done"]):
            result = notify.parse_input()
            self.assertEqual(result["platform"], "aider")
            self.assertEqual(result["message"], "Task done")
            self.assertIn("project", result)

    @patch("notify._detect_project_context", return_value="proj")
    @patch("notify._read_stdin", return_value="plain text message")
    def test_non_json_stdin_has_project(self, mock_stdin, mock_ctx):
        result = notify.parse_input()
        self.assertEqual(result["platform"], "unknown")
        self.assertEqual(result["message"], "plain text message")
        self.assertIn("project", result)

    @patch("notify._detect_project_context", return_value="proj")
    @patch("notify._read_stdin", return_value='{"some":"unknown","data":true}')
    def test_fallback_json_has_project(self, mock_stdin, mock_ctx):
        result = notify.parse_input()
        self.assertEqual(result["platform"], "unknown")
        self.assertIn("project", result)


class TestSendEmailSubject(unittest.TestCase):
    """Test that send_email() includes project in subject."""

    @patch("notify.smtplib.SMTP")
    def test_email_subject_with_project(self, mock_smtp_cls):
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        cfg = {
            "smtp_host": "smtp.test.com",
            "smtp_port": 587,
            "username": "user@test.com",
            "password": "pass",
            "to_addr": "to@test.com",
        }
        event_info = {
            "platform": "claude_code",
            "event": "idle_prompt",
            "message": "Task completed",
            "project": "my-proj",
        }
        notify.send_email(cfg, event_info)
        # Check the sent message contains project in subject
        sent_msg = mock_server.sendmail.call_args[0][2]
        self.assertIn("[my-proj]", sent_msg)

    @patch("notify.smtplib.SMTP")
    def test_email_subject_without_project(self, mock_smtp_cls):
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        cfg = {
            "smtp_host": "smtp.test.com",
            "smtp_port": 587,
            "username": "user@test.com",
            "password": "pass",
            "to_addr": "to@test.com",
        }
        event_info = {
            "platform": "claude_code",
            "event": "idle_prompt",
            "message": "Task completed",
        }
        notify.send_email(cfg, event_info)
        sent_msg = mock_server.sendmail.call_args[0][2]
        # Subject should contain "Agent Notifier" but NOT a project tag
        self.assertIn("Agent_Notifier", sent_msg)
        self.assertNotIn("[my-proj]", sent_msg)


if __name__ == "__main__":
    unittest.main()
