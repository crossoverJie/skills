# deleteUser

## Interface Definition

Delete user

### Proto Definition

```protobuf
service TestService {
    rpc deleteUser(DeleteUserRequest) returns (DeleteUserResponse){}
}

message DeleteUserRequest {
    int64 userId = 1;
}

message DeleteUserResponse {
    bool success = 1;
}
```

**Proto Source**: [app.proto](https://github.com/username/generate-wiki/blob/main/message-queue-api/src/main/proto/app.proto)

---

## Call Flow

```mermaid
flowchart TD
    A[gRPC Client] -->|1. deleteUser| B[TestService.deleteUser]
    B -->|2. Parameter validation| C[Validation logic]
    B -->|3. Call business layer| D[Business logic layer]
    D -->|4. Data operation| E[(Database)]
    D -->|5. Return result| F[DeleteUserResponse]
    F --> B
    B --> G[Return response]
```

### Flow Description

| Step | Component | Description |
|------|------|------|
| 1 | gRPC Client | Call deleteUser RPC interface |
| 2 | TestService | Receive gRPC request, parameter validation |
| 3-4 | Business logic layer | Execute core business logic |
| 5 | Return | Package response result |

---

## Core Logic Implementation

### 1. gRPC Entry Layer

```java
// TODO: Add gRPC entry code
public DeleteUserResponse deleteUser(DeleteUserRequest request) {
    // Implementation code
}
```

**Source Location**: [TestServiceGrpcImpl.java](#)

### 2. Business Logic Layer

```java
// TODO: Add business logic implementation
public DeleteUserResponse deleteUser(DeleteUserRequest request) {
    // Implementation code
}
```

**Source Location**: [Service.java](#)

---

## Data Model

### DeleteUserRequest

| Field | Type | Description | Required |
|------|------|------|------|
| userId | int64 |  |  |

### DeleteUserResponse

| Field | Type | Description |
|------|------|------|
| success | bool |  |

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
    DeleteUserRequest request = DeleteUserRequest.newBuilder()
        .setUserId(1)
        .build();

    // Call RPC method
    DeleteUserResponse response = stub.deleteUser(request);

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
  "success": true
}
```

---

## Summary

### Use Cases

1. **Clean up resources**: Delete Topics or subscriptions that are no longer in use
2. **Service decommission**: Clean up related resources as part of the application decommission process

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
| [normalMethod](normalMethod.md) | Normal method |
| [getUser](getUser.md) | Get user information |
| [createUser](createUser.md) | Create user |
| [updateUser](updateUser.md) | Update user information |
