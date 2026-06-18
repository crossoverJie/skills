# queryUsers

## Interface Definition

Query all users

### Proto Definition

```protobuf
service AdminService {
    rpc queryUsers(QueryUsersRequest) returns (QueryUsersResponse){}
}

message QueryUsersRequest {
    int32 page = 1;
    int32 size = 2;
}

message QueryUsersResponse {
    repeated GetUserResponse users = 1;
    int32 total = 2;
}
```

**Proto Source**: [app.proto](https://github.com/username/generate-wiki/blob/main/message-queue-api/src/main/proto/app.proto)

---

## Call Flow

```mermaid
flowchart TD
    A[gRPC Client] -->|1. queryUsers| B[AdminService.queryUsers]
    B -->|2. Parameter validation| C[Validation logic]
    B -->|3. Call business layer| D[Business logic layer]
    D -->|4. Data operation| E[(Database)]
    D -->|5. Return result| F[QueryUsersResponse]
    F --> B
    B --> G[Return response]
```

### Flow Description

| Step | Component | Description |
|------|------|------|
| 1 | gRPC Client | Call queryUsers RPC interface |
| 2 | AdminService | Receive gRPC request, parameter validation |
| 3-4 | Business logic layer | Execute core business logic |
| 5 | Return | Package response result |

---

## Core Logic Implementation

### 1. gRPC Entry Layer

```java
// TODO: Add gRPC entry code
public QueryUsersResponse queryUsers(QueryUsersRequest request) {
    // Implementation code
}
```

**Source Location**: [AdminServiceGrpcImpl.java](#)

### 2. Business Logic Layer

```java
// TODO: Add business logic implementation
public QueryUsersResponse queryUsers(QueryUsersRequest request) {
    // Implementation code
}
```

**Source Location**: [Service.java](#)

---

## Data Model

### QueryUsersRequest

| Field | Type | Description | Required |
|------|------|------|------|
| page | int32 |  |  |
| size | int32 | Current page record count |  |

### QueryUsersResponse

| Field | Type | Description |
|------|------|------|
| users | repeated GetUserResponse |  |
| total | int32 | Total record count |

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
    QueryUsersRequest request = QueryUsersRequest.newBuilder()
        .setPage(1)
        .setSize(1)
        .build();

    // Call RPC method
    QueryUsersResponse response = stub.queryUsers(request);

    // Handle response
    System.out.println("Response: " + response);
} finally {
    channel.shutdown();
}
```

### curl (via gateway)

```bash
# gRPC interface needs to be called via gRPC client
# For HTTP access, please use REST interface forwarded through gateway
```

### Response Example

```json
{
  "users": "",
  "total": 12345
}
```

---

## Summary

### Use Cases

1. **Query details**: Get detailed configuration and status information of resources
2. **Monitoring troubleshooting**: View resource running status for problem troubleshooting

### Key Notes

<div class="info-box warning">
<strong>⚠️ Notes</strong>

1. Please ensure the input parameters are correct
2. Check permissions before calling
</div>

### Related APIs

| API | Description |
|------|------|
| [methodWithOptions](methodWithOptions.md) | Method with option braces |
| [normalMethod](normalMethod.md) | Normal method |
| [getUser](getUser.md) | Get user information |
| [createUser](createUser.md) | Create user |
| [updateUser](updateUser.md) | Update user information |
