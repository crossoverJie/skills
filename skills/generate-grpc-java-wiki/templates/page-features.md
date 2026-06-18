# {{title}}

## Feature Overview

{{projectName}} core feature module description, covering business feature panorama, core processes, feature matrix, etc.

**Feature Design Philosophy**:
{{featureDesignDescription}}

---

## 1. {{featureDomain1}}

### {{subFeature1_1}}
{{subFeature1_1Description}}

**Core Features:**
{{subFeature1_1Points}}

### {{subFeature1_2}}
{{subFeature1_2Description}}

**Core Features:**
{{subFeature1_2Points}}

### {{subFeature1_3}}
{{subFeature1_3Description}}

**Core Features:**
{{subFeature1_3Points}}

### {{subFeature1_4}}
{{subFeature1_4Description}}

**Core Features:**
{{subFeature1_4Points}}

---

## 2. {{featureDomain2}}

### {{subFeature2_1}}
{{subFeature2_1Description}}

**Core Features:**
{{subFeature2_1Points}}

### {{subFeature2_2}}
{{subFeature2_2Description}}

**Core Features:**
{{subFeature2_2Points}}

### {{subFeature2_3}}
{{subFeature2_3Description}}

**Core Features:**
{{subFeature2_3Points}}

---

## 3. {{featureDomain3}}

### {{subFeature3_1}}
{{subFeature3_1Description}}

**Core Features:**
{{subFeature3_1Points}}

### {{subFeature3_2}}
{{subFeature3_2Description}}

**Core Features:**
{{subFeature3_2Points}}

### {{subFeature3_3}}
{{subFeature3_3Description}}

**Core Features:**
{{subFeature3_3Points}}

---

## 4. {{featureDomain4}}

### {{subFeature4_1}}
{{subFeature4_1Description}}

**Core Features:**
{{subFeature4_1Points}}

### {{subFeature4_2}}
{{subFeature4_2Description}}

**Core Features:**
{{subFeature4_2Points}}

### {{subFeature4_3}}
{{subFeature4_3Description}}

**Core Features:**
{{subFeature4_3Points}}

---

## 5. {{featureDomain5}}

### {{subFeature5_1}}
{{subFeature5_1Description}}

**Core Features:**
{{subFeature5_1Points}}

### {{subFeature5_2}}
{{subFeature5_2Description}}

**Core Features:**
{{subFeature5_2Points}}

### {{subFeature5_3}}
{{subFeature5_3Description}}

**Core Features:**
{{subFeature5_3Points}}

---

## 6. Core Business Processes

### 1. {{businessProcess1}}

{{businessProcess1Description}}

```mermaid
sequenceDiagram
{{businessProcess1SequenceDiagram}}
```

### 2. {{businessProcess2}}

{{businessProcess2Description}}

```mermaid
sequenceDiagram
{{businessProcess2SequenceDiagram}}
```

### 3. {{businessProcess3}}

{{businessProcess3Description}}

```mermaid
sequenceDiagram
{{businessProcess3SequenceDiagram}}
```

---

## 7. Business Feature Matrix

Display the support capability of business scenarios vs feature modules:

| Business Scenario | {{module1}} | {{module2}} | {{module3}} | {{module4}} | {{module5}} |
|---------|:-------:|:-------:|:-------:|:-------:|:-------:|
| {{scenario1}} | {{support1_1}} | {{support1_2}} | {{support1_3}} | {{support1_4}} | {{support1_5}} |
| {{scenario2}} | {{support2_1}} | {{support2_2}} | {{support2_3}} | {{support2_4}} | {{support2_5}} |
| {{scenario3}} | {{support3_1}} | {{support3_2}} | {{support3_3}} | {{support3_4}} | {{support3_5}} |
| {{scenario4}} | {{support4_1}} | {{support4_2}} | {{support4_3}} | {{support4_4}} | {{support4_5}} |
| {{scenario5}} | {{support5_1}} | {{support5_2}} | {{support5_3}} | {{support5_4}} | {{support5_5}} |

**Legend:**
- ✓ Fully supported
- △ Partially supported
- - Not supported

---

## 8. Product Feature Architecture Diagram

### Four-Layer Architecture

```mermaid
flowchart TB
    subgraph AccessLayer["{{accessLayerName}}"]
        A1[{{accessPoint1}}]
        A2[{{accessPoint2}}]
        A3[{{accessPoint3}}]
        A4[{{accessPoint4}}]
        A5[{{accessPoint5}}]
    end

    subgraph AppLayer["{{appLayerName}}"]
        subgraph FeatureDomain1["{{featureDomain1}}"]
            B1[{{feature1_1}}]
            B2[{{feature1_2}}]
            B3[{{feature1_3}}]
            B4[{{feature1_4}}]
        end

        subgraph FeatureDomain2["{{featureDomain2}}"]
            B5[{{feature2_1}}]
            B6[{{feature2_2}}]
            B7[{{feature2_3}}]
            B8[{{feature2_4}}]
        end

        subgraph FeatureDomain3["{{featureDomain3}}"]
            B9[{{feature3_1}}]
            B10[{{feature3_2}}]
            B11[{{feature3_3}}]
            B12[{{feature3_4}}]
        end

        subgraph FeatureDomain4["{{featureDomain4}}"]
            B13[{{feature4_1}}]
            B14[{{feature4_2}}]
            B15[{{feature4_3}}]
            B16[{{feature4_4}}]
        end
    end

    subgraph SupportLayer["{{supportLayerName}}"]
        subgraph AsyncTasks["{{asyncTaskGroup}}"]
            C1[{{asyncTask1}}]
            C2[{{asyncTask2}}]
            C3[{{asyncTask3}}]
            C4[{{asyncTask4}}]
        end

        subgraph MessageConsumers["{{consumerGroup}}"]
            C5[{{consumer1}}]
            C6[{{consumer2}}]
            C7[{{consumer3}}]
            C8[{{consumer4}}]
        end
    end

    subgraph InfraLayer["{{infraLayerName}}"]
        subgraph DataStorage["{{dataStorageGroup}}"]
            D1[({{storage1}})]
            D2[({{storage2}})]
            D3[({{storage3}})]
            D4[({{storage4}})]
        end

        subgraph ExternalSystems["{{externalSystemGroup}}"]
            D5[{{externalSystem1}}]
            D6[{{externalSystem2}}]
            D7[{{externalSystem3}}]
            D8[{{externalSystem4}}]
            D9[{{externalSystem5}}]
        end
    end

    AccessLayer --> AppLayer
    AppLayer --> SupportLayer
    SupportLayer --> InfraLayer
```

### Feature Module Panorama

```mermaid
flowchart LR
    subgraph Clients["{{clientGroup}}"]
        E1[{{client1}}]
        E2[{{client2}}]
        E3[{{client3}}]
        E4[{{client4}}]
    end

    subgraph CoreFeatures["{{coreFeatureGroup}}"]
        direction TB
        F1[{{coreFeature1}}]
        F2[{{coreFeature2}}]
        F3[{{coreFeature3}}]
        F4[{{coreFeature4}}]
        F5[{{coreFeature5}}]
        F6[{{coreFeature6}}]
        F7[{{coreFeature7}}]
        F8[{{coreFeature8}}]
    end

    subgraph BusinessScenarios["{{scenarioGroup}}"]
        direction TB
        G1[{{scenario1}}]
        G2[{{scenario2}}]
        G3[{{scenario3}}]
        G4[{{scenario4}}]
        G5[{{scenario5}}]
    end

    Clients --> CoreFeatures
    CoreFeatures --> BusinessScenarios
```

### Business Object Lifecycle

```mermaid
flowchart LR
    H1[{{lifecycleStage1}}] --> H2[{{lifecycleStage2}}]
    H2 --> H3[{{lifecycleStage3}}]
    H3 --> H4[{{lifecycleStage4}}]
    H4 --> H5[{{lifecycleStage5}}]
    H5 --> H6[{{lifecycleStage6}}]
    H6 --> H7[{{lifecycleStage7}}]
    H7 --> H8[{{lifecycleStage8}}]
    H8 --> H9[{{lifecycleStage9}}]
```

---

## 9. Feature Comparison

| Feature | {{version1}} | {{version2}} | Description |
|---------|------------|----------------|------|
| {{compareFeature1}} | {{version1Status1}} | {{version2Status1}} | {{compareDesc1}} |
| {{compareFeature2}} | {{version1Status2}} | {{version2Status2}} | {{compareDesc2}} |
| {{compareFeature3}} | {{version1Status3}} | {{version2Status3}} | {{compareDesc3}} |
| {{compareFeature4}} | {{version1Status4}} | {{version2Status4}} | {{compareDesc4}} |
| {{compareFeature5}} | {{version1Status5}} | {{version2Status5}} | {{compareDesc5}} |
| {{compareFeature6}} | {{version1Status6}} | {{version2Status6}} | {{compareDesc6}} |

---

## 10. System Integration Capabilities

| Integrated System | Main Function |
|---------|---------|
| **{{integrationSystem1}}** | {{integrationDesc1}} |
| **{{integrationSystem2}}** | {{integrationDesc2}} |
| **{{integrationSystem3}}** | {{integrationDesc3}} |
| **{{integrationSystem4}}** | {{integrationDesc4}} |
| **{{integrationSystem5}}** | {{integrationDesc5}} |
| **{{integrationSystem6}}** | {{integrationDesc6}} |

---

**Generation Basis**: This page is a second-pass aggregation page and MUST be generated after all gRPC, PowerJob, and Pulsar component pages are complete. Before generating, you MUST re-read the generated component pages and component inventory manifest, and only summarize business capabilities supported by component content.

**Usage Instructions**:

This template uses placeholders (such as `{{featureDomain1}}`, `{{subFeature1_1}}`, etc.) that need to be replaced with actual business content during generation:

1. **Feature Domains** (`{{featureDomainN}}`): e.g., "Product Management", "Order Management", "User Management", etc.
2. **Sub-features** (`{{subFeatureN_N}}`): e.g., "Merchant Products", "Inventory Management", etc. specific feature modules
3. **Business Scenarios** (`{{scenarioN}}`): e.g., "Store Self-operated", "Delivery Service", etc. actual business scenarios
4. **System Layers** (`{{accessLayerName}}`, etc.): e.g., "Access Layer", "Application Service Layer", etc. technical layers
5. **Business Processes** (`{{businessProcessN}}`): e.g., "Product Listing Flow", "Price Change Flow", etc. core processes

The generating Agent should automatically fill these placeholders based on the actual project's gRPC services, proto definitions, and Java implementations to generate core feature documentation that matches the project's reality.
