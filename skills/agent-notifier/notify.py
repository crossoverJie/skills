#!/usr/bin/env python3
"""Multi-platform, multi-channel notification script for AI code agents.

Reads hook input from stdin (JSON) or command-line arguments, normalizes it
into a unified event model, and dispatches notifications to all enabled
channels concurrently.

Requires only the Python standard library (no pip dependencies).
"""

import base64
import hashlib
import hmac
import json
import os
import platform
import smtplib
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from email.mime.text import MIMEText
from urllib.parse import quote_plus
from urllib.request import ProxyHandler, Request, build_opener, urlopen

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_SEARCH_PATHS = [
    os.path.expanduser("~/.claude/notify-config.json"),
    os.path.join(SCRIPT_DIR, "notify-config.json"),
]

# ---------------------------------------------------------------------------
# Input parsing – each platform sends a different JSON schema via stdin
# ---------------------------------------------------------------------------

PLATFORM_LABELS = {
    "claude_code": "Claude Code",
    "copilot_cli": "GitHub Copilot CLI",
    "cursor": "Cursor",
    "codex": "Codex",
    "aider": "Aider",
    "opencode": "OpenCode",
    "unknown": "AI Agent",
}

PLATFORM_ALIASES = {
    "claude": "claude_code",
    "claude-code": "claude_code",
    "claude_code": "claude_code",
    "copilot": "copilot_cli",
    "copilot-cli": "copilot_cli",
    "copilot_cli": "copilot_cli",
    "cursor": "cursor",
    "codex": "codex",
    "aider": "aider",
    "opencode": "opencode",
}


def _read_stdin():
    """Read all of stdin if available, return empty string otherwise."""
    if sys.stdin.isatty():
        return ""
    try:
        return sys.stdin.read()
    except Exception:
        return ""


def _parse_cli_args(argv=None):
    """Extract ``--platform <name>`` flag and remaining positional args."""
    args = list(sys.argv[1:] if argv is None else argv)
    platform_hint = None
    positional = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--platform" and i + 1 < len(args):
            raw_plat = args[i + 1].strip().lower()
            platform_hint = PLATFORM_ALIASES.get(raw_plat, raw_plat)
            i += 2
        elif arg.startswith("--platform="):
            raw_plat = arg.split("=", 1)[1].strip().lower()
            platform_hint = PLATFORM_ALIASES.get(raw_plat, raw_plat)
            i += 1
        else:
            positional.append(arg)
            i += 1
    return platform_hint, positional


def _has_running_subagent(data):
    """Return True if a Stop payload indicates a background subagent is still running."""
    tasks = data.get("background_tasks")
    if not isinstance(tasks, list):
        return False
    for task in tasks:
        if (
            isinstance(task, dict)
            and task.get("type") == "subagent"
            and task.get("status") == "running"
        ):
            return True
    return False


def _format_permission_message(data):
    """Format a concise PermissionRequest message from tool metadata."""
    tool = data.get("tool_name") or data.get("toolName") or data.get("permission") or ""
    tool_input = data.get("tool_input") if isinstance(data.get("tool_input"), dict) else {}
    preview = ""
    if tool_input:
        preview = (
            tool_input.get("command")
            or tool_input.get("file_path")
            or tool_input.get("path")
            or ""
        )
        if isinstance(preview, str):
            preview = " ".join(preview.split())
            if len(preview) > 60:
                preview = preview[:57] + "..."
        else:
            preview = ""

    if tool and preview:
        return f"🔐 Permission required ({tool}: {preview})"
    if tool:
        return f"🔐 Permission required ({tool})"
    return "🔐 Permission required"


def parse_input(argv=None):
    """Parse hook input from stdin/argv into a unified event dict.

    Returns ``{"platform": str, "event": str, "message": str, "project": str}``,
    possibly with ``"skip": True`` when an intermediate event should be suppressed.
    """
    platform_hint, positional = _parse_cli_args(argv)
    raw = _read_stdin().strip()

    # Fallback: command-line arguments (used by Aider)
    if not raw and positional:
        plat = platform_hint or "aider"
        result = {
            "platform": plat,
            "event": "notification",
            "message": " ".join(positional),
        }
        result["project"] = _detect_project_context({}, plat)
        return result

    if not raw:
        plat = platform_hint or "unknown"
        result = {"platform": plat, "event": "notification", "message": ""}
        result["project"] = _detect_project_context({}, plat)
        return result

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Non-JSON stdin – treat the text as a plain message
        plat = platform_hint or "unknown"
        result = {"platform": plat, "event": "notification", "message": raw}
        result["project"] = _detect_project_context({}, plat)
        return result

    if not isinstance(data, dict):
        plat = platform_hint or "unknown"
        result = {"platform": plat, "event": "notification", "message": str(data)}
        result["project"] = _detect_project_context({}, plat)
        return result

    # --- OpenCode (1.x and 2.x plugin payloads) ---
    if data.get("platform") == "opencode" or platform_hint == "opencode":
        event_type = data.get("event_type") or data.get("event") or "notification"
        custom_msg = data.get("message", "")
        event_messages = {
            "session.idle": "✅ Session completed — waiting for your input",
            "session.execution.succeeded": "✅ Task completed — waiting for your input",
            "session.execution.failed": (
                f"❌ Execution failed: {custom_msg}" if custom_msg else "❌ Execution failed"
            ),
            "session.error": (
                f"❌ Session error: {custom_msg}" if custom_msg else "❌ Session error occurred"
            ),
            "permission.asked": (
                f"🔐 {custom_msg}" if custom_msg and not custom_msg.startswith("🔐")
                else (custom_msg or "🔐 Permission required")
            ),
            "form.created": (
                f"❓ {custom_msg}" if custom_msg and not custom_msg.startswith("❓")
                else (custom_msg or "❓ Waiting for your answer")
            ),
            "question.asked": (
                f"❓ {custom_msg}" if custom_msg and not custom_msg.startswith("❓")
                else (custom_msg or "❓ Waiting for your answer")
            ),
        }
        event_msg = event_messages.get(event_type, custom_msg or event_type)
        result = {"platform": "opencode", "event": event_type, "message": event_msg}
        result["project"] = _detect_project_context(data, "opencode")
        return result

    # --- Claude Code Notification hook (notification_type) ---
    if "notification_type" in data:
        ntype = data["notification_type"]
        msg = data.get("message", "")
        if ntype == "idle_prompt":
            event_msg = "⏳ Waiting for your input"
        elif ntype == "permission_prompt":
            event_msg = f"🔐 {msg}" if msg else "🔐 Permission required"
        elif ntype == "elicitation_dialog":
            event_msg = f"❓ {msg}" if msg else "❓ Input required"
        elif ntype == "auth_success":
            event_msg = "✅ Authentication succeeded"
        else:
            event_msg = msg or ntype
        plat = platform_hint or "claude_code"
        result = {"platform": plat, "event": ntype, "message": event_msg}
        result["project"] = _detect_project_context(data, plat)
        return result

    # --- Structured hook_event_name (Claude Code 2.x, Codex hooks.json, Cursor, Copilot) ---
    hook_event = data.get("hook_event_name", "")
    if hook_event:
        if platform_hint:
            plat = platform_hint
        elif "cursor" in str(data.get("agent", "")).lower():
            plat = "cursor"
        elif any(k in data for k in ("stop_hook_active", "transcript_path", "permission_mode")):
            plat = "claude_code"
        elif "codex_turn_id" in data:
            plat = "codex"
        elif hook_event in ("Stop", "StopFailure", "PermissionRequest", "Notification"):
            plat = "claude_code"
        else:
            plat = "copilot_cli"

        skip = False
        if hook_event in ("Stop", "stop"):
            if data.get("stop_hook_active") is True or _has_running_subagent(data):
                skip = True
            status = data.get("status", "")
            if plat == "cursor":
                event_msg = "Task completed" if status == "completed" else "Session ended"
            else:
                event_msg = "✅ Task completed — waiting for your input"
        elif hook_event == "StopFailure":
            err_type = data.get("error", "")
            detail = f" ({err_type})" if err_type else ""
            event_msg = f"❌ Task failed{detail} — intervention needed"
        elif hook_event == "PermissionRequest":
            event_msg = _format_permission_message(data)
        elif hook_event in ("AskUserQuestion", "Elicitation"):
            msg = data.get("message", "")
            event_msg = f"❓ {msg}" if msg else "❓ Waiting for your input"
        elif hook_event == "Notification":
            msg = data.get("message", "")
            event_msg = msg or "🔔 Waiting for your input"
        elif hook_event == "sessionEnd":
            status = data.get("status", "")
            event_msg = "Task completed" if status == "completed" else "Session ended"
        elif hook_event in ("SessionEnd", "Interrupt"):
            reason = data.get("reason", "")
            if hook_event == "Interrupt":
                event_msg = "⚠️ Task interrupted — waiting for your input"
            else:
                event_msg = f"Session ended ({reason})" if reason else "Session ended"
        elif hook_event in ("postToolUse", "PostToolUse"):
            tool = data.get("tool_name") or data.get("toolName") or "tool"
            event_msg = f"Tool '{tool}' finished"
        elif hook_event == "PostToolUseFailure":
            tool = data.get("tool_name") or data.get("toolName") or "tool"
            event_msg = f"❌ Tool '{tool}' failed"
        elif hook_event == "afterFileEdit":
            file = data.get("file_path", "file")
            event_msg = f"Edited {os.path.basename(file)}"
        else:
            event_msg = data.get("message") or hook_event

        result = {"platform": plat, "event": hook_event, "message": event_msg}
        if skip:
            result["skip"] = True
        result["project"] = _detect_project_context(data, plat)
        return result

    # --- Platform-hinted payloads without hook_event_name (e.g. Codex hooks.json) ---
    if platform_hint in ("codex", "claude_code"):
        if "tool_name" in data or "permission" in data:
            event_name = "PermissionRequest"
            event_msg = _format_permission_message(data)
        elif "error" in data and not data.get("last_assistant_message", "").startswith("✅"):
            err_type = data.get("error", "")
            detail = f" ({err_type})" if isinstance(err_type, str) and err_type else ""
            event_name = "StopFailure"
            event_msg = f"❌ Task failed{detail} — intervention needed"
        else:
            event_name = "Stop"
            event_msg = "✅ Task completed — waiting for your input"

        skip = data.get("stop_hook_active") is True or _has_running_subagent(data)
        result = {"platform": platform_hint, "event": event_name, "message": event_msg}
        if skip:
            result["skip"] = True
        result["project"] = _detect_project_context(data, platform_hint)
        return result

    # --- Copilot CLI (field-signature detection) ---
    # sessionEnd: payload contains "reason" (complete/error/abort/timeout/user_exit)
    if "reason" in data and "toolName" not in data:
        reason = data["reason"]
        reason_messages = {
            "complete": "Task completed",
            "error": "Session ended with error",
            "abort": "Session aborted",
            "timeout": "Session timed out",
            "user_exit": "User exited session",
        }
        event_msg = reason_messages.get(reason, f"Session ended ({reason})")
        plat = platform_hint or "copilot_cli"
        result = {"platform": plat, "event": "sessionEnd", "message": event_msg}
        result["project"] = _detect_project_context(data, plat)
        return result

    # postToolUse: payload contains "toolName" + "toolResult"
    if "toolName" in data and "toolResult" in data:
        tool = data["toolName"]
        result_data = data["toolResult"]
        result_type = result_data.get("resultType", "") if isinstance(result_data, dict) else ""
        result_messages = {
            "success": f"Tool '{tool}' completed successfully",
            "failure": f"Tool '{tool}' failed",
            "denied": f"Tool '{tool}' was denied",
        }
        event_msg = result_messages.get(result_type, f"Tool '{tool}' finished")
        plat = platform_hint or "copilot_cli"
        result = {"platform": plat, "event": "postToolUse", "message": event_msg}
        result["project"] = _detect_project_context(data, plat)
        return result

    # sessionStart: payload contains "source" but no "toolName"
    if "source" in data and "toolName" not in data and "notification_type" not in data:
        source = data["source"]
        event_msg = f"Session started ({source})"
        plat = platform_hint or "copilot_cli"
        result = {"platform": plat, "event": "sessionStart", "message": event_msg}
        result["project"] = _detect_project_context(data, plat)
        return result

    # --- Legacy Codex ---
    if "agent-turn-complete" in data or data.get("type") == "agent-turn-complete":
        result = {
            "platform": "codex",
            "event": "agent-turn-complete",
            "message": data.get("message", "✅ Task completed — waiting for your input"),
        }
        result["project"] = _detect_project_context(data, "codex")
        return result

    # Fallback
    plat = platform_hint or "unknown"
    result = {
        "platform": plat,
        "event": "notification",
        "message": data.get("message", json.dumps(data, ensure_ascii=False)),
    }
    result["project"] = _detect_project_context(data, plat)
    return result


# ---------------------------------------------------------------------------
# Project context detection
# ---------------------------------------------------------------------------

def _get_git_repo_name(directory):
    """Return the basename of the git repo root for *directory*, or ``""``."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=directory,
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode == 0 and result.stdout.strip():
            return os.path.basename(result.stdout.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return ""


def _detect_project_context(data, _platform):
    """Return a short project identifier string, or ``""`` if unknown.

    Resolution order:
    1. ``cwd`` or ``directory`` field in the JSON payload
    2. ``os.getcwd()`` (hook subprocess inherits the parent's cwd)
    3. Try ``_get_git_repo_name()`` on the resolved directory
    4. Fall back to ``os.path.basename(cwd)``
    """
    try:
        cwd = ""
        if isinstance(data, dict):
            cwd = data.get("cwd") or data.get("directory") or ""
        if not cwd:
            cwd = os.getcwd()

        repo = _get_git_repo_name(cwd)
        if repo:
            return repo

        name = os.path.basename(cwd.rstrip("/\\"))
        return name if name else ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def load_config():
    """Load the first existing notify-config.json from the search path."""
    for path in CONFIG_SEARCH_PATHS:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    # Return minimal defaults so the script always works
    return {
        "channels": {
            "sound": {"enabled": True, "file": "/System/Library/Sounds/Glass.aiff"},
            "macos_notification": {"enabled": True},
        }
    }


# ---------------------------------------------------------------------------
# Notification channels
# ---------------------------------------------------------------------------

def _format_title(event_info):
    label = PLATFORM_LABELS.get(event_info["platform"], event_info["platform"])
    return f"Agent Notifier — {label}"


def _format_body(event_info):
    body = event_info["message"] or event_info["event"]
    project = event_info.get("project", "")
    if project:
        return f"[{project}] {body}"
    return body


def send_sound(cfg, _event_info):
    """Play a notification sound."""
    sound_file = cfg.get("file", "/System/Library/Sounds/Glass.aiff")
    system = platform.system()
    if system == "Darwin":
        subprocess.Popen(
            ["afplay", sound_file],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    elif system == "Linux":
        # Try paplay (PulseAudio), then aplay (ALSA)
        for player in ("paplay", "aplay"):
            try:
                subprocess.Popen(
                    [player, sound_file],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                break
            except FileNotFoundError:
                continue


def send_macos_notification(cfg, event_info):
    """Send a macOS notification centre alert via osascript."""
    if platform.system() != "Darwin":
        return
    title = _format_title(event_info)
    body = _format_body(event_info).replace("\\", "\\\\").replace('"', '\\"')
    title = title.replace("\\", "\\\\").replace('"', '\\"')
    script = f'display notification "{body}" with title "{title}"'
    subprocess.Popen(
        ["osascript", "-e", script],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def send_telegram(cfg, event_info):
    """Send a Telegram message via Bot API."""
    token = cfg.get("bot_token", "")
    chat_id = cfg.get("chat_id", "")
    if not token or not chat_id:
        return
    title = _format_title(event_info)
    body = _format_body(event_info)
    # Send plain text to avoid Telegram Markdown parse errors on underscores/brackets
    text = f"{title}\n{body}"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text})

    proxy = (
        cfg.get("proxy")
        or os.environ.get("all_proxy")
        or os.environ.get("ALL_PROXY")
        or ""
    ).strip()

    if "socks5" in proxy.lower():
        proxy_addr = proxy.split("://", 1)[-1] if "://" in proxy else proxy
        subprocess.run(
            [
                "curl", "-s", "--socks5-hostname", proxy_addr,
                "--connect-timeout", "4", "--max-time", "6",
                "-X", "POST", url,
                "-H", "Content-Type: application/json",
                "-d", payload,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=8,
        )
        return

    req = Request(url, data=payload.encode(), headers={"Content-Type": "application/json"})
    if proxy:
        opener = build_opener(ProxyHandler({"http": proxy, "https": proxy}))
        opener.open(req, timeout=6)
    else:
        urlopen(req, timeout=6)


def send_email(cfg, event_info):
    """Send an email notification via SMTP."""
    host = cfg.get("smtp_host", "")
    port = cfg.get("smtp_port", 587)
    username = cfg.get("username", "")
    password = cfg.get("password", "")
    from_addr = cfg.get("from_addr", username)
    to_addr = cfg.get("to_addr", "")
    if not all([host, username, password, to_addr]):
        return
    title = _format_title(event_info)
    body = _format_body(event_info)
    msg = MIMEText(body)
    msg["Subject"] = f"[Agent Notifier] {title}"
    project = event_info.get("project", "")
    if project:
        msg["Subject"] = f"[Agent Notifier] [{project}] {title}"
    msg["From"] = from_addr
    msg["To"] = to_addr
    with smtplib.SMTP(host, port, timeout=8) as server:
        server.starttls()
        server.login(username, password)
        server.sendmail(from_addr, [to_addr], msg.as_string())


def send_slack(cfg, event_info):
    """Send a Slack message via incoming webhook."""
    webhook_url = cfg.get("webhook_url", "")
    if not webhook_url:
        return
    title = _format_title(event_info)
    body = _format_body(event_info)
    payload = json.dumps({"text": f"*{title}*\n{body}"}).encode()
    req = Request(webhook_url, data=payload, headers={"Content-Type": "application/json"})
    urlopen(req, timeout=8)


def send_discord(cfg, event_info):
    """Send a Discord message via webhook."""
    webhook_url = cfg.get("webhook_url", "")
    if not webhook_url:
        return
    title = _format_title(event_info)
    body = _format_body(event_info)
    payload = json.dumps({"content": f"**{title}**\n{body}"}).encode()
    req = Request(webhook_url, data=payload, headers={"Content-Type": "application/json"})
    urlopen(req, timeout=8)


def send_dingtalk(cfg, event_info):
    """Send a DingTalk (钉钉) message via group robot webhook."""
    webhook_url = cfg.get("webhook_url", "")
    if not webhook_url:
        return
    title = _format_title(event_info)
    body = _format_body(event_info)
    # Optional HMAC-SHA256 signing
    secret = cfg.get("secret", "")
    if secret:
        timestamp = str(int(time.time() * 1000))
        string_to_sign = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(
            secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        sign = quote_plus(base64.b64encode(hmac_code).decode("utf-8"))
        sep = "&" if "?" in webhook_url else "?"
        webhook_url = f"{webhook_url}{sep}timestamp={timestamp}&sign={sign}"
    payload = json.dumps({
        "msgtype": "markdown",
        "markdown": {"title": title, "text": f"**{title}**\n\n{body}"},
    }).encode()
    req = Request(webhook_url, data=payload, headers={"Content-Type": "application/json"})
    urlopen(req, timeout=8)


# Map channel name → sender function
CHANNEL_SENDERS = {
    "sound": send_sound,
    "macos_notification": send_macos_notification,
    "telegram": send_telegram,
    "email": send_email,
    "slack": send_slack,
    "discord": send_discord,
    "dingtalk": send_dingtalk,
}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    event_info = parse_input()
    if event_info.get("skip"):
        return 0

    config = load_config()
    channels = config.get("channels", {})

    enabled = [
        (name, cfg)
        for name, cfg in channels.items()
        if cfg.get("enabled") and name in CHANNEL_SENDERS
    ]

    if not enabled:
        return 0

    def _dispatch(name_cfg):
        name, cfg = name_cfg
        try:
            CHANNEL_SENDERS[name](cfg, event_info)
        except Exception as exc:
            print(f"[agent-notifier] {name} failed: {exc}", file=sys.stderr)

    with ThreadPoolExecutor(max_workers=len(enabled)) as pool:
        pool.map(_dispatch, enabled)

    return 0


if __name__ == "__main__":
    sys.exit(main())
