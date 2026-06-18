# getUser

## Interface Definition

Get user information

### Proto Definition

```protobuf
service TestService {
    rpc getUser(GetUserRequest) returns (GetUserResponse){}
}

message GetUserRequest {
    int64 userId = 1;
    string userName = 2;
}

message GetUserResponse {
    int64 userId = 1;
    string userName = 2;
    int32 age = 3;
    repeated string tags = 4;
}
```

**Proto Source**: [app.proto](https://github.com/username/generate-wiki/blob/main/message-queue-api/src/main/proto/app.proto)

---

## Call Flow

```mermaid
flowchart TD
    A[gRPC Client] -->|1. getUser| B[TestService.getUser]
    B -->|2. Parameter validation| C[Validation logic]
    B -->|3. Call business layer| D[Business logic layer]
    D -->|4. Data operation| E[(Database)]
    D -->|5. Return result| F[GetUserResponse]
    F --> B
    B --> G[Return response]
```

### Flow Description

| Step | Component | Description |
|------|------|------|
| 1 | gRPC Client | Call getUser RPC interface |
| 2 | TestService | Receive gRPC request, parameter validation |
| 3-4 | Business logic layer | Execute core business logic |
| 5 | Return | Package response result |

---

## Core Logic Implementation

### 1. gRPC Entry Layer

```java
// gRPC Entry Layer - TestServiceImpl
public void getUser(GetUserRequest request, StreamObserver<GetUserResponse> responseObserver) {
    responseObserver.onNext(appService.getUser(request));
    responseObserver.onCompleted();
}
```

**Source Location**: [TestServiceImpl.java](https://github.com/username/generate-wiki/blob/main/test/fixtures/TestServiceImpl.java#L22-27)

### 2. Business Logic Layer

```java
// TODO: Add business logic implementation
public GetUserResponse getUser(GetUserRequest request) {
    // Implementation code
}
```

**Source Location**: [Service.java](#)

---

## Data Model

### GetUserRequest

| Field | Type | Description | Required |
|------|------|------|------|
| userId | int64 |  |  |
| userName | string |  |  |

### GetUserResponse

| Field | Type | Description |
|------|------|------|
| userId | int64 |  |
| userName | string |  |
| age | int32 |  |
| tags | repeated string |  |

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
    GetUserRequest request = GetUserRequest.newBuilder()
        .setUserId(1)
        .setUserName("example")
        .build();

    // Call RPC method
    GetUserResponse response = stub.getUser(request);

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
  "userName": "string_value",
  "age": 12345,
  "tags": "string_value"
}
```

---

## Summary

### Use Cases

1. **Query details**: Get detailed configuration and status information of a resource
2. **Monitoring and troubleshooting**: View resource runtime status for issue investigation

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
| [createUser](createUser.md) | Create user |
| [updateUser](updateUser.md) | Update user information |
| [deleteUser](deleteUser.md) | Delete user |
