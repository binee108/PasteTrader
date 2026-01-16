"""Tests for Graph data structure.

TAG: [SPEC-010] [DAG] [GRAPH]

Test suite for the directed graph implementation including node/edge operations,
traversal methods, and property access.
"""

from uuid import uuid4

from app.services.workflow.graph import Graph


class TestGraphInitialization:
    """Tests for Graph class initialization and basic properties."""

    def test_empty_graph_initialization(self) -> None:
        """Test that a new graph is empty."""
        graph = Graph[uuid4]()
        assert graph.node_count == 0
        assert graph.edge_count == 0
        assert len(graph) == 0

    def test_empty_graph_contains_no_nodes(self) -> None:
        """Test that an empty graph contains no nodes."""
        graph = Graph[str]()
        node = "test_node"
        assert node not in graph

    def test_graph_repr(self) -> None:
        """Test string representation of graph."""
        graph = Graph[str]()
        expected = "Graph(nodes=0, edges=0)"
        assert repr(graph) == expected


class TestNodeOperations:
    """Tests for node addition and related operations."""

    def test_add_single_node(self) -> None:
        """Test adding a single node to the graph."""
        graph = Graph[str]()
        graph.add_node("node1")
        assert graph.node_count == 1
        assert "node1" in graph

    def test_add_multiple_nodes(self) -> None:
        """Test adding multiple distinct nodes."""
        graph = Graph[int]()
        graph.add_node(1)
        graph.add_node(2)
        graph.add_node(3)
        assert graph.node_count == 3
        assert 1 in graph
        assert 2 in graph
        assert 3 in graph

    def test_add_duplicate_node_is_noop(self) -> None:
        """Test that adding a duplicate node doesn't increase count."""
        graph = Graph[str]()
        graph.add_node("node1")
        graph.add_node("node1")
        assert graph.node_count == 1

    def test_len_matches_node_count(self) -> None:
        """Test that len() returns node_count."""
        graph = Graph[str]()
        graph.add_node("a")
        graph.add_node("b")
        graph.add_node("c")
        assert len(graph) == graph.node_count == 3


class TestEdgeOperations:
    """Tests for edge addition and related operations."""

    def test_add_edge_adds_both_nodes(self) -> None:
        """Test that adding an edge adds both source and target nodes."""
        graph = Graph[str]()
        graph.add_edge("source", "target")
        assert "source" in graph
        assert "target" in graph
        assert graph.node_count == 2

    def test_add_edge_increments_edge_count(self) -> None:
        """Test that adding an edge increments edge count."""
        graph = Graph[str]()
        graph.add_edge("a", "b")
        assert graph.edge_count == 1

    def test_add_multiple_edges(self) -> None:
        """Test adding multiple distinct edges."""
        graph = Graph[str]()
        graph.add_edge("a", "b")
        graph.add_edge("b", "c")
        graph.add_edge("a", "c")
        assert graph.edge_count == 3

    def test_add_edge_to_existing_nodes(self) -> None:
        """Test adding edge when nodes already exist."""
        graph = Graph[str]()
        graph.add_node("x")
        graph.add_node("y")
        assert graph.node_count == 2
        assert graph.edge_count == 0

        graph.add_edge("x", "y")
        assert graph.node_count == 2  # No new nodes
        assert graph.edge_count == 1  # One edge

    def test_duplicate_edges_are_allowed(self) -> None:
        """Test that duplicate edges increment edge count."""
        graph = Graph[str]()
        graph.add_edge("a", "b")
        graph.add_edge("a", "b")
        assert graph.edge_count == 2

    def test_self_loop_edge(self) -> None:
        """Test adding an edge from node to itself."""
        graph = Graph[str]()
        graph.add_edge("node", "node")
        assert "node" in graph
        assert graph.edge_count == 1


class TestEdgeQuery:
    """Tests for edge existence checking."""

    def test_has_edge_returns_true_for_existing_edge(self) -> None:
        """Test has_edge returns True for existing edge."""
        graph = Graph[str]()
        graph.add_edge("a", "b")
        assert graph.has_edge("a", "b") is True

    def test_has_edge_returns_false_for_nonexistent_edge(self) -> None:
        """Test has_edge returns False for nonexistent edge."""
        graph = Graph[str]()
        graph.add_edge("a", "b")
        assert graph.has_edge("a", "c") is False
        assert graph.has_edge("b", "a") is False

    def test_has_edge_with_nonexistent_nodes(self) -> None:
        """Test has_edge returns False when nodes don't exist."""
        graph = Graph[str]()
        assert graph.has_edge("x", "y") is False

    def test_has_edge_detects_direction(self) -> None:
        """Test that has_edge respects edge direction."""
        graph = Graph[str]()
        graph.add_edge("a", "b")
        assert graph.has_edge("a", "b") is True
        assert graph.has_edge("b", "a") is False


class TestSuccessors:
    """Tests for getting successor nodes."""

    def test_get_successors_empty_graph(self) -> None:
        """Test get_successors on empty graph returns empty list."""
        graph = Graph[str]()
        assert graph.get_successors("node") == []

    def test_get_successors_no_outgoing_edges(self) -> None:
        """Test get_successors for node with no outgoing edges."""
        graph = Graph[str]()
        graph.add_node("isolated")
        assert graph.get_successors("isolated") == []

    def test_get_successors_single_edge(self) -> None:
        """Test get_successors returns single successor."""
        graph = Graph[str]()
        graph.add_edge("a", "b")
        successors = graph.get_successors("a")
        assert successors == ["b"]
        assert len(successors) == 1

    def test_get_successors_multiple_edges(self) -> None:
        """Test get_successors returns all successors."""
        graph = Graph[int]()
        graph.add_edge(1, 2)
        graph.add_edge(1, 3)
        graph.add_edge(1, 4)
        successors = graph.get_successors(1)
        assert set(successors) == {2, 3, 4}
        assert len(successors) == 3

    def test_get_successors_with_duplicate_edges(self) -> None:
        """Test get_successors includes duplicates."""
        graph = Graph[str]()
        graph.add_edge("a", "b")
        graph.add_edge("a", "b")
        graph.add_edge("a", "c")
        successors = graph.get_successors("a")
        assert successors == ["b", "b", "c"]


class TestPredecessors:
    """Tests for getting predecessor nodes."""

    def test_get_predecessors_empty_graph(self) -> None:
        """Test get_predecessors on empty graph returns empty list."""
        graph = Graph[str]()
        assert graph.get_predecessors("node") == []

    def test_get_predecessors_no_incoming_edges(self) -> None:
        """Test get_predecessors for node with no incoming edges."""
        graph = Graph[str]()
        graph.add_node("isolated")
        assert graph.get_predecessors("isolated") == []

    def test_get_predecessors_single_edge(self) -> None:
        """Test get_predecessors returns single predecessor."""
        graph = Graph[str]()
        graph.add_edge("a", "b")
        predecessors = graph.get_predecessors("b")
        assert predecessors == ["a"]
        assert len(predecessors) == 1

    def test_get_predecessors_multiple_edges(self) -> None:
        """Test get_predecessors returns all predecessors."""
        graph = Graph[int]()
        graph.add_edge(1, 4)
        graph.add_edge(2, 4)
        graph.add_edge(3, 4)
        predecessors = graph.get_predecessors(4)
        assert set(predecessors) == {1, 2, 3}
        assert len(predecessors) == 3

    def test_get_predecessors_with_duplicate_edges(self) -> None:
        """Test get_predecessors includes duplicates."""
        graph = Graph[str]()
        graph.add_edge("a", "c")
        graph.add_edge("b", "c")
        graph.add_edge("a", "c")
        predecessors = graph.get_predecessors("c")
        assert predecessors == ["a", "b", "a"]


class TestNodeDegree:
    """Tests for in-degree and out-degree calculations."""

    def test_get_in_degree_no_edges(self) -> None:
        """Test in-degree for isolated node."""
        graph = Graph[str]()
        graph.add_node("isolated")
        assert graph.get_in_degree("isolated") == 0

    def test_get_in_degree_single_edge(self) -> None:
        """Test in-degree with single incoming edge."""
        graph = Graph[str]()
        graph.add_edge("a", "b")
        assert graph.get_in_degree("b") == 1
        assert graph.get_in_degree("a") == 0

    def test_get_in_degree_multiple_edges(self) -> None:
        """Test in-degree with multiple incoming edges."""
        graph = Graph[int]()
        graph.add_edge(1, 4)
        graph.add_edge(2, 4)
        graph.add_edge(3, 4)
        assert graph.get_in_degree(4) == 3

    def test_get_in_degree_counts_duplicates(self) -> None:
        """Test in-degree counts duplicate edges."""
        graph = Graph[str]()
        graph.add_edge("a", "b")
        graph.add_edge("a", "b")
        graph.add_edge("c", "b")
        assert graph.get_in_degree("b") == 3

    def test_get_out_degree_no_edges(self) -> None:
        """Test out-degree for isolated node."""
        graph = Graph[str]()
        graph.add_node("isolated")
        assert graph.get_out_degree("isolated") == 0

    def test_get_out_degree_single_edge(self) -> None:
        """Test out-degree with single outgoing edge."""
        graph = Graph[str]()
        graph.add_edge("a", "b")
        assert graph.get_out_degree("a") == 1
        assert graph.get_out_degree("b") == 0

    def test_get_out_degree_multiple_edges(self) -> None:
        """Test out-degree with multiple outgoing edges."""
        graph = Graph[int]()
        graph.add_edge(1, 2)
        graph.add_edge(1, 3)
        graph.add_edge(1, 4)
        assert graph.get_out_degree(1) == 3

    def test_get_out_degree_counts_duplicates(self) -> None:
        """Test out-degree counts duplicate edges."""
        graph = Graph[str]()
        graph.add_edge("a", "b")
        graph.add_edge("a", "b")
        graph.add_edge("a", "c")
        assert graph.get_out_degree("a") == 3


class TestGraphCopy:
    """Tests for graph copying functionality."""

    def test_copy_creates_independent_graph(self) -> None:
        """Test that copy creates independent graph instance."""
        graph = Graph[str]()
        graph.add_node("a")
        graph.add_edge("a", "b")

        copy_graph = graph.copy()
        assert copy_graph is not graph

    def test_copy_preserves_nodes(self) -> None:
        """Test that copy preserves all nodes."""
        graph = Graph[str]()
        graph.add_node("a")
        graph.add_node("b")
        graph.add_node("c")

        copy_graph = graph.copy()
        assert copy_graph.node_count == graph.node_count
        assert "a" in copy_graph
        assert "b" in copy_graph
        assert "c" in copy_graph

    def test_copy_preserves_edges(self) -> None:
        """Test that copy preserves all edges."""
        graph = Graph[str]()
        graph.add_edge("a", "b")
        graph.add_edge("b", "c")

        copy_graph = graph.copy()
        assert copy_graph.edge_count == graph.edge_count
        assert copy_graph.has_edge("a", "b")
        assert copy_graph.has_edge("b", "c")

    def test_copy_modifications_dont_affect_original(self) -> None:
        """Test that modifying copy doesn't affect original."""
        graph = Graph[str]()
        graph.add_node("a")
        graph.add_edge("a", "b")

        copy_graph = graph.copy()
        copy_graph.add_node("c")
        copy_graph.add_edge("b", "c")

        assert "c" not in graph
        assert graph.edge_count == 1
        assert copy_graph.edge_count == 2

    def test_copy_preserves_successors_predecessors(self) -> None:
        """Test that copy preserves successors and predecessors."""
        graph = Graph[int]()
        graph.add_edge(1, 2)
        graph.add_edge(1, 3)
        graph.add_edge(2, 3)

        copy_graph = graph.copy()
        assert set(copy_graph.get_successors(1)) == {2, 3}
        assert set(copy_graph.get_predecessors(3)) == {1, 2}


class TestGraphWithUUID:
    """Tests for Graph with UUID node identifiers (common use case)."""

    def test_graph_with_uuid_nodes(self) -> None:
        """Test graph operations with UUID node identifiers."""
        from uuid import UUID

        graph = Graph[UUID]()
        node1 = uuid4()
        node2 = uuid4()
        node3 = uuid4()

        graph.add_edge(node1, node2)
        graph.add_edge(node2, node3)

        assert node1 in graph
        assert node2 in graph
        assert node3 in graph
        assert graph.has_edge(node1, node2)
        assert graph.has_edge(node2, node3)
        assert graph.get_successors(node1) == [node2]
        assert graph.get_predecessors(node3) == [node2]


class TestGraphComplexScenarios:
    """Tests for complex graph scenarios."""

    def test_linear_chain(self) -> None:
        """Test graph representing a linear chain: a -> b -> c -> d."""
        graph = Graph[str]()
        edges = [("a", "b"), ("b", "c"), ("c", "d")]

        for src, tgt in edges:
            graph.add_edge(src, tgt)

        assert graph.node_count == 4
        assert graph.edge_count == 3
        assert set(graph.get_successors("a")) == {"b"}
        assert set(graph.get_successors("b")) == {"c"}
        assert set(graph.get_successors("c")) == {"d"}
        assert graph.get_successors("d") == []

    def test_star_topology(self) -> None:
        """Test graph representing star topology with center node."""
        graph = Graph[str]()
        center = "center"
        leaves = ["leaf1", "leaf2", "leaf3", "leaf4"]

        for leaf in leaves:
            graph.add_edge(center, leaf)

        assert graph.node_count == 5
        assert graph.edge_count == 4
        assert len(graph.get_successors(center)) == 4
        for leaf in leaves:
            assert graph.get_predecessors(leaf) == [center]

    def test_diamond_pattern(self) -> None:
        """Test graph with diamond pattern: a -> (b, c) -> d."""
        graph = Graph[str]()
        graph.add_edge("a", "b")
        graph.add_edge("a", "c")
        graph.add_edge("b", "d")
        graph.add_edge("c", "d")

        assert graph.node_count == 4
        assert graph.edge_count == 4
        assert set(graph.get_successors("a")) == {"b", "c"}
        assert set(graph.get_predecessors("d")) == {"b", "c"}

    def test_bidirectional_edges(self) -> None:
        """Test graph with edges in both directions between nodes."""
        graph = Graph[str]()
        graph.add_edge("a", "b")
        graph.add_edge("b", "a")

        assert graph.has_edge("a", "b")
        assert graph.has_edge("b", "a")
        assert graph.get_successors("a") == ["b"]
        assert graph.get_successors("b") == ["a"]
        assert graph.get_predecessors("a") == ["b"]
        assert graph.get_predecessors("b") == ["a"]
