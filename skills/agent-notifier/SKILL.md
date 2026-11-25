---
name: agent-notifier
description: >
  Multi-platform, multi-channel notification skill for AI code agents.
  Sends notifications (sound, macOS alert, Telegram, Email, Slack, Discord, DingTalk)
  when the agent needs user interaction, encounters a failure, or completes a task.
  Supports Claude Code, Codex, OpenCode (2.x), GitHub Copilot CLI, Cursor, and Aider.
license: Apache-2.0
metadata:
  author: crossoverJie
  version: "1.1"
---

# Agent Notifier Skill

Deterministic, hook-driven notifications for AI code agents. Never miss when your agent finishes a task, fails, or needs permission/input.

## Why

LLM-based "play a sound when done" prompts are unreliable — context compression drops them, and the model's judgement of "done" is inconsistent. This skill uses each platform's **Hooks / Plugin system** for guaranteed triggering.

## Prerequisites

- **Python 3** (standard library only, no external dependencies)
- At least one supported AI agent platform

## Supported Platforms

| Platform | Hook / Plugin Events |
|----------|----------------------|
| Claude Code | `Stop`, `StopFailure`, `PermissionRequest`, `Notification` (`idle_prompt`, `elicitation_dialog`) |
| Codex | `hooks.json`: `Stop`, `PermissionRequest` (`[features] hooks = true`) |
| OpenCode (2.x) | Plugin `setup(ctx)` (`session.execution.succeeded`, `session.execution.failed`, `session.error`, `permission.asked`, `form.created`) |
| GitHub Copilot CLI | `sessionEnd`, `postToolUse` |
| Cursor | `stop`, `afterFileEdit` |
| Aider | `--notifications-command` |

## Quick Start

```bash
# Interactive setup — detects platforms, configures channels, merges hooks safely
python3 skills/agent-notifier/setup.py
```

### Claude Code Users

`setup.py` merges the following hooks into `~/.claude/settings.json` without overwriting existing hooks:
- `Stop` — task completed (ignores intermediate background subagent stops and `stop_hook_active`)
- `StopFailure` — API / turn failure requiring user attention
- `PermissionRequest` — tool approval needed
- `Notification` — `idle_prompt` / `elicitation_dialog`

### Codex Users

`setup.py` enables `[features] hooks = true` in `~/.codex/config.toml` and merges `Stop` and `PermissionRequest` hooks into `~/.codex/hooks.json`.

> Note: Codex may prompt you once on next launch to trust the newly added hook commands.

### OpenCode (2.x) Users

OpenCode 2.x uses ESM plugins with `export default { id, server, setup }`. Copy the plugin to your plugins directory (and remove any legacy `agent-notifier.ts` file):

```bash
mkdir -p ~/.config/opencode/plugins
rm -f ~/.config/opencode/plugins/agent-notifier.ts
cp skills/agent-notifier/opencode-plugin.js ~/.config/opencode/plugins/agent-notifier.js
```

### Copilot CLI Users

Copilot CLI loads hooks from the project's `.github/hooks/` directory (per-project):

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

## Manual Usage

```bash
# Test with simulated Claude Code Stop event
echo '{"hook_event_name":"Stop"}' | python3 skills/agent-notifier/notify.py --platform claude_code

# Test with simulated Codex PermissionRequest event
echo '{"hook_event_name":"PermissionRequest","tool_name":"Bash","tool_input":{"command":"git status"}}' | python3 skills/agent-notifier/notify.py --platform codex

# Test with simulated OpenCode 2.x event
echo '{"platform":"opencode","event_type":"session.execution.succeeded"}' | python3 skills/agent-notifier/notify.py --platform opencode

# Test with command-line args (Aider style)
python3 skills/agent-notifier/notify.py "Task completed"
```

## Notification Channels

| Channel | Default | Requirements |
|---------|---------|-------------|
| Sound | Enabled | macOS (`afplay`) or Linux (`paplay`/`aplay`) |
| macOS Notification | Enabled | macOS only |
| Telegram | Disabled | Bot token + Chat ID (+ optional `proxy`) |
| Email | Disabled | SMTP credentials |
| Slack | Disabled | Incoming Webhook URL |
| Discord | Disabled | Webhook URL |
| DingTalk | Disabled | Webhook URL + optional Secret |

## Configuration

Config file is searched in order:
1. `~/.claude/notify-config.json`
2. `skills/agent-notifier/notify-config.json` (template)

Run `python3 skills/agent-notifier/setup.py` to configure interactively, or edit the JSON directly.

## Output

Notifications are sent concurrently to all enabled channels. Individual channel failures are logged to stderr without affecting other channels.
