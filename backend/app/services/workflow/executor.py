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

import contextlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import select

from app.models.enums import ExecutionStatus, LogLevel, TriggerType
from app.models.execution import ExecutionLog, NodeExecution, WorkflowExecution
from app.models.workflow import Edge, Node, Workflow
from app.services.workflow.context import ExecutionContext
from app.services.workflow.exceptions import (
    ExecutionCancelledError,
    ExecutionError,
    NodeTimeoutError,
)
from app.services.workflow.graph import Graph
from app.services.workflow.validator import DAGValidator

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

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

        # Store execution_id early to avoid accessing session objects later
        execution_id = execution.id

        # Log workflow start
        await self._log_execution_event(
            execution_id=execution_id,
            level=LogLevel.INFO,
            message=f"Workflow execution started: {workflow.name}",
        )

        # Create execution context
        context = ExecutionContext(
            workflow_execution_id=execution_id,
            input_data=input_data,
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
            # Convert UUID keys to strings for JSON storage
            outputs = await context.get_all_outputs()
            execution.output_data = {str(k): v for k, v in outputs.items()}

            # Log workflow completion
            await self._log_execution_event(
                execution_id=execution_id,
                level=LogLevel.INFO,
                message="Workflow execution completed successfully",
            )

            await self.db.commit()

            return ExecutionResult(
                execution_id=execution_id,
                status=ExecutionStatus.COMPLETED,
                output_data=execution.output_data,
                node_results=await context.get_all_outputs(),
            )

        except Exception as e:
            # Store execution_id before any database operations
            # to avoid accessing stale session objects
            execution_id = execution.id

            return ExecutionResult(
                execution_id=execution_id,
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

    async def _log_execution_event(
        self,
        execution_id: UUID,
        level: LogLevel,
        message: str,
        node_execution_id: UUID | None = None,
    ) -> None:
        """Log an execution event to the database.

        TAG: [SPEC-011] [EXECUTION] [EXECUTOR]
        REQ: REQ-011-010 - ExecutionLog integration

        Args:
            execution_id: Workflow execution ID.
            level: Log level (DEBUG, INFO, WARNING, ERROR).
            message: Log message.
            node_execution_id: Optional node execution ID for node-level logs.

        """
        from sqlalchemy import exc

        log = ExecutionLog(
            workflow_execution_id=execution_id,
            node_execution_id=node_execution_id,
            level=level,
            message=message,
        )
        self.db.add(log)
        with contextlib.suppress(exc.PendingRollbackError):
            # Session is in rollback state - skip logging
            # This happens when there's been a previous error
            await self.db.flush()

    async def _get_workflow(self, workflow_id: UUID) -> Workflow:
        """Fetch workflow by ID."""
        result = await self.db.execute(
            select(Workflow).where(Workflow.id == workflow_id),
        )
        workflow = result.scalars().first()
        if workflow is None:
            raise ExecutionError(f"Workflow {workflow_id} not found")
        return workflow

    async def _execute_node_with_timeout(
        self,
        node: Node,
        input_data: dict[str, Any],
        execution_order: int,  # noqa: ARG002
    ) -> dict[str, Any]:
        """Execute a single node with timeout handling.

        TAG: [SPEC-011] [EXECUTION] [EXECUTOR]
        REQ: REQ-011-008 - Node timeout handling with asyncio.timeout()

        Args:
            node: Node to execute.
            input_data: Input data for the node.
            execution_order: Execution order counter.

        Returns:
            Output data from node execution.

        Raises:
            NodeTimeoutError: If node execution exceeds timeout.

        """
        import asyncio

        # Get timeout from node config (default to 30 seconds)
        timeout_seconds = node.config.get("timeout_seconds", 30) if node.config else 30

        # Get simulated execution time from node config (for testing, default 0.01s)
        sleep_seconds = node.config.get("sleep_seconds", 0.01) if node.config else 0.01

        async def execute_node_logic() -> dict[str, Any]:
            """Execute the actual node logic."""
            # Placeholder implementation - in real scenario, this would execute
            # the node's configured operation (API call, transformation, etc.)
            await asyncio.sleep(sleep_seconds)  # Simulate work
            return {"executed": True, "input": input_data}

        try:
            async with asyncio.timeout(timeout_seconds):
                return await execute_node_logic()
        except TimeoutError:
            raise NodeTimeoutError(node_id=node.id, timeout_seconds=timeout_seconds)

    async def _execute_node_with_retry(
        self,
        node: Node,
        input_data: dict[str, Any],
        execution_order: int,
    ) -> tuple[dict[str, Any], int]:
        """Execute a node with exponential backoff retry.

        TAG: [SPEC-011] [EXECUTION] [EXECUTOR]
        REQ: REQ-011-004 - Exponential backoff retry

        Args:
            node: Node to execute.
            input_data: Input data for the node.
            execution_order: Execution order counter.

        Returns:
            Tuple of (output_data, retry_count).

        Raises:
            ExecutionError: If all retries are exhausted.

        """
        import asyncio

        # Get retry config from node
        retry_config = node.config.get("retry_config", {}) if node.config else {}
        max_retries = retry_config.get("max_retries", 0)
        delay = retry_config.get("delay", 1)

        last_error: Exception | None = None

        for attempt in range(max_retries + 1):  # +1 for initial attempt
            try:
                # Execute with timeout
                output_data = await self._execute_node_with_timeout(
                    node,
                    input_data,
                    execution_order,
                )
                # Success - return output and retry count
                return output_data, attempt

            except Exception as e:
                last_error = e

                # If this was not the last attempt, wait before retry
                if attempt < max_retries:
                    # Exponential backoff: delay * (2 ** attempt)
                    backoff_delay = delay * (2**attempt)
                    await asyncio.sleep(backoff_delay)

        # All retries exhausted
        raise ExecutionError(
            f"Node {str(node.id)[:8]} failed after {max_retries} retries: {last_error}",
        ) from last_error

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
        REQ: REQ-011-005 - Failure isolation policy
        REQ: REQ-011-006 - Condition node branching

        Executes all nodes in each level in parallel using asyncio.TaskGroup.
        Tracks failed nodes and marks downstream nodes as SKIPPED.
        Processes condition nodes and excludes non-matching paths from execution.

        Args:
            execution: WorkflowExecution record.
            workflow: Workflow being executed.
            topology: TopologyResult with execution levels.
            context: ExecutionContext for data passing.

        """
        from app.models.workflow import NodeType
        from app.services.workflow.graph import Graph

        # Fetch all nodes and edges
        nodes, edges = await self._get_workflow_graph_data(workflow.id)
        node_map = {node.id: node for node in nodes}

        # Create edge maps for lookups
        edge_map_by_pair = {(e.source_node_id, e.target_node_id): e for e in edges}
        edge_map_by_id = {e.id: (e.source_node_id, e.target_node_id) for e in edges}

        # Build graph for downstream traversal
        graph = Graph[UUID]()
        for edge in edges:
            graph.add_edge(edge.source_node_id, edge.target_node_id)

        # Track failed and skipped node IDs
        failed_node_ids: set[UUID] = set()
        skipped_node_ids: set[UUID] = set()

        # Execute each level
        for level_data in topology.execution_order:
            if self._cancelled:
                raise ExecutionCancelledError(execution_id=execution.id)

            # Check for CONDITION nodes in this level
            condition_nodes_in_level = [
                node_map[nid]
                for nid in level_data.node_ids
                if nid in node_map and node_map[nid].node_type == NodeType.CONDITION
            ]

            # Process condition nodes and apply routing
            for condition_node in condition_nodes_in_level:
                # Evaluate condition (placeholder - SPEC-012 will implement)
                evaluation_result = await self._evaluate_condition_node(
                    node=condition_node,
                    context=context,
                )

                # Apply condition routing to get skipped nodes
                matched_edges = evaluation_result.get("matched_edges", [])
                condition_skipped = await self._apply_condition_routing(
                    condition_node_id=condition_node.id,
                    matched_edges=matched_edges,
                    graph=graph,
                    node_map=node_map,
                    edge_map=edge_map_by_id,
                )

                # Add to global skipped set
                skipped_node_ids.update(condition_skipped)

                # Create SKIPPED NodeExecution records for skipped nodes
                await self._create_skipped_executions(
                    skipped_nodes=condition_skipped,
                    node_map=node_map,
                    execution_id=execution.id,
                    reason="Condition node excluded this path",
                )

            # Filter out skipped nodes from this level
            nodes_to_execute = [
                nid for nid in level_data.node_ids if nid not in skipped_node_ids
            ]

            # Execute non-skipped nodes in this level in parallel
            level_failed_nodes = await self._execute_level(
                execution,
                nodes_to_execute,
                node_map,
                edge_map_by_pair,
                context,
            )

            # Add failed nodes to tracking set
            failed_node_ids.update(level_failed_nodes)

        # Mark all downstream nodes of failed nodes as SKIPPED
        if failed_node_ids:
            await self._mark_downstream_blocked(
                failed_node_ids=failed_node_ids,
                graph=graph,
                node_map=node_map,
                execution_id=execution.id,
            )

            # Raise exception to mark workflow as failed
            failed_node_names = [
                node_map[nid].name for nid in failed_node_ids if nid in node_map
            ]
            raise ExecutionError(
                f"Workflow execution failed: {len(failed_node_ids)} node(s) failed: "
                f"{', '.join(failed_node_names)}"
            )

    async def _execute_level(
        self,
        execution: WorkflowExecution,
        node_ids: list[UUID],
        node_map: dict[UUID, Node],
        edge_map: dict[tuple[UUID, UUID], Edge],
        context: ExecutionContext,
    ) -> list[UUID]:
        """Execute all nodes in a level in parallel.

        TAG: [SPEC-011] [EXECUTION] [EXECUTOR]
        REQ: REQ-011-005 - Failure isolation policy

        Uses asyncio.TaskGroup to execute nodes in parallel.
        Returns list of failed node IDs for downstream blocking.

        Args:
            execution: WorkflowExecution record.
            node_ids: List of node IDs to execute.
            node_map: Map of node ID to Node object.
            edge_map: Map of (source, target) to Edge object.
            context: ExecutionContext for data passing.

        Returns:
            List of node IDs that failed during execution.

        """
        import asyncio

        # Track execution order and failed nodes
        execution_counter = 0
        failed_node_ids: list[UUID] = []

        async def execute_single_node(node_id: UUID) -> NodeExecution | None:
            """Execute a single node.

            Returns:
                NodeExecution record if successful, None if failed.
            """
            nonlocal execution_counter
            execution_counter += 1

            node = node_map[node_id]

            # Get incoming edges
            incoming_edges = [
                edge_map[(s, t)]
                for (s, t) in edge_map
                if t == node_id and (s, t) in edge_map
            ]

            # Get input data
            input_data = await context.get_input(node, incoming_edges)

            try:
                # Execute node with retry and timeout
                output_data, retry_count = await self._execute_node_with_retry(
                    node,
                    input_data,
                    execution_counter,
                )
                await context.set_output(node_id, output_data)

                # Create COMPLETED node execution record (don't flush yet)
                node_execution = NodeExecution(
                    workflow_execution_id=execution.id,
                    node_id=node_id,
                    status=ExecutionStatus.COMPLETED,
                    started_at=datetime.now(UTC),
                    ended_at=datetime.now(UTC),
                    input_data=input_data,
                    output_data=output_data,
                    execution_order=execution_counter,
                    retry_count=retry_count,
                )
                self.db.add(node_execution)
                return node_execution

            except Exception as e:
                # Track failed node
                failed_node_ids.append(node_id)

                # Create FAILED node execution record (don't flush yet)
                node_execution = NodeExecution(
                    workflow_execution_id=execution.id,
                    node_id=node_id,
                    status=ExecutionStatus.FAILED,
                    started_at=datetime.now(UTC),
                    ended_at=datetime.now(UTC),
                    input_data=input_data,
                    error_message=str(e),
                    execution_order=execution_counter,
                    retry_count=0,
                )
                self.db.add(node_execution)
                # Return None to indicate failure
                return None

        # Execute all nodes in parallel using TaskGroup
        # Collect node execution records for logging after flush
        node_executions: list[NodeExecution] = []

        async def execute_and_collect(node_id: UUID) -> NodeExecution | None:
            """Execute node and collect result."""
            result = await execute_single_node(node_id)
            if result is not None:
                node_executions.append(result)
            return result

        try:
            async with asyncio.TaskGroup() as tg:
                for node_id in node_ids:
                    tg.create_task(execute_and_collect(node_id))
        except ExceptionGroup:
            # TaskGroup failed - some nodes may have succeeded, some failed
            # All records have been added to session but not flushed yet
            pass

        # Flush all node executions (successful and failed) to database
        # Note: We don't commit here - let the caller handle commit/rollback
        # This ensures proper test isolation and session state management
        await self.db.flush()

        # Now that flush succeeded, log all node executions (safe to do now)
        for node_exec in node_executions:
            node = node_map.get(node_exec.node_id)
            if not node:
                continue

            # Log node execution start
            await self._log_execution_event(
                execution_id=execution.id,
                node_execution_id=node_exec.id,
                level=LogLevel.INFO,
                message=f"Node '{node.name}' execution started",
            )

            # Log retry warnings if retries occurred
            if node_exec.retry_count > 0:
                await self._log_execution_event(
                    execution_id=execution.id,
                    node_execution_id=node_exec.id,
                    level=LogLevel.WARNING,
                    message=f"Node '{node.name}' required {node_exec.retry_count} retry(ies)",
                )

            # Log node execution completion
            if node_exec.status == ExecutionStatus.COMPLETED:
                await self._log_execution_event(
                    execution_id=execution.id,
                    node_execution_id=node_exec.id,
                    level=LogLevel.INFO,
                    message=f"Node '{node.name}' execution completed",
                )

        # Log failures
        if failed_node_ids:
            for node_id in failed_node_ids:
                node = node_map.get(node_id)
                if node:
                    await self._log_execution_event(
                        execution_id=execution.id,
                        level=LogLevel.ERROR,
                        message=f"Node '{node.name}' execution failed",
                    )

        return failed_node_ids

    async def _mark_downstream_blocked(
        self,
        failed_node_ids: set[UUID] | list[UUID],
        graph: Graph[UUID],
        node_map: dict[UUID, Node],
        execution_id: UUID,
    ) -> None:
        """Mark all downstream nodes of failed nodes as SKIPPED.

        TAG: [SPEC-011] [EXECUTION] [EXECUTOR]
        REQ: REQ-011-005 - Failure isolation policy

        Uses BFS to find all downstream nodes from failed nodes and marks
        them as SKIPPED. Independent branches continue execution.

        Args:
            failed_node_ids: Set/list of failed node IDs.
            graph: Graph[UUID] with get_successors method.
            node_map: Map of node ID to Node object.
            execution_id: Workflow execution ID.

        """
        from collections import deque

        # Find all downstream nodes using BFS
        visited: set[UUID] = set()
        queue: deque[UUID] = deque()

        # Initialize queue with all failed nodes
        for failed_node_id in failed_node_ids:
            queue.append(failed_node_id)
            visited.add(failed_node_id)

        downstream_nodes: list[UUID] = []

        while queue:
            current_node = queue.popleft()

            # Get all successors (downstream nodes)
            successors = graph.get_successors(current_node)

            for successor_id in successors:
                if successor_id not in visited:
                    visited.add(successor_id)
                    queue.append(successor_id)
                    downstream_nodes.append(successor_id)

        # Create SKIPPED NodeExecution records for downstream nodes
        # First add all records, then flush, then log (to avoid session state issues)
        execution_order = 9999  # High number to indicate skipped
        skipped_executions: list[tuple[Node, NodeExecution]] = []

        for node_id in downstream_nodes:
            node = node_map.get(node_id)
            if not node:
                continue

            # Create SKIPPED node execution record
            node_execution = NodeExecution(
                workflow_execution_id=execution_id,
                node_id=node_id,
                status=ExecutionStatus.SKIPPED,
                started_at=datetime.now(UTC),
                ended_at=datetime.now(UTC),
                input_data={},
                output_data=None,
                execution_order=execution_order,
                retry_count=0,
                error_message="Blocked by upstream node failure",
            )
            self.db.add(node_execution)
            skipped_executions.append((node, node_execution))

        # Flush all SKIPPED node executions
        await self.db.flush()

        # Now log blocked nodes (safe after flush)
        for node, node_execution in skipped_executions:
            await self._log_execution_event(
                execution_id=execution_id,
                node_execution_id=node_execution.id,
                level=LogLevel.WARNING,
                message=f"Node '{node.name}' skipped due to upstream failure",
            )

    async def _create_skipped_executions(
        self,
        skipped_nodes: set[UUID] | list[UUID],
        node_map: dict[UUID, Node],
        execution_id: UUID,
        reason: str,
    ) -> None:
        """Create SKIPPED NodeExecution records for skipped nodes.

        TAG: [SPEC-011] [EXECUTION] [EXECUTOR]
        REQ: REQ-011-006 - Condition node path exclusion

        Args:
            skipped_nodes: Set/list of node IDs to skip.
            node_map: Map of node ID to Node object.
            execution_id: Workflow execution ID.
            reason: Reason for skipping.

        """
        execution_order = 9999  # High number to indicate skipped

        for node_id in skipped_nodes:
            node = node_map.get(node_id)
            if not node:
                continue

            # Create SKIPPED node execution record
            node_execution = NodeExecution(
                workflow_execution_id=execution_id,
                node_id=node_id,
                status=ExecutionStatus.SKIPPED,
                started_at=datetime.now(UTC),
                ended_at=datetime.now(UTC),
                input_data={},
                output_data=None,
                execution_order=execution_order,
                retry_count=0,
                error_message=reason,
            )
            self.db.add(node_execution)

        # Flush all SKIPPED node executions
        await self.db.flush()

        # Log skipped nodes
        for node_id in skipped_nodes:
            node = node_map.get(node_id)
            if node:
                await self._log_execution_event(
                    execution_id=execution_id,
                    level=LogLevel.WARNING,
                    message=f"Node '{node.name}' skipped: {reason}",
                )

    async def _get_workflow_graph_data(
        self,
        workflow_id: UUID,
    ) -> tuple[list[Node], list[Edge]]:
        """Fetch all nodes and edges for a workflow."""
        # Fetch nodes
        nodes_result = await self.db.execute(
            select(Node).where(Node.workflow_id == workflow_id),
        )
        nodes = list(nodes_result.scalars().all())

        # Fetch edges
        edges_result = await self.db.execute(
            select(Edge).where(Edge.workflow_id == workflow_id),
        )
        edges = list(edges_result.scalars().all())

        return nodes, edges

    async def _create_execution_context(
        self, execution_id: UUID, input_data: dict[str, Any]
    ) -> ExecutionContext:
        """Create an execution context for node execution.

        TAG: [SPEC-011] [EXECUTION] [EXECUTOR]
        REQ: REQ-011-003 - ExecutionContext for node data passing

        Args:
            execution_id: Workflow execution ID.
            input_data: Initial input data.

        Returns:
            ExecutionContext instance.

        """
        return ExecutionContext(
            workflow_execution_id=execution_id,
            input_data=input_data,
        )

    async def _evaluate_condition_node(
        self,
        node: Node,
        context: ExecutionContext,  # noqa: ARG002
    ) -> dict[str, Any]:
        """Evaluate condition node and return evaluation result.

        TAG: [SPEC-011] [EXECUTION] [EXECUTOR]
        REQ: REQ-011-006 - Condition node branching

        SPEC-011: Handles routing based on result
        SPEC-012: Will implement actual expression evaluation

        Args:
            node: CONDITION 타입 노드.
            context: ExecutionContext with execution data.

        Returns:
            dict with "matched_edges": list[edge_id] and "result": bool

        """
        from app.models.workflow import NodeType

        # Placeholder implementation - SPEC-012 will implement actual evaluation
        # For now, return all outgoing edges as matched
        if node.node_type != NodeType.CONDITION:
            return {"matched_edges": [], "result": False}

        # Get outgoing edges for this node
        edges_result = await self.db.execute(
            select(Edge).where(Edge.source_node_id == node.id)
        )
        outgoing_edges = list(edges_result.scalars().all())

        # SPEC-011: Return all edges as matched (placeholder)
        # SPEC-012: Will evaluate conditions and return only matching edges
        return {
            "matched_edges": [e.id for e in outgoing_edges],
            "result": True,
        }

    async def _apply_condition_routing(
        self,
        condition_node_id: UUID,
        matched_edges: list[UUID],
        graph: _Graph,
        node_map: dict[UUID, Node],  # noqa: ARG002
        edge_map: dict[UUID, tuple[UUID, UUID]] | None = None,
    ) -> set[UUID]:
        """Mark non-matching paths as SKIPPED.

        TAG: [SPEC-011] [EXECUTION] [EXECUTOR]
        REQ: REQ-011-006 - Path exclusion based on condition result

        Args:
            condition_node_id: ID of the condition node.
            matched_edges: List of edge IDs that matched the condition.
            graph: Graph[UUID] for traversal.
            node_map: Map of node ID to Node object.
            edge_map: Optional map of edge_id to (source_id, target_id).

        Returns:
            Set of node IDs to skip (exclude from execution).

        """
        from collections import deque

        skipped_nodes: set[UUID] = set()

        # If no edge_map provided, return empty set (no skipping)
        if not edge_map:
            return skipped_nodes

        # Get target nodes of matched edges
        matched_targets: set[UUID] = set()
        for edge_id in matched_edges:
            if edge_id in edge_map:
                _, target_id = edge_map[edge_id]
                matched_targets.add(target_id)

        # Get all immediate successors of condition node
        all_successors = graph.get_successors(condition_node_id)

        # Find non-matching paths (successors not in matched_targets)
        non_matching_successors = [
            succ for succ in all_successors if succ not in matched_targets
        ]

        # For each non-matching successor, find all downstream nodes
        for successor_id in non_matching_successors:
            # BFS to find all descendants
            visited: set[UUID] = set()
            queue: deque[UUID] = deque([successor_id])

            while queue:
                current = queue.popleft()

                if current in visited:
                    continue
                visited.add(current)

                # Add to skipped nodes
                skipped_nodes.add(current)

                # Add all successors to queue
                for succ in graph.get_successors(current):
                    if succ not in visited:
                        queue.append(succ)

        return skipped_nodes
