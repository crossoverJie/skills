# {{title}}

## System Overview

{{systemOverview}}

**Note**: The system architecture page should focus on displaying **the architecture design itself**, and should NOT include statistics cards that duplicate the homepage (such as gRPC service counts, RPC method counts, scheduled job counts, etc.). These statistics should be displayed on the homepage, while the architecture page focuses on:
- Layered architecture diagram
- Service categories & responsibilities
- Core service dependencies
- Typical data flows
- Message flow architecture
- Architecture summary

## Architecture Diagram

System architecture diagram aggregated from the generated component pages. The diagram supports **scroll to zoom** and **drag to pan** for viewing details.

**HTML Structure with Zoom/Pan Controls:**
```html
<div class="mermaid-container">
    <div class="mermaid-hint">🖱️ Scroll to zoom · Drag to pan</div>
    <div class="mermaid-zoom-level">100%</div>
    <div class="mermaid-controls">
        <button class="mermaid-control-btn" onclick="zoomMermaid(this, 0.2)" title="Zoom in">+</button>
        <button class="mermaid-control-btn" onclick="zoomMermaid(this, -0.2)" title="Zoom out">−</button>
        <button class="mermaid-control-btn" onclick="resetMermaid(this)" title="Reset">⟲</button>
    </div>
    <div class="mermaid-wrapper" onmousedown="startPan(event, this)" onmousemove="pan(event, this)" onmouseup="endPan(this)" onmouseleave="endPan(this)" onwheel="wheelZoom(event, this)">
        <div class="mermaid-inner">
            <div class="mermaid">
graph TB
    subgraph ExternalSystems
        Client[Client/Gateway]
    end

    subgraph CoreServices
        {{grpcServicesDiagram}}
    end

    subgraph MessageQueue
        {{pulsarTopicsDiagram}}
    end

    subgraph ScheduledJobs
        {{powerjobDiagram}}
    end

    subgraph DataStorage
        DB[(Database)]
        Cache[(Cache)]
    end

    Client -->|gRPC| CoreServices
    CoreServices -->|produces| Pulsar
    Pulsar -->|consumes| Consumers
    Scheduler -->|triggers| ScheduledJobs
    CoreServices --> DB
    CoreServices --> Cache
            </div>
        </div>
    </div>
</div>
```

## Module Division

### gRPC Service Modules ({{grpcServiceCount}})

{{grpcServicesList}}

### Pulsar Consumer Modules ({{pulsarConsumerCount}})

{{pulsarConsumersList}}

### PowerJob Scheduled Jobs ({{powerjobCount}})

{{powerjobList}}

## Technology Stack

{{techStack}}

## Service Dependencies

```mermaid
graph LR
    {{serviceDependenciesDiagram}}
```

---

**Generation Basis**: This page is a second-pass aggregation page and MUST be generated after all component pages are complete. Before generating, you MUST re-read:
- gRPC Services: `service/**/index.html` and `service/**/*.html`
- Pulsar Consumers: `consumer/index.html` and `consumer/*/index.html` (if present)
- PowerJob Processors: `job/index.html` and `job/*/index.html` (if present)
- Phase 1 component inventory manifest

**Aggregation Results**:
- gRPC Services: {{grpcServiceCount}} services, {{grpcMethodCount}} methods
- Pulsar Consumers: {{pulsarConsumerCount}} consumers
- PowerJob Processors: {{powerjobCount}} scheduled jobs
