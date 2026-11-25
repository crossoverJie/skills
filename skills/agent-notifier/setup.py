#!/usr/bin/env python3
"""Interactive setup script for agent-notifier.

Detects installed AI agent platforms, guides channel configuration,
writes hook configs, and sends a test notification.

Requires only the Python standard library.
"""

import json
import os
import re
import shutil
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
NOTIFY_SCRIPT = os.path.join(SCRIPT_DIR, "notify.py")
DEFAULT_CONFIG_PATH = os.path.expanduser("~/.claude/notify-config.json")
TEMPLATE_CONFIG = os.path.join(SCRIPT_DIR, "notify-config.json")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _input(prompt, default=""):
    """Prompt with a default value shown in brackets."""
    suffix = f" [{default}]" if default else ""
    result = input(f"{prompt}{suffix}: ").strip()
    return result or default


def _confirm(prompt, default=True):
    hint = "Y/n" if default else "y/N"
    result = input(f"{prompt} ({hint}): ").strip().lower()
    if not result:
        return default
    return result in ("y", "yes")


def _command_exists(cmd):
    return shutil.which(cmd) is not None


def _is_agent_notifier_entry(entry):
    """Return True if a hook entry invokes agent-notifier's notify.py."""
    if not isinstance(entry, dict):
        return False
    for hook in entry.get("hooks", []):
        if isinstance(hook, dict):
            cmd = hook.get("command") or hook.get("bash") or ""
            if "agent-notifier/notify.py" in cmd or cmd.endswith("notify.py"):
                return True
    cmd = entry.get("command") or entry.get("bash") or ""
    return "agent-notifier/notify.py" in cmd or cmd.endswith("notify.py")


def _upsert_hook_entry(event_list, new_entry):
    """Append *new_entry* to *event_list* after removing stale agent-notifier entries."""
    filtered = [e for e in event_list if not _is_agent_notifier_entry(e)]
    filtered.append(new_entry)
    return filtered


# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

PLATFORMS = {
    "claude_code": "Claude Code",
    "codex": "Codex",
    "opencode": "OpenCode",
    "copilot_cli": "GitHub Copilot CLI",
    "cursor": "Cursor",
    "aider": "Aider",
}


def detect_platforms():
    """Return a dict of platform_key -> bool for detected platforms."""
    found = {}

    # Claude Code
    claude_settings = os.path.expanduser("~/.claude/settings.json")
    found["claude_code"] = (
        _command_exists("claude")
        or os.path.isfile(claude_settings)
        or os.path.isdir(os.path.expanduser("~/.claude"))
    )

    # Codex
    found["codex"] = _command_exists("codex") or os.path.isdir(
        os.path.expanduser("~/.codex")
    )

    # OpenCode
    found["opencode"] = _command_exists("opencode") or os.path.isdir(
        os.path.expanduser("~/.config/opencode")
    )

    # Copilot CLI
    found["copilot_cli"] = _command_exists("copilot")

    # Cursor
    found["cursor"] = os.path.isdir(os.path.expanduser("~/.cursor"))

    # Aider
    found["aider"] = _command_exists("aider")

    return found


# ---------------------------------------------------------------------------
# Channel configuration
# ---------------------------------------------------------------------------

def configure_channels(config):
    """Interactively configure notification channels."""
    channels = config.setdefault("channels", {})

    print("\n--- Notification Channels ---\n")

    # Sound
    print("1. Sound notification")
    enabled = _confirm("   Enable sound?", default=True)
    channels["sound"] = {
        "enabled": enabled,
        "file": channels.get("sound", {}).get("file", "/System/Library/Sounds/Glass.aiff"),
    }
    if enabled:
        custom = _input("   Sound file path", channels["sound"]["file"])
        channels["sound"]["file"] = custom

    # macOS notification
    if sys.platform == "darwin":
        print("\n2. macOS Notification Center")
        enabled = _confirm("   Enable macOS notifications?", default=True)
        channels["macos_notification"] = {"enabled": enabled}
    else:
        channels.setdefault("macos_notification", {"enabled": False})

    # Telegram
    print("\n3. Telegram")
    enabled = _confirm("   Enable Telegram?", default=False)
    tg = channels.get("telegram", {"enabled": False, "bot_token": "", "chat_id": "", "proxy": ""})
    tg["enabled"] = enabled
    if enabled:
        tg["bot_token"] = _input("   Bot token (from @BotFather)", tg.get("bot_token", ""))
        tg["chat_id"] = _input("   Chat ID", tg.get("chat_id", ""))
        tg["proxy"] = _input("   Proxy URL (optional, e.g. socks5://127.0.0.1:7898)", tg.get("proxy", ""))
    channels["telegram"] = tg

    # Email
    print("\n4. Email (SMTP)")
    enabled = _confirm("   Enable email?", default=False)
    em = channels.get("email", {
        "enabled": False, "smtp_host": "smtp.gmail.com", "smtp_port": 587,
        "username": "", "password": "", "from_addr": "", "to_addr": "",
    })
    em["enabled"] = enabled
    if enabled:
        em["smtp_host"] = _input("   SMTP host", em.get("smtp_host", "smtp.gmail.com"))
        em["smtp_port"] = int(_input("   SMTP port", str(em.get("smtp_port", 587))))
        em["username"] = _input("   Username", em.get("username", ""))
        em["password"] = _input("   Password/App password", em.get("password", ""))
        em["from_addr"] = _input("   From address", em.get("from_addr", em["username"]))
        em["to_addr"] = _input("   To address", em.get("to_addr", ""))
    channels["email"] = em

    # Slack
    print("\n5. Slack (Incoming Webhook)")
    enabled = _confirm("   Enable Slack?", default=False)
    sl = channels.get("slack", {"enabled": False, "webhook_url": ""})
    sl["enabled"] = enabled
    if enabled:
        sl["webhook_url"] = _input("   Webhook URL", sl.get("webhook_url", ""))
    channels["slack"] = sl

    # Discord
    print("\n6. Discord (Webhook)")
    enabled = _confirm("   Enable Discord?", default=False)
    dc = channels.get("discord", {"enabled": False, "webhook_url": ""})
    dc["enabled"] = enabled
    if enabled:
        dc["webhook_url"] = _input("   Webhook URL", dc.get("webhook_url", ""))
    channels["discord"] = dc

    # DingTalk
    print("\n7. DingTalk (钉钉群机器人)")
    enabled = _confirm("   Enable DingTalk?", default=False)
    dt = channels.get("dingtalk", {"enabled": False, "webhook_url": "", "secret": ""})
    dt["enabled"] = enabled
    if enabled:
        dt["webhook_url"] = _input("   Webhook URL", dt.get("webhook_url", ""))
        dt["secret"] = _input("   Secret (optional, for signing)", dt.get("secret", ""))
    channels["dingtalk"] = dt

    return config


# ---------------------------------------------------------------------------
# Hook installation per platform
# ---------------------------------------------------------------------------

def install_claude_code_hooks(notify_script=NOTIFY_SCRIPT, settings_path=None):
    """Merge Stop, StopFailure, PermissionRequest, and Notification hooks into ~/.claude/settings.json."""
    if settings_path is None:
        settings_path = os.path.expanduser("~/.claude/settings.json")
    settings = {}
    if os.path.isfile(settings_path):
        with open(settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)

    hooks = settings.setdefault("hooks", {})
    notify_cmd = f"python3 {notify_script} --platform claude_code"

    event_configs = {
        "Stop": {
            "hooks": [{"type": "command", "command": notify_cmd}],
        },
        "StopFailure": {
            "hooks": [{"type": "command", "command": notify_cmd}],
        },
        "PermissionRequest": {
            "matcher": "*",
            "hooks": [{"type": "command", "command": notify_cmd}],
        },
        "Notification": {
            "matcher": "idle_prompt|elicitation_dialog",
            "hooks": [{"type": "command", "command": notify_cmd}],
        },
    }

    for event_name, entry in event_configs.items():
        existing_list = hooks.get(event_name, [])
        if not isinstance(existing_list, list):
            existing_list = []
        hooks[event_name] = _upsert_hook_entry(existing_list, entry)

    os.makedirs(os.path.dirname(settings_path), exist_ok=True)
    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"   Wrote Claude Code hooks (Stop, StopFailure, PermissionRequest, Notification) to {settings_path}")


def _ensure_codex_hooks_feature(config_toml_path):
    """Ensure ``[features] hooks = true`` is enabled in ~/.codex/config.toml."""
    if not os.path.isfile(config_toml_path):
        os.makedirs(os.path.dirname(config_toml_path), exist_ok=True)
        with open(config_toml_path, "w", encoding="utf-8") as f:
            f.write("[features]\nhooks = true\n")
        return

    with open(config_toml_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Check if [features] section exists
    features_match = re.search(r"(?m)^\[features\]\s*$", content)
    if features_match:
        start = features_match.end()
        next_sec = re.search(r"(?m)^\[", content[start:])
        end = start + next_sec.start() if next_sec else len(content)
        section_body = content[start:end]
        if re.search(r"(?m)^\s*hooks\s*=", section_body):
            updated_body = re.sub(
                r"(?m)^(\s*hooks\s*=\s*).*$",
                r"\1true",
                section_body,
            )
        else:
            updated_body = "\nhooks = true" + section_body
        content = content[:start] + updated_body + content[end:]
    else:
        if not content.endswith("\n"):
            content += "\n"
        content += "\n[features]\nhooks = true\n"

    with open(config_toml_path, "w", encoding="utf-8") as f:
        f.write(content)


def install_codex_hooks(notify_script=NOTIFY_SCRIPT, codex_dir=None):
    """Merge Stop, PermissionRequest, and Interrupt hooks into ~/.codex/hooks.json."""
    if codex_dir is None:
        codex_dir = os.path.expanduser("~/.codex")
    os.makedirs(codex_dir, exist_ok=True)

    config_toml_path = os.path.join(codex_dir, "config.toml")
    _ensure_codex_hooks_feature(config_toml_path)

    hooks_path = os.path.join(codex_dir, "hooks.json")
    data = {}
    if os.path.isfile(hooks_path):
        with open(hooks_path, "r", encoding="utf-8") as f:
            data = json.load(f)

    hooks = data.setdefault("hooks", {})
    notify_cmd = f"python3 {notify_script} --platform codex"

    for event_name in ("Stop", "PermissionRequest"):
        entry = {
            "hooks": [
                {
                    "type": "command",
                    "command": notify_cmd,
                    "timeout": 10,
                }
            ]
        }
        existing_list = hooks.get(event_name, [])
        if not isinstance(existing_list, list):
            existing_list = []
        hooks[event_name] = _upsert_hook_entry(existing_list, entry)

    with open(hooks_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"   Enabled [features].hooks in {config_toml_path}")
    print(f"   Wrote Codex hooks (Stop, PermissionRequest) to {hooks_path}")
    print("   Note: Codex may ask you to trust the new hook on next launch.")


def install_copilot_cli_hooks():
    """Install Copilot CLI hooks to .github/hooks/agent-notifier.json."""
    project_dir = _input("   Project directory for Copilot CLI hooks", os.getcwd())
    hooks_dir = os.path.join(project_dir, ".github", "hooks")
    hooks_file = os.path.join(hooks_dir, "agent-notifier.json")

    notify_cmd = f"python3 {NOTIFY_SCRIPT} --platform copilot_cli"
    hook_config = {
        "version": 1,
        "hooks": {
            "sessionEnd": [
                {"type": "command", "bash": notify_cmd}
            ],
            "postToolUse": [
                {"type": "command", "bash": notify_cmd}
            ],
        },
    }

    # Merge into existing hooks.json if present
    if os.path.isfile(hooks_file):
        with open(hooks_file, "r", encoding="utf-8") as f:
            existing = json.load(f)
        existing.setdefault("version", 1)
        existing_hooks = existing.setdefault("hooks", {})
        for event, entries in hook_config["hooks"].items():
            existing_hooks[event] = _upsert_hook_entry(
                existing_hooks.get(event, []), entries[0]
            )
        hook_config = existing

    os.makedirs(hooks_dir, exist_ok=True)
    with open(hooks_file, "w", encoding="utf-8") as f:
        json.dump(hook_config, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"   Wrote Copilot CLI hooks to {hooks_file}")


def install_cursor_hooks():
    """Print instructions for Cursor hook setup."""
    cursor_dir = os.path.expanduser("~/.cursor")
    print("   Cursor hook configuration:")
    print(f"   Add to {cursor_dir}/hooks.json:")
    print(f'   {{"stop": [{{"command": "python3 {NOTIFY_SCRIPT} --platform cursor"}}]}}')


def install_aider_hooks():
    """Print instructions for Aider notification setup."""
    print("   Aider notification configuration:")
    print("   Add to .aider.conf.yml or pass as CLI flag:")
    print(f"   notifications-command: python3 {NOTIFY_SCRIPT}")


def install_opencode_hooks(plugins_dir=None):
    """Copy the OpenCode 2.x plugin to ~/.config/opencode/plugins/ and remove legacy .ts copies."""
    if plugins_dir is None:
        plugins_dir = os.path.expanduser("~/.config/opencode/plugins")
    os.makedirs(plugins_dir, exist_ok=True)

    # Remove stale legacy TypeScript plugin file if present to avoid duplicate load errors
    legacy_ts = os.path.join(plugins_dir, "agent-notifier.ts")
    if os.path.isfile(legacy_ts):
        os.remove(legacy_ts)
        print(f"   Removed legacy plugin {legacy_ts}")

    src = os.path.join(SCRIPT_DIR, "opencode-plugin.js")
    dst = os.path.join(plugins_dir, "agent-notifier.js")
    shutil.copy2(src, dst)
    print(f"   Installed OpenCode 2.x plugin to {dst}")

    if _command_exists("opencode"):
        try:
            subprocess.run(
                ["opencode", "service", "restart"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )
            print("   Restarted OpenCode background service")
        except Exception:
            pass


PLATFORM_INSTALLERS = {
    "claude_code": install_claude_code_hooks,
    "codex": install_codex_hooks,
    "opencode": install_opencode_hooks,
    "copilot_cli": install_copilot_cli_hooks,
    "cursor": install_cursor_hooks,
    "aider": install_aider_hooks,
}


# ---------------------------------------------------------------------------
# Test notification
# ---------------------------------------------------------------------------

def send_test_notification():
    """Send a test notification via notify.py."""
    test_payload = json.dumps({
        "hook_event_name": "Stop",
        "message": "Setup complete! Notifications are working.",
    })
    try:
        proc = subprocess.run(
            [sys.executable, NOTIFY_SCRIPT, "--platform", "claude_code"],
            input=test_payload,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if proc.returncode == 0:
            print("   Test notification sent successfully!")
        else:
            print(f"   Test notification failed: {proc.stderr.strip()}")
    except Exception as exc:
        print(f"   Test notification error: {exc}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 50)
    print("  Agent Notifier - Setup")
    print("=" * 50)

    # 1. Detect platforms
    print("\nDetecting installed AI agent platforms...")
    detected = detect_platforms()
    for key, label in PLATFORMS.items():
        status = "found" if detected.get(key) else "not found"
        print(f"  - {label}: {status}")

    # 2. Load existing or template config
    config = {}
    if os.path.isfile(DEFAULT_CONFIG_PATH):
        with open(DEFAULT_CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        print(f"\nLoaded existing config from {DEFAULT_CONFIG_PATH}")
    elif os.path.isfile(TEMPLATE_CONFIG):
        with open(TEMPLATE_CONFIG, "r", encoding="utf-8") as f:
            config = json.load(f)
        print(f"\nLoaded template config from {TEMPLATE_CONFIG}")

    # 3. Configure channels
    config = configure_channels(config)

    # 4. Save config
    config_path = _input(
        "\nSave config to",
        DEFAULT_CONFIG_PATH,
    )
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Config saved to {config_path}")

    # 5. Install hooks for detected platforms
    print("\n--- Hook Installation ---\n")
    default_enabled = {"claude_code", "codex", "opencode"}
    for key in PLATFORMS:
        if not detected.get(key):
            continue
        label = PLATFORMS[key]
        if _confirm(f"Install hooks for {label}?", default=(key in default_enabled)):
            PLATFORM_INSTALLERS[key]()
            print()

    # 6. Test notification
    print("\n--- Test Notification ---\n")
    if _confirm("Send a test notification?", default=True):
        send_test_notification()

    print("\nSetup complete! Your AI agents will now send notifications.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
