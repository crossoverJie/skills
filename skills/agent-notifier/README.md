# Agent Notifier

Multi-platform, multi-channel notification system for AI code agents. Get notified via sound, macOS alerts, Telegram, Email, Slack, or Discord when your agent needs input or completes a task.

## Problem

Telling an LLM "play a sound when done" via prompts is unreliable:
- Context compression drops the instruction
- The model's judgement of "done" is inconsistent
- It's a "soft prompt" with no guarantee of execution

## Solution

Use each platform's **Hooks system** for deterministic triggering. The hook fires a Python script that dispatches notifications to all configured channels concurrently.

## Supported Platforms

| Platform | Hook Mechanism | Trigger Events |
|----------|---------------|----------------|
| **Claude Code** | `settings.json` hooks | `Notification` (idle_prompt, permission_prompt) |
| **GitHub Copilot CLI** | `hooks.json` | `sessionEnd`, `postToolUse` |
| **Cursor** | `hooks.json` | `stop`, `afterFileEdit` |
| **Codex (OpenAI)** | notify setting | `agent-turn-complete` |
| **Aider** | CLI flag | `--notifications-command` |

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
# Interactive setup — detects platforms, configures channels, installs hooks
python3 skills/agent-notifier/setup.py
```

The setup script will:
1. Detect which AI agent platforms you have installed
2. Guide you through enabling notification channels
3. Automatically install hooks for detected platforms
4. Send a test notification to verify everything works

## Manual Platform Configuration

### Claude Code

Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "Notification": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python3 $HOME/.claude/skills/agent-notifier/notify.py"
          }
        ]
      }
    ]
  }
}
```

### GitHub Copilot CLI

> **Note:** Copilot CLI loads hooks from the project's `.github/hooks/` directory. You need to in **each project** that you want notifications for create this file. Claude Code hooks are global (`~/.claude/settings.json`), but Copilot CLI hooks are per-project.

Create `.github/hooks/agent-notifier.json` in your project root:

```bash
mkdir -p .github/hooks
cat > .github/hooks/agent-notifier.json << 'EOF'
{
  "version": 1,
  "hooks": {
    "sessionEnd": [
      {"type": "command", "bash": "python3 $HOME/.claude/skills/agent-notifier/notify.py"}
    ],
    "postToolUse": [
      {"type": "command", "bash": "python3 $HOME/.claude/skills/agent-notifier/notify.py"}
    ]
  }
}
EOF
```

Or run `python3 ~/.claude/skills/agent-notifier/setup.py` to install automatically.

### Cursor

Add to `.cursor/hooks.json`:

```json
{
  "stop": [
    {"command": "python3 $HOME/.claude/skills/agent-notifier/notify.py"}
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
4. Enable Telegram in the config and fill in `bot_token` and `chat_id`

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
      "chat_id": "987654321"
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
    }
  }
}
```

## Testing

```bash
# Simulate a Claude Code idle_prompt event
echo '{"notification_type":"idle_prompt","message":"Waiting for your input"}' | python3 skills/agent-notifier/notify.py

# Simulate a Copilot CLI sessionEnd event
echo '{"timestamp":1704618000000,"cwd":"/path","reason":"complete"}' | python3 skills/agent-notifier/notify.py

# Simulate a Copilot CLI postToolUse event
echo '{"timestamp":1704614700000,"cwd":"/path","toolName":"bash","toolArgs":"ls","toolResult":{"resultType":"success","textResultForLlm":"done"}}' | python3 skills/agent-notifier/notify.py

# Simulate a Cursor task completion
echo '{"hook_event_name":"stop","status":"completed","agent":"cursor"}' | python3 skills/agent-notifier/notify.py

# Aider-style (command-line argument)
python3 skills/agent-notifier/notify.py "Task completed"

# Debug with Claude Code
claude --debug
```

## Troubleshooting

**No sound on macOS:**
- Check that the sound file exists: `ls /System/Library/Sounds/Glass.aiff`
- Try playing it manually: `afplay /System/Library/Sounds/Glass.aiff`

**No macOS notification:**
- Check System Settings > Notifications > Script Editor is allowed

**Telegram not working:**
- Verify bot token: `curl https://api.telegram.org/bot<TOKEN>/getMe`
- Verify chat ID: send a message to the bot first, then check `getUpdates`

**Hook not firing:**
- Claude Code: Run `claude --debug` and look for hook execution logs
- Check that `python3` is in your PATH
- Verify the script path in the hook config is absolute and correct

## Session Context

When running multiple AI agent sessions simultaneously, notifications include a **project name prefix** so you can tell which session generated each alert.

```
Title: Agent Notifier — Claude Code
Body:  [my-project] ✅ Task completed — waiting for your input
```

The project name is detected automatically:

1. **Copilot CLI** — uses the `cwd` field from the hook payload
2. **All platforms** — falls back to `os.getcwd()` (the hook subprocess inherits the parent's working directory)
3. If the directory is inside a **git repository**, the repo name is used (e.g. `my-project` from `/Users/dev/my-project`)
4. Otherwise the directory basename is used

No configuration is needed — the context is always included when a project name can be determined.

## Architecture

```
stdin (JSON from hook) → parse_input() → unified event model
                                              ↓
                              load_config() → notify-config.json
                                              ↓
                              ThreadPoolExecutor → [sound, macOS, telegram, ...]
```

Each channel runs in its own thread. A failure in one channel does not affect others. Errors are logged to stderr.
