# Core Features

## Feature Module List

### NestedService

- **methodWithOptions**: Method with option braces
- **normalMethod**: Normal method

### TestService

- **getUser**: Get user information
- **createUser**: Create user
- **updateUser**: Update user information
- **deleteUser**: Delete user

### AdminService

- **queryUsers**: Query all users
- **disableUser**: Disable user



## Core Business Processes

```mermaid
flowchart TB
    A[Client] --> B[gRPC Service]
    B --> C[Business Logic]
    C --> D[Database]
    C --> E[External System]
```

## Detailed Description

TODO: Add detailed description for each feature
