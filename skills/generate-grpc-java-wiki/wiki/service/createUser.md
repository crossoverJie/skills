# createUser

## Interface Definition

Create user

### Proto Definition

```protobuf
service TestService {
    rpc createUser(CreateUserRequest) returns (CreateUserResponse){}
}

message CreateUserRequest {
    string userName = 1;
    int32 age = 2;
}

message CreateUserResponse {
    int64 userId = 1;
    bool success = 2;
}
```

**Proto Source**: [app.proto](https://github.com/username/generate-wiki/blob/main/message-queue-api/src/main/proto/app.proto)

---

## Call Flow

```mermaid
flowchart TD
    A[gRPC Client] -->|1. createUser| B[TestService.createUser]
    B -->|2. Parameter validation| C[Validation logic]
    B -->|3. Call business layer| D[Business logic layer]
    D -->|4. Data operation| E[(Database)]
    D -->|5. Return result| F[CreateUserResponse]
    F --> B
    B --> G[Return response]
```

### Flow Description

| Step | Component | Description |
|------|------|------|
| 1 | gRPC Client | Call createUser RPC interface |
| 2 | TestService | Receive gRPC request, parameter validation |
| 3-4 | Business logic layer | Execute core business logic |
| 5 | Return | Package response result |

---

## Core Logic Implementation

### 1. gRPC Entry Layer

```java
// gRPC Entry Layer - TestServiceImpl
public void createUser(CreateUserRequest request, StreamObserver<CreateUserResponse> responseObserver) {
    responseObserver.onNext(appService.createUser(request));
    responseObserver.onCompleted();
}
```

**Source Location**: [TestServiceImpl.java](https://github.com/username/generate-wiki/blob/main/test/fixtures/TestServiceImpl.java#L35-40)

### 2. Business Logic Layer

```java
// TODO: Add business logic implementation
public CreateUserResponse createUser(CreateUserRequest request) {
    // Implementation code
}
```

**Source Location**: [Service.java](#)

---

## Data Model

### CreateUserRequest

| Field | Type | Description | Required |
|------|------|------|------|
| userName | string |  |  |
| age | int32 |  |  |

### CreateUserResponse

| Field | Type | Description |
|------|------|------|
| userId | int64 |  |
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
    CreateUserRequest request = CreateUserRequest.newBuilder()
        .setUserName("example")
        .setAge(1)
        .build();

    // Call RPC method
    CreateUserResponse response = stub.createUser(request);

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
  "userId": 12345,
  "success": true
}
```

---

## Summary

### Use Cases

1. **Create resource**: Use this interface when creating new Topics or subscriptions
2. **Initialize configuration**: Set basic attributes, permissions, and limits for resources

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
| [updateUser](updateUser.md) | Update user information |
| [deleteUser](deleteUser.md) | Delete user |
