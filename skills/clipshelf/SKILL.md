---
name: clipshelf-cli
description: Read from and write to ClipShelf via the clipshelf CLI — query clipboard history, add items, manage tags, and delete entries from the terminal.
triggers:
  - clipshelf
  - shelf
  - clipboard history
  - clipboard query
  - clipboard add
---

# ClipShelf CLI Skill

Use the `clipshelf` CLI to interact with the ClipShelf clipboard manager from the terminal. The CLI shares the same SQLite database as the macOS GUI app, so changes are reflected in both.

## Prerequisites

The `clipshelf` binary must be available on `$PATH`. Install via Homebrew:

```bash
brew tap crossoverJie/homebrew-tap
brew install crossoverjie/tap/clipshelf
```

Verify:

```bash
clipshelf --help
```

If the binary is not found, inform the user and stop — do not attempt alternative access methods.

## Command Reference

### Read Operations

#### Fetch recent items

```bash
clipshelf recent [--limit N] [--output json|ndjson|text]
```

- Default limit: 10
- Default output: `json`
- Use `--output text` when you only need plain text content
- Use `--output ndjson` for streaming / large result sets

#### Query by tag or text

```bash
clipshelf query [--tag TAG ...] [--match-any-tag] [--text "substring"] [--limit N] [--output json|ndjson|text]
```

- Multiple `--tag` values use AND semantics by default
- Add `--match-any-tag` to switch to OR semantics
- `--text` performs case-insensitive substring matching

#### Get a single item by ID

```bash
clipshelf get <uuid> [--output json|ndjson|text]
```

### Write Operations

#### Add a text item

```bash
# From argument
clipshelf add --text "content" [--tags TAG ...] [--print-id]

# From stdin (pipe-friendly)
echo "content" | clipshelf add --stdin [--tags TAG ...] [--print-id]
```

- Either `--text` or `--stdin` is required (mutually exclusive)
- `--tags` accepts multiple values: `--tags work --tags important`
- `--print-id` outputs only the UUID of the created item (useful for scripting)

#### Delete an item

```bash
clipshelf delete <uuid>
```

### Tag Management

```bash
# List all tags
clipshelf tags list [--output json|ndjson|text]

# Create a tag
clipshelf tags create <name> [--color #808080]
```

## Output Formats

| Format | Flag | Use case |
|--------|------|----------|
| JSON | `--output json` (default) | Structured data, jq processing. Wrapped in `{"schemaVersion":"1","data":[...]}` |
| NDJSON | `--output ndjson` | Streaming, large datasets. One JSON object per line (no envelope) |
| Text | `--output text` | Plain content only, one item per line. No metadata |

### JSON envelope structure (default)

```json
{
  "schemaVersion": "1",
  "data": [
    {
      "id": "uuid-string",
      "contentType": "text",
      "textContent": "...",
      "createdAt": "ISO-8601",
      "tags": ["tag1"],
      "isPinned": false
    }
  ]
}
```

## Error Handling

Errors are written to stderr as structured JSON. Check exit codes:

| Exit code | Meaning |
|-----------|---------|
| 0 | Success |
| 2 | Invalid argument or empty stdin |
| 3 | Resource not found |
| 4 | Access denied |
| 5 | Store/database error |
| 6 | Conflict (e.g. duplicate tag) |
| 10 | Unknown error |

Always check the exit code when running CLI commands. On non-zero exit, read stderr for the error message and report it to the user.

## Common Patterns

### Search for specific content

```bash
clipshelf query --text "keyword" --limit 20
```

### Get all items with a tag

```bash
clipshelf query --tag work --limit 100
```

### Save output for later processing

```bash
clipshelf recent --limit 50 --output ndjson > /tmp/shelf_export.ndjson
```

### Add multi-line content from a file

```bash
cat notes.txt | clipshelf add --stdin --tags notes
```

### Add an item and capture its ID

```bash
ITEM_ID=$(clipshelf add --text "hello" --print-id)
echo "Created: $ITEM_ID"
```

### Combine with jq for filtering

```bash
clipshelf recent --limit 100 | jq '.data[] | select(.isPinned == true) | .textContent'
```

## Guidelines

1. **Default to JSON output** — it provides the most context (IDs, tags, timestamps). Use `--output text` only when the user explicitly wants plain content.
2. **Respect limits** — always set `--limit` to a reasonable value. Don't fetch thousands of items unless the user asks.
3. **Use --print-id when scripting** — if you need the created item's ID for follow-up operations, use `--print-id` instead of parsing full JSON output.
4. **Prefer --stdin for long content** — for multi-line or large text, pipe via stdin rather than passing `--text` with embedded newlines.
5. **Check exit codes** — always verify the command succeeded before acting on the output.
6. **Don't modify data without confirmation** — before deleting items or creating tags, confirm with the user what will be changed.
7. **Same database as the GUI app** — items added/deleted via CLI are immediately visible in the macOS app and vice versa.
