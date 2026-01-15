# Tool Schema Documentation

## Overview

The Tool schema defines the data model for executable tools in the PasteTrader platform. Tools are configurable units that can perform various operations including HTTP requests, Python code execution, shell commands, and more.

**Tags:** [SPEC-009] [SCHEMA] [TOOL]

**Table Name:** `tools`

---

## Schema Definition

### SQLAlchemy Model

**Location:** `backend/app/models/tool.py`

```python
class Tool(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Tool model for executable tool configuration."""

    __tablename__ = "tools"

    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
    )
    tool_type: Mapped[ToolType] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )
    input_schema: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )
    output_schema: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    auth_config: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    rate_limit: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )
    is_public: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )
```

---

## Field Descriptions

### Base Fields (Inherited)

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key (inherited from UUIDMixin) |
| `created_at` | datetime | Creation timestamp (inherited from TimestampMixin) |
| `updated_at` | datetime | Last update timestamp (inherited from TimestampMixin) |
| `deleted_at` | datetime | Soft deletion timestamp (inherited from SoftDeleteMixin) |
| `is_deleted` | bool | Deletion status (inherited from SoftDeleteMixin) |

### Tool-Specific Fields

| Field | Type | Nullable | Indexed | Description |
|-------|------|----------|---------|-------------|
| `owner_id` | UUID | No | Yes | Foreign key to users table (tool owner) |
| `name` | string(255) | No | Yes | Unique tool name |
| `description` | string(2000) | Yes | No | Optional tool description |
| `tool_type` | string(50) | No | Yes | Type: http, mcp, python, shell, builtin |
| `config` | JSONB | No | No | Tool-specific configuration |
| `input_schema` | JSONB | No | No | JSON Schema for input validation |
| `output_schema` | JSONB | Yes | No | JSON Schema for output validation |
| `auth_config` | JSONB | Yes | No | Authentication configuration (encrypted) |
| `rate_limit` | JSONB | Yes | No | Rate limiting configuration |
| `is_active` | boolean | No | Yes | Active status flag |
| `is_public` | boolean | No | Yes | Public accessibility flag |

---

## Tool Types

### Tool Type Enum

```python
class ToolType(str, Enum):
    HTTP = "http"
    MCP = "mcp"
    PYTHON = "python"
    SHELL = "shell"
    BUILTIN = "builtin"
```

### Type-Specific Config Requirements

#### HTTP Tool

```json
{
  "url": "https://api.example.com/endpoint",
  "method": "GET",
  "headers": {"Content-Type": "application/json"},
  "timeout": 30
}
```

**Required Fields:** `url`, `method`

#### MCP Tool

```json
{
  "server_url": "http://localhost:3000/mcp",
  "method": "call_tool",
  "timeout": 30
}
```

**Required Fields:** `server_url`

#### Python Tool

```json
{
  "code": "def calculate_rsi(prices, period=14):\n    return result",
  "timeout": 10,
  "libraries": ["pandas", "numpy"]
}
```

**Required Fields:** `code`

#### Shell Tool

```json
{
  "command": "python process.py --input data.csv",
  "working_dir": "/tmp",
  "timeout": 60,
  "env": {"API_KEY": "secret"}
}
```

**Required Fields:** `command`

#### Builtin Tool

```json
{
  "operation": "calculate_rsi",
  "parameters": {"period": 14, "overbought": 70}
}
```

**Required Fields:** `operation`

---

## JSON Schema Fields

### Input Schema

Defines the expected input structure for tool execution.

```json
{
  "type": "object",
  "properties": {
    "symbol": {
      "type": "string",
      "description": "Stock symbol"
    },
    "period": {
      "type": "string",
      "enum": ["1d", "1w", "1m", "3m"],
      "description": "Time period"
    }
  },
  "required": ["symbol"]
}
```

### Output Schema

Defines the expected output structure from tool execution.

```json
{
  "type": "object",
  "properties": {
    "price": {
      "type": "number",
      "description": "Current price"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time"
    }
  },
  "required": ["price", "timestamp"]
}
```

---

## Authentication Configuration

### Auth Config Structure

```json
{
  "type": "bearer|basic|api_key|custom",
  "token": "...",
  "username": "...",
  "password": "...",
  "api_key": "...",
  "headers": {...},
  "custom": {...}
}
```

### Auth Types

| Type | Description | Fields |
|------|-------------|--------|
| `bearer` | Bearer token | `token` |
| `basic` | Basic auth | `username`, `password` |
| `api_key` | API key in header | `api_key`, `header_name` |
| `custom` | Custom auth | Arbitrary fields |

**Security Note:** `auth_config` is encrypted at rest using AES-256-GCM.

---

## Rate Limiting Configuration

### Rate Limit Structure

```json
{
  "max_calls": 100,
  "period": "hour|minute|second",
  "burst": 10
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `max_calls` | integer | Maximum calls per period |
| `period` | string | Time period (hour, minute, second) |
| `burst` | integer | Burst allowance |

---

## Constraints and Indexes

### Database Constraints

```sql
-- Primary key (inherited from UUIDMixin)
PRIMARY KEY (id)

-- Unique constraint
UNIQUE (name) WHERE is_deleted IS FALSE

-- Foreign key constraint
FOREIGN KEY (owner_id) REFERENCES users(id)

-- Check constraints
CHECK (tool_type IN ('http', 'mcp', 'python', 'shell', 'builtin'))
CHECK (is_active IS NOT NULL)
CHECK (is_public IS NOT NULL)
```

### Database Indexes

```sql
-- Owner index (user resource queries)
CREATE INDEX idx_tool_owner ON tools(owner_id)
  WHERE is_deleted IS FALSE;

-- Name index (lookup by name)
CREATE INDEX idx_tool_name ON tools(name)
  WHERE is_deleted IS FALSE;

-- Type index (filtering by type)
CREATE INDEX idx_tool_type ON tools(tool_type)
  WHERE is_deleted IS FALSE;

-- Active status index
CREATE INDEX idx_tool_active ON tools(is_active)
  WHERE is_deleted IS FALSE;

-- Public status index
CREATE INDEX idx_tool_public ON tools(is_public)
  WHERE is_deleted IS FALSE;

-- Composite index for user's active tools
CREATE INDEX idx_tool_owner_active ON tools(owner_id, is_active)
  WHERE is_deleted IS FALSE;
```

---

## Pydantic Schemas

### API Request/Response Schemas

**Location:** `backend/app/schemas/tool.py`

#### ToolCreate

```python
class ToolCreate(BaseSchema):
    name: str
    description: str | None
    tool_type: str
    config: dict[str, Any]
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None
    auth_config: dict[str, Any] | None
    rate_limit: dict[str, Any] | None
    is_active: bool
    is_public: bool
```

#### ToolUpdate

```python
class ToolUpdate(BaseSchema):
    name: str | None
    description: str | None
    tool_type: str | None
    config: dict[str, Any] | None
    input_schema: dict[str, Any] | None
    output_schema: dict[str, Any] | None
    auth_config: dict[str, Any] | None
    rate_limit: dict[str, Any] | None
    is_active: bool | None
    is_public: bool | None
```

#### ToolResponse

```python
class ToolResponse(ToolBase, BaseResponse):
    owner_id: UUID
    # All ToolCreate fields plus timestamps
```

---

## Relationships

### User Relationship

```python
class Tool(Base):
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    owner: Mapped["User"] = relationship(back_populates="tools")
```

### Agent Relationship (Many-to-Many)

Tools are associated with agents through the agent's `tools` field:

```python
class Agent(Base):
    tools: Mapped[list[str]] = mapped_column(JSONB)
    # Contains list of tool UUIDs
```

---

## Migration

### Create Table Migration

```Alembic
def upgrade():
    op.create_table(
        'tools',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('owner_id', postgresql.UUID(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.String(2000), nullable=True),
        sa.Column('tool_type', sa.String(50), nullable=False),
        sa.Column('config', postgresql.JSONB(), nullable=False),
        sa.Column('input_schema', postgresql.JSONB(), nullable=False),
        sa.Column('output_schema', postgresql.JSONB(), nullable=True),
        sa.Column('auth_config', postgresql.JSONB(), nullable=True),
        sa.Column('rate_limit', postgresql.JSONB(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_public', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_tool_name')
    )
```

---

## Validation Rules

### Name Validation

- Must be unique (case-insensitive)
- Length: 1-255 characters
- Allowed characters: alphanumeric, underscore, hyphen
- Cannot start with a number
- Cannot be a reserved keyword

### Config Validation

Type-specific required fields:
- **http**: `url`, `method`
- **mcp**: `server_url`
- **python**: `code`
- **shell**: `command`
- **builtin**: `operation`

### Schema Validation

- Must be valid JSON Schema Draft 7
- `input_schema` is required
- `output_schema` is optional

---

## Related Documentation

- [Tool API Reference](../../api/tools.md) - Tool endpoint documentation
- [Tool-Agent Registry](../../architecture/tool-agent-registry.md) - System architecture
- [Agent Schema](./agent-schema.md) - Agent data model
- [User Schema](./user-schema.md) - User/owner data model
