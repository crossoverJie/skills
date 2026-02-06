#!/usr/bin/env python3
"""Interactive setup script for agent-notifier.

Detects installed AI agent platforms, guides channel configuration,
writes hook configs, and sends a test notification.

Requires only the Python standard library.
"""

import json
import os
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


# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

PLATFORMS = {
    "claude_code": "Claude Code",
    "copilot_cli": "GitHub Copilot CLI",
    "cursor": "Cursor",
    "aider": "Aider",
}


def detect_platforms():
    """Return a dict of platform_key -> bool for detected platforms."""
    found = {}

    # Claude Code
    claude_settings = os.path.expanduser("~/.claude/settings.json")
    found["claude_code"] = os.path.isfile(claude_settings) or os.path.isdir(
        os.path.expanduser("~/.claude")
    )

    # Copilot CLI
    found["copilot_cli"] = _command_exists("gh") and shutil.which("gh") is not None

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
    tg = channels.get("telegram", {"enabled": False, "bot_token": "", "chat_id": ""})
    tg["enabled"] = enabled
    if enabled:
        tg["bot_token"] = _input("   Bot token (from @BotFather)", tg.get("bot_token", ""))
        tg["chat_id"] = _input("   Chat ID", tg.get("chat_id", ""))
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

    return config


# ---------------------------------------------------------------------------
# Hook installation per platform
# ---------------------------------------------------------------------------

def install_claude_code_hooks():
    """Add Notification hook to ~/.claude/settings.json."""
    settings_path = os.path.expanduser("~/.claude/settings.json")
    settings = {}
    if os.path.isfile(settings_path):
        with open(settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)

    hooks = settings.setdefault("hooks", {})
    notify_cmd = f"python3 {NOTIFY_SCRIPT}"

    hooks["Notification"] = [
        {
            "matcher": "",
            "hooks": [
                {"type": "command", "command": notify_cmd}
            ],
        }
    ]

    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"   Wrote hooks to {settings_path}")


def install_copilot_cli_hooks():
    """Print instructions for Copilot CLI hook setup."""
    print("   GitHub Copilot CLI hook configuration:")
    print(f"   Add to your hooks.json:")
    print(f'   {{"sessionEnd": [{{"command": "python3 {NOTIFY_SCRIPT}"}}]}}')
    print("   See: https://docs.github.com/en/copilot/using-github-copilot/using-copilot-cli")


def install_cursor_hooks():
    """Print instructions for Cursor hook setup."""
    cursor_dir = os.path.expanduser("~/.cursor")
    print(f"   Cursor hook configuration:")
    print(f"   Add to {cursor_dir}/hooks.json:")
    print(f'   {{"stop": [{{"command": "python3 {NOTIFY_SCRIPT}"}}]}}')


def install_aider_hooks():
    """Print instructions for Aider notification setup."""
    print("   Aider notification configuration:")
    print(f"   Add to .aider.conf.yml or pass as CLI flag:")
    print(f"   notifications-command: python3 {NOTIFY_SCRIPT}")


PLATFORM_INSTALLERS = {
    "claude_code": install_claude_code_hooks,
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
        "notification_type": "idle_prompt",
        "message": "Setup complete! Notifications are working.",
    })
    try:
        proc = subprocess.run(
            [sys.executable, NOTIFY_SCRIPT],
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
    for key in PLATFORMS:
        if not detected.get(key):
            continue
        label = PLATFORMS[key]
        if _confirm(f"Install hooks for {label}?", default=(key == "claude_code")):
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
