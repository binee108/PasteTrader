"""WorkflowExecutor for DAG-based workflow execution.

TAG: [SPEC-011] [EXECUTION] [EXECUTOR]
REQ: REQ-011-001 - DAG topological sort based execution
REQ: REQ-011-002 - asyncio.TaskGroup parallel execution
REQ: REQ-011-003 - ExecutionContext for node data passing
REQ: REQ-011-004 - Exponential backoff retry
REQ: REQ-011-005 - Failure isolation policy
REQ: REQ-011-009 - Workflow cancellation support
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ExecutionStatus, TriggerType
from app.models.execution import ExecutionLog, NodeExecution, WorkflowExecution
from app.models.workflow import Edge, Node, Workflow
from app.services.workflow.algorithms import GraphAlgorithms
from app.services.workflow.context import ExecutionContext
from app.services.workflow.exceptions import (
    ExecutionCancelledError,
    ExecutionError,
)
from app.services.workflow.graph import Graph
from app.services.workflow.validator import DAGValidator

type _Graph = Graph[UUID]


@dataclass
class ExecutionResult:
    """Result of workflow execution.

    TAG: [SPEC-011] [EXECUTION] [EXECUTOR]

    Attributes:
        execution_id: UUID of the workflow execution.
        status: Final execution status.
        output_data: Output data from the workflow (if successful).
        error_message: Error message (if failed).
        node_results: Dictionary of node ID to execution result.
    """

    execution_id: UUID
    status: ExecutionStatus
    output_data: dict[str, Any] | None = None
    error_message: str | None = None
    node_results: dict[UUID, dict[str, Any]] | None = None


class WorkflowExecutor:
    """DAG-based workflow execution engine.

    TAG: [SPEC-011] [EXECUTION] [EXECUTOR]

    Executes workflows using topological sort for ordering and
    asyncio.TaskGroup for parallel node execution.

    Attributes:
        db: Async database session.
        max_parallel_nodes: Maximum number of nodes to execute in parallel.
        _validator: DAGValidator instance for validation.
        _cancelled: Flag indicating if execution was cancelled.
    """

    def __init__(self, db: AsyncSession, max_parallel_nodes: int = 10) -> None:
        """Initialize the executor.

        Args:
            db: Async database session.
            max_parallel_nodes: Maximum parallel node executions (default: 10).
        """
        import asyncio

        self.db = db
        self.max_parallel_nodes = max_parallel_nodes
        self._semaphore = asyncio.Semaphore(max_parallel_nodes)
        self._cancelled = False
        self._validator = DAGValidator(db)

    async def execute(
        self,
        workflow_id: UUID,
        input_data: dict[str, Any],
        trigger_type: TriggerType = TriggerType.MANUAL,
    ) -> ExecutionResult:
        """Execute a workflow.

        TAG: [SPEC-011] [EXECUTION] [EXECUTOR]
        REQ: REQ-011-001 - DAG topological sort based execution
        REQ: REQ-011-002 - asyncio.TaskGroup parallel execution

        Args:
            workflow_id: UUID of the workflow to execute.
            input_data: Input data for the workflow.
            trigger_type: How the execution was triggered.

        Returns:
            ExecutionResult with execution details.

        Raises:
            ExecutionCancelledError: If executor was cancelled.
        """
        # Check if cancelled
        if self._cancelled:
            raise ExecutionCancelledError(execution_id=UUID(int=0))

        # Fetch workflow
        workflow = await self._get_workflow(workflow_id)

        # Create workflow execution record
        execution = WorkflowExecution(
            workflow_id=workflow_id,
            trigger_type=trigger_type,
            status=ExecutionStatus.PENDING,
            input_data=input_data,
            started_at=datetime.now(UTC),
        )
        self.db.add(execution)
        await self.db.flush()

        # Create execution context
        context = ExecutionContext(
            workflow_execution_id=execution.id, input_data=input_data
        )

        try:
            # Validate workflow topology
            topology = await self._validator.get_topology(workflow_id)

            # Update execution status to RUNNING
            execution.status = ExecutionStatus.RUNNING
            await self.db.commit()

            # Execute nodes by topological levels
            await self._execute_by_levels(execution, workflow, topology, context)

            # Mark as completed
            execution.status = ExecutionStatus.COMPLETED
            execution.ended_at = datetime.now(UTC)
            execution.output_data = await context.get_all_outputs()
            await self.db.commit()

            return ExecutionResult(
                execution_id=execution.id,
                status=ExecutionStatus.COMPLETED,
                output_data=execution.output_data,
                node_results=await context.get_all_outputs(),
            )

        except Exception as e:
            # Mark as failed
            execution.status = ExecutionStatus.FAILED
            execution.ended_at = datetime.now(UTC)
            execution.error_message = str(e)
            await self.db.commit()

            return ExecutionResult(
                execution_id=execution.id,
                status=ExecutionStatus.FAILED,
                error_message=str(e),
            )

    async def cancel(self, execution_id: UUID) -> None:
        """Cancel a running workflow execution.

        TAG: [SPEC-011] [EXECUTION] [EXECUTOR]
        REQ: REQ-011-009 - Workflow cancellation support

        Args:
            execution_id: UUID of the execution to cancel.
        """
        self._cancelled = True

        # Update execution record
        execution = await self.db.get(WorkflowExecution, execution_id)
        if execution and execution.status == ExecutionStatus.RUNNING:
            execution.status = ExecutionStatus.CANCELLED
            execution.ended_at = datetime.now(UTC)
            await self.db.commit()

    # ==========================================================================
    # Private Helper Methods
    # ==========================================================================

    async def _get_workflow(self, workflow_id: UUID) -> Workflow:
        """Fetch workflow by ID."""
        result = await self.db.execute(select(Workflow).where(Workflow.id == workflow_id))
        workflow = result.scalars().first()
        if workflow is None:
            raise ExecutionError(f"Workflow {workflow_id} not found")
        return workflow

    async def _execute_by_levels(
        self,
        execution: WorkflowExecution,
        workflow: Workflow,
        topology: Any,  # TopologyResult
        context: ExecutionContext,
    ) -> None:
        """Execute nodes by topological levels.

        TAG: [SPEC-011] [EXECUTION] [EXECUTOR]
        REQ: REQ-011-002 - asyncio.TaskGroup parallel execution

        Executes all nodes in each level in parallel using asyncio.TaskGroup.

        Args:
            execution: WorkflowExecution record.
            workflow: Workflow being executed.
            topology: TopologyResult with execution levels.
            context: ExecutionContext for data passing.
        """
        import asyncio

        # Fetch all nodes and edges
        nodes, edges = await self._get_workflow_graph_data(workflow.id)
        node_map = {node.id: node for node in nodes}
        edge_map = {(e.source_node_id, e.target_node_id): e for e in edges}

        # Execute each level
        for level_data in topology.execution_order:
            if self._cancelled:
                raise ExecutionCancelledError(execution_id=execution.id)

            # Execute nodes in this level in parallel
            await self._execute_level(
                execution, level_data.node_ids, node_map, edge_map, context
            )

    async def _execute_level(
        self,
        execution: WorkflowExecution,
        node_ids: list[UUID],
        node_map: dict[UUID, Node],
        edge_map: dict[tuple[UUID, UUID], Edge],
        context: ExecutionContext,
    ) -> None:
        """Execute all nodes in a level in parallel.

        TAG: [SPEC-011] [EXECUTION] [EXECUTOR]

        Uses asyncio.TaskGroup to execute nodes in parallel.

        Args:
            execution: WorkflowExecution record.
            node_ids: List of node IDs to execute.
            node_map: Map of node ID to Node object.
            edge_map: Map of (source, target) to Edge object.
            context: ExecutionContext for data passing.
        """
        import asyncio

        async def execute_single_node(node_id: UUID) -> None:
            """Execute a single node."""
            node = node_map[node_id]

            # Get incoming edges
            incoming_edges = [
                edge_map[(s, t)]
                for (s, t) in edge_map
                if t == node_id and (s, t) in edge_map
            ]

            # Get input data
            input_data = await context.get_input(node, incoming_edges)

            # Execute node (placeholder - actual implementation in later tasks)
            # For now, just store a simple output
            output_data = {"executed": True, "input": input_data}
            await context.set_output(node_id, output_data)

            # Create node execution record
            node_execution = NodeExecution(
                workflow_execution_id=execution.id,
                node_id=node_id,
                status=ExecutionStatus.COMPLETED,
                started_at=datetime.now(UTC),
                ended_at=datetime.now(UTC),
                input_data=input_data,
                output_data=output_data,
            )
            self.db.add(node_execution)

        # Execute all nodes in parallel using TaskGroup
        async with asyncio.TaskGroup() as tg:
            for node_id in node_ids:
                tg.create_task(execute_single_node(node_id))

        # Commit all node executions
        await self.db.commit()

    async def _get_workflow_graph_data(
        self, workflow_id: UUID
    ) -> tuple[list[Node], list[Edge]]:
        """Fetch all nodes and edges for a workflow."""
        # Fetch nodes
        nodes_result = await self.db.execute(
            select(Node).where(Node.workflow_id == workflow_id)
        )
        nodes = list(nodes_result.scalars().all())

        # Fetch edges
        edges_result = await self.db.execute(
            select(Edge).where(Edge.workflow_id == workflow_id)
        )
        edges = list(edges_result.scalars().all())

        return nodes, edges
