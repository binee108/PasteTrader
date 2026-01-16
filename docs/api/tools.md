# Tool API Reference

## Overview

The Tool API provides comprehensive CRUD operations for managing tools in the PasteTrader platform. Tools are executable units that can perform various operations such as HTTP requests, Python code execution, shell commands, MCP server calls, and builtin operations.

**Base URL:** `/api/v1/tools`

**Authentication:** JWT Bearer Token (Required for all endpoints)

**Tags:** [SPEC-009] [API] [TOOL]

---

## Tool Types

PasteTrader supports five types of tools:

| Type | Description | Required Config Fields |
|------|-------------|----------------------|
| `http` | HTTP/HTTPS API calls | `url`, `method` |
| `mcp` | MCP (Model Context Protocol) server calls | `server_url` |
| `python` | Python code execution | `code` |
| `shell` | Shell command execution | `command` |
| `builtin` | Built-in system operations | Varies by operation |

---

## Endpoints

### 1. List Tools

Retrieve a paginated list of tools with optional filtering.

```
GET /api/v1/tools
```

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `skip` | integer | No | 0 | Number of records to skip |
| `limit` | integer | No | 20 | Page size |
| `tool_type` | string | No | - | Filter by tool type |
| `is_active` | boolean | No | - | Filter by active status |
| `is_public` | boolean | No | - | Filter by public status |

**Response (200 OK):**

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "price_fetcher",
      "tool_type": "http",
      "is_active": true,
      "is_public": false,
      "created_at": "2026-01-13T09:00:00+09:00"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 20,
  "pages": 1
}
```

---

### 2. Create Tool

Create a new tool with the provided configuration.

```
POST /api/v1/tools
```

**Request Body:**

```json
{
  "name": "price_fetcher",
  "description": "Fetches stock price data from external API",
  "tool_type": "http",
  "config": {
    "url": "https://api.example.com/price",
    "method": "GET",
    "headers": {
      "Content-Type": "application/json"
    }
  },
  "input_schema": {
    "type": "object",
    "properties": {
      "symbol": {
        "type": "string",
        "description": "Stock symbol"
      },
      "period": {
        "type": "string",
        "enum": ["1d", "1w", "1m", "3m"]
      }
    },
    "required": ["symbol"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "price": {"type": "number"},
      "timestamp": {"type": "string"}
    }
  },
  "auth_config": {
    "type": "bearer",
    "token": "${API_TOKEN}"
  },
  "rate_limit": {
    "max_calls": 100,
    "period": "hour"
  },
  "is_active": true,
  "is_public": false
}
```

**Field Descriptions:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique tool name (max 255 chars) |
| `description` | string | No | Tool description (max 2000 chars) |
| `tool_type` | string | Yes | Type: http, mcp, python, shell, builtin |
| `config` | object | Yes | Tool-specific configuration |
| `input_schema` | object | Yes | JSON Schema for input validation |
| `output_schema` | object | No | JSON Schema for output validation |
| `auth_config` | object | No | Authentication configuration (encrypted) |
| `rate_limit` | object | No | Rate limiting configuration |
| `is_active` | boolean | No | Active status (default: true) |
| `is_public` | boolean | No | Public accessibility (default: false) |

**Tool Type Config Requirements:**

- **http**: Requires `url` and `method` fields
- **mcp**: Requires `server_url` field
- **python**: Requires `code` field
- **shell**: Requires `command` field
- **builtin**: Varies by operation

**Response (201 Created):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "owner_id": "00000000-0000-0000-0000-000000000001",
  "name": "price_fetcher",
  "description": "Fetches stock price data from external API",
  "tool_type": "http",
  "config": {
    "url": "https://api.example.com/price",
    "method": "GET",
    "headers": {
      "Content-Type": "application/json"
    }
  },
  "input_schema": {
    "type": "object",
    "properties": {
      "symbol": {"type": "string"},
      "period": {"type": "string"}
    },
    "required": ["symbol"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "price": {"type": "number"},
      "timestamp": {"type": "string"}
    }
  },
  "auth_config": {
    "type": "bearer",
    "token": "***"
  },
  "rate_limit": {
    "max_calls": 100,
    "period": "hour"
  },
  "is_active": true,
  "is_public": false,
  "created_at": "2026-01-13T09:00:00+09:00",
  "updated_at": "2026-01-13T09:00:00+09:00"
}
```

**Error Response (400 Bad Request):**

```json
{
  "detail": "'http' type tool configuration missing required field: 'url'"
}
```

---

### 3. Get Tool

Retrieve a tool by its ID.

```
GET /api/v1/tools/{tool_id}
```

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tool_id` | UUID | Yes | Tool UUID |

**Response (200 OK):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "owner_id": "00000000-0000-0000-0000-000000000001",
  "name": "price_fetcher",
  "description": "Fetches stock price data from external API",
  "tool_type": "http",
  "config": {
    "url": "https://api.example.com/price",
    "method": "GET"
  },
  "input_schema": {...},
  "output_schema": {...},
  "auth_config": {...},
  "rate_limit": {...},
  "is_active": true,
  "is_public": false,
  "created_at": "2026-01-13T09:00:00+09:00",
  "updated_at": "2026-01-13T09:00:00+09:00"
}
```

**Error Response (404 Not Found):**

```json
{
  "detail": "Tool 550e8400-e29b-41d4-a716-446655440000 not found"
}
```

---

### 4. Update Tool

Update an existing tool. All fields are optional for partial updates.

```
PUT /api/v1/tools/{tool_id}
```

**Request Body:**

```json
{
  "description": "Updated description",
  "config": {
    "url": "https://api.example.com/v2/price",
    "method": "GET"
  },
  "is_active": false
}
```

**Response (200 OK):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "price_fetcher",
  "description": "Updated description",
  "tool_type": "http",
  "config": {
    "url": "https://api.example.com/v2/price",
    "method": "GET"
  },
  "input_schema": {...},
  "output_schema": {...},
  "auth_config": {...},
  "rate_limit": {...},
  "is_active": false,
  "is_public": false,
  "created_at": "2026-01-13T09:00:00+09:00",
  "updated_at": "2026-01-15T10:30:00+09:00"
}
```

**Error Response (404 Not Found):**

```json
{
  "detail": "Tool 550e8400-e29b-41d4-a716-446655440000 not found"
}
```

---

### 5. Delete Tool

Soft delete a tool. The tool can be restored later if needed.

```
DELETE /api/v1/tools/{tool_id}
```

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tool_id` | UUID | Yes | Tool UUID |

**Response (204 No Content):**

Empty response body on successful deletion.

**Error Response (404 Not Found):**

```json
{
  "detail": "Tool 550e8400-e29b-41d4-a716-446655440000 not found"
}
```

---

### 6. Test Tool

Test execute a tool with sample input data for validation purposes.

```
POST /api/v1/tools/{tool_id}/test
```

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tool_id` | UUID | Yes | Tool UUID |

**Request Body:**

```json
{
  "input_data": {
    "symbol": "005930",
    "period": "1d"
  }
}
```

**Response (200 OK):**

```json
{
  "success": true,
  "output": {
    "price": 82500,
    "timestamp": "2026-01-15T09:00:00+09:00"
  },
  "error": null,
  "execution_time_ms": 150.5
}
```

**Response (200 OK - Failed):**

```json
{
  "success": false,
  "output": null,
  "error": "Connection timeout: Failed to reach API endpoint",
  "execution_time_ms": 5000.0
}
```

**Error Response (404 Not Found):**

```json
{
  "detail": "Tool 550e8400-e29b-41d4-a716-446655440000 not found"
}
```

---

## Authentication

All Tool API endpoints require JWT authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

See [Authentication Guide](./authentication.md) for details on obtaining JWT tokens.

---

## Error Codes

| Status Code | Description |
|-------------|-------------|
| 200 | Successful operation |
| 201 | Resource created |
| 204 | Resource deleted (no content) |
| 400 | Bad request (validation error) |
| 401 | Unauthorized (invalid/missing token) |
| 404 | Resource not found |
| 500 | Internal server error |

---

## Examples

### Creating an HTTP Tool

```bash
curl -X POST https://api.pastetrader.com/api/v1/tools \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "stock_price_fetcher",
    "description": "Fetch real-time stock prices",
    "tool_type": "http",
    "config": {
      "url": "https://api.market.com/v1/quote",
      "method": "GET"
    },
    "input_schema": {
      "type": "object",
      "properties": {
        "symbol": {"type": "string"}
      },
      "required": ["symbol"]
    },
    "is_active": true
  }'
```

### Creating a Python Tool

```bash
curl -X POST https://api.pastetrader.com/api/v1/tools \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "rsi_calculator",
    "description": "Calculate RSI indicator",
    "tool_type": "python",
    "config": {
      "code": "def calculate_rsi(prices, period=14): ..."
    },
    "input_schema": {
      "type": "object",
      "properties": {
        "prices": {"type": "array", "items": {"type": "number"}}
      }
    },
    "is_active": true
  }'
```

### Testing a Tool

```bash
curl -X POST https://api.pastetrader.com/api/v1/tools/{tool_id}/test \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "input_data": {
      "symbol": "005930"
    }
  }'
```

---

## Related Documentation

- [Agent API Reference](./agents.md) - Agent management endpoints
- [Authentication Guide](./authentication.md) - JWT authentication details
- [Tool Schema Documentation](../database/schemas/tool-schema.md) - Database schema
- [Architecture: Tool-Agent Registry](../architecture/tool-agent-registry.md) - System architecture
