"""DAG Validation Service for workflow graphs.

TAG: [SPEC-010] [DAG] [VALIDATION]
REQ: REQ-010-B - Core Validation Service Interface

This module provides the main DAGValidator service for comprehensive
workflow graph validation including cycle detection, connectivity analysis,
topology validation, and data flow verification.
"""

import asyncio
from datetime import UTC, datetime
from typing import Any, TypeAlias
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import NodeType
from app.models.workflow import Edge, Node, Workflow
from app.schemas.validation import (
    CycleCheckResult,
    TopologyLevel,
    TopologyResult,
    ValidationError as ValidationErrorDTO,
    ValidationErrorCode,
    ValidationLevel,
    ValidationOptions,
    ValidationResult,
    ValidationWarning,
)
from app.services.workflow.algorithms import GraphAlgorithms
from app.services.workflow.cache import (
    get_validation_cache,
)
from app.services.workflow.exceptions import (
    CycleDetectedError,
    InvalidNodeReferenceError,
)
from app.services.workflow.graph import Graph

_Graph: TypeAlias = "Graph[UUID]"


class DAGValidator:
    """Standalone DAG Validation Service.

    TAG: [SPEC-010] [DAG] [VALIDATION]

    This service provides comprehensive validation for workflow graphs.
    It is designed to be stateless and can be used independently of
    the existing workflow_service.py.

    Example:
        >>> validator = DAGValidator(db_session)
        >>> result = await validator.validate_workflow(workflow_id)
        >>> if result.is_valid:
        ...     print("Workflow is valid!")
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize the validator with a database session.

        Args:
            db: Async database session for querying workflow data.
        """
        self.db = db

    async def validate_workflow(
        self,
        workflow_id: UUID,
        options: ValidationOptions | None = None,
    ) -> ValidationResult:
        """Validate entire workflow graph.

        TAG: [SPEC-010] [DAG] [VALIDATION]
        REQ: REQ-010-017 - Timeout Protection
        REQ: REQ-010-018 - Validation Caching

        Performs all validation checks and returns comprehensive result.
        Uses asyncio.wait_for to enforce timeout limits.
        Implements caching to avoid redundant validations.

        Args:
            workflow_id: ID of the workflow to validate.
            options: Optional validation settings.

        Returns:
            ValidationResult with errors, warnings, and topology info.

        Raises:
            InvalidNodeReferenceError: If workflow doesn't exist.
            asyncio.TimeoutError: If validation exceeds timeout.
        """
        if options is None:
            options = ValidationOptions()

        # Get cache instance
        cache = get_validation_cache()

        # Fetch workflow first to get version for cache key
        workflow = await self._get_workflow(workflow_id)
        if workflow is None:
            raise InvalidNodeReferenceError([workflow_id])

        # Try to get from cache
        if cache.available:
            cached_result = await cache.get(workflow_id, workflow.version)
            if cached_result is not None:
                # Deserialize and reconstruct ValidationResult
                result = ValidationResult(**cached_result)
                # Mark as cached
                return result.model_copy(update={"cached": True})

        # Cache miss - perform validation
        try:
            # Wrap validation with timeout protection (REQ-010-017)
            result = await asyncio.wait_for(
                self._validate_workflow_impl(workflow_id, options),
                timeout=options.timeout_seconds,
            )

            # Store in cache (only if validation succeeded)
            if cache.available and result.is_valid:
                await cache.set(
                    workflow_id,
                    result.workflow_version,
                    result.model_dump(),
                )

            return result
        except TimeoutError:
            # Return timeout error instead of raising
            timeout_result = ValidationResult(
                is_valid=False,
                workflow_id=workflow_id,
                workflow_version=workflow.version,
                validated_at=datetime.now(UTC),
                errors=[
                    ValidationErrorDTO(
                        code=ValidationErrorCode.VALIDATION_TIMEOUT,
                        message=f"Validation exceeded timeout of {options.timeout_seconds}s",
                        details={"timeout_seconds": options.timeout_seconds},
                    )
                ],
                warnings=[],
                validation_duration_ms=options.timeout_seconds * 1000,
                validation_level=options.level,
                cached=False,
            )
            # Don't cache timeout errors
            return timeout_result

    async def _validate_workflow_impl(
        self,
        workflow_id: UUID,
        options: ValidationOptions,
    ) -> ValidationResult:
        """Internal implementation of workflow validation.

        TAG: [SPEC-010] [DAG] [VALIDATION]

        Separated from validate_workflow to allow timeout wrapping.
        """
        start_time = datetime.now(UTC)
        errors: list[ValidationErrorDTO] = []
        warnings: list[ValidationWarning] = []

        # Fetch workflow
        workflow = await self._get_workflow(workflow_id)
        if workflow is None:
            raise InvalidNodeReferenceError([workflow_id])

        # Fetch nodes and edges
        nodes, edges = await self._get_workflow_graph_data(workflow_id)

        # Build graph
        graph = self._build_graph(nodes, edges)

        # Check size limits
        self._validate_size_limits(graph, options, errors)

        # Structural validation (always performed)
        self._validate_structural(graph, nodes, edges, errors)

        # Connectivity validation (STRICT and above)
        if options.level in (ValidationLevel.STANDARD, ValidationLevel.STRICT):
            self._validate_connectivity(graph, nodes, errors, warnings)

        # Node compatibility validation (STRICT only)
        if options.level == ValidationLevel.STRICT:
            await self._validate_node_compatibility(nodes, errors)
            await self._validate_data_flow(nodes, edges, workflow.variables, errors)

        # Topology analysis (if requested and no blocking errors)
        topology: TopologyResult | None = None
        if options.include_topology and not errors:
            topology = self._generate_topology(graph)

        # Calculate duration
        duration_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

        return ValidationResult(
            is_valid=len(errors) == 0,
            workflow_id=workflow_id,
            workflow_version=workflow.version,
            validated_at=datetime.now(UTC),
            errors=errors,
            warnings=warnings,
            topology=topology,
            node_count=len(nodes),
            edge_count=len(edges),
            validation_duration_ms=duration_ms,
            validation_level=options.level,
            cached=False,
        )

    async def validate_edge_addition(
        self,
        workflow_id: UUID,
        source_node_id: UUID,
        target_node_id: UUID,
        source_handle: str | None = None,
        target_handle: str | None = None,
    ) -> ValidationResult:
        """Validate adding a new edge (pre-creation check).

        TAG: [SPEC-010] [DAG] [VALIDATION]

        Useful for real-time validation in UI before committing changes.

        Args:
            workflow_id: ID of the workflow.
            source_node_id: Source node ID.
            target_node_id: Target node ID.
            source_handle: Optional source handle.
            target_handle: Optional target handle.

        Returns:
            ValidationResult with any errors found.
        """
        errors: list[ValidationErrorDTO] = []
        warnings: list[ValidationWarning] = []

        # Fetch workflow for version
        workflow = await self._get_workflow(workflow_id)
        workflow_version = workflow.version if workflow else 1

        # Fetch current graph for node positions
        nodes, edges = await self._get_workflow_graph_data(workflow_id)
        node_positions = self._build_node_positions_map(nodes)

        # Check self-loop
        if source_node_id == target_node_id:
            errors.append(
                ValidationErrorDTO(
                    code=ValidationErrorCode.SELF_LOOP_DETECTED,
                    message="Self-loops are not allowed",
                    node_ids=[source_node_id],
                    details={
                        "node_id": str(source_node_id),
                        "node_positions": {
                            str(source_node_id): node_positions[str(source_node_id)]
                        },
                    },
                )
            )
            return ValidationResult(
                is_valid=False,
                workflow_id=workflow_id,
                workflow_version=workflow_version,
                validated_at=datetime.now(UTC),
                errors=errors,
                warnings=warnings,
            )

        # Build graph
        graph = self._build_graph(nodes, edges)

        # Check if nodes exist
        node_ids = {node.id for node in nodes}
        missing = []
        if source_node_id not in node_ids:
            missing.append(source_node_id)
        if target_node_id not in node_ids:
            missing.append(target_node_id)

        if missing:
            errors.append(
                ValidationErrorDTO(
                    code=ValidationErrorCode.NODE_NOT_FOUND,
                    message="Referenced nodes not found",
                    node_ids=missing,
                    details={"missing_nodes": [str(n) for n in missing]},
                )
            )
            return ValidationResult(
                is_valid=False,
                workflow_id=workflow_id,
                workflow_version=workflow_version,
                validated_at=datetime.now(UTC),
                errors=errors,
                warnings=warnings,
            )

        # Check for cycle with proposed edge
        cycle_path = GraphAlgorithms.detect_cycle_with_proposed_edge(
            graph, source_node_id, target_node_id
        )

        if cycle_path:
            cycle_str = " -> ".join(str(n)[:8] for n in cycle_path)
            # Get positions for nodes in cycle
            cycle_positions = {
                str(node_id): node_positions[str(node_id)] for node_id in cycle_path
            }
            errors.append(
                ValidationErrorDTO(
                    code=ValidationErrorCode.CYCLE_DETECTED,
                    message=f"Adding this edge would create a cycle: {cycle_str}",
                    node_ids=cycle_path,
                    details={
                        "cycle_path": [str(n) for n in cycle_path],
                        "node_positions": cycle_positions,
                    },
                )
            )

        # Check duplicate edge
        for edge in edges:
            if (
                edge.source_node_id == source_node_id
                and edge.target_node_id == target_node_id
                and edge.source_handle == source_handle
                and edge.target_handle == target_handle
            ):
                errors.append(
                    ValidationErrorDTO(
                        code=ValidationErrorCode.DUPLICATE_EDGE,
                        message="An edge with this connection already exists",
                        edge_ids=[edge.id],
                        details={
                            "source": str(source_node_id),
                            "target": str(target_node_id),
                        },
                    )
                )
                break

        return ValidationResult(
            is_valid=len(errors) == 0,
            workflow_id=workflow_id,
            workflow_version=workflow_version,
            validated_at=datetime.now(UTC),
            errors=errors,
            warnings=warnings,
        )

    async def validate_batch_edges(
        self,
        workflow_id: UUID,
        edges_data: list[dict[str, Any]],
    ) -> ValidationResult:
        """Validate batch edge creation.

        TAG: [SPEC-010] [DAG] [VALIDATION]

        Validates all edges together for efficiency.

        Args:
            workflow_id: ID of the workflow.
            edges_data: List of edge data to validate.

        Returns:
            ValidationResult with any errors found.
        """
        errors: list[ValidationErrorDTO] = []
        warnings: list[ValidationWarning] = []

        # Fetch workflow for version
        workflow = await self._get_workflow(workflow_id)
        workflow_version = workflow.version if workflow else 1

        # Fetch current graph
        nodes, edges = await self._get_workflow_graph_data(workflow_id)
        graph = self._build_graph(nodes, edges)
        node_ids = {node.id for node in nodes}

        # Validate each edge
        for edge_data in edges_data:
            source_id = UUID(edge_data["source_node_id"])
            target_id = UUID(edge_data["target_node_id"])
            edge_data.get("source_handle")
            edge_data.get("target_handle")

            # Check self-loop
            if source_id == target_id:
                errors.append(
                    ValidationErrorDTO(
                        code=ValidationErrorCode.SELF_LOOP_DETECTED,
                        message="Self-loops are not allowed",
                        node_ids=[source_id],
                    )
                )
                continue

            # Check nodes exist
            if source_id not in node_ids:
                errors.append(
                    ValidationErrorDTO(
                        code=ValidationErrorCode.NODE_NOT_FOUND,
                        message="Source node not found",
                        node_ids=[source_id],
                    )
                )
            if target_id not in node_ids:
                errors.append(
                    ValidationErrorDTO(
                        code=ValidationErrorCode.NODE_NOT_FOUND,
                        message="Target node not found",
                        node_ids=[target_id],
                    )
                )

        # Check for cycles with all proposed edges
        # Create a temporary graph with all edges
        temp_graph = graph.copy()
        for edge_data in edges_data:
            source_id = UUID(edge_data["source_node_id"])
            target_id = UUID(edge_data["target_node_id"])
            temp_graph.add_edge(source_id, target_id)

        cycle: list[UUID] | None = GraphAlgorithms.detect_cycle(temp_graph)
        if cycle:
            cycle_str = " -> ".join(str(n)[:8] for n in cycle)
            errors.append(
                ValidationErrorDTO(
                    code=ValidationErrorCode.CYCLE_DETECTED,
                    message=f"Batch edges would create cycle: {cycle_str}",
                    node_ids=cycle,
                    details={"cycle_path": [str(n) for n in cycle]},
                )
            )

        return ValidationResult(
            is_valid=len(errors) == 0,
            workflow_id=workflow_id,
            workflow_version=workflow_version,
            validated_at=datetime.now(UTC),
            errors=errors,
            warnings=warnings,
        )

    async def get_topology(self, workflow_id: UUID) -> TopologyResult:
        """Generate topological sort and execution order.

        TAG: [SPEC-010] [DAG] [VALIDATION]

        Returns execution levels for parallel processing.

        Args:
            workflow_id: ID of the workflow.

        Returns:
            TopologyResult with execution order analysis.

        Raises:
            CycleDetectedError: If workflow contains a cycle.
        """
        nodes, edges = await self._get_workflow_graph_data(workflow_id)
        graph = self._build_graph(nodes, edges)

        # Check for cycle first
        cycle: list[UUID] | None = GraphAlgorithms.detect_cycle(graph)
        if cycle:
            raise CycleDetectedError(cycle)

        return self._generate_topology(graph)

    async def check_cycle(
        self,
        workflow_id: UUID,
        proposed_edges: list[dict[str, Any]] | None = None,
    ) -> CycleCheckResult:
        """Check for cycles with optional proposed edges.

        TAG: [SPEC-010] [DAG] [VALIDATION]

        Lightweight check for UI real-time validation.

        Args:
            workflow_id: ID of the workflow.
            proposed_edges: Optional edges to add before checking.

        Returns:
            CycleCheckResult indicating if cycle exists.
        """
        nodes, edges = await self._get_workflow_graph_data(workflow_id)
        graph = self._build_graph(nodes, edges)

        # Add proposed edges if provided
        if proposed_edges:
            for edge_data in proposed_edges:
                source_id = UUID(edge_data["source_node_id"])
                target_id = UUID(edge_data["target_node_id"])
                graph.add_edge(source_id, target_id)

        cycle_path: list[UUID] | None = GraphAlgorithms.detect_cycle(graph)

        if cycle_path:
            cycle_str = " -> ".join(str(n)[:8] for n in cycle_path)
            return CycleCheckResult(
                has_cycle=True,
                cycle_path=cycle_path,
                cycle_description=f"Cycle detected: {cycle_str}",
            )

        return CycleCheckResult(has_cycle=False)

    # ==========================================================================
    # Private Helper Methods
    # ==========================================================================

    async def _get_workflow(self, workflow_id: UUID) -> Workflow | None:
        """Fetch workflow by ID."""
        result = await self.db.execute(
            select(Workflow).where(Workflow.id == workflow_id)
        )
        return result.scalars().first()

    async def _get_workflow_graph_data(
        self,
        workflow_id: UUID,
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

    def _build_graph(self, nodes: list[Node], edges: list[Edge]) -> _Graph:
        """Build Graph data structure from nodes and edges."""
        graph = Graph[UUID]()

        # Add all nodes
        for node in nodes:
            graph.add_node(node.id)

        # Add all edges
        for edge in edges:
            graph.add_edge(edge.source_node_id, edge.target_node_id)

        return graph

    def _validate_size_limits(
        self,
        graph: _Graph,
        options: ValidationOptions,
        errors: list[ValidationErrorDTO],
    ) -> None:
        """Validate graph size against configured limits."""
        if graph.node_count > options.max_nodes:
            errors.append(
                ValidationErrorDTO(
                    code=ValidationErrorCode.GRAPH_TOO_LARGE,
                    message="Workflow exceeds maximum node limit",
                    details={
                        "current": graph.node_count,
                        "limit": options.max_nodes,
                        "metric": "nodes",
                    },
                )
            )

        if graph.edge_count > options.max_edges:
            errors.append(
                ValidationErrorDTO(
                    code=ValidationErrorCode.GRAPH_TOO_LARGE,
                    message="Workflow exceeds maximum edge limit",
                    details={
                        "current": graph.edge_count,
                        "limit": options.max_edges,
                        "metric": "edges",
                    },
                )
            )

    def _build_node_positions_map(
        self, nodes: list[Node]
    ) -> dict[str, dict[str, float]]:
        """Build a map of node UUID to position coordinates.

        Args:
            nodes: List of Node objects.

        Returns:
            Dictionary mapping node UUID string to {"x": float, "y": float}.
        """
        return {
            str(node.id): {"x": float(node.position_x), "y": float(node.position_y)}
            for node in nodes
        }

    def _validate_structural(
        self,
        graph: _Graph,
        nodes: list[Node],
        edges: list[Edge],
        errors: list[ValidationErrorDTO],
    ) -> None:
        """Validate structural integrity (cycles, duplicates)."""
        # Build node positions map
        node_positions = self._build_node_positions_map(nodes)

        # Check for cycles
        cycle: list[UUID] | None = GraphAlgorithms.detect_cycle(graph)
        if cycle:
            cycle_str = " -> ".join(str(n)[:8] for n in cycle)
            # Get positions for nodes in cycle
            cycle_positions = {
                str(node_id): node_positions[str(node_id)] for node_id in cycle
            }
            errors.append(
                ValidationErrorDTO(
                    code=ValidationErrorCode.CYCLE_DETECTED,
                    message=f"Cycle detected: {cycle_str}",
                    node_ids=cycle,
                    details={
                        "cycle_path": [str(n) for n in cycle],
                        "node_positions": cycle_positions,
                    },
                )
            )

        # Check for duplicate edges
        edge_signatures: dict[tuple[UUID, UUID, str | None, str | None], int] = {}
        for edge in edges:
            sig = (
                edge.source_node_id,
                edge.target_node_id,
                edge.source_handle,
                edge.target_handle,
            )
            edge_signatures[sig] = edge_signatures.get(sig, 0) + 1

        duplicates = [
            (sig, count) for sig, count in edge_signatures.items() if count > 1
        ]
        if duplicates:
            dup_edges = []
            for (source, target, src_handle, tgt_handle), count in duplicates:
                dup_edges.append(
                    {
                        "source": str(source),
                        "target": str(target),
                        "source_handle": src_handle,
                        "target_handle": tgt_handle,
                        "count": count,
                    }
                )

            errors.append(
                ValidationErrorDTO(
                    code=ValidationErrorCode.DUPLICATE_EDGE,
                    message="Duplicate edges detected",
                    details={"duplicates": dup_edges},
                )
            )

    def _validate_connectivity(
        self,
        graph: _Graph,
        nodes: list[Node],
        errors: list[ValidationErrorDTO],
        warnings: list[ValidationWarning],
    ) -> None:
        """Validate connectivity (triggers, dangling, unreachable nodes)."""
        # Check for trigger node
        trigger_nodes = [n for n in nodes if n.node_type == NodeType.TRIGGER]
        if not trigger_nodes:
            errors.append(
                ValidationErrorDTO(
                    code=ValidationErrorCode.NO_TRIGGER_NODE,
                    message="Workflow must have at least one trigger node",
                )
            )

        # Check for dangling nodes
        dangling: set[UUID] = GraphAlgorithms.find_dangling_nodes(graph)
        if dangling:
            errors.append(
                ValidationErrorDTO(
                    code=ValidationErrorCode.DANGLING_NODES,
                    message="Isolated nodes detected with no connections",
                    node_ids=list(dangling),
                    details={"dangling_node_ids": [str(n) for n in dangling]},
                )
            )

        # Check for unreachable nodes (if we have trigger nodes)
        if trigger_nodes:
            trigger_ids = {t.id for t in trigger_nodes}
            unreachable = GraphAlgorithms.find_unreachable_from(graph, trigger_ids)
            if unreachable:
                errors.append(
                    ValidationErrorDTO(
                        code=ValidationErrorCode.UNREACHABLE_NODES,
                        message="Nodes not reachable from trigger",
                        node_ids=list(unreachable),
                        details={
                            "unreachable_node_ids": [str(n) for n in unreachable],
                            "trigger_node_ids": [str(t) for t in trigger_ids],
                        },
                    )
                )

        # Check for dead-end nodes
        terminal_types = {NodeType.AGGREGATOR}
        dead_ends = GraphAlgorithms.find_dead_ends(graph, terminal_types)
        # Filter out terminal nodes and trigger nodes
        non_terminal_dead_ends = [
            node_id
            for node_id in dead_ends
            if node_id not in {n.id for n in nodes if n.node_type in terminal_types}
        ]
        if non_terminal_dead_ends:
            for node_id in non_terminal_dead_ends:
                node = next((n for n in nodes if n.id == node_id), None)
                if node and node.node_type != NodeType.TRIGGER:
                    warnings.append(
                        ValidationWarning(
                            code="DEAD_END_NODE",
                            message="Node has no outgoing edges",
                            node_id=node_id,
                            suggestion="Add outgoing edge or mark as terminal",
                            position_x=node.position_x,
                            position_y=node.position_y,
                        )
                    )

    async def _validate_node_compatibility(
        self,
        nodes: list[Node],
        errors: list[ValidationErrorDTO],
    ) -> None:
        """Validate node type requirements."""
        # Build node positions map
        node_positions = self._build_node_positions_map(nodes)

        for node in nodes:
            node_errors = []

            # Check tool_id for TOOL nodes
            if node.node_type == NodeType.TOOL and node.tool_id is None:
                node_errors.append("tool_id is required for tool nodes")

            # Check agent_id for AGENT nodes
            if node.node_type == NodeType.AGENT and node.agent_id is None:
                node_errors.append("agent_id is required for agent nodes")

            if node_errors:
                errors.append(
                    ValidationErrorDTO(
                        code=ValidationErrorCode.INVALID_NODE_CONFIG,
                        message=f"Node configuration invalid: {', '.join(node_errors)}",
                        node_ids=[node.id],
                        details={
                            "node_id": str(node.id),
                            "node_type": node.node_type.value,
                            "missing_fields": node_errors,
                            "node_positions": {
                                str(node.id): node_positions[str(node.id)]
                            },
                        },
                    )
                )

    async def _validate_data_flow(
        self,
        nodes: list[Node],
        edges: list[Edge],
        variables: dict[str, Any],
        errors: list[ValidationErrorDTO],
    ) -> None:
        """Validate data flow (schema compatibility, variable binding)."""
        # Build node positions map
        node_positions = self._build_node_positions_map(nodes)

        # Build variable set
        var_set = self._extract_variables(variables)

        # Check each node's config for variable references
        for node in nodes:
            undefined = self._find_undefined_variables(node.config, var_set)
            if undefined:
                errors.append(
                    ValidationErrorDTO(
                        code=ValidationErrorCode.UNDEFINED_VARIABLE,
                        message="Undefined variables referenced in node",
                        node_ids=[node.id],
                        details={
                            "node_id": str(node.id),
                            "undefined_variables": undefined,
                            "node_positions": {
                                str(node.id): node_positions[str(node.id)]
                            },
                        },
                    )
                )

        # Check schema compatibility for connected edges
        node_map = {node.id: node for node in nodes}
        for edge in edges:
            source = node_map.get(edge.source_node_id)
            target = node_map.get(edge.target_node_id)

            if source and target:
                if source.output_schema and target.input_schema:
                    if not self._schemas_compatible(
                        source.output_schema, target.input_schema
                    ):
                        errors.append(
                            ValidationErrorDTO(
                                code=ValidationErrorCode.SCHEMA_MISMATCH,
                                message="Output schema incompatible with input schema",
                                node_ids=[source.id, target.id],
                                edge_ids=[edge.id],
                                details={
                                    "source_node_id": str(source.id),
                                    "target_node_id": str(target.id),
                                    "source_output_schema": source.output_schema,
                                    "target_input_schema": target.input_schema,
                                    "node_positions": {
                                        str(source.id): node_positions[str(source.id)],
                                        str(target.id): node_positions[str(target.id)],
                                    },
                                },
                            )
                        )

    def _generate_topology(self, graph: _Graph) -> TopologyResult:
        """Generate topology analysis from graph."""
        levels_data = GraphAlgorithms.topological_sort_levels(graph)
        if levels_data is None:
            # Graph has a cycle, return empty topology
            return TopologyResult(
                execution_order=[],
                total_levels=0,
                max_parallel_nodes=0,
                critical_path_length=0,
                critical_path=[],
            )

        # Build topology levels
        execution_order: list[TopologyLevel] = []
        for i, level_nodes in enumerate(levels_data):
            execution_order.append(
                TopologyLevel(
                    level=i,
                    node_ids=level_nodes,
                    can_parallel=len(level_nodes) > 1,
                )
            )

        # Get critical path
        critical_path, path_length = GraphAlgorithms.get_critical_path(graph)

        # Calculate max parallel nodes
        max_parallel = max((len(level) for level in levels_data), default=0)

        return TopologyResult(
            execution_order=execution_order,
            total_levels=len(levels_data),
            max_parallel_nodes=max_parallel,
            critical_path_length=path_length,
            critical_path=critical_path,
        )

    def _extract_variables(self, variables: dict[str, Any]) -> set[str]:
        """Extract top-level variable names from workflow variables."""
        return set(variables.keys()) if variables else set()

    def _find_undefined_variables(
        self,
        config: dict[str, Any],
        defined_vars: set[str],
    ) -> list[str]:
        """Find undefined variable references in config."""
        undefined: list[str] = []

        if not config:
            return undefined

        # Simple variable pattern matching ({{variable.name}})
        import re

        pattern = r"\{\{([^}]+)\}\}"
        config_str = str(config)
        matches = re.findall(pattern, config_str)

        for match in matches:
            var_path = match.strip()
            top_level = var_path.split(".")[0]
            if top_level not in defined_vars:
                undefined.append(var_path)

        return undefined

    def _schemas_compatible(
        self,
        output_schema: dict[str, Any],
        input_schema: dict[str, Any],
    ) -> bool:
        """Check if output schema is compatible with input schema."""
        # Simple type compatibility check
        # In production, this would use full JSON Schema validation
        out_type = output_schema.get("type")
        in_type = input_schema.get("type")

        # Same type is compatible
        if out_type == in_type:
            return True

        # Any output is compatible with any input
        if out_type == "any" or in_type == "any":
            return True

        # Number output compatible with number or integer input
        if out_type == "number" and in_type in ("number", "integer"):
            return True

        # Integer output compatible with integer input
        if out_type == "integer" and in_type == "integer":
            return True

        # Object output compatible with object input
        if out_type == "object" and in_type == "object":
            return True

        # Array output compatible with array input
        if out_type == "array" and in_type == "array":
            return True

        # String output compatible with string input
        if out_type == "string" and in_type == "string":
            return True

        # Boolean output compatible with boolean input
        if out_type == "boolean" and in_type == "boolean":
            return True

        # Default to incompatible
        return False


__all__ = ["DAGValidator"]
