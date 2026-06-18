# generate-wiki Skill Installation Guide

## File Description

| File | Description |
|------|------|
| `skill.json` | Skill metadata configuration |
| `SKILL.md` | Skill main document, defines Agent workflow |
| `README.md` | Usage instructions |
| `docs/workflow.md` | Agent workflow detailed description |
| `docs/quality-checklist.md` | Quality checklist |
| `templates/` | Page template directory |

## Installation Steps

### Method 1: Direct copy to Claude Code Skill directory

1. Copy this directory to Claude Code's skill directory:
```bash
cp -r generate-grpc-java-wiki ~/.claude/skills/generate-wiki
```

2. Restart Claude Code or reload skills

### Method 2: Install via Claude Code command

Execute in Claude Code:
```
/skill add generate-wiki /path/to/generate-grpc-java-wiki
```

## Usage

After installation, this skill is used through the Agent workflow, not through in-project parsing scripts.

Call the skill in the target repository and let the Agent scan code, identify interfaces, and output wiki according to the `SKILL.md` workflow.

Recommended commands:

```
Scan all gRPC interfaces in the current project and generate a wiki draft
```

Or execute step by step:

```
First list all RPC methods, then generate service documentation one by one
```

## Generated Wiki Structure

```
wiki/
├── index.html              # Main page
├── assets/
│   ├── css/style.css       # Style file
│   └── js/nav.js           # Navigation interaction
├── 01-system-architecture.md  # System architecture framework document
├── 02-core-features.md        # Core features framework document
├── 03-er-diagram.md           # ER diagram framework document
└── service/                # API documentation directory
    ├── MethodName.md       # One document per RPC method
    └── ...
```

## Next Steps

1. **Complete system architecture document**: Edit `01-system-architecture.md`
2. **Complete core features document**: Edit `02-core-features.md`
3. **Complete ER diagram document**: Edit `03-er-diagram.md`
4. **Complete API documentation**: Edit `service/*.md`

## Start Preview

```bash
cd wiki
python3 -m http.server 8080
```

Then visit http://localhost:8080

## Notes

1. Generated documents are **framework templates**, the Agent will try to fill in content, but manual completion is needed
2. If proto files are updated, you need to re-call the skill to regenerate
3. Styles and interaction logic are **unified**, all projects look consistent after generation
4. The `wiki/` directory under this directory is example output, for reference only for style and structure
