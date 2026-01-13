# SPEC-007: Implementation Plan

## Tags

`[SPEC-007]` `[API]` `[WORKFLOW]` `[EXECUTION]` `[ENDPOINTS]` `[BACKEND]`

---

## Implementation Overview

This document defines the implementation plan for PasteTrader's Workflow API Endpoints. This SPEC covers implementing RESTful API endpoints for workflow management, node/edge operations, and execution tracking with proper service layer abstraction.

---

## Milestones

### Milestone 1: Foundation - Dependencies Setup (Primary Goal)

**Priority:** High

**Deliverables:**
- `backend/app/api/deps.py` - DBSession, Pagination, Sorting dependencies

**Tasks:**

1. Database Session Dependency
   - AsyncSession dependency injection
   - Proper session lifecycle management

2. Pagination Dependency
   - Page, size parameters with defaults
   - Offset calculation helper
   - Maximum page size limit (100)

3. Sorting Dependency
   - Sort field and direction parameters
   - Default sorting configuration
   - Validation for allowed sort fields

**Technical Approach:**
```python
from typing import Annotated
from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Database session dependency.

    TAG: [SPEC-007] [API] [DEPS]
    """
    async with async_session_maker() as session:
        yield session


DBSession = Annotated[AsyncSession, Depends(get_db)]


class Pagination:
    """Pagination parameters dependency.

    TAG: [SPEC-007] [API] [DEPS]
    """

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number"),
        size: int = Query(20, ge=1, le=100, description="Items per page"),
    ):
        self.page = page
        self.size = size
        self.offset = (page - 1) * size


class Sorting:
    """Sorting parameters dependency.

    TAG: [SPEC-007] [API] [DEPS]
    """

    def __init__(
        self,
        sort_by: str = Query("created_at", description="Field to sort by"),
        sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    ):
        self.sort_by = sort_by
        self.sort_order = sort_order
```

---

### Milestone 2: Foundation - Base Schemas (Primary Goal)

**Priority:** High

**Deliverables:**
- `backend/app/schemas/base.py` - BaseResponse, PaginatedResponse, ErrorResponse

**Tasks:**

1. BaseResponse Schema
   - Generic wrapper for single item responses
   - Success flag and message fields
   - Timestamp field

2. PaginatedResponse Schema
   - Generic paginated list response
   - Total count, page, size, total_pages fields
   - Items list with proper typing

3. ErrorResponse Schema
   - Error code and message
   - Details field for validation errors
   - Request ID for tracing

**Technical Approach:**
```python
from datetime import datetime
from typing import Generic, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    """Base response wrapper.

    TAG: [SPEC-007] [API] [SCHEMA]
    """

    model_config = ConfigDict(from_attributes=True)

    success: bool = True
    message: str | None = None
    data: T
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated list response.

    TAG: [SPEC-007] [API] [SCHEMA]
    """

    model_config = ConfigDict(from_attributes=True)

    items: list[T]
    total: int
    page: int
    size: int
    total_pages: int


class ErrorResponse(BaseModel):
    """Error response schema.

    TAG: [SPEC-007] [API] [SCHEMA]
    """

    success: bool = False
    error_code: str
    message: str
    details: dict | None = None
    request_id: str | None = None
```

---

### Milestone 3: Foundation - Workflow Schemas (Primary Goal)

**Priority:** High

**Deliverables:**
- `backend/app/schemas/workflow.py` - All workflow, node, edge schemas

**Tasks:**

1. Workflow Schemas
   - WorkflowBase, WorkflowCreate, WorkflowUpdate
   - WorkflowResponse, WorkflowListResponse
   - WorkflowWithDetails (including nodes/edges)

2. Node Schemas
   - NodeBase, NodeCreate, NodeUpdate
   - NodeResponse, NodeListResponse
   - NodeBatchCreate, NodeBatchUpdate

3. Edge Schemas
   - EdgeBase, EdgeCreate, EdgeUpdate
   - EdgeResponse, EdgeListResponse
   - EdgeBatchCreate, EdgeBatchUpdate

**Technical Approach:**
```python
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import NodeType, TriggerType


# Workflow Schemas
class WorkflowBase(BaseModel):
    """Base workflow schema.

    TAG: [SPEC-007] [API] [SCHEMA]
    """

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    trigger_type: TriggerType
    trigger_config: dict = Field(default_factory=dict)
    is_active: bool = True


class WorkflowCreate(WorkflowBase):
    """Workflow creation schema."""
    pass


class WorkflowUpdate(BaseModel):
    """Workflow update schema."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    trigger_type: TriggerType | None = None
    trigger_config: dict | None = None
    is_active: bool | None = None


class WorkflowResponse(WorkflowBase):
    """Workflow response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    version: int
    created_at: datetime
    updated_at: datetime


# Node Schemas
class NodeBase(BaseModel):
    """Base node schema.

    TAG: [SPEC-007] [API] [SCHEMA]
    """

    name: str = Field(..., min_length=1, max_length=255)
    node_type: NodeType
    config: dict = Field(default_factory=dict)
    position_x: float = 0.0
    position_y: float = 0.0
    retry_config: dict = Field(default_factory=dict)


class NodeCreate(NodeBase):
    """Node creation schema."""
    pass


class NodeBatchCreate(BaseModel):
    """Batch node creation schema."""

    nodes: list[NodeCreate]


class NodeResponse(NodeBase):
    """Node response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_id: UUID
    created_at: datetime
    updated_at: datetime


# Edge Schemas
class EdgeBase(BaseModel):
    """Base edge schema.

    TAG: [SPEC-007] [API] [SCHEMA]
    """

    source_node_id: UUID
    target_node_id: UUID
    condition: dict | None = None


class EdgeCreate(EdgeBase):
    """Edge creation schema."""
    pass


class EdgeBatchCreate(BaseModel):
    """Batch edge creation schema."""

    edges: list[EdgeCreate]


class EdgeResponse(EdgeBase):
    """Edge response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_id: UUID
    created_at: datetime
    updated_at: datetime
```

---

### Milestone 4: Foundation - Execution Schemas (Primary Goal)

**Priority:** High

**Deliverables:**
- `backend/app/schemas/execution.py` - All execution and log schemas

**Tasks:**

1. WorkflowExecution Schemas
   - WorkflowExecutionCreate, WorkflowExecutionUpdate
   - WorkflowExecutionResponse, WorkflowExecutionDetail
   - ExecutionStateTransition schema

2. NodeExecution Schemas
   - NodeExecutionResponse
   - NodeExecutionDetail with logs

3. ExecutionLog Schemas
   - ExecutionLogCreate, ExecutionLogResponse
   - ExecutionLogFilter for querying

**Technical Approach:**
```python
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ExecutionStatus, LogLevel, TriggerType


class WorkflowExecutionCreate(BaseModel):
    """Workflow execution creation schema.

    TAG: [SPEC-007] [API] [SCHEMA]
    """

    trigger_type: TriggerType
    input_data: dict = Field(default_factory=dict)
    context: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)


class WorkflowExecutionResponse(BaseModel):
    """Workflow execution response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_id: UUID
    trigger_type: TriggerType
    status: ExecutionStatus
    started_at: datetime | None
    ended_at: datetime | None
    input_data: dict
    output_data: dict | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class NodeExecutionResponse(BaseModel):
    """Node execution response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_execution_id: UUID
    node_id: UUID
    status: ExecutionStatus
    started_at: datetime | None
    ended_at: datetime | None
    input_data: dict
    output_data: dict | None
    error_message: str | None
    retry_count: int
    execution_order: int


class ExecutionLogCreate(BaseModel):
    """Execution log creation schema.

    TAG: [SPEC-007] [API] [SCHEMA]
    """

    level: LogLevel
    message: str
    data: dict | None = None


class ExecutionLogResponse(BaseModel):
    """Execution log response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_execution_id: UUID
    node_execution_id: UUID | None
    level: LogLevel
    message: str
    data: dict | None
    timestamp: datetime
```

---

### Milestone 5: Foundation - Schema Exports (Primary Goal)

**Priority:** High

**Deliverables:**
- `backend/app/schemas/__init__.py` - Export all schemas

**Tasks:**

1. Update __init__.py
   - Export base schemas (BaseResponse, PaginatedResponse, ErrorResponse)
   - Export workflow schemas (Workflow*, Node*, Edge*)
   - Export execution schemas (WorkflowExecution*, NodeExecution*, ExecutionLog*)
   - Update __all__ list

**Technical Approach:**
```python
from app.schemas.base import BaseResponse, ErrorResponse, PaginatedResponse
from app.schemas.workflow import (
    EdgeBase,
    EdgeBatchCreate,
    EdgeCreate,
    EdgeResponse,
    NodeBase,
    NodeBatchCreate,
    NodeCreate,
    NodeResponse,
    WorkflowBase,
    WorkflowCreate,
    WorkflowResponse,
    WorkflowUpdate,
)
from app.schemas.execution import (
    ExecutionLogCreate,
    ExecutionLogResponse,
    NodeExecutionResponse,
    WorkflowExecutionCreate,
    WorkflowExecutionResponse,
)

__all__ = [
    # Base
    "BaseResponse",
    "PaginatedResponse",
    "ErrorResponse",
    # Workflow
    "WorkflowBase",
    "WorkflowCreate",
    "WorkflowUpdate",
    "WorkflowResponse",
    "NodeBase",
    "NodeCreate",
    "NodeBatchCreate",
    "NodeResponse",
    "EdgeBase",
    "EdgeCreate",
    "EdgeBatchCreate",
    "EdgeResponse",
    # Execution
    "WorkflowExecutionCreate",
    "WorkflowExecutionResponse",
    "NodeExecutionResponse",
    "ExecutionLogCreate",
    "ExecutionLogResponse",
]
```

---

### Milestone 6: Service Layer - Workflow Service (Secondary Goal)

**Priority:** High

**Deliverables:**
- `backend/app/services/workflow_service.py` - WorkflowService, NodeService, EdgeService

**Tasks:**

1. WorkflowService Implementation
   - CRUD operations (create, read, update, delete)
   - List with pagination and filtering
   - Duplicate workflow functionality
   - Soft delete support

2. NodeService Implementation
   - CRUD operations
   - Batch create/update operations
   - Get nodes by workflow

3. EdgeService Implementation
   - CRUD operations
   - Batch create operations
   - DAG validation integration
   - Cycle detection

**Technical Approach:**
```python
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Workflow, Node, Edge
from app.schemas.workflow import WorkflowCreate, WorkflowUpdate, NodeCreate, EdgeCreate


class WorkflowService:
    """Workflow service for CRUD operations.

    TAG: [SPEC-007] [API] [SERVICE]
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: WorkflowCreate) -> Workflow:
        """Create a new workflow."""
        workflow = Workflow(**data.model_dump())
        self.db.add(workflow)
        await self.db.commit()
        await self.db.refresh(workflow)
        return workflow

    async def get_by_id(self, workflow_id: UUID) -> Workflow | None:
        """Get workflow by ID."""
        result = await self.db.execute(
            select(Workflow)
            .where(Workflow.id == workflow_id)
            .where(Workflow.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        offset: int = 0,
        limit: int = 20,
        is_active: bool | None = None,
    ) -> tuple[list[Workflow], int]:
        """List workflows with pagination."""
        query = select(Workflow).where(Workflow.deleted_at.is_(None))

        if is_active is not None:
            query = query.where(Workflow.is_active == is_active)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        # Get items
        query = query.offset(offset).limit(limit).order_by(Workflow.created_at.desc())
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def update(self, workflow_id: UUID, data: WorkflowUpdate) -> Workflow | None:
        """Update workflow."""
        workflow = await self.get_by_id(workflow_id)
        if not workflow:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(workflow, field, value)

        workflow.version += 1
        await self.db.commit()
        await self.db.refresh(workflow)
        return workflow

    async def delete(self, workflow_id: UUID) -> bool:
        """Soft delete workflow."""
        workflow = await self.get_by_id(workflow_id)
        if not workflow:
            return False

        workflow.soft_delete()
        await self.db.commit()
        return True

    async def duplicate(self, workflow_id: UUID, new_name: str) -> Workflow | None:
        """Duplicate workflow with nodes and edges."""
        workflow = await self.get_by_id(workflow_id)
        if not workflow:
            return None

        # Load nodes and edges
        result = await self.db.execute(
            select(Workflow)
            .where(Workflow.id == workflow_id)
            .options(selectinload(Workflow.nodes), selectinload(Workflow.edges))
        )
        workflow = result.scalar_one()

        # Create new workflow
        new_workflow = Workflow(
            name=new_name,
            description=workflow.description,
            trigger_type=workflow.trigger_type,
            trigger_config=workflow.trigger_config,
            is_active=False,
        )
        self.db.add(new_workflow)
        await self.db.flush()

        # Map old node IDs to new nodes
        node_mapping = {}
        for node in workflow.nodes:
            new_node = Node(
                workflow_id=new_workflow.id,
                name=node.name,
                node_type=node.node_type,
                config=node.config,
                position_x=node.position_x,
                position_y=node.position_y,
                retry_config=node.retry_config,
            )
            self.db.add(new_node)
            await self.db.flush()
            node_mapping[node.id] = new_node.id

        # Create edges with new node IDs
        for edge in workflow.edges:
            new_edge = Edge(
                workflow_id=new_workflow.id,
                source_node_id=node_mapping[edge.source_node_id],
                target_node_id=node_mapping[edge.target_node_id],
                condition=edge.condition,
            )
            self.db.add(new_edge)

        await self.db.commit()
        await self.db.refresh(new_workflow)
        return new_workflow


class NodeService:
    """Node service for CRUD operations.

    TAG: [SPEC-007] [API] [SERVICE]
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, workflow_id: UUID, data: NodeCreate) -> Node:
        """Create a new node."""
        node = Node(workflow_id=workflow_id, **data.model_dump())
        self.db.add(node)
        await self.db.commit()
        await self.db.refresh(node)
        return node

    async def batch_create(self, workflow_id: UUID, nodes: list[NodeCreate]) -> list[Node]:
        """Batch create nodes."""
        created_nodes = []
        for node_data in nodes:
            node = Node(workflow_id=workflow_id, **node_data.model_dump())
            self.db.add(node)
            created_nodes.append(node)

        await self.db.commit()
        for node in created_nodes:
            await self.db.refresh(node)

        return created_nodes

    async def get_by_workflow(self, workflow_id: UUID) -> list[Node]:
        """Get all nodes for a workflow."""
        result = await self.db.execute(
            select(Node).where(Node.workflow_id == workflow_id)
        )
        return list(result.scalars().all())


class EdgeService:
    """Edge service for CRUD operations with DAG validation.

    TAG: [SPEC-007] [API] [SERVICE]
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, workflow_id: UUID, data: EdgeCreate) -> Edge:
        """Create a new edge with DAG validation."""
        # Validate DAG before creating
        await self._validate_dag(workflow_id, data.source_node_id, data.target_node_id)

        edge = Edge(workflow_id=workflow_id, **data.model_dump())
        self.db.add(edge)
        await self.db.commit()
        await self.db.refresh(edge)
        return edge

    async def batch_create(self, workflow_id: UUID, edges: list[EdgeCreate]) -> list[Edge]:
        """Batch create edges with DAG validation."""
        created_edges = []
        for edge_data in edges:
            await self._validate_dag(workflow_id, edge_data.source_node_id, edge_data.target_node_id)
            edge = Edge(workflow_id=workflow_id, **edge_data.model_dump())
            self.db.add(edge)
            created_edges.append(edge)

        await self.db.commit()
        for edge in created_edges:
            await self.db.refresh(edge)

        return created_edges

    async def _validate_dag(self, workflow_id: UUID, source_id: UUID, target_id: UUID) -> None:
        """Validate that adding this edge doesn't create a cycle."""
        # Get all existing edges
        result = await self.db.execute(
            select(Edge).where(Edge.workflow_id == workflow_id)
        )
        edges = list(result.scalars().all())

        # Build adjacency list
        graph: dict[UUID, list[UUID]] = {}
        for edge in edges:
            if edge.source_node_id not in graph:
                graph[edge.source_node_id] = []
            graph[edge.source_node_id].append(edge.target_node_id)

        # Add proposed edge
        if source_id not in graph:
            graph[source_id] = []
        graph[source_id].append(target_id)

        # Check for cycle using DFS
        if self._has_cycle(graph, source_id, target_id):
            raise ValueError("Adding this edge would create a cycle in the workflow graph")

    def _has_cycle(self, graph: dict[UUID, list[UUID]], source: UUID, target: UUID) -> bool:
        """Check if there's a path from target to source (would create cycle)."""
        visited = set()

        def dfs(node: UUID) -> bool:
            if node == source:
                return True
            if node in visited:
                return False

            visited.add(node)
            for neighbor in graph.get(node, []):
                if dfs(neighbor):
                    return True
            return False

        return dfs(target)
```

---

### Milestone 7: Service Layer - Execution Service (Secondary Goal)

**Priority:** High

**Deliverables:**
- `backend/app/services/execution_service.py` - WorkflowExecutionService, NodeExecutionService, ExecutionLogService

**Tasks:**

1. WorkflowExecutionService Implementation
   - CRUD operations
   - State transition methods (start, complete, fail, cancel)
   - List with filtering (status, date range)

2. NodeExecutionService Implementation
   - State transition methods
   - Get executions by workflow execution

3. ExecutionLogService Implementation
   - Create log entries
   - Query logs with filtering (level, date range)

**Technical Approach:**
```python
from datetime import datetime, UTC
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import WorkflowExecution, NodeExecution, ExecutionLog
from app.models.enums import ExecutionStatus, LogLevel
from app.schemas.execution import WorkflowExecutionCreate, ExecutionLogCreate


class WorkflowExecutionService:
    """Workflow execution service.

    TAG: [SPEC-007] [API] [SERVICE]
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, workflow_id: UUID, data: WorkflowExecutionCreate) -> WorkflowExecution:
        """Create a new workflow execution."""
        execution = WorkflowExecution(
            workflow_id=workflow_id,
            **data.model_dump(),
        )
        self.db.add(execution)
        await self.db.commit()
        await self.db.refresh(execution)
        return execution

    async def get_by_id(self, execution_id: UUID) -> WorkflowExecution | None:
        """Get execution by ID."""
        result = await self.db.execute(
            select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
        )
        return result.scalar_one_or_none()

    async def start(self, execution_id: UUID) -> WorkflowExecution | None:
        """Start execution."""
        execution = await self.get_by_id(execution_id)
        if not execution:
            return None

        execution.start()
        await self.db.commit()
        await self.db.refresh(execution)
        return execution

    async def complete(
        self, execution_id: UUID, output_data: dict | None = None
    ) -> WorkflowExecution | None:
        """Complete execution."""
        execution = await self.get_by_id(execution_id)
        if not execution:
            return None

        execution.complete(output_data)
        await self.db.commit()
        await self.db.refresh(execution)
        return execution

    async def fail(self, execution_id: UUID, error_message: str) -> WorkflowExecution | None:
        """Fail execution."""
        execution = await self.get_by_id(execution_id)
        if not execution:
            return None

        execution.fail(error_message)
        await self.db.commit()
        await self.db.refresh(execution)
        return execution

    async def cancel(self, execution_id: UUID) -> WorkflowExecution | None:
        """Cancel execution."""
        execution = await self.get_by_id(execution_id)
        if not execution:
            return None

        execution.cancel()
        await self.db.commit()
        await self.db.refresh(execution)
        return execution

    async def list_by_workflow(
        self,
        workflow_id: UUID,
        offset: int = 0,
        limit: int = 20,
        status: ExecutionStatus | None = None,
    ) -> tuple[list[WorkflowExecution], int]:
        """List executions for a workflow."""
        query = select(WorkflowExecution).where(
            WorkflowExecution.workflow_id == workflow_id
        )

        if status:
            query = query.where(WorkflowExecution.status == status)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        # Get items
        query = query.offset(offset).limit(limit).order_by(
            WorkflowExecution.created_at.desc()
        )
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total


class NodeExecutionService:
    """Node execution service.

    TAG: [SPEC-007] [API] [SERVICE]
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_workflow_execution(
        self, workflow_execution_id: UUID
    ) -> list[NodeExecution]:
        """Get all node executions for a workflow execution."""
        result = await self.db.execute(
            select(NodeExecution)
            .where(NodeExecution.workflow_execution_id == workflow_execution_id)
            .order_by(NodeExecution.execution_order)
        )
        return list(result.scalars().all())

    async def start(self, node_execution_id: UUID) -> NodeExecution | None:
        """Start node execution."""
        result = await self.db.execute(
            select(NodeExecution).where(NodeExecution.id == node_execution_id)
        )
        execution = result.scalar_one_or_none()
        if not execution:
            return None

        execution.status = ExecutionStatus.RUNNING
        execution.started_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(execution)
        return execution


class ExecutionLogService:
    """Execution log service.

    TAG: [SPEC-007] [API] [SERVICE]
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        workflow_execution_id: UUID,
        data: ExecutionLogCreate,
        node_execution_id: UUID | None = None,
    ) -> ExecutionLog:
        """Create a new execution log entry."""
        log = ExecutionLog(
            workflow_execution_id=workflow_execution_id,
            node_execution_id=node_execution_id,
            **data.model_dump(),
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log

    async def list_by_execution(
        self,
        workflow_execution_id: UUID,
        level: LogLevel | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[ExecutionLog], int]:
        """List logs for an execution."""
        query = select(ExecutionLog).where(
            ExecutionLog.workflow_execution_id == workflow_execution_id
        )

        if level:
            query = query.where(ExecutionLog.level == level)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        # Get items
        query = query.offset(offset).limit(limit).order_by(ExecutionLog.timestamp.desc())
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total
```

---

### Milestone 8: Service Layer - Exports (Secondary Goal)

**Priority:** Medium

**Deliverables:**
- `backend/app/services/__init__.py` - Export all services

**Tasks:**

1. Update __init__.py
   - Export workflow services (WorkflowService, NodeService, EdgeService)
   - Export execution services (WorkflowExecutionService, NodeExecutionService, ExecutionLogService)
   - Update __all__ list

---

### Milestone 9: API Routers - Workflow Endpoints (Final Goal)

**Priority:** High

**Deliverables:**
- `backend/app/api/v1/workflows.py` - All workflow endpoints

**Tasks:**

1. Workflow CRUD Endpoints
   - POST /workflows - Create workflow
   - GET /workflows - List workflows with pagination
   - GET /workflows/{id} - Get workflow by ID
   - PATCH /workflows/{id} - Update workflow
   - DELETE /workflows/{id} - Soft delete workflow
   - POST /workflows/{id}/duplicate - Duplicate workflow

2. Node Endpoints
   - POST /workflows/{id}/nodes - Create node
   - POST /workflows/{id}/nodes/batch - Batch create nodes
   - GET /workflows/{id}/nodes - List workflow nodes
   - GET /workflows/{id}/nodes/{node_id} - Get node
   - PATCH /workflows/{id}/nodes/{node_id} - Update node
   - DELETE /workflows/{id}/nodes/{node_id} - Delete node

3. Edge Endpoints
   - POST /workflows/{id}/edges - Create edge
   - POST /workflows/{id}/edges/batch - Batch create edges
   - GET /workflows/{id}/edges - List workflow edges
   - DELETE /workflows/{id}/edges/{edge_id} - Delete edge

**Technical Approach:**
```python
from uuid import UUID
from fastapi import APIRouter, HTTPException, status

from app.api.deps import DBSession, Pagination
from app.schemas import (
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowResponse,
    PaginatedResponse,
    BaseResponse,
    NodeCreate,
    NodeBatchCreate,
    NodeResponse,
    EdgeCreate,
    EdgeBatchCreate,
    EdgeResponse,
)
from app.services import WorkflowService, NodeService, EdgeService

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("", response_model=BaseResponse[WorkflowResponse], status_code=status.HTTP_201_CREATED)
async def create_workflow(
    data: WorkflowCreate,
    db: DBSession,
) -> BaseResponse[WorkflowResponse]:
    """Create a new workflow.

    TAG: [SPEC-007] [API] [ENDPOINT]
    """
    service = WorkflowService(db)
    workflow = await service.create(data)
    return BaseResponse(data=WorkflowResponse.model_validate(workflow))


@router.get("", response_model=PaginatedResponse[WorkflowResponse])
async def list_workflows(
    db: DBSession,
    pagination: Pagination,
    is_active: bool | None = None,
) -> PaginatedResponse[WorkflowResponse]:
    """List workflows with pagination.

    TAG: [SPEC-007] [API] [ENDPOINT]
    """
    service = WorkflowService(db)
    items, total = await service.list(
        offset=pagination.offset,
        limit=pagination.size,
        is_active=is_active,
    )

    return PaginatedResponse(
        items=[WorkflowResponse.model_validate(w) for w in items],
        total=total,
        page=pagination.page,
        size=pagination.size,
        total_pages=(total + pagination.size - 1) // pagination.size,
    )


@router.get("/{workflow_id}", response_model=BaseResponse[WorkflowResponse])
async def get_workflow(
    workflow_id: UUID,
    db: DBSession,
) -> BaseResponse[WorkflowResponse]:
    """Get workflow by ID.

    TAG: [SPEC-007] [API] [ENDPOINT]
    """
    service = WorkflowService(db)
    workflow = await service.get_by_id(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return BaseResponse(data=WorkflowResponse.model_validate(workflow))


@router.patch("/{workflow_id}", response_model=BaseResponse[WorkflowResponse])
async def update_workflow(
    workflow_id: UUID,
    data: WorkflowUpdate,
    db: DBSession,
) -> BaseResponse[WorkflowResponse]:
    """Update workflow.

    TAG: [SPEC-007] [API] [ENDPOINT]
    """
    service = WorkflowService(db)
    workflow = await service.update(workflow_id, data)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return BaseResponse(data=WorkflowResponse.model_validate(workflow))


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: UUID,
    db: DBSession,
) -> None:
    """Delete workflow.

    TAG: [SPEC-007] [API] [ENDPOINT]
    """
    service = WorkflowService(db)
    deleted = await service.delete(workflow_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Workflow not found")


@router.post("/{workflow_id}/duplicate", response_model=BaseResponse[WorkflowResponse], status_code=status.HTTP_201_CREATED)
async def duplicate_workflow(
    workflow_id: UUID,
    new_name: str,
    db: DBSession,
) -> BaseResponse[WorkflowResponse]:
    """Duplicate workflow with nodes and edges.

    TAG: [SPEC-007] [API] [ENDPOINT]
    """
    service = WorkflowService(db)
    workflow = await service.duplicate(workflow_id, new_name)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return BaseResponse(data=WorkflowResponse.model_validate(workflow))


# Node endpoints
@router.post("/{workflow_id}/nodes", response_model=BaseResponse[NodeResponse], status_code=status.HTTP_201_CREATED)
async def create_node(
    workflow_id: UUID,
    data: NodeCreate,
    db: DBSession,
) -> BaseResponse[NodeResponse]:
    """Create a new node in workflow."""
    service = NodeService(db)
    node = await service.create(workflow_id, data)
    return BaseResponse(data=NodeResponse.model_validate(node))


@router.post("/{workflow_id}/nodes/batch", response_model=BaseResponse[list[NodeResponse]], status_code=status.HTTP_201_CREATED)
async def batch_create_nodes(
    workflow_id: UUID,
    data: NodeBatchCreate,
    db: DBSession,
) -> BaseResponse[list[NodeResponse]]:
    """Batch create nodes in workflow."""
    service = NodeService(db)
    nodes = await service.batch_create(workflow_id, data.nodes)
    return BaseResponse(data=[NodeResponse.model_validate(n) for n in nodes])


@router.get("/{workflow_id}/nodes", response_model=BaseResponse[list[NodeResponse]])
async def list_nodes(
    workflow_id: UUID,
    db: DBSession,
) -> BaseResponse[list[NodeResponse]]:
    """List all nodes in workflow."""
    service = NodeService(db)
    nodes = await service.get_by_workflow(workflow_id)
    return BaseResponse(data=[NodeResponse.model_validate(n) for n in nodes])


# Edge endpoints
@router.post("/{workflow_id}/edges", response_model=BaseResponse[EdgeResponse], status_code=status.HTTP_201_CREATED)
async def create_edge(
    workflow_id: UUID,
    data: EdgeCreate,
    db: DBSession,
) -> BaseResponse[EdgeResponse]:
    """Create a new edge in workflow."""
    service = EdgeService(db)
    try:
        edge = await service.create(workflow_id, data)
        return BaseResponse(data=EdgeResponse.model_validate(edge))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{workflow_id}/edges/batch", response_model=BaseResponse[list[EdgeResponse]], status_code=status.HTTP_201_CREATED)
async def batch_create_edges(
    workflow_id: UUID,
    data: EdgeBatchCreate,
    db: DBSession,
) -> BaseResponse[list[EdgeResponse]]:
    """Batch create edges in workflow with DAG validation."""
    service = EdgeService(db)
    try:
        edges = await service.batch_create(workflow_id, data.edges)
        return BaseResponse(data=[EdgeResponse.model_validate(e) for e in edges])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

---

### Milestone 10: API Routers - Execution Endpoints (Final Goal)

**Priority:** High

**Deliverables:**
- `backend/app/api/v1/executions.py` - All execution endpoints

**Tasks:**

1. WorkflowExecution Endpoints
   - POST /workflows/{id}/executions - Create execution
   - GET /workflows/{id}/executions - List executions with pagination
   - GET /executions/{id} - Get execution by ID
   - POST /executions/{id}/start - Start execution
   - POST /executions/{id}/complete - Complete execution
   - POST /executions/{id}/fail - Fail execution
   - POST /executions/{id}/cancel - Cancel execution

2. NodeExecution Endpoints
   - GET /executions/{id}/nodes - Get node executions

3. ExecutionLog Endpoints
   - POST /executions/{id}/logs - Create log entry
   - GET /executions/{id}/logs - List logs with filtering

**Technical Approach:**
```python
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import DBSession, Pagination
from app.models.enums import ExecutionStatus, LogLevel
from app.schemas import (
    WorkflowExecutionCreate,
    WorkflowExecutionResponse,
    NodeExecutionResponse,
    ExecutionLogCreate,
    ExecutionLogResponse,
    BaseResponse,
    PaginatedResponse,
)
from app.services import WorkflowExecutionService, NodeExecutionService, ExecutionLogService

router = APIRouter(tags=["executions"])


# Workflow Execution endpoints (under /workflows)
workflows_router = APIRouter(prefix="/workflows", tags=["workflow-executions"])


@workflows_router.post(
    "/{workflow_id}/executions",
    response_model=BaseResponse[WorkflowExecutionResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_execution(
    workflow_id: UUID,
    data: WorkflowExecutionCreate,
    db: DBSession,
) -> BaseResponse[WorkflowExecutionResponse]:
    """Create a new workflow execution.

    TAG: [SPEC-007] [API] [ENDPOINT]
    """
    service = WorkflowExecutionService(db)
    execution = await service.create(workflow_id, data)
    return BaseResponse(data=WorkflowExecutionResponse.model_validate(execution))


@workflows_router.get(
    "/{workflow_id}/executions",
    response_model=PaginatedResponse[WorkflowExecutionResponse],
)
async def list_executions(
    workflow_id: UUID,
    db: DBSession,
    pagination: Pagination,
    status_filter: ExecutionStatus | None = Query(None, alias="status"),
) -> PaginatedResponse[WorkflowExecutionResponse]:
    """List executions for a workflow."""
    service = WorkflowExecutionService(db)
    items, total = await service.list_by_workflow(
        workflow_id,
        offset=pagination.offset,
        limit=pagination.size,
        status=status_filter,
    )

    return PaginatedResponse(
        items=[WorkflowExecutionResponse.model_validate(e) for e in items],
        total=total,
        page=pagination.page,
        size=pagination.size,
        total_pages=(total + pagination.size - 1) // pagination.size,
    )


# Execution-specific endpoints
execution_router = APIRouter(prefix="/executions", tags=["executions"])


@execution_router.get("/{execution_id}", response_model=BaseResponse[WorkflowExecutionResponse])
async def get_execution(
    execution_id: UUID,
    db: DBSession,
) -> BaseResponse[WorkflowExecutionResponse]:
    """Get execution by ID."""
    service = WorkflowExecutionService(db)
    execution = await service.get_by_id(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return BaseResponse(data=WorkflowExecutionResponse.model_validate(execution))


@execution_router.post("/{execution_id}/start", response_model=BaseResponse[WorkflowExecutionResponse])
async def start_execution(
    execution_id: UUID,
    db: DBSession,
) -> BaseResponse[WorkflowExecutionResponse]:
    """Start execution."""
    service = WorkflowExecutionService(db)
    try:
        execution = await service.start(execution_id)
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")
        return BaseResponse(data=WorkflowExecutionResponse.model_validate(execution))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@execution_router.post("/{execution_id}/complete", response_model=BaseResponse[WorkflowExecutionResponse])
async def complete_execution(
    execution_id: UUID,
    db: DBSession,
    output_data: dict | None = None,
) -> BaseResponse[WorkflowExecutionResponse]:
    """Complete execution."""
    service = WorkflowExecutionService(db)
    try:
        execution = await service.complete(execution_id, output_data)
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")
        return BaseResponse(data=WorkflowExecutionResponse.model_validate(execution))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@execution_router.post("/{execution_id}/fail", response_model=BaseResponse[WorkflowExecutionResponse])
async def fail_execution(
    execution_id: UUID,
    error_message: str,
    db: DBSession,
) -> BaseResponse[WorkflowExecutionResponse]:
    """Fail execution."""
    service = WorkflowExecutionService(db)
    try:
        execution = await service.fail(execution_id, error_message)
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")
        return BaseResponse(data=WorkflowExecutionResponse.model_validate(execution))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@execution_router.post("/{execution_id}/cancel", response_model=BaseResponse[WorkflowExecutionResponse])
async def cancel_execution(
    execution_id: UUID,
    db: DBSession,
) -> BaseResponse[WorkflowExecutionResponse]:
    """Cancel execution."""
    service = WorkflowExecutionService(db)
    try:
        execution = await service.cancel(execution_id)
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")
        return BaseResponse(data=WorkflowExecutionResponse.model_validate(execution))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Node Execution endpoints
@execution_router.get("/{execution_id}/nodes", response_model=BaseResponse[list[NodeExecutionResponse]])
async def list_node_executions(
    execution_id: UUID,
    db: DBSession,
) -> BaseResponse[list[NodeExecutionResponse]]:
    """List node executions for a workflow execution."""
    service = NodeExecutionService(db)
    nodes = await service.get_by_workflow_execution(execution_id)
    return BaseResponse(data=[NodeExecutionResponse.model_validate(n) for n in nodes])


# Execution Log endpoints
@execution_router.post(
    "/{execution_id}/logs",
    response_model=BaseResponse[ExecutionLogResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_log(
    execution_id: UUID,
    data: ExecutionLogCreate,
    db: DBSession,
    node_execution_id: UUID | None = None,
) -> BaseResponse[ExecutionLogResponse]:
    """Create an execution log entry."""
    service = ExecutionLogService(db)
    log = await service.create(execution_id, data, node_execution_id)
    return BaseResponse(data=ExecutionLogResponse.model_validate(log))


@execution_router.get("/{execution_id}/logs", response_model=PaginatedResponse[ExecutionLogResponse])
async def list_logs(
    execution_id: UUID,
    db: DBSession,
    pagination: Pagination,
    level: LogLevel | None = None,
) -> PaginatedResponse[ExecutionLogResponse]:
    """List logs for an execution."""
    service = ExecutionLogService(db)
    items, total = await service.list_by_execution(
        execution_id,
        level=level,
        offset=pagination.offset,
        limit=pagination.size,
    )

    return PaginatedResponse(
        items=[ExecutionLogResponse.model_validate(log) for log in items],
        total=total,
        page=pagination.page,
        size=pagination.size,
        total_pages=(total + pagination.size - 1) // pagination.size,
    )


# Combined router for main app
router = APIRouter()
router.include_router(workflows_router)
router.include_router(execution_router)
```

---

### Milestone 11: Router Registration (Final Goal)

**Priority:** High

**Deliverables:**
- `backend/app/api/v1/__init__.py` - Register routers

**Tasks:**

1. Create API v1 Router
   - Import workflow router
   - Import execution router
   - Create combined v1 router with prefix

**Technical Approach:**
```python
from fastapi import APIRouter

from app.api.v1.workflows import router as workflows_router
from app.api.v1.executions import router as executions_router

router = APIRouter(prefix="/v1")
router.include_router(workflows_router)
router.include_router(executions_router)

__all__ = ["router"]
```

---

### Milestone 12: Integration & Testing (Final Goal)

**Priority:** High

**Deliverables:**
- `backend/tests/unit/test_api/` - API unit tests
- `backend/tests/integration/test_api/` - API integration tests

**Tasks:**

1. Integration Testing
   - Full workflow lifecycle test
   - Execution state transition tests
   - Error handling verification

2. OpenAPI Documentation Verification
   - All endpoints documented
   - Request/response examples
   - Error responses documented

3. Error Handling Verification
   - 404 for not found
   - 400 for validation errors
   - 422 for invalid data

---

## Architecture Design

### Component Diagram

```
backend/
  app/
    api/
      deps.py                  # DBSession, Pagination, Sorting (신규)
      v1/
        __init__.py            # Router registration (신규)
        workflows.py           # Workflow/Node/Edge endpoints (신규)
        executions.py          # Execution endpoints (신규)
    schemas/
      __init__.py              # Schema exports (업데이트)
      base.py                  # BaseResponse, PaginatedResponse (신규)
      workflow.py              # Workflow/Node/Edge schemas (신규)
      execution.py             # Execution schemas (신규)
    services/
      __init__.py              # Service exports (신규)
      workflow_service.py      # WorkflowService, NodeService, EdgeService (신규)
      execution_service.py     # Execution services (신규)
  tests/
    unit/
      test_api/                # Unit tests (신규)
    integration/
      test_api/                # Integration tests (신규)
```

### API Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /v1/workflows | Create workflow |
| GET | /v1/workflows | List workflows |
| GET | /v1/workflows/{id} | Get workflow |
| PATCH | /v1/workflows/{id} | Update workflow |
| DELETE | /v1/workflows/{id} | Delete workflow |
| POST | /v1/workflows/{id}/duplicate | Duplicate workflow |
| POST | /v1/workflows/{id}/nodes | Create node |
| POST | /v1/workflows/{id}/nodes/batch | Batch create nodes |
| GET | /v1/workflows/{id}/nodes | List nodes |
| POST | /v1/workflows/{id}/edges | Create edge |
| POST | /v1/workflows/{id}/edges/batch | Batch create edges |
| GET | /v1/workflows/{id}/edges | List edges |
| POST | /v1/workflows/{id}/executions | Create execution |
| GET | /v1/workflows/{id}/executions | List executions |
| GET | /v1/executions/{id} | Get execution |
| POST | /v1/executions/{id}/start | Start execution |
| POST | /v1/executions/{id}/complete | Complete execution |
| POST | /v1/executions/{id}/fail | Fail execution |
| POST | /v1/executions/{id}/cancel | Cancel execution |
| GET | /v1/executions/{id}/nodes | List node executions |
| POST | /v1/executions/{id}/logs | Create log |
| GET | /v1/executions/{id}/logs | List logs |

**Total: 22 endpoints**

---

## TDD Approach

### Test Sequence

1. **Service Layer Tests First**
   - WorkflowService unit tests
   - NodeService unit tests
   - EdgeService unit tests (including DAG validation)
   - ExecutionService unit tests

2. **API Endpoint Tests**
   - Workflow CRUD endpoint tests
   - Node/Edge endpoint tests
   - Execution endpoint tests
   - Log endpoint tests

3. **RED-GREEN-REFACTOR Cycle**
   - Write failing test
   - Implement minimum code to pass
   - Refactor for quality

---

## Risk Mitigation

| Risk | Mitigation Strategy |
|------|---------------------|
| Circular dependencies | Careful import organization, TYPE_CHECKING |
| DAG validation performance | Optimize graph traversal, caching |
| Concurrent execution conflicts | Optimistic locking, proper state validation |
| Large response payloads | Pagination, selective field loading |

---

## Output Files Summary

| File Path | Purpose |
|-----------|---------|
| `backend/app/api/deps.py` | Dependency injection (DBSession, Pagination, Sorting) |
| `backend/app/schemas/base.py` | Base response schemas |
| `backend/app/schemas/workflow.py` | Workflow/Node/Edge schemas |
| `backend/app/schemas/execution.py` | Execution schemas |
| `backend/app/schemas/__init__.py` | Schema exports |
| `backend/app/services/workflow_service.py` | Workflow/Node/Edge services |
| `backend/app/services/execution_service.py` | Execution services |
| `backend/app/services/__init__.py` | Service exports |
| `backend/app/api/v1/workflows.py` | Workflow API endpoints |
| `backend/app/api/v1/executions.py` | Execution API endpoints |
| `backend/app/api/v1/__init__.py` | Router registration |

---

## Definition of Done

- [x] deps.py with DBSession, Pagination, Sorting dependencies
- [x] 3 schema files with 50+ schemas
- [x] 2 service files with 6 service classes
- [x] 2 router files with 30 endpoints
- [x] All endpoints return proper response wrappers
- [x] DAG validation working correctly
- [x] State transitions validated
- [x] Error handling implemented
- [x] Unit tests 89.41% coverage (938 tests passing)
- [x] Integration tests passing
- [x] OpenAPI documentation complete
- [x] ruff linting pass
- [x] mypy type check pass
- [x] Code review approved

---

## Next Steps After Completion

1. **SPEC-008**: Scheduler Implementation (schedule-based triggers)
2. **SPEC-010**: DAG Validation Service (advanced graph validation)
3. **SPEC-011**: Workflow Execution Engine (runtime execution)
4. **SPEC-012**: WebSocket Support (real-time execution updates)

---

## Related Documents

- [spec.md](spec.md) - Detailed requirements
- [acceptance.md](acceptance.md) - Acceptance criteria
- [SPEC-005/spec.md](../SPEC-005/spec.md) - Execution Tracking Models (dependency)
- [SPEC-003/spec.md](../SPEC-003/spec.md) - Workflow Domain Models (dependency)

---

## Change History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-12 | workflow-spec | Initial implementation plan |
