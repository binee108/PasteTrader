"""Directed graph data structure for DAG operations.

TAG: [SPEC-010] [DAG] [GRAPH]

This module provides a generic directed graph implementation optimized for
DAG (Directed Acyclic Graph) operations including cycle detection, topological
sorting, and reachability analysis.

Time Complexity:
- Node/Edge addition: O(1)
- Cycle detection: O(V + E)
- Topological sort: O(V + E)
- Reachability analysis: O(V + E)

Space Complexity: O(V + E)
"""

from collections import defaultdict
from collections.abc import Hashable
from typing import Generic, TypeVar

NodeId = TypeVar("NodeId", bound=Hashable)


class Graph(Generic[NodeId]):
    """Directed graph data structure for DAG operations.

    TAG: [SPEC-010] [DAG] [GRAPH]

    This graph uses adjacency list representation for efficient graph
    algorithms. It maintains both forward and reverse adjacency for
    efficient predecessor/successor lookups.

    Type Parameters:
        NodeId: Hashable type used as node identifier (typically UUID).

    Example:
        >>> from uuid import UUID
        >>> graph = Graph[UUID]()
        >>> graph.add_edge(uuid1, uuid2)
        >>> graph.get_successors(uuid1)
        [uuid2]
    """

    __slots__ = ("_adjacency", "_edge_count", "_nodes", "_reverse_adjacency")

    def __init__(self) -> None:
        """Initialize an empty directed graph."""
        self._adjacency: defaultdict[NodeId, list[NodeId]] = defaultdict(list)
        self._reverse_adjacency: defaultdict[NodeId, list[NodeId]] = defaultdict(list)
        self._nodes: set[NodeId] = set()
        self._edge_count: int = 0

    @property
    def node_count(self) -> int:
        """Get the number of nodes in the graph."""
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        """Get the number of edges in the graph."""
        return self._edge_count

    def add_node(self, node_id: NodeId) -> None:
        """Add a node to the graph.

        If the node already exists, this is a no-op.

        Args:
            node_id: The identifier for the node to add.
        """
        self._nodes.add(node_id)

    def add_edge(self, source: NodeId, target: NodeId) -> None:
        """Add a directed edge from source to target.

        Both nodes are added to the graph if they don't exist.
        Duplicate edges are allowed (may be validated by higher layers).

        Args:
            source: The source node ID.
            target: The target node ID.
        """
        self._nodes.add(source)
        self._nodes.add(target)
        self._adjacency[source].append(target)
        self._reverse_adjacency[target].append(source)
        self._edge_count += 1

    def has_edge(self, source: NodeId, target: NodeId) -> bool:
        """Check if an edge exists from source to target.

        Args:
            source: The source node ID.
            target: The target node ID.

        Returns:
            True if the edge exists, False otherwise.
        """
        return target in self._adjacency.get(source, [])

    def get_successors(self, node_id: NodeId) -> list[NodeId]:
        """Get all successor nodes (outgoing neighbors).

        Args:
            node_id: The node ID.

        Returns:
            List of successor node IDs. Empty list if node has no successors.
        """
        return self._adjacency.get(node_id, [])

    def get_predecessors(self, node_id: NodeId) -> list[NodeId]:
        """Get all predecessor nodes (incoming neighbors).

        Args:
            node_id: The node ID.

        Returns:
            List of predecessor node IDs. Empty list if node has no predecessors.
        """
        return self._reverse_adjacency.get(node_id, [])

    def get_in_degree(self, node_id: NodeId) -> int:
        """Get the number of incoming edges for a node.

        Args:
            node_id: The node ID.

        Returns:
            The in-degree (number of incoming edges).
        """
        return len(self._reverse_adjacency.get(node_id, []))

    def get_out_degree(self, node_id: NodeId) -> int:
        """Get the number of outgoing edges for a node.

        Args:
            node_id: The node ID.

        Returns:
            The out-degree (number of outgoing edges).
        """
        return len(self._adjacency.get(node_id, []))

    def copy(self) -> "Graph[NodeId]":
        """Create a shallow copy of the graph.

        The returned graph has the same structure but independent
        adjacency lists (safe to modify without affecting original).

        Returns:
            A new Graph instance with the same nodes and edges.
        """
        new_graph = Graph[NodeId]()
        new_graph._nodes = self._nodes.copy()
        new_graph._adjacency = defaultdict(
            list,
            {k: v.copy() for k, v in self._adjacency.items()},
        )
        new_graph._reverse_adjacency = defaultdict(
            list,
            {k: v.copy() for k, v in self._reverse_adjacency.items()},
        )
        new_graph._edge_count = self._edge_count
        return new_graph

    def __contains__(self, node_id: NodeId) -> bool:
        """Check if a node exists in the graph.

        Args:
            node_id: The node ID to check.

        Returns:
            True if the node exists, False otherwise.
        """
        return node_id in self._nodes

    def __len__(self) -> int:
        """Get the number of nodes in the graph."""
        return len(self._nodes)

    def __repr__(self) -> str:
        """Return string representation of the graph."""
        return f"Graph(nodes={self.node_count}, edges={self.edge_count})"
