#!/usr/bin/env python3
"""Export Claude Code session logs to readable Markdown files."""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone


CLAUDE_DIR = os.path.expanduser("~/.claude")
PROJECTS_DIR = os.path.join(CLAUDE_DIR, "projects")

# Event types to skip
SKIP_TYPES = {"progress", "file-history-snapshot", "system"}


def encode_project_path(cwd):
    """Encode a project path the same way Claude Code does: /a/b/c -> -a-b-c"""
    return cwd.replace("/", "-")


def strip_ansi(text):
    """Remove ANSI escape codes from text."""
    return re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", text)


def find_latest_session(project_dir):
    """Find the most recently modified .jsonl file in the project directory."""
    jsonl_files = []
    for f in os.listdir(project_dir):
        if f.endswith(".jsonl"):
            path = os.path.join(project_dir, f)
            jsonl_files.append((os.path.getmtime(path), path, f))

    if not jsonl_files:
        return None, None

    jsonl_files.sort(reverse=True)
    latest = jsonl_files[0]
    session_id = latest[2].replace(".jsonl", "")
    return latest[1], session_id


def parse_session_log(filepath):
    """Parse a JSONL session log file, skipping malformed lines."""
    events = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                events.append(event)
            except json.JSONDecodeError:
                pass
    return events


def filter_conversation_events(events, is_subagent=False):
    """Filter events to only meaningful conversation messages."""
    filtered = []
    for event in events:
        event_type = event.get("type", "")

        # Skip non-conversation events
        if event_type in SKIP_TYPES:
            continue

        # Skip meta messages (like skill injections)
        if event.get("isMeta"):
            continue

        # Skip sidechain messages (but not for subagent logs, which are all sidechains)
        if not is_subagent and event.get("isSidechain"):
            continue

        # Only keep user and assistant messages
        if event_type not in ("user", "assistant"):
            continue

        # For user messages, skip tool results (they are internal plumbing)
        message = event.get("message", {})
        content = message.get("content", "")
        if event_type == "user" and isinstance(content, list):
            # Check if this is purely tool results
            has_text = any(
                item.get("type") == "text" for item in content if isinstance(item, dict)
            )
            has_tool_result = any(
                item.get("type") == "tool_result"
                for item in content
                if isinstance(item, dict)
            )
            if has_tool_result and not has_text:
                continue

        filtered.append(event)
    return filtered


def extract_text_content(content):
    """Extract plain text from content which can be a string or array."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    parts.append(item.get("text", ""))
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts)
    return str(content)


def render_user_message(event, max_tool_output):
    """Render a user message event to markdown."""
    lines = []
    timestamp = event.get("timestamp", "")
    lines.append(f"## User")
    if timestamp:
        lines.append(f"*{timestamp}*")
    lines.append("")

    message = event.get("message", {})
    content = message.get("content", "")
    text = extract_text_content(content)
    text = strip_ansi(text)

    # Remove command-message XML tags that come from skill invocations
    text = re.sub(r"<command-message>.*?</command-message>\n?", "", text, flags=re.DOTALL)
    text = re.sub(r"<command-name>.*?</command-name>\n?", "", text, flags=re.DOTALL)
    text = re.sub(r"<command-args>.*?</command-args>\n?", "", text, flags=re.DOTALL)

    text = text.strip()
    if text:
        lines.append(text)
    lines.append("")
    return "\n".join(lines)


def render_tool_use(tool_use, max_tool_output):
    """Render a single tool_use block as a collapsible details section."""
    tool_name = tool_use.get("name", "Unknown Tool")
    tool_input = tool_use.get("input", {})

    input_str = json.dumps(tool_input, indent=2, ensure_ascii=False)
    if len(input_str) > max_tool_output:
        input_str = input_str[:max_tool_output] + "\n... (truncated)"

    lines = [
        "<details>",
        f"<summary>Tool Call: {tool_name}</summary>",
        "",
        "```json",
        input_str,
        "```",
        "</details>",
        "",
    ]
    return "\n".join(lines)


def render_assistant_message(event, max_tool_output):
    """Render an assistant message event to markdown."""
    lines = []
    timestamp = event.get("timestamp", "")
    message = event.get("message", {})
    model = message.get("model", "")

    lines.append("## Assistant")
    meta_parts = []
    if timestamp:
        meta_parts.append(timestamp)
    if model:
        meta_parts.append(f"model: {model}")
    if meta_parts:
        lines.append(f"*{' | '.join(meta_parts)}*")
    lines.append("")

    content = message.get("content", [])
    if isinstance(content, str):
        text = strip_ansi(content)
        if text.strip():
            lines.append(text)
            lines.append("")
    elif isinstance(content, list):
        for item in content:
            if not isinstance(item, dict):
                continue
            item_type = item.get("type", "")
            if item_type == "text":
                text = strip_ansi(item.get("text", ""))
                if text.strip():
                    lines.append(text)
                    lines.append("")
            elif item_type == "tool_use":
                lines.append(render_tool_use(item, max_tool_output))
            elif item_type == "thinking":
                thinking_text = item.get("thinking", "")
                if thinking_text and thinking_text.strip():
                    lines.append("<details>")
                    lines.append("<summary>Thinking</summary>")
                    lines.append("")
                    lines.append(strip_ansi(thinking_text))
                    lines.append("")
                    lines.append("</details>")
                    lines.append("")

    return "\n".join(lines)


def find_subagent_logs(project_dir, session_id):
    """Find and return paths to subagent log files for a session."""
    subagent_dir = os.path.join(project_dir, session_id, "subagents")
    if not os.path.isdir(subagent_dir):
        return []

    logs = []
    for f in sorted(os.listdir(subagent_dir)):
        if f.endswith(".jsonl"):
            agent_id = f.replace(".jsonl", "")
            logs.append((agent_id, os.path.join(subagent_dir, f)))
    return logs


def render_markdown(session_id, project_path, events, subagent_sections, max_tool_output):
    """Assemble the full markdown document."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    message_count = len(events)

    lines = [
        "---",
        f"session_id: {session_id}",
        f"project: {project_path}",
        f"exported_at: {now}",
        f"message_count: {message_count}",
        "export_mode: claude-code-logs",
        "---",
        "",
        "# Session Export",
        "",
    ]

    for event in events:
        event_type = event.get("type", "")
        if event_type == "user":
            lines.append(render_user_message(event, max_tool_output))
        elif event_type == "assistant":
            lines.append(render_assistant_message(event, max_tool_output))

    if subagent_sections:
        lines.append("---")
        lines.append("")
        lines.append("# Subagent Conversations")
        lines.append("")
        for agent_id, agent_events in subagent_sections:
            lines.append(f"## Subagent: {agent_id}")
            lines.append("")
            for event in agent_events:
                event_type = event.get("type", "")
                if event_type == "user":
                    lines.append(
                        render_user_message(event, max_tool_output).replace(
                            "## User", "### User"
                        )
                    )
                elif event_type == "assistant":
                    lines.append(
                        render_assistant_message(event, max_tool_output).replace(
                            "## Assistant", "### Assistant"
                        )
                    )

    return "\n".join(lines)


def main():

    parser = argparse.ArgumentParser(
        description="Export Claude Code session logs to Markdown."
    )
    parser.add_argument(
        "--output-dir",
        default=os.environ.get("SESSION_EXPORT_OUTPUT_DIR", "."),
        help="Directory to save the exported markdown file (env: SESSION_EXPORT_OUTPUT_DIR, default: current directory)",
    )
    parser.add_argument(
        "--cwd",
        default=os.getcwd(),
        help="Project working directory, used to locate session logs (default: current directory)",
    )
    parser.add_argument(
        "--session-id",
        help="Export a specific session by ID (default: most recent session)",
    )
    parser.add_argument(
        "--name",
        help="Custom filename for the exported markdown (without .md extension). e.g. --name 'create-session-export-skill'",
    )
    parser.add_argument(
        "--summarize",
        action="store_true",
        help="Request AI to generate a summary after export (default: export raw conversation)",
    )
    parser.add_argument(
        "--no-subagents",
        action="store_true",
        help="Exclude subagent conversations from the export",
    )
    parser.add_argument(
        "--max-tool-output",
        type=int,
        default=5000,
        help="Max characters per tool call output (default: 5000)",
    )

    args = parser.parse_args()
    max_tool_output = args.max_tool_output

    # Check if Claude Code projects directory exists
    if not os.path.isdir(PROJECTS_DIR):
        print(
            "Claude Code log directory not found (~/.claude/projects/).\n"
            "FALLBACK_MODE: AI should write conversation from context directly.",
            file=sys.stderr,
        )
        sys.exit(2)

    # Locate the project log directory
    encoded_path = encode_project_path(args.cwd)
    project_dir = os.path.join(PROJECTS_DIR, encoded_path)

    if not os.path.isdir(project_dir):
        print(
            f"No session logs found for project: {args.cwd}\n"
            f"Expected log directory: {project_dir}\n"
            "FALLBACK_MODE: AI should write conversation from context directly.",
            file=sys.stderr,
        )
        sys.exit(2)

    # Find or validate session
    if args.session_id:
        session_file = os.path.join(project_dir, f"{args.session_id}.jsonl")
        if not os.path.isfile(session_file):
            print(f"Session file not found: {session_file}", file=sys.stderr)
            sys.exit(1)
        session_id = args.session_id
    else:
        session_file, session_id = find_latest_session(project_dir)
        if not session_file:
            print(f"No session logs found in: {project_dir}", file=sys.stderr)
            sys.exit(1)

    # Parse and filter events
    print(f"Parsing session: {session_id}", file=sys.stderr)
    events = parse_session_log(session_file)
    conversation = filter_conversation_events(events)
    print(f"Found {len(conversation)} conversation messages", file=sys.stderr)

    # Process subagent logs
    subagent_sections = []
    if not args.no_subagents:
        subagent_logs = find_subagent_logs(project_dir, session_id)
        for agent_id, agent_path in subagent_logs:
            agent_events = parse_session_log(agent_path)
            agent_conversation = filter_conversation_events(agent_events, is_subagent=True)
            if agent_conversation:
                subagent_sections.append((agent_id, agent_conversation))
        if subagent_sections:
            print(
                f"Found {len(subagent_sections)} subagent conversation(s)",
                file=sys.stderr,
            )

    # Render markdown
    markdown = render_markdown(
        session_id, args.cwd, conversation, subagent_sections, max_tool_output
    )

    # Generate output filename
    now = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    if args.name:
        # Sanitize: remove .md suffix if provided, strip whitespace
        name = args.name.strip().removesuffix(".md")
        filename = f"{name}.md"
    else:
        short_id = session_id[:8]
        filename = f"session-{short_id}-{now}.md"

    # Write output
    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    print(f"\nExported to: {output_path}")
    print(f"Session: {session_id}")
    print(f"Messages: {len(conversation)}")
    if subagent_sections:
        print(f"Subagents: {len(subagent_sections)}")

    if args.summarize:
        print(
            "\nSUMMARIZE_REQUESTED: AI should read the exported file and generate "
            f"a summary at: {output_path.replace('.md', '-summary.md')}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
