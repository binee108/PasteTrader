# Agent API Reference

## Overview

The Agent API provides comprehensive CRUD operations for managing AI-powered agents in the PasteTrader platform. Agents are LLM-based reasoning entities that can use tools to perform complex tasks autonomously.

**Base URL:** `/api/v1/agents`

**Authentication:** JWT Bearer Token (Required for all endpoints)

**Tags:** [SPEC-009] [API] [AGENT]

---

## Agent Capabilities

Agents in PasteTrader support:

- **Multiple LLM Providers**: Anthropic, OpenAI, GLM
- **Custom System Prompts**: Define agent behavior and personality
- **Tool Integration**: Agents can use multiple tools
- **Memory Configuration**: Configure context window and conversation turns
- **Public/Private Agents**: Control agent accessibility

---

## Supported Model Providers

| Provider | Models |
|----------|--------|
| `anthropic` | claude-3-5-sonnet-20241022, claude-3-opus-20240229 |
| `openai` | gpt-4-turbo-preview, gpt-4-vision-preview |
| `glm` | glm-4-plus, glm-4-air |

---

## Endpoints

### 1. List Agents

Retrieve a paginated list of agents with optional filtering.

```
GET /api/v1/agents
```

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `skip` | integer | No | 0 | Number of records to skip |
| `limit` | integer | No | 20 | Page size |
| `model_provider` | string | No | - | Filter by model provider |
| `is_active` | boolean | No | - | Filter by active status |
| `is_public` | boolean | No | - | Filter by public status |

**Response (200 OK):**

```json
{
  "items": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "name": "buy_signal_analyzer",
      "model_provider": "anthropic",
      "model_name": "claude-3-5-sonnet-20241022",
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

### 2. Create Agent

Create a new agent with the provided configuration.

```
POST /api/v1/agents
```

**Request Body:**

```json
{
  "name": "buy_signal_analyzer",
  "description": "Analyzes stock data to identify buy signals",
  "system_prompt": "You are a professional trading analyst specializing in technical analysis...",
  "model_provider": "anthropic",
  "model_name": "claude-3-5-sonnet-20241022",
  "config": {
    "temperature": 0.3,
    "max_tokens": 4096,
    "top_p": 0.9
  },
  "tools": [
    "550e8400-e29b-41d4-a716-446655440000",
    "550e8400-e29b-41d4-a716-446655440001"
  ],
  "memory_config": {
    "max_turns": 10,
    "context_window": 200000
  },
  "is_active": true,
  "is_public": false
}
```

**Field Descriptions:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique agent name (max 255 chars) |
| `description` | string | No | Agent description (max 2000 chars) |
| `system_prompt` | string | No | System prompt for the agent |
| `model_provider` | string | Yes | LLM provider (anthropic, openai, glm) |
| `model_name` | string | Yes | Specific model identifier |
| `config` | object | No | Model configuration (temperature, etc.) |
| `tools` | array | No | List of tool UUIDs |
| `memory_config` | object | No | Memory/context configuration |
| `is_active` | boolean | No | Active status (default: true) |
| `is_public` | boolean | No | Public accessibility (default: false) |

**Model Config Options:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `temperature` | float | 0.7 | Sampling temperature (0.0-1.0) |
| `max_tokens` | integer | 4096 | Maximum tokens to generate |
| `top_p` | float | 0.9 | Nucleus sampling threshold |

**Memory Config Options:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_turns` | integer | 10 | Maximum conversation turns |
| `context_window` | integer | 200000 | Context window size |

**Response (201 Created):**

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "owner_id": "00000000-0000-0000-0000-000000000001",
  "name": "buy_signal_analyzer",
  "description": "Analyzes stock data to identify buy signals",
  "system_prompt": "You are a professional trading analyst...",
  "model_provider": "anthropic",
  "model_name": "claude-3-5-sonnet-20241022",
  "config": {
    "temperature": 0.3,
    "max_tokens": 4096,
    "top_p": 0.9
  },
  "tools": [
    "550e8400-e29b-41d4-a716-446655440000",
    "550e8400-e29b-41d4-a716-446655440001"
  ],
  "memory_config": {
    "max_turns": 10,
    "context_window": 200000
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
  "detail": "Agent with name 'buy_signal_analyzer' already exists"
}
```

---

### 3. Get Agent

Retrieve an agent by its ID.

```
GET /api/v1/agents/{agent_id}
```

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_id` | UUID | Yes | Agent UUID |

**Response (200 OK):**

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "owner_id": "00000000-0000-0000-0000-000000000001",
  "name": "buy_signal_analyzer",
  "description": "Analyzes stock data to identify buy signals",
  "system_prompt": "You are a professional trading analyst...",
  "model_provider": "anthropic",
  "model_name": "claude-3-5-sonnet-20241022",
  "config": {
    "temperature": 0.3,
    "max_tokens": 4096
  },
  "tools": [
    "550e8400-e29b-41d4-a716-446655440000"
  ],
  "memory_config": {
    "max_turns": 10,
    "context_window": 200000
  },
  "is_active": true,
  "is_public": false,
  "created_at": "2026-01-13T09:00:00+09:00",
  "updated_at": "2026-01-13T09:00:00+09:00"
}
```

**Error Response (404 Not Found):**

```json
{
  "detail": "Agent 660e8400-e29b-41d4-a716-446655440001 not found"
}
```

---

### 4. Update Agent

Update an existing agent. All fields are optional for partial updates.

```
PUT /api/v1/agents/{agent_id}
```

**Request Body:**

```json
{
  "description": "Updated agent description",
  "system_prompt": "You are an expert trading analyst with 20 years of experience...",
  "config": {
    "temperature": 0.2,
    "max_tokens": 8192
  },
  "is_active": true
}
```

**Response (200 OK):**

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "name": "buy_signal_analyzer",
  "description": "Updated agent description",
  "system_prompt": "You are an expert trading analyst...",
  "model_provider": "anthropic",
  "model_name": "claude-3-5-sonnet-20241022",
  "config": {
    "temperature": 0.2,
    "max_tokens": 8192
  },
  "tools": [...],
  "memory_config": {...},
  "is_active": true,
  "is_public": false,
  "created_at": "2026-01-13T09:00:00+09:00",
  "updated_at": "2026-01-15T10:30:00+09:00"
}
```

**Error Response (404 Not Found):**

```json
{
  "detail": "Agent 660e8400-e29b-41d4-a716-446655440001 not found"
}
```

---

### 5. Delete Agent

Soft delete an agent. The agent can be restored later if needed.

```
DELETE /api/v1/agents/{agent_id}
```

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_id` | UUID | Yes | Agent UUID |

**Response (204 No Content):**

Empty response body on successful deletion.

**Error Response (404 Not Found):**

```json
{
  "detail": "Agent 660e8400-e29b-41d4-a716-446655440001 not found"
}
```

---

### 6. Add Tool to Agent

Associate a tool with an agent, enabling the agent to use that tool.

```
POST /api/v1/agents/{agent_id}/tools
```

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_id` | UUID | Yes | Agent UUID |

**Request Body:**

```json
{
  "tool_id": "550e8400-e29b-41d4-a716-446655440002"
}
```

**Response (200 OK):**

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "name": "buy_signal_analyzer",
  "tools": [
    "550e8400-e29b-41d4-a716-446655440000",
    "550e8400-e29b-41d4-a716-446655440001",
    "550e8400-e29b-41d4-a716-446655440002"
  ],
  ...
}
```

**Error Response (409 Conflict):**

```json
{
  "detail": "Tool 550e8400-e29b-41d4-a716-446655440002 is already associated with this agent"
}
```

---

### 7. Remove Tool from Agent

Remove a tool association from an agent.

```
DELETE /api/v1/agents/{agent_id}/tools/{tool_id}
```

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_id` | UUID | Yes | Agent UUID |
| `tool_id` | UUID | Yes | Tool UUID to remove |

**Response (200 OK):**

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "name": "buy_signal_analyzer",
  "tools": [
    "550e8400-e29b-41d4-a716-446655440000",
    "550e8400-e29b-41d4-a716-446655440001"
  ],
  ...
}
```

**Error Response (404 Not Found):**

```json
{
  "detail": "Agent 660e8400-e29b-41d4-a716-446655440001 not found"
}
```

---

### 8. Test Agent

Test execute an agent with sample input data for validation purposes.

```
POST /api/v1/agents/{agent_id}/test
```

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_id` | UUID | Yes | Agent UUID |

**Request Body:**

```json
{
  "input_data": {
    "message": "Analyze Samsung Electronics (005930) for buy signals"
  }
}
```

**Response (200 OK):**

```json
{
  "success": true,
  "output": {
    "response": "Based on technical analysis, Samsung Electronics shows several buy signals...",
    "tool_calls": [
      {
        "tool": "price_fetcher",
        "params": {"symbol": "005930"},
        "result": {"price": 82500}
      },
      {
        "tool": "rsi_calculator",
        "params": {"symbol": "005930"},
        "result": {"rsi": 32.5}
      }
    ]
  },
  "error": null,
  "execution_time_ms": 2500.5
}
```

**Response (200 OK - Failed):**

```json
{
  "success": false,
  "output": null,
  "error": "LLM API timeout: Request exceeded 60 second limit",
  "execution_time_ms": 60000.0
}
```

**Error Response (404 Not Found):**

```json
{
  "detail": "Agent 660e8400-e29b-41d4-a716-446655440001 not found"
}
```

---

## Authentication

All Agent API endpoints require JWT authentication. Include the token in the Authorization header:

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
| 409 | Conflict (duplicate association) |
| 500 | Internal server error |

---

## Examples

### Creating an Anthropic Agent

```bash
curl -X POST https://api.pastetrader.com/api/v1/agents \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "trading_advisor",
    "description": "Provides trading advice using technical analysis",
    "system_prompt": "You are a conservative trading advisor focused on risk management...",
    "model_provider": "anthropic",
    "model_name": "claude-3-5-sonnet-20241022",
    "config": {
      "temperature": 0.3,
      "max_tokens": 4096
    },
    "tools": [],
    "is_active": true
  }'
```

### Creating an OpenAI Agent

```bash
curl -X POST https://api.pastetrader.com/api/v1/agents \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "market_analyzer",
    "description": "Analyzes market trends and patterns",
    "model_provider": "openai",
    "model_name": "gpt-4-turbo-preview",
    "config": {
      "temperature": 0.5,
      "max_tokens": 4096
    },
    "tools": [],
    "is_active": true
  }'
```

### Adding a Tool to an Agent

```bash
curl -X POST https://api.pastetrader.com/api/v1/agents/{agent_id}/tools \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_id": "550e8400-e29b-41d4-a716-446655440000"
  }'
```

### Testing an Agent

```bash
curl -X POST https://api.pastetrader.com/api/v1/agents/{agent_id}/test \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "input_data": {
      "message": "What is your analysis of AAPL stock right now?"
    }
  }'
```

---

## Related Documentation

- [Tool API Reference](./tools.md) - Tool management endpoints
- [Authentication Guide](./authentication.md) - JWT authentication details
- [Agent Schema Documentation](../database/schemas/agent-schema.md) - Database schema
- [Architecture: Tool-Agent Registry](../architecture/tool-agent-registry.md) - System architecture
