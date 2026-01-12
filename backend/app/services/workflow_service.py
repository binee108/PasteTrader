"""Workflow, Node, and Edge service layer.

TAG: [SPEC-007] [API] [SERVICE] [WORKFLOW] [NODE] [EDGE]
REQ: REQ-001 - WorkflowService CRUD Operations
REQ: REQ-002 - NodeService CRUD Operations
REQ: REQ-003 - EdgeService CRUD Operations with DAG Validation
REQ: REQ-004 - Batch Operations Support
REQ: REQ-005 - DAG Cycle Detection

This module provides service layer abstractions for workflow management.
Services handle business logic, validation, and database operations.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.models.workflow import Edge, Node, Workflow

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

# =============================================================================
# Exceptions
# =============================================================================


class WorkflowServiceError(Exception):
    """Base exception for workflow service errors."""


class WorkflowNotFoundError(WorkflowServiceError):
    """Raised when a workflow is not found."""


class NodeNotFoundError(WorkflowServiceError):
    """Raised when a node is not found."""


class EdgeNotFoundError(WorkflowServiceError):
    """Raised when an edge is not found."""


class InvalidNodeReferenceError(WorkflowServiceError):
    """Raised when a node reference is invalid."""


class DAGValidationError(WorkflowServiceError):
    """Raised when DAG validation fails."""


class VersionConflictError(WorkflowServiceError):
    """Raised when version conflict occurs during optimistic locking."""


# =============================================================================
# WorkflowService
# =============================================================================


class WorkflowService:
    """Service for workflow CRUD operations.

    TAG: [SPEC-007] [API] [SERVICE] [WORKFLOW]
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize workflow service."""
        self.db = db

    async def create(self, owner_id: UUID, data: Any) -> Workflow:
        """Create a new workflow."""
        try:
            workflow = Workflow(
                owner_id=owner_id,
                name=data.name,
                description=data.description,
                config=data.config,
                variables=data.variables,
                is_active=data.is_active,
            )
            self.db.add(workflow)
            await self.db.flush()
            await self.db.refresh(workflow)
            return workflow
        except Exception as e:
            raise WorkflowServiceError(f"Failed to create workflow: {e}") from e

    async def get(self, workflow_id: UUID) -> Workflow | None:
        """Get a workflow by ID."""
        result = await self.db.execute(
            select(Workflow).where(Workflow.id == workflow_id)
        )
        return result.scalar_one_or_none()

    async def get_with_nodes(self, workflow_id: UUID) -> Workflow:
        """Get a workflow with nodes and edges preloaded."""
        result = await self.db.execute(
            select(Workflow)
            .where(Workflow.id == workflow_id)
            .options(
                selectinload(Workflow.nodes),
                selectinload(Workflow.edges),
            )
        )
        workflow = result.scalar_one_or_none()
        if workflow is None:
            raise WorkflowNotFoundError(f"Workflow {workflow_id} not found")
        return workflow

    async def list(
        self,
        owner_id: UUID,
        skip: int = 0,
        limit: int = 20,
        is_active: bool | None = None,
    ) -> list[Workflow]:
        """List workflows with pagination and filtering."""
        query = select(Workflow).where(Workflow.owner_id == owner_id)

        if is_active is not None:
            query = query.where(Workflow.is_active == is_active)

        query = query.offset(skip).limit(limit).order_by(Workflow.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count(
        self,
        owner_id: UUID,
        is_active: bool | None = None,
    ) -> int:
        """Count workflows with optional filtering."""
        query = select(func.count()).where(Workflow.owner_id == owner_id)

        if is_active is not None:
            query = query.where(Workflow.is_active == is_active)

        result = await self.db.scalar(query)
        return result or 0

    async def update(self, workflow_id: UUID, data: Any) -> Workflow:
        """Update a workflow with optimistic locking."""
        workflow = await self.get(workflow_id)
        if workflow is None:
            raise WorkflowNotFoundError(f"Workflow {workflow_id} not found")

        if workflow.version != data.version:
            raise VersionConflictError(
                f"Version conflict: expected {workflow.version}, got {data.version}"
            )

        update_data = data.model_dump(exclude_unset=True, exclude={"version"})
        for field, value in update_data.items():
            if hasattr(workflow, field):
                setattr(workflow, field, value)

        workflow.version += 1
        workflow.updated_at = datetime.now(UTC)

        await self.db.flush()
        await self.db.refresh(workflow)
        return workflow

    async def delete(self, workflow_id: UUID) -> Workflow:
        """Soft delete a workflow."""
        workflow = await self.get(workflow_id)
        if workflow is None:
            raise WorkflowNotFoundError(f"Workflow {workflow_id} not found")

        workflow.soft_delete()
        await self.db.flush()
        await self.db.refresh(workflow)
        return workflow

    async def duplicate(self, workflow_id: UUID, new_name: str) -> Workflow:
        """Duplicate a workflow with all nodes and edges."""
        workflow = await self.get_with_nodes(workflow_id)

        new_workflow = Workflow(
            owner_id=workflow.owner_id,
            name=new_name,
            description=workflow.description,
            config=workflow.config.copy(),
            variables=workflow.variables.copy(),
            is_active=False,
        )
        self.db.add(new_workflow)
        await self.db.flush()

        node_mapping: dict[UUID, UUID] = {}

        for node in workflow.nodes:
            new_node = Node(
                workflow_id=new_workflow.id,
                name=node.name,
                node_type=node.node_type,
                position_x=node.position_x,
                position_y=node.position_y,
                config=node.config.copy(),
                input_schema=node.input_schema.copy() if node.input_schema else None,
                output_schema=node.output_schema.copy() if node.output_schema else None,
                tool_id=node.tool_id,
                agent_id=node.agent_id,
                timeout_seconds=node.timeout_seconds,
                retry_config=node.retry_config.copy(),
            )
            self.db.add(new_node)
            await self.db.flush()
            node_mapping[node.id] = new_node.id

        for edge in workflow.edges:
            if (
                edge.source_node_id not in node_mapping
                or edge.target_node_id not in node_mapping
            ):
                continue

            new_edge = Edge(
                workflow_id=new_workflow.id,
                source_node_id=node_mapping[edge.source_node_id],
                target_node_id=node_mapping[edge.target_node_id],
                source_handle=edge.source_handle,
                target_handle=edge.target_handle,
                condition=edge.condition.copy() if edge.condition else None,
                priority=edge.priority,
                label=edge.label,
            )
            self.db.add(new_edge)

        await self.db.flush()

        # Refresh with nodes and edges loaded to avoid lazy loading issues
        result = await self.db.execute(
            select(Workflow)
            .where(Workflow.id == new_workflow.id)
            .options(
                selectinload(Workflow.nodes),
                selectinload(Workflow.edges),
            )
        )
        duplicate = result.scalar_one_or_none()
        return duplicate


# =============================================================================
# NodeService
# =============================================================================


class NodeService:
    """Service for node CRUD operations.

    TAG: [SPEC-007] [API] [SERVICE] [NODE]
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize node service."""
        self.db = db

    async def create(self, workflow_id: UUID, data: Any) -> Node:
        """Create a new node."""
        workflow = await self.db.execute(
            select(Workflow).where(Workflow.id == workflow_id)
        )
        if workflow.scalar_one_or_none() is None:
            raise InvalidNodeReferenceError(f"Workflow {workflow_id} not found")

        try:
            node = Node(
                workflow_id=workflow_id,
                name=data.name,
                node_type=data.node_type,
                position_x=data.position_x,
                position_y=data.position_y,
                config=data.config,
                input_schema=data.input_schema,
                output_schema=data.output_schema,
                tool_id=data.tool_id,
                agent_id=data.agent_id,
                timeout_seconds=data.timeout_seconds,
                retry_config=data.retry_config.model_dump(),
            )
            self.db.add(node)
            await self.db.flush()
            await self.db.refresh(node)
            return node
        except IntegrityError as e:
            raise InvalidNodeReferenceError(f"Invalid node reference: {e}") from e

    async def get(self, node_id: UUID) -> Node | None:
        """Get a node by ID."""
        result = await self.db.execute(select(Node).where(Node.id == node_id))
        return result.scalar_one_or_none()

    async def list_by_workflow(self, workflow_id: UUID) -> list[Node]:
        """Get all nodes for a workflow."""
        result = await self.db.execute(
            select(Node)
            .where(Node.workflow_id == workflow_id)
            .order_by(Node.created_at.asc())
        )
        return list(result.scalars().all())

    async def update(self, node_id: UUID, data: Any) -> Node:
        """Update a node."""
        node = await self.get(node_id)
        if node is None:
            raise NodeNotFoundError(f"Node {node_id} not found")

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(node, field):
                setattr(node, field, value)

        node.updated_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(node)
        return node

    async def delete(self, node_id: UUID) -> Node:
        """Delete a node."""
        node = await self.get(node_id)
        if node is None:
            raise NodeNotFoundError(f"Node {node_id} not found")

        await self.db.delete(node)
        await self.db.flush()
        return node

    async def batch_create(self, workflow_id: UUID, nodes_data: Any) -> list[Node]:
        """Batch create nodes."""
        workflow = await self.db.execute(
            select(Workflow).where(Workflow.id == workflow_id)
        )
        if workflow.scalar_one_or_none() is None:
            raise InvalidNodeReferenceError(f"Workflow {workflow_id} not found")

        # Extract nodes list from NodeBatchCreate if needed
        # nodes_data can be a NodeBatchCreate object or a plain list
        if isinstance(nodes_data, list):
            nodes_list = nodes_data
        elif hasattr(nodes_data, "nodes"):
            nodes_list = nodes_data.nodes
        else:
            nodes_list = nodes_data

        created_nodes = []
        for node_data in nodes_list:
            node = Node(
                workflow_id=workflow_id,
                name=node_data.name,
                node_type=node_data.node_type,
                position_x=node_data.position_x,
                position_y=node_data.position_y,
                config=node_data.config,
                input_schema=node_data.input_schema,
                output_schema=node_data.output_schema,
                tool_id=node_data.tool_id,
                agent_id=node_data.agent_id,
                timeout_seconds=node_data.timeout_seconds,
                retry_config=node_data.retry_config.model_dump(),
            )
            self.db.add(node)
            created_nodes.append(node)

        await self.db.flush()
        for node in created_nodes:
            await self.db.refresh(node)

        return created_nodes


# =============================================================================
# EdgeService
# =============================================================================


class EdgeService:
    """Service for edge CRUD operations with DAG validation.

    TAG: [SPEC-007] [API] [SERVICE] [EDGE] [DAG]
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize edge service."""
        self.db = db

    async def create(self, workflow_id: UUID, data: Any) -> Edge:
        """Create a new edge with DAG validation."""
        await self._validate_dag(workflow_id, data.source_node_id, data.target_node_id)

        try:
            edge = Edge(
                workflow_id=workflow_id,
                source_node_id=data.source_node_id,
                target_node_id=data.target_node_id,
                source_handle=data.source_handle,
                target_handle=data.target_handle,
                condition=data.condition,
                priority=data.priority,
                label=data.label,
            )
            self.db.add(edge)
            await self.db.flush()
            await self.db.refresh(edge)
            return edge
        except IntegrityError as e:
            raise InvalidNodeReferenceError(f"Invalid edge reference: {e}") from e

    async def get(self, edge_id: UUID) -> Edge | None:
        """Get an edge by ID."""
        result = await self.db.execute(select(Edge).where(Edge.id == edge_id))
        return result.scalar_one_or_none()

    async def list_by_workflow(self, workflow_id: UUID) -> list[Edge]:
        """Get all edges for a workflow."""
        result = await self.db.execute(
            select(Edge)
            .where(Edge.workflow_id == workflow_id)
            .order_by(Edge.created_at.asc())
        )
        return list(result.scalars().all())

    async def delete(self, edge_id: UUID) -> Edge:
        """Delete an edge."""
        edge = await self.get(edge_id)
        if edge is None:
            raise EdgeNotFoundError(f"Edge {edge_id} not found")

        await self.db.delete(edge)
        await self.db.flush()
        return edge

    async def batch_create(self, workflow_id: UUID, edges_data: Any) -> list[Edge]:
        """Batch create edges with DAG validation."""
        # Extract edges list from EdgeBatchCreate if needed
        # edges_data can be an EdgeBatchCreate object or a plain list
        if isinstance(edges_data, list):
            edges_list = edges_data
        elif hasattr(edges_data, "edges"):
            edges_list = edges_data.edges
        else:
            edges_list = edges_data

        for edge_data in edges_list:
            await self._validate_dag(
                workflow_id, edge_data.source_node_id, edge_data.target_node_id
            )

        created_edges = []
        try:
            for edge_data in edges_list:
                edge = Edge(
                    workflow_id=workflow_id,
                    source_node_id=edge_data.source_node_id,
                    target_node_id=edge_data.target_node_id,
                    source_handle=edge_data.source_handle,
                    target_handle=edge_data.target_handle,
                    condition=edge_data.condition,
                    priority=edge_data.priority,
                    label=edge_data.label,
                )
                self.db.add(edge)
                created_edges.append(edge)

            await self.db.flush()
            for edge in created_edges:
                await self.db.refresh(edge)

            return created_edges
        except IntegrityError as e:
            raise InvalidNodeReferenceError(f"Invalid edge reference: {e}") from e

    async def _validate_dag(
        self, workflow_id: UUID, source_id: UUID, target_id: UUID
    ) -> None:
        """Validate that adding an edge doesn't create a cycle."""
        # Query actual nodes in the workflow to validate node references
        nodes_result = await self.db.execute(
            select(Node.id).where(Node.workflow_id == workflow_id)
        )
        node_ids = {row[0] for row in nodes_result.fetchall()}

        if source_id not in node_ids or target_id not in node_ids:
            raise InvalidNodeReferenceError(
                f"Nodes not found in workflow: source={source_id}, target={target_id}"
            )

        # Get existing edges for cycle detection
        result = await self.db.execute(
            select(Edge).where(Edge.workflow_id == workflow_id)
        )
        existing_edges = list(result.scalars().all())

        graph: dict[UUID, list[UUID]] = {}
        for edge in existing_edges:
            if edge.source_node_id not in graph:
                graph[edge.source_node_id] = []
            graph[edge.source_node_id].append(edge.target_node_id)

        if source_id not in graph:
            graph[source_id] = []
        graph[source_id].append(target_id)

        if self._has_cycle(graph, source_id, target_id):
            raise DAGValidationError(
                "Adding this edge would create a cycle in the workflow graph"
            )

    def _has_cycle(
        self, graph: dict[UUID, list[UUID]], source: UUID, target: UUID
    ) -> bool:
        """Check if there's a path from target to source."""
        visited: set[UUID] = set()

        def dfs(node: UUID) -> bool:
            if node == source:
                return True
            if node in visited:
                return False

            visited.add(node)
            return any(dfs(neighbor) for neighbor in graph.get(node, []))

        return dfs(target)


__all__ = [
    "DAGValidationError",
    "EdgeNotFoundError",
    "EdgeService",
    "InvalidNodeReferenceError",
    "NodeNotFoundError",
    "NodeService",
    "VersionConflictError",
    "WorkflowNotFoundError",
    "WorkflowService",
    "WorkflowServiceError",
]
