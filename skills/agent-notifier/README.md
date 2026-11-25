# Agent Notifier

Multi-platform, multi-channel notification system for AI code agents. Get notified via sound, macOS alerts, Telegram, Email, Slack, Discord, or DingTalk when your agent completes a task, encounters an error, or needs your input/approval.

## Problem

Telling an LLM "play a sound when done" via prompts is unreliable:
- Context compression drops the instruction
- The model's judgement of "done" is inconsistent
- It's a "soft prompt" with no guarantee of execution

## Solution

Use each platform's **Hooks / Plugin system** for deterministic triggering. The hook fires a Python script that dispatches notifications to all configured channels concurrently.

## Supported Platforms

| Platform               | Hook Mechanism            | Trigger Events                                                                                          |
|------------------------|---------------------------|---------------------------------------------------------------------------------------------------------|
| **Claude Code**        | `~/.claude/settings.json` | `Stop`, `StopFailure`, `PermissionRequest`, `Notification` (`idle_prompt`, `elicitation_dialog`)        |
| **Codex (OpenAI)**     | `~/.codex/hooks.json`     | `Stop`, `PermissionRequest` (with `[features] hooks = true` in `~/.codex/config.toml`)                  |
| **OpenCode (2.x)**     | `~/.config/opencode/plugins/` | `session.execution.succeeded`, `session.execution.failed`, `session.error`, `permission.asked`, `form.created` |
| **GitHub Copilot CLI** | `.github/hooks/*.json`    | `sessionEnd`, `postToolUse`                                                                             |
| **Cursor**             | `.cursor/hooks.json`      | `stop`, `afterFileEdit`                                                                                 |
| **Aider**              | CLI flag / `.aider.conf.yml` | `--notifications-command`                                                                            |

## Installation

### Skills CLI (Recommended)

```bash
npx skills add crossoverJie/skills@agent-notifier
```

### Manual Installation

```bash
# Clone the repository
git clone https://github.com/crossoverJie/skills.git ~/skills

# Run the interactive setup
python3 ~/skills/skills/agent-notifier/setup.py
```

## Quick Start

```bash
# Interactive setup — detects platforms, configures channels, merges hooks safely
python3 skills/agent-notifier/setup.py
```

The setup script will:
1. Detect which AI agent platforms you have installed
2. Guide you through enabling notification channels
3. Incrementally merge hooks for detected platforms without clobbering existing hooks
4. Send a test notification to verify everything works

## Manual Platform Configuration

### Claude Code

Merge into `~/.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 $HOME/.claude/skills/agent-notifier/notify.py --platform claude_code"
          }
        ]
      }
    ],
    "StopFailure": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 $HOME/.claude/skills/agent-notifier/notify.py --platform claude_code"
          }
        ]
      }
    ],
    "PermissionRequest": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 $HOME/.claude/skills/agent-notifier/notify.py --platform claude_code"
          }
        ]
      }
    ],
    "Notification": [
      {
        "matcher": "idle_prompt|elicitation_dialog",
        "hooks": [
          {
            "type": "command",
            "command": "python3 $HOME/.claude/skills/agent-notifier/notify.py --platform claude_code"
          }
        ]
      }
    ]
  }
}
```

### Codex

1. Enable hooks in `~/.codex/config.toml`:

```toml
[features]
hooks = true
```

2. Add `Stop` and `PermissionRequest` hooks in `~/.codex/hooks.json`:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 /Users/<you>/.claude/skills/agent-notifier/notify.py --platform codex",
            "timeout": 10
          }
        ]
      }
    ],
    "PermissionRequest": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 /Users/<you>/.claude/skills/agent-notifier/notify.py --platform codex",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

> **Note:** Codex tracks hook trust hashes in `~/.codex/config.toml`. On your next interactive Codex launch, approve the trust prompt if asked.

### OpenCode (2.x)

Copy `opencode-plugin.js` into `~/.config/opencode/plugins/` (and remove any legacy `agent-notifier.ts` file):

```bash
mkdir -p ~/.config/opencode/plugins
rm -f ~/.config/opencode/plugins/agent-notifier.ts
cp skills/agent-notifier/opencode-plugin.js ~/.config/opencode/plugins/agent-notifier.js
```

### GitHub Copilot CLI

> **Note:** Copilot CLI loads hooks from the project's `.github/hooks/` directory (per-project).

Create `.github/hooks/agent-notifier.json` in your project root:

```bash
mkdir -p .github/hooks
cat > .github/hooks/agent-notifier.json << 'EOF'
{
  "version": 1,
  "hooks": {
    "sessionEnd": [
      {"type": "command", "bash": "python3 $HOME/.claude/skills/agent-notifier/notify.py --platform copilot_cli"}
    ],
    "postToolUse": [
      {"type": "command", "bash": "python3 $HOME/.claude/skills/agent-notifier/notify.py --platform copilot_cli"}
    ]
  }
}
EOF
```

### Cursor

Add to `.cursor/hooks.json`:

```json
{
  "stop": [
    {"command": "python3 $HOME/.claude/skills/agent-notifier/notify.py --platform cursor"}
  ]
}
```

### Aider

Add to `.aider.conf.yml`:

```yaml
notifications-command: python3 $HOME/.claude/skills/agent-notifier/notify.py
```

Or pass as a CLI flag:

```bash
aider --notifications-command "python3 $HOME/.claude/skills/agent-notifier/notify.py"
```

## Notification Channels

### Sound (default: enabled)

Plays a sound file using the system audio player.

- **macOS**: Uses `afplay` (default: `/System/Library/Sounds/Glass.aiff`)
- **Linux**: Uses `paplay` (PulseAudio) or `aplay` (ALSA)

### macOS Notification Center (default: enabled)

Shows a native macOS notification via `osascript`. Only available on macOS.

### Telegram

1. Create a bot via [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow the prompts to get your **Bot Token**
3. Send a message to your bot, then visit `https://api.telegram.org/bot<TOKEN>/getUpdates` to find your **Chat ID**
4. Enable Telegram in the config and fill in `bot_token`, `chat_id`, and optional `proxy` (e.g. `socks5://127.0.0.1:7898` or `http://127.0.0.1:7890`)

### Email (SMTP)

1. For Gmail, create an [App Password](https://myaccount.google.com/apppasswords)
2. Configure SMTP settings in `notify-config.json`:
   - `smtp_host`: Your SMTP server (default: `smtp.gmail.com`)
   - `smtp_port`: SMTP port (default: `587`)
   - `username`: Your email address
   - `password`: Your password or app password
   - `to_addr`: Recipient email address

### Slack

1. Go to [Slack API: Incoming Webhooks](https://api.slack.com/messaging/webhooks)
2. Create a new webhook for your workspace and channel
3. Copy the webhook URL and set it in `notify-config.json`

### Discord

1. In your Discord server, go to **Server Settings > Integrations > Webhooks**
2. Create a new webhook, choose the target channel
3. Copy the webhook URL and set it in `notify-config.json`

### DingTalk (钉钉)

1. In your DingTalk group, go to **Group Settings > Bots > Add Robot > Custom (via Webhook)**
2. Choose a security method — **Sign (加签)** is recommended
3. Copy the **Webhook URL** and optional **Secret** (signing key) into `notify-config.json`

## Configuration File

The config file is searched in order:
1. `~/.claude/notify-config.json`
2. `skills/agent-notifier/notify-config.json` (template)

```json
{
  "channels": {
    "sound": {
      "enabled": true,
      "file": "/System/Library/Sounds/Glass.aiff"
    },
    "macos_notification": {
      "enabled": true
    },
    "telegram": {
      "enabled": false,
      "bot_token": "123456:ABC-DEF...",
      "chat_id": "987654321",
      "proxy": ""
    },
    "email": {
      "enabled": false,
      "smtp_host": "smtp.gmail.com",
      "smtp_port": 587,
      "username": "you@gmail.com",
      "password": "your-app-password",
      "from_addr": "you@gmail.com",
      "to_addr": "you@gmail.com"
    },
    "slack": {
      "enabled": false,
      "webhook_url": "https://hooks.slack.com/services/T.../B.../..."
    },
    "discord": {
      "enabled": false,
      "webhook_url": "https://discord.com/api/webhooks/..."
    },
    "dingtalk": {
      "enabled": false,
      "webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=...",
      "secret": "SEC..."
    }
  }
}
```

## Testing

```bash
# Simulate a Claude Code Stop event
echo '{"hook_event_name":"Stop"}' | python3 skills/agent-notifier/notify.py --platform claude_code

# Simulate a Claude Code StopFailure event
echo '{"hook_event_name":"StopFailure","error":"rate_limit"}' | python3 skills/agent-notifier/notify.py --platform claude_code

# Simulate a Codex PermissionRequest event
echo '{"hook_event_name":"PermissionRequest","tool_name":"Bash","tool_input":{"command":"rm -rf dist"}}' | python3 skills/agent-notifier/notify.py --platform codex

# Simulate an OpenCode 2.x execution succeeded event
echo '{"platform":"opencode","event_type":"session.execution.succeeded"}' | python3 skills/agent-notifier/notify.py --platform opencode

# Simulate a Copilot CLI sessionEnd event
echo '{"timestamp":1704618000000,"cwd":"/path","reason":"complete"}' | python3 skills/agent-notifier/notify.py --platform copilot_cli

# Simulate a Cursor task completion
echo '{"hook_event_name":"stop","status":"completed","agent":"cursor"}' | python3 skills/agent-notifier/notify.py

# Aider-style (command-line argument)
python3 skills/agent-notifier/notify.py "Task completed"

# Run unit tests
python3 -m unittest skills/agent-notifier/test_notify.py
```

## Troubleshooting

**No sound on macOS:**
- Check that the sound file exists: `ls /System/Library/Sounds/Glass.aiff`
- Try playing it manually: `afplay /System/Library/Sounds/Glass.aiff`

**No macOS notification:**
- Check System Settings > Notifications > Script Editor is allowed

**Telegram not working / timing out:**
- Verify bot token: `curl https://api.telegram.org/bot<TOKEN>/getMe`
- If you are behind a local proxy and agent hooks don't inherit shell proxy env vars, set `"proxy": "socks5://127.0.0.1:7898"` (or your HTTP proxy URL) in `notify-config.json`

**Hook not firing:**
- Claude Code: Run `claude --debug` and look for hook execution logs
- Codex: Run `codex doctor` and check `[features] hooks = true` in `~/.codex/config.toml`
- OpenCode 2.x: Check `~/.local/share/opencode/log/opencode.log` for plugin loading status

## Session Context

When running multiple AI agent sessions simultaneously, notifications include a **project name prefix** so you can tell which session generated each alert.

```
Title: Agent Notifier — Claude Code
Body:  [my-project] ✅ Task completed — waiting for your input
```

The project name is detected automatically:

1. Uses the `cwd` or `directory` field from the hook payload when present
2. Falls back to `os.getcwd()` (the hook subprocess inherits the parent's working directory)
3. If the directory is inside a **git repository**, the repo name is used (e.g. `my-project` from `/Users/dev/my-project`)
4. Otherwise the directory basename is used

## Architecture

```
stdin (JSON from hook) + --platform → parse_input() → unified event model
                                                            ↓
                                            load_config() → notify-config.json
                                                            ↓
                                            ThreadPoolExecutor → [sound, macOS, telegram, dingtalk, ...]
```

Each channel runs in its own thread. A failure in one channel does not affect others. Errors are logged to stderr.
