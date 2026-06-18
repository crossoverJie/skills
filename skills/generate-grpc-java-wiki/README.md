# Generate Wiki Skill

Agent-driven wiki generation workflow for gRPC + Java projects with consistent styling.

## Features

- Consistent project documentation style
- Agent-driven code scanning and interface identification
- Code syntax highlighting (Java, Protobuf, JSON, SQL, etc.)
- Mermaid diagram support (flowcharts, sequence diagrams, ER diagrams)
- Responsive sidebar navigation
- Automatic source code link navigation

## Usage

Call this skill in the target project, then let the Agent:

1. Scan proto and Java source code
2. List all gRPC interfaces
3. Generate a wiki page for each interface
4. Output the `wiki/` directory with unified structure

Recommended command examples:

- "Scan all gRPC interfaces in the current project and generate a wiki draft"
- "First list all RPC methods, then generate service documentation one by one"

## Output Directory Structure

```
wiki/
├── index.html              # Main page (SPA or navigation page)
├── assets/
│   ├── css/style.css       # Style file
│   └── js/nav.js           # Navigation interaction
├── 01-system-architecture.html  # System architecture document (HTML format)
├── 02-core-features.html       # Core features document (HTML format)
├── 03-er-diagram.html          # ER diagram document (HTML format)
├── service/                # gRPC API documentation directory (required)
│   └── {ServiceName}/      # Grouped by gRPC Service
│       ├── index.html      # Service overview page
│       ├── {MethodName}.html  # One HTML document per RPC method
│       └── ...
├── job/                    # PowerJob scheduled tasks (if present)
│   └── {JobClassName}/     # Grouped by Job Processor class
│       ├── index.html      # Job overview page (name, cron, etc.)
│       └── execute.html    # execute method documentation
└── consumer/               # Pulsar consumers (if present)
    └── {ConsumerClassName}/  # Grouped by Consumer class
        ├── index.html      # Consumer overview page (topic, subscription, etc.)
        └── consume.html    # receive/consume method documentation
```

**Notes**:
- `service/` **Required** - gRPC is the core
- `job/` **Optional** - Only generated when the project uses PowerJob
- `consumer/` **Optional** - Only generated when the project uses Pulsar
- All pages must be in **HTML format**, viewable directly in the browser
- Navigation links must point to HTML files (or SPA routes)
- Users should see rendered pages when clicking any link, not raw markdown

## Output Format Requirements

- **All generated pages must be in HTML format**, viewable directly in the browser
- Navigation links must point to HTML files (or SPA routes)
- Users should see rendered pages when clicking any link, not raw markdown
- Two implementation approaches supported:
  1. **Static HTML**: Each page generates an independent `.html` file
  2. **SPA single-page application**: Single `index.html` dynamically renders content

## Agent Workflow

This skill no longer parses code through built-in scripts, but through the Agent workflow:

1. **Scan** - Agent uses tools to search proto and Java files
2. **Identify** - List all gRPC services and RPC methods
3. **Extended Scan** - Detect PowerJob and Pulsar (if used by the project)
4. **Locate** - Find the entry point and business implementation of each component
5. **Extract** - Get source code snippets and file/line number information
6. **Generate** - Generate wiki pages according to templates
7. **Check** - Run quality checklist

Supported component types:
- **gRPC Services** (required) - RPC interfaces defined by proto
- **PowerJob Processors** (optional) - Scheduled task processors
- **Pulsar Consumers** (optional) - Message queue consumers

See [docs/workflow.md](docs/workflow.md) for details

## Page Templates

- [templates/page-service.md](templates/page-service.md) - gRPC API documentation template
- [templates/page-powerjob.md](templates/page-powerjob.md) - PowerJob task documentation template
- [templates/page-pulsar.md](templates/page-pulsar.md) - Pulsar consumer documentation template
- [templates/page-architecture.md](templates/page-architecture.md) - System architecture template
- [templates/page-features.md](templates/page-features.md) - Core features template
- [templates/page-er.md](templates/page-er.md) - ER diagram template

## Quality Check

After generation, the Agent will check:

- Whether all RPC methods are listed
- Whether PowerJob processors are identified (if used)
- Whether Pulsar consumers are identified (if used)
- Whether each page contains source references or TODO markers
- Whether there are fabricated file paths or class names
- Whether uncertain mappings are clearly labeled
- Whether Mermaid diagrams render correctly

See [docs/quality-checklist.md](docs/quality-checklist.md) for details

## Start Preview

```bash
cd wiki
python3 -m http.server 8080
```

Then visit http://localhost:8080

## Technology Stack

- HTML5 + CSS3
- JavaScript (Vanilla)
- Marked.js (Markdown rendering)
- Mermaid.js (Diagram rendering)
- Highlight.js (Code highlighting)

## Notes

1. Generated documents require the Agent to scan project code, mark as TODO when automatic parsing is not possible
2. Styles and interaction logic are **unified**, all projects look consistent after generation
3. The `wiki/` directory under this directory is example output, for reference only for style and structure
