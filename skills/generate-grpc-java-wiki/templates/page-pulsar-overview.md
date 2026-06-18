# Pulsar Consumers Overview Template

## Template Structure

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pulsar Consumers - Message Consumer Overview</title>
    <link rel="stylesheet" href="../assets/css/style.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css">
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
</head>
<body>
    <div class="wiki-container">
        <aside class="sidebar" id="sidebar-nav-root"></aside>

        <main class="main-content">
            <div class="breadcrumbs">
                <a href="../index.html">Home</a>
                <span class="separator">/</span>
                <span class="current">Pulsar Consumers</span>
            </div>

            <div class="service-header">
                <div class="service-icon">📨</div>
                <div class="service-title">
                    <h1>Pulsar Consumers</h1>
                    <p>Message queue consumer overview - Apache Pulsar async message processing system</p>
                </div>
            </div>

            <!-- Statistics cards -->
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon">🔢</div>
                    <div class="stat-value">{{totalCount}}</div>
                    <div class="stat-label">Total Consumers</div>
                </div>
                <div class="stat-card active">
                    <div class="stat-icon">✅</div>
                    <div class="stat-value">{{activeCount}}</div>
                    <div class="stat-label">Active Status</div>
                </div>
                <div class="stat-card inactive">
                    <div class="stat-icon">⏸️</div>
                    <div class="stat-value">{{inactiveCount}}</div>
                    <div class="stat-label">Inactive Status</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">📊</div>
                    <div class="stat-value">{{activePercentage}}%</div>
                    <div class="stat-label">Active Ratio</div>
                </div>
            </div>

            <div class="content-section">
                <h2>Message Flow Architecture</h2>
                <p>
                    The diagram below shows the complete flow of Pulsar messages, including upstream producers, topic routing, and dependencies between consumers.
                    Messages are uniformly packaged and sent by business services, and consumers may trigger downstream messages after processing, forming a complete event-driven chain.
                </p>

                <div class="mermaid">
flowchart TB
    subgraph Sources["📤 Message Source Layer"]
        MS[MessageService<br/>Unified message packaging]
        API[gRPC API Service]
        Job[PowerJob Scheduled Task]
        Ext[External System]
    end

    subgraph PulsarTopics["📨 Pulsar Topic Layer"]
        {{#each topics}}
        T{{index}}[{{name}}<br/>{{description}}]
        {{/each}}
    end

    subgraph Consumers["📥 Message Consumer Layer"]
        {{#each consumerGroups}}
        subgraph {{groupId}}["{{groupIcon}} {{groupName}}"]
            {{#each consumers}}
            C{{index}}[{{name}}]
            {{/each}}
        end
        {{/each}}
    end

    %% Message sources to Topics
    MS --> {{#each topicsFromMessageService}}T{{index}}{{/each}}
    API --> {{#each topicsFromApi}}T{{index}}{{/each}}
    Job --> {{#each topicsFromJob}}T{{index}}{{/each}}
    Ext --> {{#each topicsFromExternal}}T{{index}}{{/each}}

    %% Topics to consumers
    {{#each topicConsumerMappings}}
    T{{topicIndex}} --> C{{consumerIndex}}
    {{/each}}

    %% Message triggers between consumers
    {{#each consumerDependencies}}
    C{{sourceIndex}} -.->|{{triggerEvent}}| T{{targetTopicIndex}}
    {{/each}}

    style Sources fill:#e0e7ff
    style PulsarTopics fill:#dbeafe
    style Consumers fill:#d1fae5
                </div>
            </div>

            <div class="content-section">
                <h2>Consumer Dependencies</h2>
                <p>Display the call chains and message trigger relationships between consumers. Dashed lines indicate downstream consumption triggered by sending messages.</p>

                <div class="dependency-grid">
                    {{#each dependencyGroups}}
                    <div class="dependency-card">
                        <div class="dependency-header">
                            <span class="dependency-icon">{{icon}}</span>
                            <span class="dependency-title">{{title}}</span>
                        </div>
                        <div class="dependency-body">
                            {{#each dependencies}}
                            <div class="dependency-item">
                                <span class="dep-source">{{source}}</span>
                                <span class="dep-arrow">➜</span>
                                <span class="dep-target">{{target}}</span>
                            </div>
                            <div class="dependency-desc">
                                {{description}}
                            </div>
                            {{/each}}
                            {{#if hasChain}}
                            <div class="dependency-chain">
                                {{#each chain}}
                                <span class="chain-item">{{name}}</span>
                                {{#unless @last}}<span class="chain-arrow">➜</span>{{/unless}}
                                {{/each}}
                            </div>
                            <div class="dependency-desc">
                                {{chainDescription}}
                            </div>
                            {{/if}}
                        </div>
                    </div>
                    {{/each}}
                </div>
            </div>

            <div class="content-section">
                <h2>Consumer Categories</h2>

                {{#each consumerGroups}}
                <div class="consumer-group">
                    <h3 class="group-header">
                        <span class="group-icon">{{icon}}</span>
                        <span class="group-title">{{groupName}}</span>
                        <span class="group-count">{{count}} consumers</span>
                    </h3>
                    <div class="consumer-cards">
                        {{#each consumers}}
                        <a href="{{name}}/index.html" class="consumer-card {{status}}">
                            <div class="card-header">
                                <span class="card-name">{{name}}</span>
                                <span class="badge {{status}}">{{statusText}}</span>
                            </div>
                            <div class="card-topic">Topic: <code>{{topic}}</code></div>
                            <div class="card-desc">{{description}}</div>
                            <div class="card-meta">
                                <span class="meta-item">📦 {{serialization}}</span>
                                <span class="meta-item">{{tagIcon}} {{tagText}}</span>
                            </div>
                        </a>
                        {{/each}}
                    </div>
                </div>
                {{/each}}
            </div>

            <div class="content-section">
                <h2>Message Serialization Statistics</h2>
                <table class="table">
                    <tr><th>Serialization Type</th><th>Consumer Count</th><th>Percentage</th><th>Typical Consumer</th></tr>
                    {{#each serializationStats}}
                    <tr>
                        <td><code>{{type}}</code></td>
                        <td>{{count}}</td>
                        <td>{{percentage}}%</td>
                        <td>{{examples}}</td>
                    </tr>
                    {{/each}}
                </table>
            </div>

            <div class="content-section">
                <h2>Consumer Status Details</h2>
                <div class="two-column">
                    <div class="column">
                        <h3>Active Status ({{activeCount}})</h3>
                        <ul class="status-list">
                            {{#each activeConsumers}}
                            <li><span class="badge success">Active</span> {{name}}</li>
                            {{/each}}
                        </ul>
                    </div>
                    <div class="column">
                        <h3>Inactive Status ({{inactiveCount}})</h3>
                        <ul class="status-list">
                            {{#each inactiveConsumers}}
                            <li><span class="badge warning">Inactive</span> {{name}} <small>({{reason}})</small></li>
                            {{/each}}
                        </ul>
                    </div>
                </div>
            </div>

            <div class="content-section">
                <h2>Technical Specifications</h2>
                <table class="table">
                    <tr><th>Config Item</th><th>Value</th><th>Description</th></tr>
                    <tr>
                        <td>Message Platform</td>
                        <td>Apache Pulsar</td>
                        <td>Distributed message streaming platform</td>
                    </tr>
                    <tr>
                        <td>Consumer Framework</td>
                        <td>PulsarBusinessConsumer</td>
                        <td>Extended from <code>AbstractPulsarBusinessConsumer</code></td>
                    </tr>
                    <tr>
                        <td>Tenant</td>
                        <td><code>biz</code></td>
                        <td>Pulsar tenant name</td>
                    </tr>
                    <tr>
                        <td>Thread Pool</td>
                        <td><code>pulsarMsgThreadPoolExecutor</code></td>
                        <td>Dedicated thread pool for message consumption</td>
                    </tr>
                </table>
            </div>

            <div class="content-section">
                <h2>Relevant Source Files</h2>
                <ul class="file-list">
                    <li><a href="{{gitUrl}}/blob/{{branch}}/{{consumerDir}}" target="_blank">{{consumerDir}}</a> - Pulsar consumer implementation directory</li>
                </ul>
            </div>
        </main>
    </div>

    <script>
        mermaid.initialize({
            startOnLoad: true,
            theme: 'default',
            securityLevel: 'loose'
        });
    </script>
    <script src="../assets/js/nav-data.js"></script>
    <script src="../assets/js/nav.js"></script>
</body>
</html>
```

## Variables

| Variable | Description |
|----------|-------------|
| `{{totalCount}}` | Total number of consumers |
| `{{activeCount}}` | Number of active consumers |
| `{{inactiveCount}}` | Number of inactive consumers |
| `{{activePercentage}}` | Percentage of active consumers |
| `{{consumerGroups}}` | Array of consumer groups |
| `{{serializationStats}}` | Serialization type statistics |
| `{{activeConsumers}}` | List of active consumers |
| `{{inactiveConsumers}}` | List of inactive consumers with reasons |
| `{{gitUrl}}` | Git repository URL |
| `{{branch}}` | Git branch name |
| `{{consumerDir}}` | Consumer source directory |

## CSS Classes Required

- `.stats-grid` - Grid layout for stat cards
- `.stat-card` - Individual stat card
- `.stat-card.active` - Active status styling
- `.stat-card.inactive` - Inactive status styling
- `.consumer-group` - Consumer group section
- `.group-header` - Group header with icon and count
- `.consumer-cards` - Grid of consumer cards
- `.consumer-card` - Individual consumer card
- `.consumer-card.active/inactive` - Status variants
- `.two-column` - Two column layout
- `.status-list` - Status list styling
- **NEW**: `.dependency-grid` - Grid layout for dependency cards
- **NEW**: `.dependency-card` - Individual dependency relationship card
- **NEW**: `.dependency-header` - Card header with icon and title
- **NEW**: `.dependency-body` - Card body container
- **NEW**: `.dependency-item` - Single dependency row (source -> target)
- **NEW**: `.dep-source` - Source consumer styling (blue badge)
- **NEW**: `.dep-target` - Target consumer styling (green badge)
- **NEW**: `.dependency-desc` - Description text with code highlight
- **NEW**: `.dependency-chain` - Horizontal chain display
- **NEW**: `.chain-item` - Chain node styling

## New Template Variables

### Message Flow Variables

| Variable | Description |
|----------|-------------|
| `{{topics}}` | Array of all Pulsar topics |
| `{{topics.*.name}}` | Topic name (e.g., "merchantItem") |
| `{{topics.*.description}}` | Topic description |
| `{{topicsFromMessageService}}` | Topics sent by MessageService |
| `{{topicsFromApi}}` | Topics sent by gRPC API |
| `{{topicsFromJob}}` | Topics sent by PowerJob |
| `{{topicsFromExternal}}` | Topics from external systems |
| `{{topicConsumerMappings}}` | Topic to consumer mappings |
| `{{consumerDependencies}}` | Consumer trigger relationships |

### Dependency Variables

| Variable | Description |
|----------|-------------|
| `{{dependencyGroups}}` | Array of dependency groups |
| `{{dependencyGroups.*.icon}}` | Group icon emoji |
| `{{dependencyGroups.*.title}}` | Group title |
| `{{dependencyGroups.*.dependencies}}` | Array of dependencies |
| `{{dependencies.*.source}}` | Source consumer name |
| `{{dependencies.*.target}}` | Target consumer name |
| `{{dependencies.*.description}}` | Relationship description |
| `{{dependencyGroups.*.hasChain}}` | Boolean for chain display |
| `{{dependencyGroups.*.chain}}` | Array of chain nodes |
| `{{dependencyGroups.*.chainDescription}}` | Chain description text |
