# generate-wiki Skill Design Document

## 1. Overall Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    generate-wiki skill                   │
├─────────────────────────────────────────────────────────┤
│  1. Project Structure Analysis                          │
│     ├── Find proto files                                │
│     ├── Find Java source directories                    │
│     └── Detect project type (Maven/Gradle)              │
│                                                          │
│  2. Parse Proto Files                                   │
│     ├── Extract service definitions                     │
│     ├── Extract message definitions                     │
│     └── Generate interface metadata                     │
│                                                          │
│  3. Analyze Java Code                                   │
│     ├── Find Service implementation classes             │
│     ├── Extract method comments                         │
│     └── Find entity classes/DAOs                        │
│                                                          │
│  4. Generate Wiki Files                                 │
│     ├── Copy template files (HTML/CSS/JS)               │
│     ├── Generate system-architecture.md                 │
│     ├── Generate core-features.md                       │
│     ├── Generate er-diagram.md                          │
│     └── Generate service/*.md API documentation         │
└─────────────────────────────────────────────────────────┘
```

## 2. Input Detection

### 2.1 Project Structure Identification

```javascript
// Detected project information
const projectInfo = {
  name: "message-queue",                    // Obtained from pom.xml/build.gradle
  type: "maven",                         // maven | gradle
  protoFiles: [                          // Proto file list
    "message-queue-api/src/main/proto/app.proto"
  ],
  javaSourceDirs: [                      // Java source directories
    "message-queue-core/src/main/java"
  ],
  gitRepo: "org-group/message-queue", // Obtained from git remote
  baseBranch: "main"                     // Default branch
};
```

### 2.2 Proto Parsing

```javascript
// Parsed proto structure
const protoInfo = {
  services: [
    {
      name: "MqManagerService",
      methods: [
        {
          name: "addTopic",
          input: "TopicFromRequest",
          output: "TopicFormResponse",
          comments: "Create new topic"
        }
      ]
    }
  ],
  messages: {
    "TopicFromRequest": {
      fields: [
        { name: "name", type: "string", number: 1, comments: "Topic name" }
      ]
    }
  }
};
```

## 3. Output Structure

```
wiki/
├── index.html                    # Main page (built-in template)
├── assets/
│   ├── css/
│   │   └── style.css            # Style file (built-in template)
│   └── js/
│       └── nav.js               # Navigation interaction (built-in template)
├── 01-system-architecture.md    # System architecture document (generated framework)
├── 02-core-features.md          # Core features document (generated framework)
├── 03-er-diagram.md             # ER diagram document (generated framework)
└── service/                     # API documentation directory
    └── addTopic.md              # One document per RPC method
```

## 4. Template System

### 4.1 Built-in Templates (directly embedded in skill)

- **index.html**: Main page framework, contains navigation structure
- **style.css**: Style definitions
- **nav.js**: Interaction logic

### 4.2 Document Templates

Use JavaScript template strings with variable substitution support:

```javascript
// service.md template
const serviceTemplate = (data) => `# ${data.methodName}

## Interface Definition

${data.methodComments}

### Proto Definition

\`\`\`protobuf
${data.protoDefinition}
\`\`\`

**Source Location**: [${data.sourceFile}#L${data.lineStart}-${data.lineEnd}](${data.gitUrl})

---

## Call Flow

\`\`\`mermaid
${data.flowchart}
\`\`\`

### Flow Description

${data.flowSteps}

---

## Core Logic Implementation

### 1. gRPC Entry Layer

\`\`\`java
// ${data.grpcSourceLocation}
${data.grpcCode}
\`\`\`

**Source Location**: [${data.grpcSourceFile}](${data.grpcGitUrl})

---

## Data Model

${data.dataModel}

## Request Model

### ${data.requestType}

\`\`\`java
// ${data.requestType}.java
${data.requestModel}
\`\`\`

### Validation Rules

${data.validationRules}

---

## Call Example

### Java Client

\`\`\`java
// Java call example
${data.javaExample}
\`\`\`

---

## Summary

### Use Cases

1. **Scenario 1**: Description
2. **Scenario 2**: Description

### Key Notes

<div class="info-box warning">
<strong>⚠️ Notes</strong>

${data.warnings}
</div>

### Related APIs

| API | Description |
|------|------|
${data.relatedApis}
`;
```

## 5. Key Implementation Logic

### 5.1 Proto File Parsing

```javascript
// Use regular expressions to extract proto definitions
function parseProto(content) {
  // Extract service
  const serviceMatch = content.match(/service\s+(\w+)\s*\{([^}]+)\}/s);
  // Extract rpc methods
  const rpcMatches = content.matchAll(/rpc\s+(\w+)\s*\(\s*(\w+)\s*\)\s*returns\s*\(\s*(\w+)\s*\)/g);
  // Extract message
  const messageMatches = content.matchAll(/message\s+(\w+)\s*\{([^}]+)\}/gs);
}
```

### 5.2 Java Source Code Location

```javascript
// Find Service implementation class
function findServiceImpl(projectDir, serviceName) {
  // Search for *ServiceImpl.java or *Grpc.java
  // Match the implementation of the addTopic method
  // Return file path, line number range
}

// Extract method code
function extractMethodCode(filePath, methodName) {
  // Read file
  // Locate method
  // Extract method body (including comments)
  // Return code snippet and line numbers
}
```

### 5.3 Git Link Generation

```javascript
// Generate GitHub/GitLab links (auto-detect platform from git remote)
function generateGitUrl(filePath, lineStart, lineEnd) {
  const remoteUrl = getGitRemoteUrl();
  const branch = getGitBranch();
  const relativePath = getRelativePath(filePath);

  if (remoteUrl.includes('github.com')) {
    const [owner, repo] = parseGitHubRemote(remoteUrl);
    return `https://github.com/${owner}/${repo}/blob/${branch}/${relativePath}#L${lineStart}-${lineEnd}`;
  } else {
    const [group, project] = parseGitLabRemote(remoteUrl);
    return `https://${gitlabHost}/${group}/${project}/-/blob/${branch}/${relativePath}#L${lineStart}-${lineEnd}`;
  }
}
```

## 6. Usage Flow

```
1. User executes /generate-wiki
   │
2. Skill detects project structure
   ├── Read pom.xml/build.gradle to get project name
   ├── Find proto files
   ├── Find Java source directories
   └── Get git repository information
   │
3. Create wiki/ directory
   │
4. Copy built-in templates
   ├── index.html
   ├── assets/css/style.css
   └── assets/js/nav.js
   │
5. Generate 01-system-architecture.md (framework)
6. Generate 02-core-features.md (framework)
7. Generate 03-er-diagram.md (framework)
8. Parse proto files
   └── Generate service/*.md for each rpc method
   │
9. Update index.html navigation menu
   └── Generate navigation links based on proto services
   │
10. Output completion report
    └── Prompt user for content that needs manual completion
```

## 7. Extensibility Design

### 7.1 Configuration File Support

Support reading `.wiki-config.json` from project root directory:

```json
{
  "projectName": "Custom project name",
  "protoDir": "custom/proto/path",
  "javaSourceDir": "custom/java/path",
  "gitUrl": "https://custom-git.com/repo/project",
  "branch": "develop",
  "excludeServices": ["HealthCheck", "InternalService"],
  "includePackages": ["com.example.*"]
}
```

### 7.2 Custom Templates

If a `wiki-templates/` directory exists in the project root, custom templates take priority:

```
wiki-templates/
├── index.html          # Override default template
├── service.md          # Custom API documentation template
├── system-arch.md      # Custom system architecture template
└── er-diagram.md       # Custom ER diagram template
```

## 8. CLI Parameter Design

```bash
# Generate wiki to specified directory
/generate-wiki --output docs/

# Only generate API documentation
/generate-wiki --only-service

# Overwrite existing files during generation
/generate-wiki --force

# Specify proto file path
/generate-wiki --proto custom/path/app.proto

# Debug mode (output more information)
/generate-wiki --verbose
```

## 9. Technology Selection

| Component | Choice | Reason |
|------|------|------|
| Script language | Node.js | Claude Code native support, convenient file operations |
| Template engine | JavaScript template strings | Simple, no additional dependencies |
| File traversal | fs + glob | Standard Node API |
| Code highlighting | highlight.js (CDN) | Frontend rendering, no server-side needed |
| Markdown rendering | marked.js (CDN) | Mature, supports custom renderer |
| Diagram rendering | mermaid.js (CDN) | Supports flowcharts, sequence diagrams, ER diagrams |
