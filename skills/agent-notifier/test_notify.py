"""Unit tests for agent-notifier notify.py and setup.py."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# Ensure the module directory is importable
sys.path.insert(0, os.path.dirname(__file__))
import notify
import setup


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

    @patch("notify._get_git_repo_name", return_value="oc-repo")
    def test_uses_directory_from_payload(self, mock_git):
        result = notify._detect_project_context(
            {"directory": "/Users/dev/oc-repo"}, "opencode"
        )
        self.assertEqual(result, "oc-repo")
        mock_git.assert_called_once_with("/Users/dev/oc-repo")

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

    def test_codex_platform(self):
        event = {"platform": "codex"}
        self.assertEqual(notify._format_title(event), "Agent Notifier — Codex")

    def test_opencode_platform(self):
        event = {"platform": "opencode"}
        self.assertEqual(notify._format_title(event), "Agent Notifier — OpenCode")

    def test_unknown_platform(self):
        event = {"platform": "unknown"}
        self.assertEqual(notify._format_title(event), "Agent Notifier — AI Agent")


class TestParseInput(unittest.TestCase):
    """Integration tests for parse_input() across all platforms and events."""

    @patch("notify._detect_project_context", return_value="skills")
    @patch("notify._read_stdin", return_value='{"notification_type":"idle_prompt"}')
    def test_claude_code_idle_prompt(self, mock_stdin, mock_ctx):
        result = notify.parse_input([])
        self.assertEqual(result["platform"], "claude_code")
        self.assertEqual(result["event"], "idle_prompt")
        self.assertEqual(result["message"], "⏳ Waiting for your input")
        self.assertEqual(result["project"], "skills")

    @patch("notify._detect_project_context", return_value="skills")
    @patch("notify._read_stdin", return_value='{"hook_event_name":"Stop","stop_hook_active":false}')
    def test_claude_code_stop_event(self, mock_stdin, mock_ctx):
        result = notify.parse_input(["--platform", "claude_code"])
        self.assertEqual(result["platform"], "claude_code")
        self.assertEqual(result["event"], "Stop")
        self.assertEqual(result["message"], "✅ Task completed — waiting for your input")
        self.assertFalse(result.get("skip", False))

    @patch("notify._detect_project_context", return_value="skills")
    @patch("notify._read_stdin", return_value='{"hook_event_name":"Stop","stop_hook_active":true}')
    def test_claude_code_stop_skips_when_stop_hook_active(self, mock_stdin, mock_ctx):
        result = notify.parse_input(["--platform", "claude_code"])
        self.assertTrue(result.get("skip"))

    @patch("notify._detect_project_context", return_value="skills")
    @patch(
        "notify._read_stdin",
        return_value='{"hook_event_name":"Stop","background_tasks":[{"type":"subagent","status":"running"}]}',
    )
    def test_claude_code_stop_skips_running_subagent(self, mock_stdin, mock_ctx):
        result = notify.parse_input(["--platform", "claude_code"])
        self.assertTrue(result.get("skip"))

    @patch("notify._detect_project_context", return_value="skills")
    @patch("notify._read_stdin", return_value='{"hook_event_name":"StopFailure","error":"rate_limit"}')
    def test_claude_code_stop_failure(self, mock_stdin, mock_ctx):
        result = notify.parse_input(["--platform", "claude_code"])
        self.assertEqual(result["platform"], "claude_code")
        self.assertEqual(result["event"], "StopFailure")
        self.assertIn("rate_limit", result["message"])
        self.assertIn("❌", result["message"])

    @patch("notify._detect_project_context", return_value="skills")
    @patch(
        "notify._read_stdin",
        return_value='{"hook_event_name":"PermissionRequest","tool_name":"Bash","tool_input":{"command":"git push"}}',
    )
    def test_claude_code_permission_request(self, mock_stdin, mock_ctx):
        result = notify.parse_input(["--platform", "claude_code"])
        self.assertEqual(result["platform"], "claude_code")
        self.assertEqual(result["event"], "PermissionRequest")
        self.assertEqual(result["message"], "🔐 Permission required (Bash: git push)")

    @patch("notify._detect_project_context", return_value="codex-proj")
    @patch("notify._read_stdin", return_value='{"session_id":"abc","cwd":"/tmp/codex-proj","last_assistant_message":"Done"}')
    def test_codex_stop_without_hook_event_name(self, mock_stdin, mock_ctx):
        result = notify.parse_input(["--platform", "codex"])
        self.assertEqual(result["platform"], "codex")
        self.assertEqual(result["event"], "Stop")
        self.assertEqual(result["message"], "✅ Task completed — waiting for your input")
        self.assertEqual(result["project"], "codex-proj")

    @patch("notify._detect_project_context", return_value="codex-proj")
    @patch("notify._read_stdin", return_value='{"hook_event_name":"PermissionRequest","tool_name":"shell","tool_input":{"command":"ls -la"}}')
    def test_codex_permission_request(self, mock_stdin, mock_ctx):
        result = notify.parse_input(["--platform=codex"])
        self.assertEqual(result["platform"], "codex")
        self.assertEqual(result["event"], "PermissionRequest")
        self.assertEqual(result["message"], "🔐 Permission required (shell: ls -la)")

    @patch("notify._detect_project_context", return_value="codex-proj")
    @patch("notify._read_stdin", return_value='{"type":"agent-turn-complete","message":"Done"}')
    def test_codex_legacy_has_project(self, mock_stdin, mock_ctx):
        result = notify.parse_input([])
        self.assertEqual(result["platform"], "codex")
        self.assertEqual(result["project"], "codex-proj")

    @patch("notify._detect_project_context", return_value="oc-proj")
    @patch("notify._read_stdin", return_value='{"platform":"opencode","event_type":"session.execution.succeeded"}')
    def test_opencode_v2_execution_succeeded(self, mock_stdin, mock_ctx):
        result = notify.parse_input(["--platform", "opencode"])
        self.assertEqual(result["platform"], "opencode")
        self.assertEqual(result["event"], "session.execution.succeeded")
        self.assertEqual(result["message"], "✅ Task completed — waiting for your input")
        self.assertEqual(result["project"], "oc-proj")

    @patch("notify._detect_project_context", return_value="oc-proj")
    @patch("notify._read_stdin", return_value='{"platform":"opencode","event_type":"session.execution.failed","message":"502 Bad Gateway"}')
    def test_opencode_v2_execution_failed(self, mock_stdin, mock_ctx):
        result = notify.parse_input(["--platform", "opencode"])
        self.assertEqual(result["platform"], "opencode")
        self.assertEqual(result["event"], "session.execution.failed")
        self.assertEqual(result["message"], "❌ Execution failed: 502 Bad Gateway")

    @patch("notify._detect_project_context", return_value="oc-proj")
    @patch("notify._read_stdin", return_value='{"platform":"opencode","event_type":"permission.asked","message":"Permission required (bash)"}')
    def test_opencode_v2_permission_asked(self, mock_stdin, mock_ctx):
        result = notify.parse_input(["--platform", "opencode"])
        self.assertEqual(result["platform"], "opencode")
        self.assertEqual(result["event"], "permission.asked")
        self.assertEqual(result["message"], "🔐 Permission required (bash)")

    @patch("notify._detect_project_context", return_value="oc-proj")
    @patch("notify._read_stdin", return_value='{"platform":"opencode","event_type":"form.created","message":"Waiting for your answer: Pick branch"}')
    def test_opencode_v2_form_created(self, mock_stdin, mock_ctx):
        result = notify.parse_input(["--platform", "opencode"])
        self.assertEqual(result["platform"], "opencode")
        self.assertEqual(result["event"], "form.created")
        self.assertEqual(result["message"], "❓ Waiting for your answer: Pick branch")

    @patch("notify._detect_project_context", return_value="my-project")
    @patch("notify._read_stdin", return_value='{"reason":"complete","cwd":"/dev/my-project"}')
    def test_copilot_session_end_has_project(self, mock_stdin, mock_ctx):
        result = notify.parse_input([])
        self.assertEqual(result["platform"], "copilot_cli")
        self.assertEqual(result["event"], "sessionEnd")
        self.assertEqual(result["project"], "my-project")

    @patch("notify._detect_project_context", return_value="repo")
    @patch("notify._read_stdin", return_value='{"toolName":"bash","toolResult":{"resultType":"success"}}')
    def test_copilot_post_tool_use_has_project(self, mock_stdin, mock_ctx):
        result = notify.parse_input([])
        self.assertEqual(result["platform"], "copilot_cli")
        self.assertEqual(result["event"], "postToolUse")
        self.assertEqual(result["project"], "repo")

    @patch("notify._detect_project_context", return_value="repo")
    @patch("notify._read_stdin", return_value='{"source":"terminal"}')
    def test_copilot_session_start_has_project(self, mock_stdin, mock_ctx):
        result = notify.parse_input([])
        self.assertEqual(result["platform"], "copilot_cli")
        self.assertEqual(result["event"], "sessionStart")
        self.assertEqual(result["project"], "repo")

    @patch("notify._detect_project_context", return_value="cur-proj")
    @patch("notify._read_stdin", return_value='{"hook_event_name":"stop","status":"completed","agent":"cursor"}')
    def test_cursor_has_project(self, mock_stdin, mock_ctx):
        result = notify.parse_input([])
        self.assertEqual(result["platform"], "cursor")
        self.assertEqual(result["message"], "Task completed")
        self.assertEqual(result["project"], "cur-proj")

    @patch("notify._detect_project_context", return_value="proj")
    @patch("notify._read_stdin", return_value="")
    def test_empty_stdin_has_project(self, mock_stdin, mock_ctx):
        result = notify.parse_input([])
        self.assertEqual(result["platform"], "unknown")
        self.assertIn("project", result)

    @patch("notify._detect_project_context", return_value="proj")
    @patch("notify._read_stdin", return_value="")
    def test_aider_argv_has_project(self, mock_stdin, mock_ctx):
        result = notify.parse_input(["Task", "done"])
        self.assertEqual(result["platform"], "aider")
        self.assertEqual(result["message"], "Task done")
        self.assertIn("project", result)

    @patch("notify._detect_project_context", return_value="proj")
    @patch("notify._read_stdin", return_value="plain text message")
    def test_non_json_stdin_has_project(self, mock_stdin, mock_ctx):
        result = notify.parse_input([])
        self.assertEqual(result["platform"], "unknown")
        self.assertEqual(result["message"], "plain text message")
        self.assertIn("project", result)

    @patch("notify._detect_project_context", return_value="proj")
    @patch("notify._read_stdin", return_value='{"some":"unknown","data":true}')
    def test_fallback_json_has_project(self, mock_stdin, mock_ctx):
        result = notify.parse_input([])
        self.assertEqual(result["platform"], "unknown")
        self.assertIn("project", result)


class TestMainSkip(unittest.TestCase):
    """Tests that main() exits cleanly without dispatching when skip=True."""

    @patch("notify.load_config")
    @patch("notify.parse_input", return_value={"platform": "claude_code", "event": "Stop", "message": "", "skip": True})
    def test_main_skips_dispatch(self, mock_parse, mock_load):
        rc = notify.main()
        self.assertEqual(rc, 0)
        mock_load.assert_not_called()


class TestSendTelegram(unittest.TestCase):
    """Tests for send_telegram() proxy and plain-text handling."""

    @patch("notify.subprocess.run")
    def test_uses_curl_when_socks5_proxy_configured(self, mock_run):
        cfg = {
            "bot_token": "123:abc",
            "chat_id": "456",
            "proxy": "socks5://127.0.0.1:7898",
        }
        event_info = {
            "platform": "claude_code",
            "event": "Stop",
            "message": "Done_with_[brackets]",
            "project": "my_repo",
        }
        notify.send_telegram(cfg, event_info)
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        self.assertIn("--socks5-hostname", cmd)
        self.assertIn("127.0.0.1:7898", cmd)

    @patch("notify.urlopen")
    def test_uses_urlopen_without_proxy(self, mock_urlopen):
        with patch.dict(os.environ, {}, clear=True):
            cfg = {"bot_token": "123:abc", "chat_id": "456"}
            event_info = {"platform": "codex", "event": "Stop", "message": "Done"}
            notify.send_telegram(cfg, event_info)
            mock_urlopen.assert_called_once()


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
        self.assertIn("Agent_Notifier", sent_msg)
        self.assertNotIn("[my-proj]", sent_msg)


class TestSendDingtalk(unittest.TestCase):
    """Tests for send_dingtalk()."""

    @patch("notify.urlopen")
    def test_sends_markdown_with_valid_config(self, mock_urlopen):
        cfg = {"webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=abc"}
        event_info = {
            "platform": "claude_code",
            "event": "idle_prompt",
            "message": "Task completed",
            "project": "my-app",
        }
        notify.send_dingtalk(cfg, event_info)
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        body = json.loads(req.data.decode())
        self.assertEqual(body["msgtype"], "markdown")
        self.assertIn("my-app", body["markdown"]["text"])

    @patch("notify.urlopen")
    def test_returns_early_without_webhook_url(self, mock_urlopen):
        cfg = {"webhook_url": ""}
        event_info = {
            "platform": "claude_code",
            "event": "idle_prompt",
            "message": "Task completed",
        }
        notify.send_dingtalk(cfg, event_info)
        mock_urlopen.assert_not_called()

    @patch("notify.urlopen")
    @patch("notify.time.time", return_value=1700000000.0)
    def test_signs_request_when_secret_configured(self, mock_time, mock_urlopen):
        cfg = {
            "webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=abc",
            "secret": "SEC123456",
        }
        event_info = {
            "platform": "claude_code",
            "event": "idle_prompt",
            "message": "Done",
        }
        notify.send_dingtalk(cfg, event_info)
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        url = req.full_url
        self.assertIn("timestamp=1700000000000", url)
        self.assertIn("sign=", url)


class TestSetupInstallers(unittest.TestCase):
    """Tests for non-destructive hook installation in setup.py."""

    def test_claude_installer_preserves_existing_hooks_and_dedupes(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = os.path.join(tmp, "settings.json")
            initial = {
                "model": "sonnet",
                "hooks": {
                    "Stop": [
                        {"hooks": [{"type": "command", "command": "/path/to/orca-hook.sh"}]}
                    ],
                    "Notification": [
                        {"matcher": "", "hooks": [{"type": "command", "command": "python3 /old/agent-notifier/notify.py"}]}
                    ],
                },
            }
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(initial, f)

            setup.install_claude_code_hooks(
                notify_script="/new/agent-notifier/notify.py",
                settings_path=settings_path,
            )
            # Run a second time to verify idempotency
            setup.install_claude_code_hooks(
                notify_script="/new/agent-notifier/notify.py",
                settings_path=settings_path,
            )

            with open(settings_path, "r", encoding="utf-8") as f:
                updated = json.load(f)

            self.assertEqual(updated["model"], "sonnet")
            # Orca hook preserved + 1 agent-notifier hook added
            self.assertEqual(len(updated["hooks"]["Stop"]), 2)
            self.assertEqual(updated["hooks"]["Stop"][0]["hooks"][0]["command"], "/path/to/orca-hook.sh")
            self.assertIn("--platform claude_code", updated["hooks"]["Stop"][1]["hooks"][0]["command"])
            # Old Notification entry replaced (not duplicated)
            self.assertEqual(len(updated["hooks"]["Notification"]), 1)
            self.assertIn("/new/agent-notifier/notify.py", updated["hooks"]["Notification"][0]["hooks"][0]["command"])
            self.assertIn("StopFailure", updated["hooks"])
            self.assertIn("PermissionRequest", updated["hooks"])

    def test_codex_installer_enables_feature_and_merges_hooks(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_toml = os.path.join(tmp, "config.toml")
            hooks_json = os.path.join(tmp, "hooks.json")
            with open(config_toml, "w", encoding="utf-8") as f:
                f.write('model = "gpt-5"\n\n[features]\nhooks = false\n')
            with open(hooks_json, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "hooks": {
                            "Stop": [
                                {"_otty": True, "hooks": [{"type": "command", "command": "otty-hook.sh"}]}
                            ]
                        }
                    },
                    f,
                )

            setup.install_codex_hooks(
                notify_script="/skills/agent-notifier/notify.py",
                codex_dir=tmp,
            )

            with open(config_toml, "r", encoding="utf-8") as f:
                toml_text = f.read()
            self.assertIn("hooks = true", toml_text)

            with open(hooks_json, "r", encoding="utf-8") as f:
                hooks_data = json.load(f)
            self.assertEqual(len(hooks_data["hooks"]["Stop"]), 2)
            self.assertEqual(hooks_data["hooks"]["Stop"][0]["_otty"], True)
            self.assertIn("--platform codex", hooks_data["hooks"]["Stop"][1]["hooks"][0]["command"])
            self.assertEqual(len(hooks_data["hooks"]["PermissionRequest"]), 1)

    @patch("setup._command_exists", return_value=False)
    def test_opencode_installer_removes_legacy_ts_and_copies_js(self, _mock_cmd):
        with tempfile.TemporaryDirectory() as tmp:
            legacy_ts = os.path.join(tmp, "agent-notifier.ts")
            with open(legacy_ts, "w", encoding="utf-8") as f:
                f.write("// legacy")

            setup.install_opencode_hooks(plugins_dir=tmp)

            self.assertFalse(os.path.exists(legacy_ts))
            installed_js = os.path.join(tmp, "agent-notifier.js")
            self.assertTrue(os.path.isfile(installed_js))
            with open(installed_js, "r", encoding="utf-8") as f:
                js_text = f.read()
            self.assertIn('id: "agent-notifier"', js_text)
            self.assertIn("setup:", js_text)


if __name__ == "__main__":
    unittest.main()
