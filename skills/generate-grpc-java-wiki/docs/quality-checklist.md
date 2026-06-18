# Generate Wiki Quality Checklist

- All RPC methods discovered in the project are listed.
- Every generated service page includes source file references or an explicit `TODO`.
- No file path, class name, or method name is fabricated.
- Any uncertain mapping is labeled clearly.
- The generated wiki structure matches the documented layout.

## Generation Order Checklist (CRITICAL)

**MUST follow this exact order:**

### Phase 1: Discovery (First)
- [ ] ALL proto files discovered first
- [ ] ALL gRPC services and methods listed
- [ ] ALL PowerJob processors discovered (if present)
- [ ] ALL Pulsar consumers discovered (if present)
- [ ] ALL proto message types recorded (for ER diagram)
- [ ] Component inventory output BEFORE generating any pages
- [ ] **Component count calculated** (to determine if parallel generation needed)

### Phase 2: Component Pages (Second)
- [ ] Generate ALL gRPC method pages first
- [ ] Generate ALL PowerJob pages second (if present)
- [ ] Generate ALL Pulsar consumer pages third (if present)
- [ ] **Parallel Generation** (if total components ≥ 50):
  - [ ] Different services generated in parallel
  - [ ] Different PowerJob processors generated in parallel
  - [ ] Different Pulsar consumers generated in parallel
  - [ ] Methods within same service generated sequentially
  - [ ] All subagents completed before proceeding to Phase 3
- [ ] Verify component page count matches inventory

### Phase 3: Summary Pages (LAST)
- [ ] **System Architecture generated LAST** (after all component pages)
- [ ] **Core Features generated LAST** (after all component pages)
- [ ] **ER Diagram generated LAST** (after all component pages)
- [ ] Summary pages reference data from component pages
- [ ] No component data fabricated in summary pages
- [ ] Summary pages were generated from completed component pages, not memory
- [ ] Component inventory manifest was re-read before writing summary pages
- [ ] gRPC service/method pages were re-read before architecture and feature summaries
- [ ] PowerJob pages were re-read before architecture and feature summaries (if present)
- [ ] Pulsar pages were re-read before architecture and feature summaries (if present)
- [ ] ER diagram relationships are traceable to proto messages, proto fields, enums, or generated service request/response mappings

## Completeness Checklist (Critical)

### Proto Discovery
- [ ] **ALL** proto files found (use `**/*.proto` pattern)
- [ ] Total proto file count reported
- [ ] Every proto file path listed before parsing

### Message Type Extraction (For ER Diagram)
- [ ] **ALL** Request message types extracted
- [ ] **ALL** Response message types extracted
- [ ] **ALL** DTO/Entity message types extracted
- [ ] **ALL** Enum types extracted
- [ ] Message field types and relationships recorded
- [ ] Cross-service message references identified

### Service and Method Extraction
- [ ] **ALL** `service XXX` blocks extracted from every proto file
- [ ] **ALL** `rpc XXX` methods extracted from every service
- [ ] Total service count reported
- [ ] Total RPC method count reported
- [ ] Complete list of services and methods displayed before generation

### PowerJob Discovery (Conditional)
- [ ] Checked if PowerJob dependency exists in build files
- [ ] If present: **ALL** PowerJob processors found
- [ ] Each processor: job name, cron/config, class, execute method identified
- [ ] Total PowerJob processors count reported

### Pulsar Consumer Discovery (Conditional)
- [ ] Checked if Pulsar dependency exists in build files
- [ ] If present: **ALL** Pulsar consumers found
- [ ] Each consumer: topic, subscription, class, receive method identified
- [ ] Total Pulsar consumers count reported

### Generation Verification
- [ ] One markdown file generated per RPC method
- [ ] One page per PowerJob processor (if present)
- [ ] One page per Pulsar consumer (if present)
- [ ] Generated file count equals discovered component count
- [ ] **No components skipped** (even if implementation details missing)

## Directory Structure Checklist

- [ ] `service/` directory created with gRPC documentation
- [ ] `job/` directory created **only if** PowerJob is used
- [ ] `consumer/` directory created **only if** Pulsar is used
- [ ] RPC method files are grouped by gRPC service name
- [ ] PowerJob processors grouped under `job/`
- [ ] Pulsar consumers grouped under `consumer/`
- [ ] Each component type has its own subdirectory
- [ ] Directory names match class/service names exactly
- [ ] Navigation includes all component types (gRPC, PowerJob, Pulsar)

## Source Reference Section Checklist

- [ ] Every page includes "Relevant source files" section at the top
- [ ] **All** source files used for generation are listed
- [ ] File paths are relative to project root
- [ ] Each file has a brief description of its role
- [ ] Files are formatted as bullet points
- [ ] **Each file path is a clickable link to source repository (GitHub or GitLab)**
- [ ] **Links open in new tab** (`target="_blank"` for HTML)
- [ ] GitHub URL pattern: `https://github.com/{owner}/{repo}/blob/{branch}/{path}`
- [ ] GitLab URL pattern: `https://{host}/{group}/{project}/-/blob/{branch}/{path}`
- [ ] Links to source repository included when available
- [ ] If Git remote unavailable, mark as `TODO`

## Page Structure Checklist

### gRPC Service Pages
- [ ] **# Introduction** - Overview and description of the RPC method
- [ ] **# API Definition**
  - [ ] **## Service Definition** - Proto service/method with source attribution
  - [ ] **## Request & Response** - Request/response tables with source attribution
  - [ ] **## Implementation Class** - gRPC entry and business logic with source attribution
- [ ] **# Data Model & Structure** - Proto message definitions with source attribution
- [ ] **# Business Logic Flow**
  - [ ] **## Sequence Diagram** - Mermaid sequence diagram with all participants
- [ ] **# Summary** - Conclusion, key points, warnings, examples

### PowerJob Pages
- [ ] **# Introduction** - Job purpose and description
- [ ] **# Task Definition**
  - [ ] **## Scheduling Configuration** - Job name, cron, processor with source attribution
  - [ ] **## Execution Parameters** - Job parameters and context
  - [ ] **## Implementation Class** - Processor and business logic with source attribution
- [ ] **# Data Model & Structure** - Input/output data structures with source attribution
- [ ] **# Business Logic Flow**
  - [ ] **## Sequence Diagram** - Mermaid sequence diagram
- [ ] **# Summary** - Conclusion, key points, warnings, schedule examples

### Pulsar Consumer Pages
- [ ] **# Introduction** - Consumer purpose and description
- [ ] **# Consumption Definition**
  - [ ] **## Topic Configuration** - Topic, subscription, consumer class with source attribution
  - [ ] **## Message Structure** - Message format and properties
  - [ ] **## Implementation Class** - Consumer and business logic with source attribution
- [ ] **# Data Model & Structure** - Message data model with source attribution
- [ ] **# Business Logic Flow**
  - [ ] **## Sequence Diagram** - Mermaid sequence diagram
- [ ] **# Summary** - Conclusion, key points, warnings, config examples

### ER Diagram Page (03-er-diagram.html) - GENERATED LAST
- [ ] **## Entity Relationship Diagram** - Complete ER diagram using Mermaid `erDiagram` syntax
  - [ ] **ALL Request message types included**
  - [ ] **ALL Response message types included**
  - [ ] **ALL DTO/Entity types included**
  - [ ] **ALL Enum types included**
  - [ ] Relationships shown with cardinality (`||--o{`, `}o--||`, `||--||`)
- [ ] **## Proto Message Type Statistics** - Table with counts
  - [ ] Request message count
  - [ ] Response message count
  - [ ] DTO/Entity message count
  - [ ] Enum count
  - [ ] Total message count
- [ ] **## Service & Message Relationships** - Per-service message mapping
  - [ ] Each service lists its RPC methods
  - [ ] Each method shows Request → Response mapping
- [ ] **## Core Entity Description** - Description of key entities
- [ ] **## Data Table Relationships** - Table-level relationships
- [ ] **## Cross-Service Message References** - Messages shared across services
- [ ] **## Generation Basis** - List of all proto files used

### Core Features Pages (REQUIRED) - GENERATED LAST
- [ ] **# Feature Overview** - High-level description of the system's purpose
- [ ] **## 1. {Feature Domain}** - Feature modules grouped by business domain
  - [ ] **### {Sub-feature}** - Each sub-feature with description
  - [ ] **Core Features** - Bullet points of capabilities
- [ ] **## Core Business Processes** - Mermaid sequence diagrams
  - [ ] Business process flow charts
- [ ] **## Business Feature Matrix** - Business scenario vs. feature support matrix
- [ ] **## Product Feature Architecture Diagram** - Layered architecture diagrams
  - [ ] Access Layer / Application Service Layer / Supporting Service Layer / Infrastructure Layer
- [ ] **## Feature Comparison** - Version comparison tables
- [ ] **## System Integration Capabilities** - Integration capabilities overview
- [ ] **MUST focus on business value** (NOT technical implementation details)
- [ ] **MUST NOT include** service counts, method statistics, or technical architecture
- [ ] **MUST replace all template placeholders** with actual content

## Code Attribution Checklist (Critical)

- [ ] **Every code block** has a "Sources:" line below it
- [ ] Source attribution includes **exact file path** (relative)
- [ ] Source attribution includes **line number range** (start-end)
- [ ] Single lines use `{file}:{line}` format
- [ ] Line ranges use `{file}:{start}-{end}` format
- [ ] Source link format (auto-detect from `git remote -v`):
  - GitHub: `https://github.com/{owner}/{repo}/blob/{branch}/{path}#L{start}-{end}`
  - GitLab: `https://{host}/{group}/{project}/-/blob/{branch}/{path}#L{start}-{end}`
- [ ] Source URL obtained from `git remote -v`
- [ ] Current branch obtained from `git rev-parse --abbrev-ref HEAD`
- [ ] Proto definitions have source attribution
- [ ] Java code snippets have source attribution
- [ ] Configuration files (yaml, properties) have source attribution
- [ ] SQL statements have source attribution
- [ ] JSON/XML data have source attribution

## Output Format Checklist

### HTML Rendering (Critical)
- [ ] All generated pages are rendered as HTML (not raw markdown)
- [ ] Users never see raw markdown or download `.md` files when clicking links
- [ ] Navigation links point to HTML pages or SPA routes
- [ ] If using SPA approach, URL routing works correctly

### Mermaid Diagram Rendering (Critical)
- [ ] Mermaid.js library is loaded in all pages with diagrams
- [ ] Mermaid is properly initialized (`mermaid.initialize()` called)
- [ ] Diagrams render as graphics (not displayed as raw code)
- [ ] All Mermaid code blocks have correct `class="mermaid"` attribute
- [ ] For SPA: `mermaid.init()` is called after dynamic content loads
- [ ] **Mermaid syntax follows strict rules**:
  - [ ] Participant names are single words without spaces (e.g., `participant Client as Client` not `participant Client as API Client`)
  - [ ] No angle brackets `<>` in message text (use simple descriptions)
  - [ ] No special characters in participant aliases (no parentheses, quotes, etc.)
  - [ ] Message text uses camelCase or snake_case where possible
  - [ ] Loop labels are simple text without special characters
  - [ ] Alt/else conditions use simple identifiers

### Syntax Highlighting (Critical)
- [ ] Highlight.js library is loaded in all pages (`hljs`)
- [ ] All code blocks use proper language identifiers (\`\`\`java, \`\`\`protobuf, etc.)
- [ ] **No plain \`\`\` blocks without language identifier**
- [ ] Java code displays with Java syntax highlighting (keywords, strings, comments colored)
- [ ] Proto definitions display with protobuf syntax highlighting
- [ ] JSON code displays with JSON syntax highlighting
- [ ] SQL code displays with SQL syntax highlighting
- [ ] Highlight.js languages are loaded: java, protobuf, json, yaml, sql

### Static HTML Generation
- [ ] Each page has complete HTML structure (`<html>`, `<head>`, `<body>`)
- [ ] CSS styles are included (inline or linked)
- [ ] JavaScript for interactivity is included

### SPA with Router
- [ ] Single `index.html` handles all routes
- [ ] Markdown content is dynamically loaded and rendered
- [ ] URLs use hash or history API routing (e.g., `/#/service/UserService/GetUser`)
- [ ] Direct `.md` access redirects to SPA or shows rendered content

- [ ] Proto source files include file name and line number (e.g., `api.proto (L12)`)
- [ ] Proto source links follow format: `{git-host}/{repo}/-/blob/{branch}/{path}#L{line}`
- [ ] Java implementation includes class name and line range (e.g., `ServiceImpl.java (L45-67)`)
- [ ] Java source links follow format: `{git-host}/{repo}/-/blob/{branch}/{path}#L{start}-{end}`
- [ ] When Git remote cannot be detected, source references are marked as `TODO`
- [ ] When line numbers are uncertain, file path is linked without line anchor
