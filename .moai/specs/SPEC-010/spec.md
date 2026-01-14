# SPEC-010: DAG Validation Service for Workflow Engine

## Metadata

| Field | Value |
|-------|-------|
| SPEC ID | SPEC-010 |
| Title | DAG Validation Service for Workflow Engine |
| Created | 2026-01-14 |
| Status | Planned |
| Priority | High (P0) |
| Lifecycle | spec-anchored |
| Author | workflow-spec |
| Phase | Phase 3 - Engine Core |

## Tags

`[SPEC-010]` `[DAG]` `[VALIDATION]` `[GRAPH]` `[WORKFLOW]` `[ENGINE]` `[BACKEND]`

---

## Overview

This SPEC defines a dedicated, standalone DAG Validation Service for the PasteTrader workflow engine. The service provides comprehensive graph validation capabilities including cycle detection, connectivity analysis, topology validation, and data flow verification. It is designed for parallel implementation with no conflicts with existing codebase.

### Scope

- Standalone validation module (`backend/app/services/workflow/validator.py`)
- Validation schemas (`backend/app/schemas/validation.py`)
- Comprehensive structural validation (cycles, connectivity, dangling nodes)
- Node compatibility validation (type requirements, handle validation)
- Data flow validation (schema compatibility, variable binding)
- Topology analysis (topological sort, parallel path detection)
- API endpoint for on-demand validation

### Out of Scope

- Modification of existing `workflow_service.py` (Phase 2 integration)
- Runtime validation during execution (SPEC-011)
- Real-time WebSocket validation updates (future SPEC)
- Authentication/Authorization (separate SPEC)

---

## Environment

### Technology Stack (Constitution Reference)

| Component | Version | Purpose |
|-----------|---------|---------|
| FastAPI | 0.115.x | API framework |
| Pydantic | 2.10.x | Schema validation |
| SQLAlchemy | 2.0.x | Async ORM |
| Python | 3.13.x | Runtime environment |

### Configuration Dependencies

- SPEC-001: Base models, Mixins, Enums
- SPEC-003: Workflow, Node, Edge models
- SPEC-007: Workflow API Endpoints (DAG validation interface defined in REQ-DAG-001)

---

## Assumptions

### Technical Assumptions

| Assumption | Confidence | Evidence | Risk if Wrong |
|------------|------------|----------|---------------|
| DFS-based cycle detection scales to 1000+ nodes | High | Standard algorithm complexity O(V+E) | Need alternative algorithm |
| Validation can complete in <100ms for typical workflows | High | Most workflows have <50 nodes | Async processing needed |
| Standalone module can be imported without circular dependencies | High | Clean architecture design | Refactoring required |
| All node types have well-defined input/output specifications | Medium | NodeType enum exists | Schema migration needed |

### Design Assumptions

| Assumption | Confidence | Risk if Wrong |
|------------|------------|---------------|
| Validation results can be cached for repeated checks | Medium | Add caching layer |
| Batch validation is more efficient than individual edge checks | High | Sequential fallback |
| Error messages should include visualization hints (cycle path) | High | Add post-processing |

---

## Requirements

### Structural Validation Requirements

#### REQ-010-001: Cycle Detection

**Event-Driven Requirement**

**WHEN** a validation request is made for a workflow, **THEN** the system shall detect any cycles in the graph and return the cycle path if found.

**Details:**

- Algorithm: Depth-First Search (DFS) with path tracking
- Output: List of node IDs forming the cycle
- Performance: O(V+E) time complexity
- Support for finding all cycles (not just first detected)

**Error Response:**
```json
{
  "is_valid": false,
  "error_code": "CYCLE_DETECTED",
  "cycle_path": ["node-a", "node-b", "node-c", "node-a"],
  "message": "Cycle detected: node-a -> node-b -> node-c -> node-a"
}
```

#### REQ-010-002: Self-Loop Prevention

**Ubiquitous Requirement**

The system shall **always** reject edges where source_node_id equals target_node_id.

**Error Response:**
```json
{
  "is_valid": false,
  "error_code": "SELF_LOOP_DETECTED",
  "node_id": "node-a",
  "message": "Self-loop detected: node-a cannot connect to itself"
}
```

#### REQ-010-003: Node Existence Validation

**Event-Driven Requirement**

**WHEN** validating edges, **THEN** the system shall verify that both source and target nodes exist in the workflow.

**Error Response:**
```json
{
  "is_valid": false,
  "error_code": "NODE_NOT_FOUND",
  "missing_nodes": ["node-xyz"],
  "message": "Referenced nodes not found in workflow"
}
```

#### REQ-010-004: Duplicate Edge Detection

**Event-Driven Requirement**

**WHEN** validating edges, **THEN** the system shall detect duplicate edges (same source-target-handle combination).

**Error Response:**
```json
{
  "is_valid": false,
  "error_code": "DUPLICATE_EDGE",
  "duplicates": [
    {"source": "node-a", "target": "node-b", "count": 2}
  ],
  "message": "Duplicate edges detected"
}
```

---

### Connectivity Validation Requirements

#### REQ-010-005: Trigger Node Requirement

**Event-Driven Requirement**

**WHEN** validating workflow connectivity, **THEN** the system shall verify that at least one trigger node exists.

**Details:**

- NodeType.TRIGGER must be present
- Trigger nodes must have no incoming edges
- Multiple trigger nodes are allowed (parallel start)

**Error Response:**
```json
{
  "is_valid": false,
  "error_code": "NO_TRIGGER_NODE",
  "message": "Workflow must have at least one trigger node"
}
```

#### REQ-010-006: Dangling Node Detection

**Event-Driven Requirement**

**WHEN** validating workflow connectivity, **THEN** the system shall detect nodes with no connections (isolated nodes).

**Details:**

- Nodes with neither incoming nor outgoing edges
- Exception: Single-node workflows (trigger only)

**Error Response:**
```json
{
  "is_valid": false,
  "error_code": "DANGLING_NODES",
  "dangling_node_ids": ["node-orphan-1", "node-orphan-2"],
  "message": "Isolated nodes detected with no connections"
}
```

#### REQ-010-007: Unreachable Node Detection

**Event-Driven Requirement**

**WHEN** validating workflow connectivity, **THEN** the system shall detect nodes not reachable from any trigger node.

**Details:**

- BFS/DFS from all trigger nodes
- Compare reachable set with all nodes
- Report unreachable nodes

**Error Response:**
```json
{
  "is_valid": false,
  "error_code": "UNREACHABLE_NODES",
  "unreachable_node_ids": ["node-isolated-1"],
  "trigger_node_ids": ["trigger-1"],
  "message": "Nodes not reachable from trigger: node-isolated-1"
}
```

#### REQ-010-008: Dead-End Detection

**Event-Driven Requirement**

**WHEN** validating workflow connectivity, **THEN** the system shall detect non-terminal nodes with no outgoing edges.

**Details:**

- Nodes that should have outputs but don't
- Exception: Aggregator nodes (can be terminal)
- Exception: Nodes marked as terminal in config

**Warning Response (non-blocking):**
```json
{
  "is_valid": true,
  "warnings": [
    {
      "code": "DEAD_END_NODE",
      "node_id": "node-tool-1",
      "message": "Tool node has no outgoing edges"
    }
  ]
}
```

---

### Node Compatibility Validation Requirements

#### REQ-010-009: Node Type Requirements Validation

**Event-Driven Requirement**

**WHEN** validating node configuration, **THEN** the system shall verify type-specific requirements are met.

**Node Type Requirements:**

| NodeType | Required Fields | Validation Rule |
|----------|-----------------|-----------------|
| TRIGGER | trigger_config | Must have valid trigger configuration |
| TOOL | tool_id | Must reference existing tool |
| AGENT | agent_id | Must reference existing agent |
| CONDITION | condition config | Must have valid condition expression |
| ADAPTER | input_schema, output_schema | Must have both schemas defined |
| AGGREGATOR | aggregation_config | Must define aggregation strategy |

**Error Response:**
```json
{
  "is_valid": false,
  "error_code": "INVALID_NODE_CONFIG",
  "node_errors": [
    {
      "node_id": "node-tool-1",
      "node_type": "tool",
      "missing_fields": ["tool_id"],
      "message": "Tool node must reference a valid tool"
    }
  ]
}
```

#### REQ-010-010: Handle Validation

**Event-Driven Requirement**

**WHEN** validating edge connections, **THEN** the system shall verify that source and target handles are valid for the connected node types.

**Details:**

- Condition nodes have named output handles (e.g., "true", "false", "default")
- Aggregator nodes have multiple input handles
- Standard nodes have single input/output

**Error Response:**
```json
{
  "is_valid": false,
  "error_code": "INVALID_HANDLE",
  "errors": [
    {
      "edge_id": "edge-1",
      "source_node_id": "condition-1",
      "invalid_handle": "maybe",
      "valid_handles": ["true", "false", "default"],
      "message": "Invalid source handle 'maybe' for condition node"
    }
  ]
}
```

#### REQ-010-011: Tool/Agent Reference Validation

**Event-Driven Requirement**

**WHEN** validating tool or agent nodes, **THEN** the system shall verify that referenced tool_id or agent_id exists and is active.

**Error Response:**
```json
{
  "is_valid": false,
  "error_code": "INVALID_REFERENCE",
  "errors": [
    {
      "node_id": "node-tool-1",
      "reference_type": "tool",
      "reference_id": "tool-uuid",
      "message": "Referenced tool does not exist or is inactive"
    }
  ]
}
```

---

### Data Flow Validation Requirements

#### REQ-010-012: Schema Compatibility Validation

**State-Driven Requirement**

**IF** connected nodes have defined input/output schemas, **THEN** the system shall validate schema compatibility.

**Details:**

- Source output_schema must be compatible with target input_schema
- Use JSON Schema compatibility rules
- Support partial schema matching (subset validation)

**Error Response:**
```json
{
  "is_valid": false,
  "error_code": "SCHEMA_MISMATCH",
  "errors": [
    {
      "source_node_id": "node-a",
      "target_node_id": "node-b",
      "source_output_schema": {"type": "string"},
      "target_input_schema": {"type": "number"},
      "message": "Output schema incompatible with input schema"
    }
  ]
}
```

#### REQ-010-013: Variable Binding Validation

**State-Driven Requirement**

**IF** nodes reference workflow variables, **THEN** the system shall verify variables are defined.

**Details:**

- Check variable references in node configs
- Validate against workflow.variables
- Support nested variable paths

**Error Response:**
```json
{
  "is_valid": false,
  "error_code": "UNDEFINED_VARIABLE",
  "errors": [
    {
      "node_id": "node-tool-1",
      "variable_path": "input.api_key",
      "message": "Referenced variable 'input.api_key' is not defined"
    }
  ]
}
```

---

### Topology Validation Requirements

#### REQ-010-014: Topological Sort Generation

**Event-Driven Requirement**

**WHEN** a valid DAG is confirmed, **THEN** the system shall generate a topological sort for execution ordering.

**Response:**
```json
{
  "is_valid": true,
  "topology": {
    "execution_order": [
      ["trigger-1"],
      ["tool-1", "tool-2"],
      ["condition-1"],
      ["agent-1", "agent-2"],
      ["aggregator-1"]
    ],
    "total_levels": 5,
    "max_parallel_nodes": 2
  }
}
```

#### REQ-010-015: Parallel Execution Path Detection

**Event-Driven Requirement**

**WHEN** generating topology, **THEN** the system shall identify nodes that can execute in parallel.

**Details:**

- Nodes at the same topological level with no inter-dependencies
- Report maximum parallelism degree
- Support parallel path visualization

---

### Unwanted Behavior Requirements

#### REQ-010-016: Graph Size Limits

**Unwanted Behavior Requirement**

The system **shall not** validate workflows exceeding reasonable limits without explicit override.

**Limits:**

| Metric | Default Limit | Override Allowed |
|--------|---------------|------------------|
| Max Nodes | 500 | Yes, via config |
| Max Edges | 2000 | Yes, via config |
| Max Depth | 100 | Yes, via config |

**Error Response:**
```json
{
  "is_valid": false,
  "error_code": "GRAPH_TOO_LARGE",
  "current_nodes": 600,
  "max_nodes": 500,
  "message": "Workflow exceeds maximum node limit"
}
```

#### REQ-010-017: Timeout Protection

**Unwanted Behavior Requirement**

The system **shall not** allow validation to run beyond the configured timeout.

**Details:**

- Default timeout: 5 seconds
- Configurable per request
- Return partial results on timeout

---

### Optional Enhancement Requirements

#### REQ-010-018: Validation Caching

**Optional Requirement**

**Where possible**, the system shall cache validation results for unchanged workflows.

**Details:**

- Cache key: workflow_id + version hash
- TTL: 5 minutes (configurable)
- Invalidate on any graph modification

#### REQ-010-019: Visualization Hints

**Optional Requirement**

**Where possible**, the system shall provide visualization hints for detected issues.

**Details:**

- Highlight affected nodes and edges
- Suggest fix actions
- Provide coordinate hints for UI

---

## Specifications

### SPEC-010-A: File Structure (Parallel Implementation Safe)

```
backend/
  app/
    services/
      workflow/                    # NEW package (no conflicts)
        __init__.py               # Package init with exports
        validator.py              # DAG Validation Service (main)
        graph.py                  # Graph data structures
        algorithms.py             # Graph algorithms (DFS, BFS, topological sort)
        exceptions.py             # Validation-specific exceptions
    schemas/
      validation.py               # NEW file (validation schemas)
    api/
      v1/
        validation.py             # NEW file (validation endpoints)
```

### SPEC-010-B: Core Validation Service Interface

```python
# services/workflow/validator.py
from uuid import UUID
from typing import Optional

from app.schemas.validation import (
    ValidationRequest,
    ValidationResult,
    ValidationOptions,
    TopologyResult,
)


class DAGValidator:
    """Standalone DAG Validation Service.

    TAG: [SPEC-010] [DAG] [VALIDATION]

    This service provides comprehensive validation for workflow graphs.
    It is designed to be stateless and can be used independently of
    the existing workflow_service.py.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def validate_workflow(
        self,
        workflow_id: UUID,
        options: Optional[ValidationOptions] = None,
    ) -> ValidationResult:
        """Validate entire workflow graph.

        Performs all validation checks and returns comprehensive result.
        """
        ...

    async def validate_edge_addition(
        self,
        workflow_id: UUID,
        source_node_id: UUID,
        target_node_id: UUID,
        source_handle: Optional[str] = None,
        target_handle: Optional[str] = None,
    ) -> ValidationResult:
        """Validate adding a new edge (pre-creation check).

        Useful for real-time validation in UI.
        """
        ...

    async def validate_batch_edges(
        self,
        workflow_id: UUID,
        edges: list[EdgeCreate],
    ) -> ValidationResult:
        """Validate batch edge creation.

        Validates all edges together for efficiency.
        """
        ...

    async def get_topology(
        self,
        workflow_id: UUID,
    ) -> TopologyResult:
        """Generate topological sort and execution order.

        Returns execution levels for parallel processing.
        """
        ...

    async def check_cycle(
        self,
        workflow_id: UUID,
        proposed_edges: Optional[list[EdgeCreate]] = None,
    ) -> CycleCheckResult:
        """Check for cycles with optional proposed edges.

        Lightweight check for UI real-time validation.
        """
        ...
```

### SPEC-010-C: Validation Schemas

```python
# schemas/validation.py
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class ValidationLevel(str, Enum):
    """Validation strictness level."""
    MINIMAL = "minimal"      # Cycle detection only
    STANDARD = "standard"    # Structural + connectivity
    STRICT = "strict"        # All validations including schema compatibility


class ValidationErrorCode(str, Enum):
    """Validation error codes."""
    # Structural
    CYCLE_DETECTED = "CYCLE_DETECTED"
    SELF_LOOP_DETECTED = "SELF_LOOP_DETECTED"
    NODE_NOT_FOUND = "NODE_NOT_FOUND"
    DUPLICATE_EDGE = "DUPLICATE_EDGE"

    # Connectivity
    NO_TRIGGER_NODE = "NO_TRIGGER_NODE"
    DANGLING_NODES = "DANGLING_NODES"
    UNREACHABLE_NODES = "UNREACHABLE_NODES"
    DEAD_END_NODE = "DEAD_END_NODE"

    # Node compatibility
    INVALID_NODE_CONFIG = "INVALID_NODE_CONFIG"
    INVALID_HANDLE = "INVALID_HANDLE"
    INVALID_REFERENCE = "INVALID_REFERENCE"

    # Data flow
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    UNDEFINED_VARIABLE = "UNDEFINED_VARIABLE"

    # Limits
    GRAPH_TOO_LARGE = "GRAPH_TOO_LARGE"
    VALIDATION_TIMEOUT = "VALIDATION_TIMEOUT"


class ValidationOptions(BaseModel):
    """Options for validation request."""
    level: ValidationLevel = ValidationLevel.STANDARD
    include_topology: bool = True
    include_warnings: bool = True
    timeout_seconds: float = 5.0
    max_nodes: int = 500
    max_edges: int = 2000


class ValidationError(BaseModel):
    """Single validation error."""
    code: ValidationErrorCode
    message: str
    node_ids: list[UUID] = Field(default_factory=list)
    edge_ids: list[UUID] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class ValidationWarning(BaseModel):
    """Single validation warning (non-blocking)."""
    code: str
    message: str
    node_id: Optional[UUID] = None
    suggestion: Optional[str] = None


class TopologyLevel(BaseModel):
    """Single level in topological sort."""
    level: int
    node_ids: list[UUID]
    can_parallel: bool = True


class TopologyResult(BaseModel):
    """Topological analysis result."""
    execution_order: list[TopologyLevel]
    total_levels: int
    max_parallel_nodes: int
    critical_path_length: int
    critical_path: list[UUID]


class CycleCheckResult(BaseModel):
    """Result of cycle detection."""
    has_cycle: bool
    cycle_path: Optional[list[UUID]] = None
    cycle_description: Optional[str] = None


class ValidationResult(BaseModel):
    """Complete validation result."""
    model_config = ConfigDict(from_attributes=True)

    is_valid: bool
    workflow_id: UUID
    workflow_version: int
    validated_at: datetime

    # Validation details
    errors: list[ValidationError] = Field(default_factory=list)
    warnings: list[ValidationWarning] = Field(default_factory=list)

    # Topology (if requested and valid)
    topology: Optional[TopologyResult] = None

    # Statistics
    node_count: int = 0
    edge_count: int = 0
    validation_duration_ms: float = 0.0

    # Metadata
    validation_level: ValidationLevel = ValidationLevel.STANDARD
    cached: bool = False


class ValidationRequest(BaseModel):
    """Request for workflow validation."""
    workflow_id: UUID
    options: ValidationOptions = Field(default_factory=ValidationOptions)
    proposed_edges: list["EdgeCreate"] = Field(default_factory=list)
```

### SPEC-010-D: Graph Algorithm Module

```python
# services/workflow/algorithms.py
from collections import defaultdict, deque
from typing import TypeVar, Generic, Optional
from uuid import UUID


NodeId = TypeVar("NodeId")


class Graph(Generic[NodeId]):
    """Directed graph data structure for DAG operations.

    TAG: [SPEC-010] [DAG] [ALGORITHMS]
    """

    def __init__(self):
        self.adjacency: dict[NodeId, list[NodeId]] = defaultdict(list)
        self.reverse_adjacency: dict[NodeId, list[NodeId]] = defaultdict(list)
        self.nodes: set[NodeId] = set()

    def add_node(self, node_id: NodeId) -> None:
        """Add a node to the graph."""
        self.nodes.add(node_id)

    def add_edge(self, source: NodeId, target: NodeId) -> None:
        """Add a directed edge from source to target."""
        self.nodes.add(source)
        self.nodes.add(target)
        self.adjacency[source].append(target)
        self.reverse_adjacency[target].append(source)

    def detect_cycle(self) -> Optional[list[NodeId]]:
        """Detect cycle using DFS with path tracking.

        Returns cycle path if found, None otherwise.
        """
        ...

    def detect_cycle_with_proposed_edge(
        self, source: NodeId, target: NodeId
    ) -> Optional[list[NodeId]]:
        """Check if adding edge would create cycle."""
        ...

    def topological_sort_levels(self) -> list[list[NodeId]]:
        """Kahn's algorithm for level-based topological sort.

        Returns nodes grouped by execution level.
        """
        ...

    def find_unreachable_from(self, start_nodes: set[NodeId]) -> set[NodeId]:
        """Find nodes not reachable from any start node using BFS."""
        ...

    def find_dangling_nodes(self) -> set[NodeId]:
        """Find nodes with no incoming or outgoing edges."""
        ...

    def find_dead_ends(self, terminal_types: set[str]) -> set[NodeId]:
        """Find non-terminal nodes with no outgoing edges."""
        ...

    def get_critical_path(self) -> tuple[list[NodeId], int]:
        """Find longest path (critical path) in DAG."""
        ...
```

### SPEC-010-E: API Endpoint

```python
# api/v1/validation.py
from uuid import UUID
from fastapi import APIRouter, HTTPException, status

from app.api.deps import DBSession
from app.schemas.validation import (
    ValidationRequest,
    ValidationResult,
    ValidationOptions,
    TopologyResult,
    CycleCheckResult,
)
from app.services.workflow.validator import DAGValidator

router = APIRouter(prefix="/validation", tags=["validation"])


@router.post(
    "/workflows/{workflow_id}",
    response_model=ValidationResult,
    summary="Validate Workflow DAG",
    description="Perform comprehensive DAG validation for a workflow.",
)
async def validate_workflow(
    workflow_id: UUID,
    options: ValidationOptions = None,
    db: DBSession = None,
) -> ValidationResult:
    """Validate entire workflow graph.

    TAG: [SPEC-010] [API] [VALIDATION]

    Performs structural, connectivity, and optionally schema validation.
    Returns detailed validation results with errors, warnings, and topology.
    """
    validator = DAGValidator(db)

    try:
        result = await validator.validate_workflow(
            workflow_id=workflow_id,
            options=options or ValidationOptions(),
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/workflows/{workflow_id}/check-edge",
    response_model=CycleCheckResult,
    summary="Check Edge Addition",
    description="Quick check if adding an edge would create a cycle.",
)
async def check_edge(
    workflow_id: UUID,
    source_node_id: UUID,
    target_node_id: UUID,
    db: DBSession = None,
) -> CycleCheckResult:
    """Quick cycle check for proposed edge.

    TAG: [SPEC-010] [API] [VALIDATION]

    Lightweight validation for real-time UI feedback.
    """
    validator = DAGValidator(db)

    result = await validator.check_cycle(
        workflow_id=workflow_id,
        proposed_edges=[
            {"source_node_id": source_node_id, "target_node_id": target_node_id}
        ],
    )
    return result


@router.get(
    "/workflows/{workflow_id}/topology",
    response_model=TopologyResult,
    summary="Get Workflow Topology",
    description="Generate topological sort and execution order.",
)
async def get_topology(
    workflow_id: UUID,
    db: DBSession = None,
) -> TopologyResult:
    """Get execution topology for workflow.

    TAG: [SPEC-010] [API] [VALIDATION]

    Returns execution levels for parallel processing.
    """
    validator = DAGValidator(db)
    return await validator.get_topology(workflow_id)
```

### SPEC-010-F: Exception Definitions

```python
# services/workflow/exceptions.py
from typing import Optional, Any
from uuid import UUID


class DAGValidationError(Exception):
    """Base exception for DAG validation errors.

    TAG: [SPEC-010] [DAG] [EXCEPTIONS]
    """

    def __init__(
        self,
        message: str,
        error_code: str,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class CycleDetectedError(DAGValidationError):
    """Raised when a cycle is detected in the graph."""

    def __init__(self, cycle_path: list[UUID]):
        super().__init__(
            message=f"Cycle detected: {' -> '.join(str(n) for n in cycle_path)}",
            error_code="CYCLE_DETECTED",
            details={"cycle_path": [str(n) for n in cycle_path]},
        )
        self.cycle_path = cycle_path


class InvalidNodeReferenceError(DAGValidationError):
    """Raised when node reference is invalid."""

    def __init__(self, node_ids: list[UUID]):
        super().__init__(
            message=f"Invalid node references: {node_ids}",
            error_code="NODE_NOT_FOUND",
            details={"missing_nodes": [str(n) for n in node_ids]},
        )
        self.missing_nodes = node_ids


class GraphTooLargeError(DAGValidationError):
    """Raised when graph exceeds size limits."""

    def __init__(self, current: int, limit: int, metric: str = "nodes"):
        super().__init__(
            message=f"Graph too large: {current} {metric} (limit: {limit})",
            error_code="GRAPH_TOO_LARGE",
            details={"current": current, "limit": limit, "metric": metric},
        )


class ValidationTimeoutError(DAGValidationError):
    """Raised when validation exceeds timeout."""

    def __init__(self, timeout_seconds: float):
        super().__init__(
            message=f"Validation timeout after {timeout_seconds}s",
            error_code="VALIDATION_TIMEOUT",
            details={"timeout_seconds": timeout_seconds},
        )
```

---

## Constraints

### Technical Constraints

- All validation functions must be pure and stateless
- No modifications to existing `workflow_service.py` in Phase 1
- Must support async/await patterns for database access
- Must use Pydantic v2 `model_config = ConfigDict(from_attributes=True)`

### Performance Constraints

- Validation response time <100ms for workflows with <100 nodes
- Cycle detection must complete in O(V+E) time complexity
- Memory usage should not exceed 2x the graph size
- Support for concurrent validation requests

### Security Constraints

- Input validation for all parameters
- No SQL injection through node/edge queries
- Rate limiting on validation endpoints
- Audit logging for validation failures

---

## Dependencies

### Internal Dependencies

- SPEC-001: Base models and mixins
- SPEC-003: Workflow, Node, Edge models
- SPEC-007: DAG validation interface (REQ-DAG-001)

### External Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | >=0.115.0 | API framework |
| pydantic | >=2.10.0 | Schema validation |
| sqlalchemy[asyncio] | >=2.0.0 | Database access |

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Circular import with existing code | Low | Medium | Isolated package structure |
| Performance degradation for large graphs | Medium | High | Caching, timeout limits |
| Breaking existing DAG validation | Low | High | Parallel implementation, no existing code changes |
| Schema evolution conflicts | Medium | Medium | Version-controlled schemas |

---

## Related SPECs

- **SPEC-001**: Database Foundation Setup (base models)
- **SPEC-003**: Workflow Domain Models (Workflow, Node, Edge)
- **SPEC-007**: Workflow API Endpoints (DAG validation interface)
- **SPEC-008**: Scheduler Implementation (uses validation before scheduling)
- **SPEC-011**: Workflow Execution Engine (uses validation before execution)

---

## Integration Strategy

### Phase 1: Standalone Implementation (This SPEC)

- Create new `services/workflow/` package
- Implement all validation functions
- Create validation schemas
- Add validation API endpoint
- **NO changes to existing files**

### Phase 2: Integration (Future SPEC)

- Integrate with `EdgeService._validate_dag()` in `workflow_service.py`
- Replace inline validation with service calls
- Add caching layer
- Enable real-time validation via WebSocket

---

## Change History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-14 | workflow-spec | Initial SPEC creation |
