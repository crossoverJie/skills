# {{title}}

## Domain Model Diagram

Display the system's core business domains, aggregate roots, entities, value objects and their relationships.

### Domain Legend

- 🔴 **Aggregate Root** - Core entry point of the domain model
- 🔵 **Entity** - Business object with unique identity
- 🟢 **Value Object** - Descriptive object without unique identity
- 🟡 **Domain Service** - Cross-entity business logic
- 🟣 **Domain Event** - Important event occurring within the domain

### Domain Model Diagram

```mermaid
graph TB
    subgraph {{domain1Name}}["{{domain1Icon}} {{domain1Name}}"]
        {{domain1Aggregate}}["{{domain1Icon}} {{domain1Aggregate}}<br/>{{domain1Desc}}"]
        {{domain1VO1}}["{{domain1VO1}}<br/>{{domain1VO1Desc}}"]
        {{domain1VO2}}["{{domain1VO2}}<br/>{{domain1VO2Desc}}"]

        {{domain1Aggregate}} --> {{domain1VO1}}
        {{domain1Aggregate}} --> {{domain1VO2}}
    end

    subgraph {{domain2Name}}["{{domain2Icon}} {{domain2Name}}"]
        {{domain2Aggregate}}["{{domain2Icon}} {{domain2Aggregate}}<br/>{{domain2Desc}}"]
        {{domain2Entity}}["📦 {{domain2Entity}}<br/>{{domain2EntityDesc}} Entity"]

        {{domain2Aggregate}} -->|contains| {{domain2Entity}}
    end

    subgraph {{domain3Name}}["{{domain3Icon}} {{domain3Name}}"]
        {{domain3Aggregate}}["{{domain3Icon}} {{domain3Aggregate}}<br/>{{domain3Desc}}"]
        {{domain3Entity}}["📦 {{domain3Entity}}<br/>{{domain3EntityDesc}} Entity"]
        {{domain3Event}}["📢 {{domain3Event}}<br/>{{domain3EventDesc}} Event"]

        {{domain3Aggregate}} -->|contains| {{domain3Entity}}
        {{domain3Aggregate}} -->|publishes| {{domain3Event}}
    end

    %% Cross-domain relationships
    {{domain1Aggregate}} -->|references| {{domain2Aggregate}}
    {{domain2Entity}} -->|references| {{domain3Aggregate}}

    subgraph DomainServices["🔌 Domain Services"]
        {{service1}}["{{service1}}<br/>{{service1Desc}}"]
        {{service2}}["{{service2}}<br/>{{service2Desc}}"]
    end

    %% Service-domain relationships
    {{service1}} -.->|operates on| {{domain1Aggregate}}
    {{service2}} -.->|operates on| {{domain2Aggregate}}
```

### Domain Description

| Domain | Aggregate Root | Entities | Value Objects | Domain Events |
|------|--------|------|--------|----------|
| {{domain1Name}} | {{domain1Aggregate}} | {{domain1Entities}} | {{domain1VOs}} | {{domain1Events}} |
| {{domain2Name}} | {{domain2Aggregate}} | {{domain2Entities}} | {{domain2VOs}} | {{domain2Events}} |
| {{domain3Name}} | {{domain3Aggregate}} | {{domain3Entities}} | {{domain3VOs}} | {{domain3Events}} |

## Entity Relationship Diagram

Complete entity relationship diagram generated based on analysis of all Proto files.

### ER Diagram Legend

```markdown
Entity relationship types:
- ||--o{ : One-to-Many (1:N)
- ||--|| : One-to-One (1:1)
- }o--o{ : Many-to-Many (N:M)

Field identifiers:
- PK: Primary Key
- FK: Foreign Key
```

### Overall ER Diagram

```mermaid
erDiagram
    {{erDiagram}}
```

## Core Entity Details

{{entityCards}}

### Example Entity Card Structure

```html
<div class="entity-card">
    <div class="entity-header">
        <span class="entity-icon">📦</span>
        <h3>ENTITY_NAME - Entity Description</h3>
    </div>
    <div class="entity-body">
        <table class="entity-table">
            <thead>
                <tr><th>Field</th><th>Type</th><th>Description</th></tr>
            </thead>
            <tbody>
                <tr><td class="field-pk">id</td><td>int64</td><td>Primary Key ID</td></tr>
                <tr><td class="field-fk">ref_id</td><td>int64</td><td>Foreign Key Reference</td></tr>
                <tr><td>name</td><td>string</td><td>Name</td></tr>
            </tbody>
        </table>
    </div>
</div>
```

## Proto Message Type Statistics

| Type | Count | Description |
|-----|------|------|
| Request messages | {{requestMessageCount}} | RPC request parameter classes |
| Response messages | {{responseMessageCount}} | RPC response result classes |
| DTO/Entity | {{dtoMessageCount}} | Data transfer/entity classes |
| Enum | {{enumCount}} | Enum definitions |
| **Total** | **{{totalMessageCount}}** | All message types |

## Service & Message Relationships

### gRPC Service Method Message Mapping

{{serviceMessageMapping}}

```
Service Name
├── RPC Method Name
│   ├── Request: Request message class
│   └── Response: Response message class
└── ...
```

## Entity Relationship Description

{{entityRelationships}}

### Key Relationship Types

- **One-to-One (1:1)**: Unique correspondence between master and slave entities
- **One-to-Many (1:N)**: Aggregate root contains multiple child entities
- **Many-to-Many (N:M)**: Relationships established through junction tables/association entities

## Cross-Service Message References

{{crossServiceMessages}}

- Identify message types shared by multiple services
- Describe message passing relationships between different services
- Record data dependencies during cross-service calls

---

**Generation Basis**: This ER diagram is a second-pass aggregation page and MUST be generated after all service method pages are complete. Before generating, you MUST re-read:

{{protoFilesList}}

And also:
- Generated `service/**/index.html`
- Generated `service/**/*.html`
- Phase 1 component inventory manifest

**Included Content**:
- All Request/Response message classes ({{requestMessageCount}} + {{responseMessageCount}})
- All DTO/Entity classes ({{dtoMessageCount}})
- All Enum types ({{enumCount}})
- References and dependencies between messages
- Request → Response mappings from service method pages

**Page Features**:
- 🖱️ **Scroll to zoom**: Mouse wheel to zoom in/out of the diagram
- 🖱️ **Drag to pan**: Hold left mouse button to drag and move the diagram
- 🔍 **Zoom controls**: Buttons in the bottom-right corner for precise zoom control
- 🔄 **Reset view**: One-click to restore default zoom and position
