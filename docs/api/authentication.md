# Authentication Guide

## Overview

PasteTrader uses JWT (JSON Web Token) based authentication for securing API endpoints. All API requests require a valid JWT token in the Authorization header.

**Tags:** [SPEC-002] [AUTH] [JWT]

---

## Authentication Flow

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Auth
    participant Database

    Client->>API: POST /auth/login (email, password)
    API->>Database: Verify user credentials
    Database-->>API: User found & password valid
    API->>Auth: create_access_token(user_id)
    Auth-->>API: JWT token
    API-->>Client: { access_token, token_type }

    Note over Client,API: Subsequent requests use JWT

    Client->>API: GET /api/v1/tools
    API->>Auth: verify_token(jwt)
    Auth-->>API: user_id
    API-->>Client: Protected data
```

---

## JWT Token Structure

JWT tokens in PasteTrader consist of three parts:

1. **Header**: Algorithm and token type
2. **Payload**: Claims (user ID, expiration)
3. **Signature**: Cryptographic signature

**Example Token:**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1NTBlODQwMC1lMjliLTQxZDQtYTcxNi00NDY2NTU0NDAwMDAiLCJleHAiOjE3Mzc1NDgwMDB9.xxx
```

**Payload Decoded:**
```json
{
  "sub": "550e8400-e29b-41d4-a716-44665540000",
  "exp": 1737548000
}
```

**Claims:**

| Claim | Description | Example |
|-------|-------------|---------|
| `sub` | Subject (User ID) | UUID string |
| `exp` | Expiration timestamp | Unix timestamp |

---

## Token Configuration

**Algorithm:** HS256 (HMAC-SHA256)

**Default Expiration:** 7 days (604,800 seconds)

**Configuration Location:** `app/core/config.py`

```python
# JWT Configuration
JWT_ALGORITHM = "HS256"
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
```

---

## Authentication Endpoints

### Login

Authenticate with email and password to receive a JWT token.

```
POST /auth/login
```

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response (200 OK):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 604800,
  "user": {
    "id": "550e8400-e29b-41d4-a716-44665540000",
    "email": "user@example.com",
    "name": "John Doe"
  }
}
```

**Error Response (401 Unauthorized):**

```json
{
  "detail": "Incorrect email or password"
}
```

---

### Token Refresh

Refresh an existing token before expiration.

```
POST /auth/refresh
```

**Request Headers:**

```
Authorization: Bearer <current-token>
```

**Response (200 OK):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 604800
}
```

**Error Response (401 Unauthorized):**

```json
{
  "detail": "Invalid or expired token"
}
```

---

### Logout

Invalidate the current token (client-side token deletion).

```
POST /auth/logout
```

**Request Headers:**

```
Authorization: Bearer <token>
```

**Response (200 OK):**

```json
{
  "message": "Successfully logged out"
}
```

---

## Using JWT Tokens

### Authorization Header

Include the JWT token in the Authorization header for all authenticated requests:

```
Authorization: Bearer <your-jwt-token>
```

### Example: Authenticated Request

```bash
curl https://api.pastetrader.com/api/v1/tools \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Example: Creating a Tool

```bash
curl -X POST https://api.pastetrader.com/api/v1/tools \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my_tool",
    "tool_type": "http",
    "config": {"url": "https://api.example.com", "method": "GET"},
    "input_schema": {"type": "object"}
  }'
```

---

## Token Validation

The API validates JWT tokens on each authenticated request using the following process:

1. **Decode Token**: Extract payload from JWT
2. **Verify Signature**: Confirm token hasn't been tampered with
3. **Check Expiration**: Ensure token hasn't expired
4. **Extract User ID**: Get subject (user ID) from claims

**Implementation:** `app/core/jwt.py`

```python
def verify_token(token: str) -> str | None:
    """Verify JWT token and return user ID."""
    payload = decode_access_token(token)
    if payload is None:
        return None
    return payload.get("sub")
```

---

## Token Expiration

Tokens expire after 7 days by default. When a token expires:

1. API returns `401 Unauthorized` with error: "Token has expired"
2. Client must re-authenticate to get a new token
3. Optional: Implement automatic token refresh

**Checking Token Expiration:**

```python
from datetime import datetime
import base64

# Decode payload (without signature verification for demo)
payload_b64 = token.split('.')[1]
payload = json.loads(base64.urlsafe_b64decode(payload_b64 + '=='))

# Check expiration
exp_timestamp = payload['exp']
exp_datetime = datetime.fromtimestamp(exp_timestamp)

if datetime.now() > exp_datetime:
    print("Token has expired")
```

---

## Security Best Practices

### Token Storage

**Recommended:**
- Store tokens in memory (React state, Vue store)
- Use httpOnly cookies for web applications
- Implement token refresh mechanism

**Avoid:**
- Storing tokens in localStorage (XSS vulnerability)
- Storing tokens in URL parameters
- Logging tokens in console or server logs

### Token Transmission

- Always use HTTPS in production
- Include tokens in Authorization header (not URL)
- Implement CORS properly
- Set appropriate CORS headers

### Token Lifecycle

- Set appropriate expiration times (7 days default)
- Implement token refresh before expiration
- Invalidate tokens on logout (optional blacklist)
- Rotate SECRET_KEY periodically

---

## Error Handling

### Common Authentication Errors

| Error | Status | Description | Solution |
|-------|--------|-------------|----------|
| Missing token | 401 | Authorization header not provided | Include `Authorization: Bearer <token>` |
| Invalid token | 401 | Token signature verification failed | Re-authenticate |
| Expired token | 401 | Token past expiration time | Re-authenticate or refresh |
| Malformed token | 401 | Token format incorrect | Ensure proper JWT format |

### Error Response Format

```json
{
  "detail": "Invalid authentication credentials",
  "code": "INVALID_TOKEN"
}
```

---

## Implementation Examples

### Python Client

```python
import requests

class PasteTraderClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.token = None

    def login(self, email: str, password: str):
        response = requests.post(
            f"{self.base_url}/auth/login",
            json={"email": email, "password": password}
        )
        response.raise_for_status()
        data = response.json()
        self.token = data["access_token"]
        return data

    def get_tools(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(
            f"{self.base_url}/api/v1/tools",
            headers=headers
        )
        response.raise_for_status()
        return response.json()

# Usage
client = PasteTraderClient("https://api.pastetrader.com")
client.login("user@example.com", "password")
tools = client.get_tools()
```

### JavaScript Client

```javascript
class PasteTraderClient {
    constructor(baseUrl) {
        this.baseUrl = baseUrl;
        this.token = null;
    }

    async login(email, password) {
        const response = await fetch(`${this.baseUrl}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await response.json();
        this.token = data.access_token;
        return data;
    }

    async getTools() {
        const response = await fetch(`${this.baseUrl}/api/v1/tools`, {
            headers: {
                'Authorization': `Bearer ${this.token}`
            }
        });
        return response.json();
    }
}

// Usage
const client = new PasteTraderClient('https://api.pastetrader.com');
await client.login('user@example.com', 'password');
const tools = await client.getTools();
```

---

## Related Documentation

- [Tool API Reference](./tools.md) - Tool endpoint authentication
- [Agent API Reference](./agents.md) - Agent endpoint authentication
- [Architecture: JWT Auth Flow](../architecture/jwt-auth-flow.md) - Architecture details
- [JWT Implementation](https://github.com/mpdavis/python-jose) - python-jose library
