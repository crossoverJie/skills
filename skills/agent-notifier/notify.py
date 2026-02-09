#!/usr/bin/env python3
"""Multi-platform, multi-channel notification script for AI code agents.

Reads hook input from stdin (JSON) or command-line arguments, normalizes it
into a unified event model, and dispatches notifications to all enabled
channels concurrently.

Requires only the Python standard library (no pip dependencies).
"""

import json
import os
import platform
import smtplib
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from email.mime.text import MIMEText
from urllib.error import URLError
from urllib.request import Request, urlopen

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
    "unknown": "AI Agent",
}


def _read_stdin():
    """Read all of stdin if available, return empty string otherwise."""
    if sys.stdin.isatty():
        return ""
    try:
        return sys.stdin.read()
    except Exception:
        return ""


def parse_input():
    """Parse hook input from stdin/argv into a unified event dict.

    Returns ``{"platform": str, "event": str, "message": str}``.
    """
    raw = _read_stdin().strip()

    # Fallback: command-line arguments (used by Aider)
    if not raw and len(sys.argv) > 1:
        return {
            "platform": "aider",
            "event": "notification",
            "message": " ".join(sys.argv[1:]),
        }

    if not raw:
        return {"platform": "unknown", "event": "notification", "message": ""}

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Non-JSON stdin – treat the text as a plain message
        return {"platform": "unknown", "event": "notification", "message": raw}

    # --- Claude Code ---
    if "notification_type" in data:
        ntype = data["notification_type"]
        msg = data.get("message", "")
        if ntype == "idle_prompt":
            event_msg = "✅ Task completed — waiting for your input"
        elif ntype == "permission_prompt":
            event_msg = "🔐 Permission required"
        else:
            event_msg = msg or ntype
        return {"platform": "claude_code", "event": ntype, "message": event_msg}

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
        return {"platform": "copilot_cli", "event": "sessionEnd", "message": event_msg}

    # postToolUse: payload contains "toolName" + "toolResult"
    if "toolName" in data and "toolResult" in data:
        tool = data["toolName"]
        result = data["toolResult"]
        result_type = result.get("resultType", "") if isinstance(result, dict) else ""
        result_messages = {
            "success": f"Tool '{tool}' completed successfully",
            "failure": f"Tool '{tool}' failed",
            "denied": f"Tool '{tool}' was denied",
        }
        event_msg = result_messages.get(result_type, f"Tool '{tool}' finished")
        return {"platform": "copilot_cli", "event": "postToolUse", "message": event_msg}

    # sessionStart: payload contains "source" but no "toolName"
    if "source" in data and "toolName" not in data and "notification_type" not in data:
        source = data["source"]
        event_msg = f"Session started ({source})"
        return {"platform": "copilot_cli", "event": "sessionStart", "message": event_msg}

    # --- Cursor / other platforms (hook_event_name) ---
    hook_event = data.get("hook_event_name", "")
    if hook_event:
        status = data.get("status", "")
        if hook_event in ("sessionEnd", "stop"):
            event_msg = "Task completed" if status == "completed" else "Session ended"
        elif hook_event == "postToolUse":
            tool = data.get("tool_name", "tool")
            event_msg = f"Tool '{tool}' finished"
        elif hook_event == "afterFileEdit":
            file = data.get("file_path", "file")
            event_msg = f"Edited {os.path.basename(file)}"
        else:
            event_msg = hook_event

        plat = "cursor" if "cursor" in data.get("agent", "").lower() else "copilot_cli"
        return {"platform": plat, "event": hook_event, "message": event_msg}

    # --- Codex ---
    if "agent-turn-complete" in data or data.get("type") == "agent-turn-complete":
        return {
            "platform": "codex",
            "event": "agent-turn-complete",
            "message": data.get("message", "Agent turn completed"),
        }

    # Fallback
    return {
        "platform": "unknown",
        "event": "notification",
        "message": data.get("message", json.dumps(data, ensure_ascii=False)),
    }


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
    return event_info["message"] or event_info["event"]


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
    body = _format_body(event_info).replace('"', '\\"')
    title = title.replace('"', '\\"')
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
    text = f"*{title}*\n{body}"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}).encode()
    req = Request(url, data=payload, headers={"Content-Type": "application/json"})
    urlopen(req, timeout=10)


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
    msg["From"] = from_addr
    msg["To"] = to_addr
    with smtplib.SMTP(host, port, timeout=10) as server:
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
    urlopen(req, timeout=10)


def send_discord(cfg, event_info):
    """Send a Discord message via webhook."""
    webhook_url = cfg.get("webhook_url", "")
    if not webhook_url:
        return
    title = _format_title(event_info)
    body = _format_body(event_info)
    payload = json.dumps({"content": f"**{title}**\n{body}"}).encode()
    req = Request(webhook_url, data=payload, headers={"Content-Type": "application/json"})
    urlopen(req, timeout=10)


# Map channel name → sender function
CHANNEL_SENDERS = {
    "sound": send_sound,
    "macos_notification": send_macos_notification,
    "telegram": send_telegram,
    "email": send_email,
    "slack": send_slack,
    "discord": send_discord,
}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    event_info = parse_input()
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
