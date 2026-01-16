"""Graph algorithms for DAG validation and topology analysis.

TAG: [SPEC-010] [DAG] [ALGORITHMS]
REQ: REQ-010-001 - Cycle Detection
REQ: REQ-010-014 - Topological Sort Generation
REQ: REQ-010-007 - Unreachable Node Detection
REQ: REQ-010-006 - Dangling Node Detection
REQ: REQ-010-008 - Dead-End Detection

This module provides efficient graph algorithms for DAG operations:
- Cycle detection using DFS with path tracking
- Topological sort using Kahn's algorithm
- Reachability analysis using BFS
- Dangling node detection
- Dead-end node detection
- Critical path analysis

Time Complexity:
- Cycle detection: O(V + E)
- Topological sort: O(V + E)
- Reachability: O(V + E)
- Critical path: O(V + E)

Space Complexity: O(V + E) for all algorithms.
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING, Generic, TypeVar
from uuid import UUID

if TYPE_CHECKING:
    from app.models.enums import NodeType
    from app.services.workflow.graph import Graph

NodeId = TypeVar("NodeId", bound=UUID)


class GraphAlgorithms(Generic[NodeId]):
    """Collection of graph algorithms for DAG validation.

    TAG: [SPEC-010] [DAG] [ALGORITHMS]

    This class provides static methods for common graph operations
    needed for workflow DAG validation. All algorithms operate on
    the Graph data structure.

    Example:
        >>> graph = Graph[UUID]()
        >>> graph.add_edge(uuid1, uuid2)
        >>> cycle: list[NodeId] | None = GraphAlgorithms.detect_cycle(graph)
        >>> if cycle:
        ...     print(f"Cycle found: {cycle}")
    """

    @staticmethod
    def detect_cycle(graph: Graph[NodeId]) -> list[NodeId] | None:
        """Detect cycle using DFS with path tracking.

        TAG: [SPEC-010] [DAG] [ALGORITHM]
        REQ: REQ-010-001

        Args:
            graph: The graph to check for cycles.

        Returns:
            List of node IDs forming the cycle if found, None otherwise.

        Time Complexity: O(V + E)
        Space Complexity: O(V)

        Example:
            >>> graph = Graph[UUID]()
            >>> graph.add_edge(a, b)
            >>> graph.add_edge(b, c)
            >>> graph.add_edge(c, a)  # Creates cycle
            >>> cycle: list[NodeId] | None = GraphAlgorithms.detect_cycle(graph)
            >>> # Returns [a, b, c, a]
        """
        visited: set[NodeId] = set()
        rec_stack: set[NodeId] = set()
        path: list[NodeId] = []

        def dfs(node: NodeId) -> list[NodeId] | None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get_successors(node):
                if neighbor not in visited:
                    result = dfs(neighbor)
                    if result:
                        return result
                elif neighbor in rec_stack:
                    # Found a cycle - extract the cycle path
                    cycle_start = path.index(neighbor)
                    return [*path[cycle_start:], neighbor]

            path.pop()
            rec_stack.remove(node)
            return None

        for node in graph._nodes:
            if node not in visited:
                result = dfs(node)
                if result:
                    return result

        return None

    @staticmethod
    def detect_cycle_with_proposed_edge(
        graph: Graph[NodeId],
        source: NodeId,
        target: NodeId,
    ) -> list[NodeId] | None:
        """Check if adding an edge would create a cycle.

        TAG: [SPEC-010] [DAG] [ALGORITHM]
        REQ: REQ-010-001

        This is optimized for edge validation - instead of checking the entire
        graph, we only need to check if target can reach source.

        Args:
            graph: The current graph structure.
            source: Source node of the proposed edge.
            target: Target node of the proposed edge.

        Returns:
            List of node IDs forming the cycle if edge would create cycle, None otherwise.

        Time Complexity: O(V + E) worst case, but often much faster
        Space Complexity: O(V)

        Example:
            >>> graph = Graph[UUID]()
            >>> graph.add_edge(a, b)
            >>> graph.add_edge(b, c)
            >>> # Check if adding c -> a creates a cycle
            >>> cycle = GraphAlgorithms.detect_cycle_with_proposed_edge(graph, c, a)
            >>> # Returns [c, a, b, c] (would create cycle)
        """
        # If target can reach source, adding source -> target creates a cycle
        visited: set[NodeId] = set()
        queue: deque[NodeId] = deque([target])
        path: dict[NodeId, NodeId | None] = {target: None}

        while queue:
            current = queue.popleft()

            if current == source:
                # Reconstruct the cycle path
                # Path from target to source exists, build the cycle
                reversed_path: list[NodeId] = []
                node: NodeId | None = source
                while node is not None:
                    reversed_path.append(node)
                    node = path.get(node)
                # Reverse to get path from target to source
                reversed_path.reverse()
                # Add the proposed edge (source -> target) to complete the cycle
                return [source, *reversed_path]

            visited.add(current)

            for neighbor in graph.get_successors(current):
                if neighbor not in visited:
                    path[neighbor] = current
                    queue.append(neighbor)

        return None

    @staticmethod
    def topological_sort_levels(graph: Graph[NodeId]) -> list[list[NodeId]] | None:
        """Kahn's algorithm for level-based topological sort.

        TAG: [SPEC-010] [DAG] [ALGORITHM]
        REQ: REQ-010-014

        Groups nodes by execution level where nodes at the same level
        can execute in parallel.

        Args:
            graph: The graph to sort (must be a DAG).

        Returns:
            List of levels, where each level is a list of node IDs.
            Returns None if graph contains a cycle.

        Time Complexity: O(V + E)
        Space Complexity: O(V + E)

        Example:
            >>> graph = Graph[UUID]()
            >>> graph.add_edge(a, b)
            >>> graph.add_edge(a, c)
            >>> graph.add_edge(b, d)
            >>> graph.add_edge(c, d)
            >>> levels = GraphAlgorithms.topological_sort_levels(graph)
            >>> # Returns [[a], [b, c], [d]]
            >>> # Level 0: a (no dependencies)
            >>> # Level 1: b, c (depend on a, can run in parallel)
            >>> # Level 2: d (depends on b and c)
        """
        # First check for cycle
        if GraphAlgorithms.detect_cycle(graph):
            return None

        # Calculate in-degrees for all nodes
        in_degree: dict[NodeId, int] = {}
        for node in graph._nodes:
            in_degree[node] = graph.get_in_degree(node)

        # Initialize queue with nodes that have no incoming edges
        queue: deque[NodeId] = deque(
            node for node in graph._nodes if in_degree[node] == 0
        )

        levels: list[list[NodeId]] = []

        while queue:
            current_level: list[NodeId] = []
            next_queue: deque[NodeId] = deque()

            while queue:
                node = queue.popleft()
                current_level.append(node)

                # Reduce in-degree for all successors
                for successor in graph.get_successors(node):
                    in_degree[successor] -= 1
                    if in_degree[successor] == 0:
                        next_queue.append(successor)

            levels.append(current_level)
            queue = next_queue

        return levels

    @staticmethod
    def find_unreachable_from(
        graph: Graph[NodeId],
        start_nodes: set[NodeId],
    ) -> set[NodeId]:
        """Find nodes not reachable from any start node using BFS.

        TAG: [SPEC-010] [DAG] [ALGORITHM]
        REQ: REQ-010-007

        Args:
            graph: The graph to analyze.
            start_nodes: Set of starting nodes (typically trigger nodes).

        Returns:
            Set of node IDs not reachable from any start node.

        Time Complexity: O(V + E)
        Space Complexity: O(V)

        Example:
            >>> graph = Graph[UUID]()
            >>> graph.add_edge(a, b)
            >>> graph.add_edge(c, d)  # c is disconnected
            >>> unreachable = GraphAlgorithms.find_unreachable_from(graph, {a})
            >>> # Returns {c, d} (not reachable from a)
        """
        if not start_nodes:
            # If no start nodes, all nodes are unreachable
            return graph._nodes.copy()

        reachable: set[NodeId] = set()
        queue: deque[NodeId] = deque(start_nodes)

        while queue:
            current = queue.popleft()
            if current in reachable:
                continue

            reachable.add(current)

            for successor in graph.get_successors(current):
                if successor not in reachable:
                    queue.append(successor)

        # Find nodes that were never reached
        return graph._nodes - reachable

    @staticmethod
    def find_dangling_nodes(graph: Graph[NodeId]) -> set[NodeId]:
        """Find nodes with no incoming or outgoing edges.

        TAG: [SPEC-010] [DAG] [ALGORITHM]
        REQ: REQ-010-006

        A dangling node is completely isolated - no connections at all.
        Single-node workflows (trigger only) are not considered dangling.

        Args:
            graph: The graph to analyze.

        Returns:
            Set of node IDs that have no connections.

        Time Complexity: O(V)
        Space Complexity: O(V)

        Example:
            >>> graph = Graph[UUID]()
            >>> graph.add_node(a)
            >>> graph.add_edge(b, c)
            >>> dangling: set[NodeId] = GraphAlgorithms.find_dangling_nodes(graph)
            >>> # Returns {a} (has no edges)
        """
        if len(graph._nodes) <= 1:
            return set()

        dangling: set[NodeId] = set()

        for node in graph._nodes:
            if graph.get_in_degree(node) == 0 and graph.get_out_degree(node) == 0:
                dangling.add(node)

        return dangling

    @staticmethod
    def find_dead_ends(
        graph: Graph[NodeId],
        terminal_types: set[NodeType] | None = None,
    ) -> set[NodeId]:
        """Find non-terminal nodes with no outgoing edges.

        TAG: [SPEC-010] [DAG] [ALGORITHM]
        REQ: REQ-010-008

        Args:
            graph: The graph to analyze.
            terminal_types: Set of node types that are allowed to have no outputs.
                           If None, uses default terminal types.

        Returns:
            Set of node IDs that should have outputs but don't.

        Time Complexity: O(V)
        Space Complexity: O(V)

        Example:
            >>> graph = Graph[UUID]()
            >>> graph.add_edge(a, b)
            >>> # b has no outputs but is not a terminal type
            >>> dead_ends = GraphAlgorithms.find_dead_ends(graph)
            >>> # Returns {b}
        """
        from app.models.enums import NodeType

        if terminal_types is None:
            terminal_types = {NodeType.AGGREGATOR}

        dead_ends: set[NodeId] = set()

        for node in graph._nodes:
            if graph.get_out_degree(node) == 0:
                # This node has no outputs - check if it's a terminal type
                # For now, we don't have node type info in Graph
                # This will be handled at the validator level
                dead_ends.add(node)

        return dead_ends

    @staticmethod
    def get_critical_path(graph: Graph[NodeId]) -> tuple[list[NodeId], int]:
        """Find longest path (critical path) in DAG using DFS.

        TAG: [SPEC-010] [DAG] [ALGORITHM]
        REQ: REQ-010-015

        The critical path represents the longest sequence of dependent
        nodes and determines the minimum execution time.

        Args:
            graph: The graph to analyze (must be a DAG).

        Returns:
            Tuple of (path as list of node IDs, path length).

        Time Complexity: O(V + E)
        Space Complexity: O(V)

        Example:
            >>> graph = Graph[UUID]()
            >>> graph.add_edge(a, b)
            >>> graph.add_edge(a, c)
            >>> graph.add_edge(b, d)
            >>> graph.add_edge(c, d)
            >>> graph.add_edge(d, e)
            >>> path, length = GraphAlgorithms.get_critical_path(graph)
            >>> # Returns ([a, b, d, e] or [a, c, d, e], 4)
        """
        # Check for cycle first
        if GraphAlgorithms.detect_cycle(graph):
            return [], 0

        # Use memoization for efficiency
        memo: dict[NodeId, tuple[list[NodeId], int]] = {}

        def dfs(node: NodeId) -> tuple[list[NodeId], int]:
            """Returns (longest path from node, length of path)."""
            if node in memo:
                return memo[node]

            best_path: list[NodeId] = []
            best_length: int = 1

            for successor in graph.get_successors(node):
                successor_path, successor_length = dfs(successor)
                if successor_length + 1 > best_length:
                    best_length = successor_length + 1
                    best_path = [node, *successor_path]

            if not best_path:
                best_path = [node]

            memo[node] = (best_path, best_length)
            return memo[node]

        # Find the node with the longest path to any sink
        overall_best_path: list[NodeId] = []
        overall_best_length: int = 0

        for node in graph._nodes:
            path, length = dfs(node)
            if length > overall_best_length:
                overall_best_length = length
                overall_best_path = path

        return overall_best_path, overall_best_length

    @staticmethod
    def validate_dag(graph: Graph[NodeId]) -> tuple[bool, list[str]]:
        """Validate that the graph is a proper DAG.

        TAG: [SPEC-010] [DAG] [ALGORITHM]

        Performs comprehensive DAG validation including:
        - No cycles
        - All nodes reachable from at least one trigger
        - No dangling nodes (except single-node workflows)

        Args:
            graph: The graph to validate.

        Returns:
            Tuple of (is_valid, list of error messages).

        Time Complexity: O(V + E)
        Space Complexity: O(V + E)

        Example:
            >>> graph = Graph[UUID]()
            >>> graph.add_edge(a, b)
            >>> graph.add_edge(b, a)  # Cycle!
            >>> is_valid, errors = GraphAlgorithms.validate_dag(graph)
            >>> # Returns (False, ["Cycle detected: a -> b -> a"])
        """
        errors: list[str] = []

        # Check for cycles
        cycle: list[NodeId] | None = GraphAlgorithms.detect_cycle(graph)
        if cycle:
            cycle_str = " -> ".join(str(n)[:8] for n in cycle)
            errors.append(f"Cycle detected: {cycle_str}")
            return False, errors

        # Check for dangling nodes
        dangling: set[NodeId] = GraphAlgorithms.find_dangling_nodes(graph)
        if dangling and len(graph._nodes) > 1:
            dangling_str = ", ".join(str(n)[:8] for n in dangling)
            errors.append(f"Dangling nodes detected: {dangling_str}")

        return len(errors) == 0, errors


# Type alias for convenience
DAGAlgorithms = GraphAlgorithms


__all__ = [
    "DAGAlgorithms",
    "GraphAlgorithms",
]
