# normalMethod

## Interface Definition

Normal method

### Proto Definition

```protobuf
service NestedService {
    rpc normalMethod(Request) returns (Response){}
}

message Request {
    string id = 1;
}

message Response {
    string result = 1;
}
```

**Proto Source**: [app.proto](https://github.com/username/generate-wiki/blob/main/message-queue-api/src/main/proto/app.proto)

---

## Call Flow

```mermaid
flowchart TD
    A[gRPC Client] -->|1. normalMethod| B[NestedService.normalMethod]
    B -->|2. Parameter validation| C[Validation logic]
    B -->|3. Call business layer| D[Business logic layer]
    D -->|4. Data operation| E[(Database)]
    D -->|5. Return result| F[Response]
    F --> B
    B --> G[Return response]
```

### Flow Description

| Step | Component | Description |
|------|------|------|
| 1 | gRPC Client | Call normalMethod RPC interface |
| 2 | NestedService | Receive gRPC request, parameter validation |
| 3-4 | Business logic layer | Execute core business logic |
| 5 | Return | Package response result |

---

## Core Logic Implementation

### 1. gRPC Entry Layer

```java
// TODO: Add gRPC entry code
public Response normalMethod(Request request) {
    // Implementation code
}
```

**Source Location**: [NestedServiceGrpcImpl.java](#)

### 2. Business Logic Layer

```java
// TODO: Add business logic implementation
public Response normalMethod(Request request) {
    // Implementation code
}
```

**Source Location**: [Service.java](#)

---

## Data Model

### Request

| Field | Type | Description | Required |
|------|------|------|------|
| id | string | Unique identifier ID |  |

### Response

| Field | Type | Description |
|------|------|------|
| result | string |  |

---

## Call Example

### Java Client

```java
// Create gRPC Channel
ManagedChannel channel = ManagedChannelBuilder
    .forAddress("localhost", 9090)
    .usePlaintext()
    .build();

try {
    // Create client Stub
    MqManagerServiceGrpc.MqManagerServiceBlockingStub stub =
        MqManagerServiceGrpc.newBlockingStub(channel);

    // Build request
    Request request = Request.newBuilder()
        .setId("123456")
        .build();

    // Call RPC method
    Response response = stub.normalMethod(request);

    // Handle response
    System.out.println("Response: " + response);
} finally {
    channel.shutdown();
}
```

### curl (via gateway)

```bash
# gRPC interface needs to be called via gRPC client
# For HTTP access, use the REST interface forwarded by the gateway
```

### Response Example

```json
{
  "result": "string_value"
}
```

---

## Summary

### Use Cases

1. **Business operation**: Execute specific business logic
2. **Data management**: Manage data resources in the system

### Key Notes

<div class="info-box warning">
<strong>Warning: Notes</strong>

1. Ensure the input parameters are correct
2. Check permissions before calling
</div>

### Related APIs

| API | Description |
|------|------|
| [methodWithOptions](methodWithOptions.md) | Method with option braces |
| [getUser](getUser.md) | Get user information |
| [createUser](createUser.md) | Create user |
| [updateUser](updateUser.md) | Update user information |
| [deleteUser](deleteUser.md) | Delete user |
