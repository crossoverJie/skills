# System Architecture

## Project Overview

generate-wiki is a microservice project based on gRPC protocol.

## Overall Architecture Diagram

```mermaid
flowchart TB
    subgraph Clients["Client Layer"]
        C1["gRPC Client"]
    end

    subgraph Server["Service Layer"]
        S1["gRPC Service"]
        S2["Business Logic Layer"]
    end

    subgraph Persistence["Persistence Layer"]
        P1["MySQL"]
    end

    C1 -->|gRPC| S1
    S1 --> S2
    S2 --> P1
```

## Module Division

| Module | Description |
|------|------|
| API Layer | Proto definitions and gRPC service interfaces |
| Service Layer | Business logic implementation |
| Persistence Layer | Database access |

## Technology Stack

- **Communication Protocol**: gRPC
- **Development Language**: Java
- **Build Tool**: Gradle
