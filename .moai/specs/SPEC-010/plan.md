# SPEC-010: Implementation Plan

## Tags

`[SPEC-010]` `[DAG]` `[VALIDATION]` `[IMPLEMENTATION]` `[BACKEND]`

---

## Implementation Overview

This document defines the implementation plan for PasteTrader's DAG Validation Service. The implementation is designed for **parallel development** with no conflicts to existing codebase. All new code resides in dedicated modules that can be developed independently.

### Parallel Implementation Strategy

| Existing File | Status | Conflict Risk |
|---------------|--------|---------------|
| `workflow_service.py` | No changes | None |
| `workflows.py` (API) | No changes | None |
| `schemas/__init__.py` | Minor export addition | Very Low |
| `services/__init__.py` | Minor export addition | Very Low |

**New Files (No Conflicts):**
- `services/workflow/__init__.py` - NEW package
- `services/workflow/validator.py` - NEW (main service)
- `services/workflow/graph.py` - NEW (data structures)
- `services/workflow/algorithms.py` - NEW (graph algorithms)
- `services/workflow/exceptions.py` - NEW (exceptions)
- `schemas/validation.py` - NEW (validation schemas)
- `api/v1/validation.py` - NEW (API endpoints)
- `tests/test_services_validator.py` - NEW (unit tests)
- `tests/test_api_validation.py` - NEW (API tests)

---

## Milestones

### Milestone 1: Foundation - Graph Data Structures (Primary Goal)

**Priority:** High

**Deliverables:**
- `backend/app/services/workflow/__init__.py`
- `backend/app/services/workflow/graph.py`
- `backend/app/services/workflow/exceptions.py`

**Tasks:**

1. Create Workflow Package Structure
   - Create `services/workflow/` directory
   - Initialize package with exports
   - Ensure no circular imports

2. Implement Graph Data Structure
   - Generic Graph class with type hints
   - Adjacency list representation
   - Reverse adjacency for predecessor lookup
   - Node and edge management

3. Define Custom Exceptions
   - DAGValidationError base class
   - CycleDetectedError with path
   - InvalidNodeReferenceError
   - GraphTooLargeError
   - ValidationTimeoutError

**Technical Approach:**

```python
# services/workflow/__init__.py
"""Workflow validation package.

TAG: [SPEC-010] [DAG] [VALIDATION]
"""
from app.services.workflow.validator import DAGValidator
from app.services.workflow.graph import Graph
from app.services.workflow.exceptions import (
    DAGValidationError,
    CycleDetectedError,
    InvalidNodeReferenceError,
    GraphTooLargeError,
    ValidationTimeoutError,
)

__all__ = [
    "DAGValidator",
    "Graph",
    "DAGValidationError",
    "CycleDetectedError",
    "InvalidNodeReferenceError",
    "GraphTooLargeError",
    "ValidationTimeoutError",
]
```

```python
# services/workflow/graph.py
from collections import defaultdict
from typing import TypeVar, Generic, Optional, Set, List, Dict
from uuid import UUID

NodeId = TypeVar("NodeId")


class Graph(Generic[NodeId]):
    """Directed graph data structure for DAG operations.

    TAG: [SPEC-010] [DAG] [GRAPH]

    Supports:
    - O(1) node/edge addition
    - O(V+E) cycle detection
    - O(V+E) topological sort
    - O(V+E) reachability analysis
    """

    def __init__(self):
        self.adjacency: Dict[NodeId, List[NodeId]] = defaultdict(list)
        self.reverse_adjacency: Dict[NodeId, List[NodeId]] = defaultdict(list)
        self.nodes: Set[NodeId] = set()
        self._edge_count: int = 0

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return self._edge_count

    def add_node(self, node_id: NodeId) -> None:
        """Add a node to the graph."""
        self.nodes.add(node_id)

    def add_edge(self, source: NodeId, target: NodeId) -> None:
        """Add a directed edge from source to target."""
        self.nodes.add(source)
        self.nodes.add(target)
        self.adjacency[source].append(target)
        self.reverse_adjacency[target].append(source)
        self._edge_count += 1

    def has_edge(self, source: NodeId, target: NodeId) -> bool:
        """Check if edge exists."""
        return target in self.adjacency.get(source, [])

    def get_successors(self, node_id: NodeId) -> List[NodeId]:
        """Get all successor nodes."""
        return self.adjacency.get(node_id, [])

    def get_predecessors(self, node_id: NodeId) -> List[NodeId]:
        """Get all predecessor nodes."""
        return self.reverse_adjacency.get(node_id, [])

    def get_in_degree(self, node_id: NodeId) -> int:
        """Get number of incoming edges."""
        return len(self.reverse_adjacency.get(node_id, []))

    def get_out_degree(self, node_id: NodeId) -> int:
        """Get number of outgoing edges."""
        return len(self.adjacency.get(node_id, []))

    def copy(self) -> "Graph[NodeId]":
        """Create a shallow copy of the graph."""
        new_graph = Graph[NodeId]()
        new_graph.nodes = self.nodes.copy()
        new_graph.adjacency = defaultdict(list, {k: v.copy() for k, v in self.adjacency.items()})
        new_graph.reverse_adjacency = defaultdict(list, {k: v.copy() for k, v in self.reverse_adjacency.items()})
        new_graph._edge_count = self._edge_count
        return new_graph
```

---

### Milestone 2: Core Algorithms (Primary Goal)

**Priority:** High

**Deliverables:**
- `backend/app/services/workflow/algorithms.py`

**Tasks:**

1. Cycle Detection Algorithm
   - DFS-based detection with path tracking
   - Support for finding cycle path
   - Handle proposed edge addition

2. Topological Sort Algorithm
   - Kahn's algorithm for level-based sort
   - Return execution levels for parallelism
   - Handle invalid DAG gracefully

3. Reachability Analysis
   - BFS from trigger nodes
   - Find unreachable nodes
   - Find dangling nodes

4. Critical Path Analysis
   - Longest path calculation
   - Support for weighted paths (future)

**Technical Approach:**

```python
# services/workflow/algorithms.py
from collections import deque
from typing import Optional, Set, List, Dict, Tuple
from uuid import UUID

from app.services.workflow.graph import Graph


def detect_cycle(graph: Graph[UUID]) -> Optional[List[UUID]]:
    """Detect cycle using DFS with path tracking.

    TAG: [SPEC-010] [DAG] [ALGORITHMS]

    Returns:
        List of node IDs forming the cycle if found, None otherwise.

    Time Complexity: O(V + E)
    Space Complexity: O(V)
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    color: Dict[UUID, int] = {node: WHITE for node in graph.nodes}
    parent: Dict[UUID, Optional[UUID]] = {node: None for node in graph.nodes}

    def dfs(node: UUID, path: List[UUID]) -> Optional[List[UUID]]:
        color[node] = GRAY
        path.append(node)

        for neighbor in graph.get_successors(node):
            if color[neighbor] == GRAY:
                # Found cycle - extract cycle path
                cycle_start = path.index(neighbor)
                return path[cycle_start:] + [neighbor]
            elif color[neighbor] == WHITE:
                parent[neighbor] = node
                result = dfs(neighbor, path)
                if result:
                    return result

        path.pop()
        color[node] = BLACK
        return None

    for node in graph.nodes:
        if color[node] == WHITE:
            result = dfs(node, [])
            if result:
                return result

    return None


def detect_cycle_with_proposed_edge(
    graph: Graph[UUID],
    source: UUID,
    target: UUID,
) -> Optional[List[UUID]]:
    """Check if adding edge would create cycle.

    TAG: [SPEC-010] [DAG] [ALGORITHMS]

    More efficient than copying graph - checks path from target to source.
    """
    if source == target:
        return [source, source]  # Self-loop

    # Check if there's already a path from target to source
    visited: Set[UUID] = set()
    path: List[UUID] = []

    def dfs(node: UUID) -> bool:
        if node == source:
            return True
        if node in visited:
            return False

        visited.add(node)
        path.append(node)

        for neighbor in graph.get_successors(node):
            if dfs(neighbor):
                return True

        path.pop()
        return False

    if dfs(target):
        # Cycle would be: source -> target -> ... -> source
        return [source, target] + path[:path.index(source) + 1] if source in path else [source, target] + path + [source]

    return None


def topological_sort_levels(graph: Graph[UUID]) -> List[List[UUID]]:
    """Kahn's algorithm for level-based topological sort.

    TAG: [SPEC-010] [DAG] [ALGORITHMS]

    Returns:
        List of levels, each containing nodes that can execute in parallel.

    Time Complexity: O(V + E)
    """
    in_degree: Dict[UUID, int] = {node: graph.get_in_degree(node) for node in graph.nodes}
    levels: List[List[UUID]] = []

    # Start with nodes having no incoming edges
    current_level = [node for node in graph.nodes if in_degree[node] == 0]

    while current_level:
        levels.append(current_level)
        next_level = []

        for node in current_level:
            for neighbor in graph.get_successors(node):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    next_level.append(neighbor)

        current_level = next_level

    # Check if all nodes are processed (valid DAG)
    processed_count = sum(len(level) for level in levels)
    if processed_count != graph.node_count:
        # Graph has cycle - return empty (should use detect_cycle for details)
        return []

    return levels


def find_reachable_nodes(
    graph: Graph[UUID],
    start_nodes: Set[UUID],
) -> Set[UUID]:
    """Find all nodes reachable from start nodes using BFS.

    TAG: [SPEC-010] [DAG] [ALGORITHMS]
    """
    reachable: Set[UUID] = set()
    queue = deque(start_nodes)

    while queue:
        node = queue.popleft()
        if node in reachable:
            continue

        reachable.add(node)
        for neighbor in graph.get_successors(node):
            if neighbor not in reachable:
                queue.append(neighbor)

    return reachable


def find_unreachable_nodes(
    graph: Graph[UUID],
    start_nodes: Set[UUID],
) -> Set[UUID]:
    """Find nodes not reachable from any start node.

    TAG: [SPEC-010] [DAG] [ALGORITHMS]
    """
    reachable = find_reachable_nodes(graph, start_nodes)
    return graph.nodes - reachable


def find_dangling_nodes(graph: Graph[UUID]) -> Set[UUID]:
    """Find nodes with no connections.

    TAG: [SPEC-010] [DAG] [ALGORITHMS]
    """
    dangling = set()
    for node in graph.nodes:
        if graph.get_in_degree(node) == 0 and graph.get_out_degree(node) == 0:
            dangling.add(node)
    return dangling


def find_dead_end_nodes(
    graph: Graph[UUID],
    terminal_node_ids: Set[UUID],
) -> Set[UUID]:
    """Find non-terminal nodes with no outgoing edges.

    TAG: [SPEC-010] [DAG] [ALGORITHMS]
    """
    dead_ends = set()
    for node in graph.nodes:
        if node not in terminal_node_ids and graph.get_out_degree(node) == 0:
            dead_ends.add(node)
    return dead_ends


def find_critical_path(graph: Graph[UUID]) -> Tuple[List[UUID], int]:
    """Find longest path (critical path) in DAG.

    TAG: [SPEC-010] [DAG] [ALGORITHMS]

    Returns:
        Tuple of (path as list of node IDs, path length)
    """
    # Get topological order
    levels = topological_sort_levels(graph)
    if not levels:
        return [], 0

    flat_order = [node for level in levels for node in level]

    # Dynamic programming for longest path
    dist: Dict[UUID, int] = {node: 0 for node in graph.nodes}
    parent: Dict[UUID, Optional[UUID]] = {node: None for node in graph.nodes}

    for node in flat_order:
        for neighbor in graph.get_successors(node):
            if dist[neighbor] < dist[node] + 1:
                dist[neighbor] = dist[node] + 1
                parent[neighbor] = node

    # Find node with maximum distance
    max_node = max(dist.keys(), key=lambda n: dist[n])
    max_dist = dist[max_node]

    # Reconstruct path
    path = []
    current = max_node
    while current is not None:
        path.append(current)
        current = parent[current]

    path.reverse()
    return path, max_dist
```

---

### Milestone 3: Validation Schemas (Primary Goal)

**Priority:** High

**Deliverables:**
- `backend/app/schemas/validation.py`

**Tasks:**

1. Define Validation Enums
   - ValidationLevel (minimal, standard, strict)
   - ValidationErrorCode (all error types)

2. Define Request/Response Schemas
   - ValidationOptions
   - ValidationRequest
   - ValidationResult

3. Define Error/Warning Schemas
   - ValidationError
   - ValidationWarning

4. Define Topology Schemas
   - TopologyLevel
   - TopologyResult
   - CycleCheckResult

**Technical Approach:**

See SPEC-010-C in spec.md for complete schema definitions.

---

### Milestone 4: DAG Validator Service (Secondary Goal)

**Priority:** High

**Deliverables:**
- `backend/app/services/workflow/validator.py`

**Tasks:**

1. Core Validator Class
   - Async database integration
   - Graph building from workflow
   - Validation orchestration

2. Structural Validation Methods
   - validate_cycles()
   - validate_node_existence()
   - validate_duplicate_edges()

3. Connectivity Validation Methods
   - validate_trigger_nodes()
   - validate_dangling_nodes()
   - validate_reachability()
   - validate_dead_ends()

4. Node Compatibility Methods
   - validate_node_configs()
   - validate_handles()
   - validate_references()

5. Topology Methods
   - get_topology()
   - get_execution_order()

**Technical Approach:**

```python
# services/workflow/validator.py
from datetime import datetime, UTC
from typing import Optional, Set
from uuid import UUID
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Workflow, Node, Edge, Tool, Agent
from app.models.enums import NodeType
from app.schemas.validation import (
    ValidationResult,
    ValidationOptions,
    ValidationLevel,
    ValidationError,
    ValidationWarning,
    ValidationErrorCode,
    TopologyResult,
    TopologyLevel,
    CycleCheckResult,
)
from app.services.workflow.graph import Graph
from app.services.workflow import algorithms
from app.services.workflow.exceptions import (
    DAGValidationError,
    CycleDetectedError,
    GraphTooLargeError,
    ValidationTimeoutError,
)


class DAGValidator:
    """Standalone DAG Validation Service.

    TAG: [SPEC-010] [DAG] [VALIDATION]

    This service provides comprehensive validation for workflow graphs.
    All methods are stateless and can be used independently.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def validate_workflow(
        self,
        workflow_id: UUID,
        options: Optional[ValidationOptions] = None,
    ) -> ValidationResult:
        """Validate entire workflow graph.

        TAG: [SPEC-010] [DAG] [VALIDATION]
        """
        start_time = datetime.now(UTC)
        options = options or ValidationOptions()

        errors: list[ValidationError] = []
        warnings: list[ValidationWarning] = []
        topology: Optional[TopologyResult] = None

        try:
            # Load workflow with nodes and edges
            workflow = await self._load_workflow(workflow_id)
            if not workflow:
                errors.append(ValidationError(
                    code=ValidationErrorCode.NODE_NOT_FOUND,
                    message=f"Workflow {workflow_id} not found",
                ))
                return self._build_result(
                    workflow_id=workflow_id,
                    workflow_version=0,
                    is_valid=False,
                    errors=errors,
                    start_time=start_time,
                    options=options,
                )

            # Check size limits
            if len(workflow.nodes) > options.max_nodes:
                raise GraphTooLargeError(
                    current=len(workflow.nodes),
                    limit=options.max_nodes,
                    metric="nodes",
                )

            if len(workflow.edges) > options.max_edges:
                raise GraphTooLargeError(
                    current=len(workflow.edges),
                    limit=options.max_edges,
                    metric="edges",
                )

            # Build graph
            graph = self._build_graph(workflow)

            # Run validations with timeout
            validation_task = self._run_validations(
                workflow=workflow,
                graph=graph,
                options=options,
            )

            try:
                validation_errors, validation_warnings = await asyncio.wait_for(
                    validation_task,
                    timeout=options.timeout_seconds,
                )
                errors.extend(validation_errors)
                warnings.extend(validation_warnings)
            except asyncio.TimeoutError:
                raise ValidationTimeoutError(options.timeout_seconds)

            # Generate topology if valid and requested
            if not errors and options.include_topology:
                topology = self._generate_topology(graph, workflow)

            return self._build_result(
                workflow_id=workflow_id,
                workflow_version=workflow.version,
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings if options.include_warnings else [],
                topology=topology,
                node_count=len(workflow.nodes),
                edge_count=len(workflow.edges),
                start_time=start_time,
                options=options,
            )

        except DAGValidationError as e:
            errors.append(ValidationError(
                code=ValidationErrorCode[e.error_code],
                message=e.message,
                details=e.details,
            ))
            return self._build_result(
                workflow_id=workflow_id,
                workflow_version=0,
                is_valid=False,
                errors=errors,
                start_time=start_time,
                options=options,
            )

    async def check_cycle(
        self,
        workflow_id: UUID,
        proposed_edges: Optional[list[dict]] = None,
    ) -> CycleCheckResult:
        """Quick cycle check for proposed edges.

        TAG: [SPEC-010] [DAG] [VALIDATION]
        """
        workflow = await self._load_workflow(workflow_id)
        if not workflow:
            return CycleCheckResult(
                has_cycle=False,
                cycle_description="Workflow not found",
            )

        graph = self._build_graph(workflow)

        # Check existing graph first
        existing_cycle = algorithms.detect_cycle(graph)
        if existing_cycle:
            return CycleCheckResult(
                has_cycle=True,
                cycle_path=existing_cycle,
                cycle_description=self._format_cycle_path(existing_cycle),
            )

        # Check proposed edges
        if proposed_edges:
            for edge in proposed_edges:
                source = edge.get("source_node_id")
                target = edge.get("target_node_id")
                if source and target:
                    cycle = algorithms.detect_cycle_with_proposed_edge(
                        graph, source, target
                    )
                    if cycle:
                        return CycleCheckResult(
                            has_cycle=True,
                            cycle_path=cycle,
                            cycle_description=self._format_cycle_path(cycle),
                        )
                    # Add edge for subsequent checks
                    graph.add_edge(source, target)

        return CycleCheckResult(has_cycle=False)

    async def get_topology(
        self,
        workflow_id: UUID,
    ) -> TopologyResult:
        """Generate topological sort and execution order.

        TAG: [SPEC-010] [DAG] [VALIDATION]
        """
        workflow = await self._load_workflow(workflow_id)
        if not workflow:
            return TopologyResult(
                execution_order=[],
                total_levels=0,
                max_parallel_nodes=0,
                critical_path_length=0,
                critical_path=[],
            )

        graph = self._build_graph(workflow)
        return self._generate_topology(graph, workflow)

    # Private helper methods

    async def _load_workflow(self, workflow_id: UUID) -> Optional[Workflow]:
        """Load workflow with nodes and edges."""
        result = await self.db.execute(
            select(Workflow)
            .where(Workflow.id == workflow_id)
            .where(Workflow.deleted_at.is_(None))
            .options(
                selectinload(Workflow.nodes),
                selectinload(Workflow.edges),
            )
        )
        return result.scalar_one_or_none()

    def _build_graph(self, workflow: Workflow) -> Graph[UUID]:
        """Build graph from workflow."""
        graph = Graph[UUID]()

        for node in workflow.nodes:
            graph.add_node(node.id)

        for edge in workflow.edges:
            graph.add_edge(edge.source_node_id, edge.target_node_id)

        return graph

    async def _run_validations(
        self,
        workflow: Workflow,
        graph: Graph[UUID],
        options: ValidationOptions,
    ) -> tuple[list[ValidationError], list[ValidationWarning]]:
        """Run all validation checks."""
        errors: list[ValidationError] = []
        warnings: list[ValidationWarning] = []

        # Always run: Cycle detection
        cycle = algorithms.detect_cycle(graph)
        if cycle:
            errors.append(ValidationError(
                code=ValidationErrorCode.CYCLE_DETECTED,
                message=f"Cycle detected: {self._format_cycle_path(cycle)}",
                node_ids=cycle,
                details={"cycle_path": [str(n) for n in cycle]},
            ))

        if options.level == ValidationLevel.MINIMAL:
            return errors, warnings

        # Standard validations
        # Trigger node check
        trigger_nodes = [n for n in workflow.nodes if n.node_type == NodeType.TRIGGER]
        if not trigger_nodes:
            errors.append(ValidationError(
                code=ValidationErrorCode.NO_TRIGGER_NODE,
                message="Workflow must have at least one trigger node",
            ))

        # Dangling nodes
        dangling = algorithms.find_dangling_nodes(graph)
        # Exclude single-trigger-only workflows
        if dangling and not (len(workflow.nodes) == 1 and len(trigger_nodes) == 1):
            errors.append(ValidationError(
                code=ValidationErrorCode.DANGLING_NODES,
                message=f"Isolated nodes detected: {len(dangling)} nodes",
                node_ids=list(dangling),
            ))

        # Unreachable nodes
        if trigger_nodes:
            trigger_ids = {n.id for n in trigger_nodes}
            unreachable = algorithms.find_unreachable_nodes(graph, trigger_ids)
            if unreachable:
                errors.append(ValidationError(
                    code=ValidationErrorCode.UNREACHABLE_NODES,
                    message=f"Nodes not reachable from trigger: {len(unreachable)} nodes",
                    node_ids=list(unreachable),
                ))

        # Dead-end warnings
        terminal_types = {NodeType.AGGREGATOR}  # Types that can be terminal
        terminal_ids = {n.id for n in workflow.nodes if n.node_type in terminal_types}
        dead_ends = algorithms.find_dead_end_nodes(graph, terminal_ids)
        for node_id in dead_ends:
            node = next((n for n in workflow.nodes if n.id == node_id), None)
            if node:
                warnings.append(ValidationWarning(
                    code="DEAD_END_NODE",
                    message=f"{node.node_type.value} node has no outgoing edges",
                    node_id=node_id,
                    suggestion="Consider connecting to downstream nodes or marking as terminal",
                ))

        if options.level == ValidationLevel.STRICT:
            # Additional strict validations
            # Node config validation
            config_errors = await self._validate_node_configs(workflow)
            errors.extend(config_errors)

            # Reference validation
            ref_errors = await self._validate_references(workflow)
            errors.extend(ref_errors)

        return errors, warnings

    async def _validate_node_configs(
        self,
        workflow: Workflow,
    ) -> list[ValidationError]:
        """Validate node-specific configuration requirements."""
        errors = []
        for node in workflow.nodes:
            if node.node_type == NodeType.TOOL and not node.tool_id:
                errors.append(ValidationError(
                    code=ValidationErrorCode.INVALID_NODE_CONFIG,
                    message=f"Tool node '{node.name}' must reference a tool",
                    node_ids=[node.id],
                    details={"missing_field": "tool_id"},
                ))
            elif node.node_type == NodeType.AGENT and not node.agent_id:
                errors.append(ValidationError(
                    code=ValidationErrorCode.INVALID_NODE_CONFIG,
                    message=f"Agent node '{node.name}' must reference an agent",
                    node_ids=[node.id],
                    details={"missing_field": "agent_id"},
                ))
        return errors

    async def _validate_references(
        self,
        workflow: Workflow,
    ) -> list[ValidationError]:
        """Validate tool and agent references exist."""
        errors = []

        # Collect tool and agent IDs
        tool_ids = {n.tool_id for n in workflow.nodes if n.tool_id}
        agent_ids = {n.agent_id for n in workflow.nodes if n.agent_id}

        # Check tools exist
        if tool_ids:
            result = await self.db.execute(
                select(Tool.id).where(Tool.id.in_(tool_ids))
            )
            existing_tools = {row[0] for row in result.fetchall()}
            missing_tools = tool_ids - existing_tools
            for tool_id in missing_tools:
                node = next(n for n in workflow.nodes if n.tool_id == tool_id)
                errors.append(ValidationError(
                    code=ValidationErrorCode.INVALID_REFERENCE,
                    message=f"Tool {tool_id} referenced by node '{node.name}' not found",
                    node_ids=[node.id],
                    details={"reference_type": "tool", "reference_id": str(tool_id)},
                ))

        # Check agents exist
        if agent_ids:
            result = await self.db.execute(
                select(Agent.id).where(Agent.id.in_(agent_ids))
            )
            existing_agents = {row[0] for row in result.fetchall()}
            missing_agents = agent_ids - existing_agents
            for agent_id in missing_agents:
                node = next(n for n in workflow.nodes if n.agent_id == agent_id)
                errors.append(ValidationError(
                    code=ValidationErrorCode.INVALID_REFERENCE,
                    message=f"Agent {agent_id} referenced by node '{node.name}' not found",
                    node_ids=[node.id],
                    details={"reference_type": "agent", "reference_id": str(agent_id)},
                ))

        return errors

    def _generate_topology(
        self,
        graph: Graph[UUID],
        workflow: Workflow,
    ) -> TopologyResult:
        """Generate topology result."""
        levels = algorithms.topological_sort_levels(graph)
        critical_path, critical_length = algorithms.find_critical_path(graph)

        return TopologyResult(
            execution_order=[
                TopologyLevel(
                    level=i,
                    node_ids=level,
                    can_parallel=len(level) > 1,
                )
                for i, level in enumerate(levels)
            ],
            total_levels=len(levels),
            max_parallel_nodes=max(len(level) for level in levels) if levels else 0,
            critical_path_length=critical_length,
            critical_path=critical_path,
        )

    def _build_result(
        self,
        workflow_id: UUID,
        workflow_version: int,
        is_valid: bool,
        errors: list[ValidationError],
        start_time: datetime,
        options: ValidationOptions,
        warnings: Optional[list[ValidationWarning]] = None,
        topology: Optional[TopologyResult] = None,
        node_count: int = 0,
        edge_count: int = 0,
    ) -> ValidationResult:
        """Build validation result."""
        duration = (datetime.now(UTC) - start_time).total_seconds() * 1000

        return ValidationResult(
            is_valid=is_valid,
            workflow_id=workflow_id,
            workflow_version=workflow_version,
            validated_at=datetime.now(UTC),
            errors=errors,
            warnings=warnings or [],
            topology=topology,
            node_count=node_count,
            edge_count=edge_count,
            validation_duration_ms=duration,
            validation_level=options.level,
            cached=False,
        )

    def _format_cycle_path(self, cycle: list[UUID]) -> str:
        """Format cycle path for human-readable message."""
        return " -> ".join(str(n)[:8] for n in cycle)
```

---

### Milestone 5: API Endpoints (Secondary Goal)

**Priority:** High

**Deliverables:**
- `backend/app/api/v1/validation.py`
- Update `backend/app/api/v1/__init__.py`

**Tasks:**

1. Validation Endpoints
   - POST `/validation/workflows/{id}` - Full validation
   - POST `/validation/workflows/{id}/check-edge` - Quick cycle check
   - GET `/validation/workflows/{id}/topology` - Get topology

2. Router Registration
   - Add to v1 router

**Technical Approach:**

See SPEC-010-E in spec.md for complete endpoint definitions.

---

### Milestone 6: Unit Tests (Final Goal)

**Priority:** High

**Deliverables:**
- `backend/tests/test_services_validator.py`
- `backend/tests/test_workflow_algorithms.py`
- `backend/tests/test_api_validation.py`

**Tasks:**

1. Graph Algorithm Tests
   - Test cycle detection (various cycle types)
   - Test topological sort
   - Test reachability analysis

2. Validator Service Tests
   - Test each validation type
   - Test options and levels
   - Test error responses

3. API Tests
   - Test validation endpoint
   - Test edge check endpoint
   - Test topology endpoint

**Test Coverage Target:** 90%+

---

### Milestone 7: Integration Tests (Final Goal)

**Priority:** Medium

**Deliverables:**
- `backend/tests/integration/test_validation_integration.py`

**Tasks:**

1. End-to-End Validation Tests
   - Create workflow with nodes/edges
   - Run validation
   - Verify results

2. Performance Tests
   - Test with large graphs (100+ nodes)
   - Verify timeout handling
   - Check memory usage

---

## Architecture Design

### Component Diagram

```
backend/
  app/
    services/
      workflow/                      # NEW package
        __init__.py                  # Package exports
        validator.py                 # DAGValidator service
        graph.py                     # Graph data structure
        algorithms.py                # Graph algorithms
        exceptions.py                # Custom exceptions
    schemas/
      validation.py                  # NEW - Validation schemas
    api/
      v1/
        validation.py                # NEW - Validation endpoints
        __init__.py                  # Updated - Router registration
  tests/
    test_services_validator.py       # NEW - Validator tests
    test_workflow_algorithms.py      # NEW - Algorithm tests
    test_api_validation.py           # NEW - API tests
    integration/
      test_validation_integration.py # NEW - Integration tests
```

### Dependency Flow

```
api/v1/validation.py
       │
       ▼
services/workflow/validator.py
       │
       ├──────────────────────┐
       ▼                      ▼
services/workflow/        schemas/validation.py
algorithms.py
       │
       ▼
services/workflow/graph.py
```

### No Conflicts Guarantee

| File | Changes | Risk |
|------|---------|------|
| `workflow_service.py` | None | No conflict |
| `workflows.py` (API) | None | No conflict |
| `schemas/__init__.py` | Add export | Very low |
| `services/__init__.py` | Add export | Very low |
| `api/v1/__init__.py` | Add router | Very low |

---

## TDD Approach

### Test Sequence

1. **Algorithm Tests First**
   - Test graph.py data structure
   - Test algorithms.py (cycle, topo sort, etc.)
   - Use simple in-memory graphs

2. **Service Tests**
   - Test validator.py with mocked DB
   - Test each validation type
   - Use fixtures for workflows

3. **API Tests**
   - Test endpoints with test client
   - Verify response schemas
   - Test error cases

### RED-GREEN-REFACTOR Cycle

1. Write failing test for algorithm
2. Implement minimum code to pass
3. Refactor for clarity and performance

---

## Risk Mitigation

| Risk | Mitigation Strategy |
|------|---------------------|
| Circular imports | Isolated package with clear boundaries |
| Performance issues | Timeout protection, size limits |
| Breaking existing code | No changes to existing files in Phase 1 |
| Test coverage gaps | TDD approach, 90%+ target |

---

## Output Files Summary

| File Path | Purpose | Priority |
|-----------|---------|----------|
| `services/workflow/__init__.py` | Package exports | High |
| `services/workflow/graph.py` | Graph data structure | High |
| `services/workflow/algorithms.py` | Graph algorithms | High |
| `services/workflow/exceptions.py` | Custom exceptions | High |
| `services/workflow/validator.py` | DAG Validator service | High |
| `schemas/validation.py` | Validation schemas | High |
| `api/v1/validation.py` | API endpoints | High |
| `tests/test_services_validator.py` | Unit tests | High |
| `tests/test_workflow_algorithms.py` | Algorithm tests | High |
| `tests/test_api_validation.py` | API tests | High |

---

## Definition of Done

- [ ] All new files created in isolated locations
- [ ] No changes to existing `workflow_service.py`
- [ ] Graph data structure with full test coverage
- [ ] All graph algorithms implemented and tested
- [ ] DAGValidator service with all validation types
- [ ] Validation schemas with Pydantic v2
- [ ] API endpoints with OpenAPI documentation
- [ ] Unit tests with 90%+ coverage
- [ ] Integration tests passing
- [ ] ruff lint pass
- [ ] mypy type check pass

---

## Next Steps After Completion

1. **Phase 2 Integration**: Integrate with existing `EdgeService._validate_dag()`
2. **SPEC-011**: Workflow Execution Engine (uses validation before execution)
3. **Caching Layer**: Add Redis caching for validation results
4. **WebSocket Support**: Real-time validation updates

---

## Related Documents

- [spec.md](spec.md) - Detailed requirements
- [acceptance.md](acceptance.md) - Acceptance criteria
- [SPEC-007/spec.md](../SPEC-007/spec.md) - Workflow API (DAG interface)
- [SPEC-003/spec.md](../SPEC-003/spec.md) - Workflow Domain Models

---

## Change History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-14 | workflow-spec | Initial implementation plan |
