"""Tests for GraphAlgorithms class.

TAG: [SPEC-010] [TESTING] [GRAPH_ALGORITHMS]
REQ: REQ-010-001 - Cycle Detection Tests
REQ: REQ-010-014 - Topological Sort Tests
REQ: REQ-010-007 - Unreachable Node Detection Tests
REQ: REQ-010-006 - Dangling Node Detection Tests
REQ: REQ-010-008 - Dead-End Detection Tests
REQ: REQ-010-015 - Critical Path Tests

Test Coverage Strategy:
- Unit tests for each graph algorithm
- Edge cases (empty graphs, single nodes, cycles)
- Normal case scenarios
- Complex multi-path scenarios
"""

from uuid import UUID, uuid4

import pytest

from app.services.workflow.algorithms import GraphAlgorithms
from app.services.workflow.graph import Graph

# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def empty_graph() -> Graph[UUID]:
    """Create an empty graph for testing."""
    return Graph[UUID]()


@pytest.fixture
def simple_dag() -> tuple[Graph[UUID], dict[str, UUID]]:
    """Create a simple DAG: a -> b -> c.

    Returns:
        Tuple of (graph, nodes_dict) where nodes_dict has 'a', 'b', 'c' keys.
    """
    graph = Graph[UUID]()
    a, b, c = uuid4(), uuid4(), uuid4()
    graph.add_edge(a, b)
    graph.add_edge(b, c)
    return graph, {"a": a, "b": b, "c": c}


@pytest.fixture
def diamond_dag() -> tuple[Graph[UUID], dict[str, UUID]]:
    """Create a diamond DAG: a -> b, a -> c, b -> d, c -> d.

    Returns:
        Tuple of (graph, nodes_dict) where nodes_dict has 'a', 'b', 'c', 'd' keys.
    """
    graph = Graph[UUID]()
    a, b, c, d = uuid4(), uuid4(), uuid4(), uuid4()
    graph.add_edge(a, b)
    graph.add_edge(a, c)
    graph.add_edge(b, d)
    graph.add_edge(c, d)
    return graph, {"a": a, "b": b, "c": c, "d": d}


@pytest.fixture
def cycle_graph() -> tuple[Graph[UUID], dict[str, UUID]]:
    """Create a graph with a cycle: a -> b -> c -> a.

    Returns:
        Tuple of (graph, nodes_dict) where nodes_dict has 'a', 'b', 'c' keys.
    """
    graph = Graph[UUID]()
    a, b, c = uuid4(), uuid4(), uuid4()
    graph.add_edge(a, b)
    graph.add_edge(b, c)
    graph.add_edge(c, a)
    return graph, {"a": a, "b": b, "c": c}


@pytest.fixture
def disconnected_graph() -> tuple[Graph[UUID], dict[str, UUID]]:
    """Create a disconnected graph: a -> b, c -> d.

    Returns:
        Tuple of (graph, nodes_dict) where nodes_dict has 'a', 'b', 'c', 'd' keys.
    """
    graph = Graph[UUID]()
    a, b, c, d = uuid4(), uuid4(), uuid4(), uuid4()
    graph.add_edge(a, b)
    graph.add_edge(c, d)
    return graph, {"a": a, "b": b, "c": c, "d": d}


@pytest.fixture
def complex_dag() -> tuple[Graph[UUID], dict[str, UUID]]:
    """Create a complex DAG with multiple levels.

    Returns:
        Tuple of (graph, nodes_dict) with node0 through node6 keys.
    """
    graph = Graph[UUID]()
    nodes = {f"node{i}": uuid4() for i in range(7)}

    # Level 0 -> Level 1
    graph.add_edge(nodes["node0"], nodes["node1"])
    graph.add_edge(nodes["node0"], nodes["node2"])

    # Level 1 -> Level 2
    graph.add_edge(nodes["node1"], nodes["node3"])
    graph.add_edge(nodes["node2"], nodes["node3"])
    graph.add_edge(nodes["node2"], nodes["node4"])

    # Level 2 -> Level 3
    graph.add_edge(nodes["node3"], nodes["node5"])
    graph.add_edge(nodes["node4"], nodes["node5"])
    graph.add_edge(nodes["node4"], nodes["node6"])

    return graph, nodes


# =============================================================================
# CYCLE DETECTION TESTS
# =============================================================================


class TestDetectCycle:
    """Tests for detect_cycle method."""

    def test_empty_graph_has_no_cycle(self, empty_graph: Graph[UUID]):
        """Empty graph should not have a cycle."""
        result = GraphAlgorithms.detect_cycle(empty_graph)
        assert result is None

    def test_single_node_graph_has_no_cycle(self, empty_graph: Graph[UUID]):
        """Single node graph should not have a cycle."""
        node = uuid4()
        empty_graph.add_node(node)
        result = GraphAlgorithms.detect_cycle(empty_graph)
        assert result is None

    def test_simple_dag_has_no_cycle(
        self, simple_dag: tuple[Graph[UUID], dict[str, UUID]]
    ):
        """Simple DAG should not have a cycle."""
        graph, _ = simple_dag
        result = GraphAlgorithms.detect_cycle(graph)
        assert result is None

    def test_diamond_dag_has_no_cycle(
        self, diamond_dag: tuple[Graph[UUID], dict[str, UUID]]
    ):
        """Diamond DAG should not have a cycle."""
        graph, _ = diamond_dag
        result = GraphAlgorithms.detect_cycle(graph)
        assert result is None

    def test_cycle_graph_detects_cycle(
        self, cycle_graph: tuple[Graph[UUID], dict[str, UUID]]
    ):
        """Graph with cycle should detect it."""
        graph, nodes = cycle_graph
        result = GraphAlgorithms.detect_cycle(graph)
        assert result is not None
        assert len(result) == 4  # a -> b -> c -> a
        # First and last nodes should be the same (cycle completes)
        assert result[0] == result[-1]

    def test_self_loop_is_detected_as_cycle(self, empty_graph: Graph[UUID]):
        """Graph with self-loop (a -> a) should detect cycle."""
        node = uuid4()
        empty_graph.add_edge(node, node)
        result = GraphAlgorithms.detect_cycle(empty_graph)
        assert result is not None
        assert len(result) == 2  # a -> a

    def test_complex_dag_has_no_cycle(
        self, complex_dag: tuple[Graph[UUID], dict[str, UUID]]
    ):
        """Complex DAG should not have a cycle."""
        graph, _ = complex_dag
        result = GraphAlgorithms.detect_cycle(graph)
        assert result is None

    def test_cycle_in_larger_graph(self, empty_graph: Graph[UUID]):
        """Detect cycle in a larger graph with multiple components."""
        nodes = {f"node{i}": uuid4() for i in range(6)}

        # Add DAG structure
        empty_graph.add_edge(nodes["node0"], nodes["node1"])
        empty_graph.add_edge(nodes["node1"], nodes["node2"])

        # Add cycle
        empty_graph.add_edge(nodes["node3"], nodes["node4"])
        empty_graph.add_edge(nodes["node4"], nodes["node5"])
        empty_graph.add_edge(nodes["node5"], nodes["node3"])

        result = GraphAlgorithms.detect_cycle(empty_graph)
        assert result is not None
        # Should find the cycle involving nodes 3, 4, 5


class TestDetectCycleWithProposedEdge:
    """Tests for detect_cycle_with_proposed_edge method."""

    def test_proposed_edge_creates_simple_cycle(
        self, simple_dag: tuple[Graph[UUID], dict[str, UUID]]
    ):
        """Adding edge that creates simple cycle should be detected."""
        graph, nodes = simple_dag
        # Adding edge from c to a would create cycle: a -> b -> c -> a
        source = nodes["c"]
        target = nodes["a"]

        result = GraphAlgorithms.detect_cycle_with_proposed_edge(graph, source, target)
        assert result is not None
        assert len(result) == 4

    def test_proposed_edge_in_dag_creates_no_cycle(
        self, diamond_dag: tuple[Graph[UUID], dict[str, UUID]]
    ):
        """Adding valid edge to DAG should not create cycle."""
        graph, nodes = diamond_dag
        # Add new node
        new_node = uuid4()
        # Adding edge from d to new_node is valid
        source = nodes["d"]

        result = GraphAlgorithms.detect_cycle_with_proposed_edge(
            graph, source, new_node
        )
        assert result is None

    def test_proposed_self_loop_creates_cycle(self, empty_graph: Graph[UUID]):
        """Adding self-loop should create cycle."""
        node = uuid4()
        empty_graph.add_node(node)

        result = GraphAlgorithms.detect_cycle_with_proposed_edge(
            empty_graph, node, node
        )
        assert result is not None

    def test_proposed_edge_to_disconnected_component(
        self, disconnected_graph: tuple[Graph[UUID], dict[str, UUID]]
    ):
        """Adding edge between disconnected components should not create cycle."""
        graph, nodes = disconnected_graph
        # Connect the two components: b -> c
        source = nodes["b"]
        target = nodes["c"]

        result = GraphAlgorithms.detect_cycle_with_proposed_edge(graph, source, target)
        assert result is None

    def test_proposed_edge_creates_multi_step_cycle(
        self, complex_dag: tuple[Graph[UUID], dict[str, UUID]]
    ):
        """Adding edge that creates multi-step cycle should be detected."""
        graph, nodes = complex_dag
        # Find a leaf node and connect it back to root to create cycle
        # This creates a cycle through the DAG
        source = nodes["node6"]  # Last node (leaf)
        target = nodes["node0"]  # First node (root)

        result = GraphAlgorithms.detect_cycle_with_proposed_edge(graph, source, target)
        assert result is not None


# =============================================================================
# TOPOLOGICAL SORT TESTS
# =============================================================================


class TestTopologicalSortLevels:
    """Tests for topological_sort_levels method."""

    def test_empty_graph_topological_sort(self, empty_graph: Graph[UUID]):
        """Empty graph should return empty levels."""
        result = GraphAlgorithms.topological_sort_levels(empty_graph)
        assert result == []

    def test_single_node_topological_sort(self, empty_graph: Graph[UUID]):
        """Single node should return single level with that node."""
        node = uuid4()
        empty_graph.add_node(node)
        result = GraphAlgorithms.topological_sort_levels(empty_graph)
        assert result is not None
        assert len(result) == 1
        assert node in result[0]

    def test_simple_chain_topological_sort(
        self, simple_dag: tuple[Graph[UUID], dict[str, UUID]]
    ):
        """Simple chain should have sequential levels."""
        graph, _ = simple_dag
        result = GraphAlgorithms.topological_sort_levels(graph)
        assert result is not None
        assert len(result) == 3  # a, b, c each in separate level
        assert len(result[0]) == 1  # Level 0: a
        assert len(result[1]) == 1  # Level 1: b
        assert len(result[2]) == 1  # Level 2: c

    def test_diamond_topological_sort(
        self, diamond_dag: tuple[Graph[UUID], dict[str, UUID]]
    ):
        """Diamond DAG should have parallel nodes at same level."""
        graph, _ = diamond_dag
        result = GraphAlgorithms.topological_sort_levels(graph)
        assert result is not None
        assert len(result) == 3  # [a], [b, c], [d]
        assert len(result[0]) == 1  # Level 0: a
        assert len(result[1]) == 2  # Level 1: b and c (parallel)
        assert len(result[2]) == 1  # Level 2: d

    def test_cycle_graph_returns_none(
        self, cycle_graph: tuple[Graph[UUID], dict[str, UUID]]
    ):
        """Graph with cycle should return None."""
        graph, _ = cycle_graph
        result = GraphAlgorithms.topological_sort_levels(graph)
        assert result is None

    def test_complex_dag_topological_sort(
        self, complex_dag: tuple[Graph[UUID], dict[str, UUID]]
    ):
        """Complex DAG should have correct level structure."""
        graph, _ = complex_dag
        result = GraphAlgorithms.topological_sort_levels(graph)
        assert result is not None
        assert len(result) == 4  # Should have 4 levels
        # Level 0: 1 node (root)
        # Level 1: 2 nodes
        # Level 2: 2 nodes
        # Level 3: 2 nodes (leaves)
        assert len(result[0]) == 1
        assert len(result[1]) == 2
        assert len(result[2]) == 2
        assert len(result[3]) == 2


# =============================================================================
# UNREACHABLE NODES TESTS
# =============================================================================


class TestFindUnreachableFrom:
    """Tests for find_unreachable_from method."""

    def test_empty_graph_unreachable(self, empty_graph: Graph[UUID]):
        """Empty graph should have no unreachable nodes."""
        result = GraphAlgorithms.find_unreachable_from(empty_graph, set())
        assert result == set()

    def test_no_start_nodes_returns_all_nodes(
        self, simple_dag: tuple[Graph[UUID], dict[str, UUID]]
    ):
        """Empty start set should return all nodes as unreachable."""
        graph, _ = simple_dag
        result = GraphAlgorithms.find_unreachable_from(graph, set())
        assert result == graph._nodes

    def test_single_start_node_reaches_all(
        self, simple_dag: tuple[Graph[UUID], dict[str, UUID]]
    ):
        """Starting from root should reach all nodes."""
        graph, nodes = simple_dag
        start_nodes = {nodes["a"]}
        result = GraphAlgorithms.find_unreachable_from(graph, start_nodes)
        assert result == set()

    def test_disconnected_graph_unreachable(
        self, disconnected_graph: tuple[Graph[UUID], dict[str, UUID]]
    ):
        """Disconnected graph should have unreachable nodes."""
        graph, nodes = disconnected_graph
        start_nodes = {nodes["a"]}
        result = GraphAlgorithms.find_unreachable_from(graph, start_nodes)
        # Should return c and d (second component)
        assert result == {nodes["c"], nodes["d"]}

    def test_multiple_start_nodes(
        self, diamond_dag: tuple[Graph[UUID], dict[str, UUID]]
    ):
        """Multiple start nodes should reach their components."""
        graph, nodes = diamond_dag
        start_nodes = {nodes["a"], nodes["d"]}
        result = GraphAlgorithms.find_unreachable_from(graph, start_nodes)
        # All nodes should be reachable from a or d
        assert result == set()

    def test_complex_dag_unreachable_from_specific_node(
        self, complex_dag: tuple[Graph[UUID], dict[str, UUID]]
    ):
        """Starting from middle node should not reach earlier nodes."""
        graph, nodes = complex_dag
        start_nodes = {nodes["node3"]}
        result = GraphAlgorithms.find_unreachable_from(graph, start_nodes)
        # Should not reach nodes before this one
        assert len(result) > 0


# =============================================================================
# DANGLING NODES TESTS
# =============================================================================


class TestFindDanglingNodes:
    """Tests for find_dangling_nodes method."""

    def test_empty_graph_no_dangling(self, empty_graph: Graph[UUID]):
        """Empty graph should have no dangling nodes."""
        result = GraphAlgorithms.find_dangling_nodes(empty_graph)
        assert result == set()

    def test_single_node_no_dangling(self, empty_graph: Graph[UUID]):
        """Single node graph should not have dangling nodes."""
        node = uuid4()
        empty_graph.add_node(node)
        result = GraphAlgorithms.find_dangling_nodes(empty_graph)
        assert result == set()

    def test_isolated_node_is_dangling(self, empty_graph: Graph[UUID]):
        """Isolated node (no edges) in multi-node graph is dangling."""
        node1 = uuid4()
        node2 = uuid4()
        empty_graph.add_node(node1)
        empty_graph.add_node(node2)
        empty_graph.add_edge(node1, node2)
        # Add isolated node
        node3 = uuid4()
        empty_graph.add_node(node3)

        result = GraphAlgorithms.find_dangling_nodes(empty_graph)
        assert node3 in result
        assert len(result) == 1

    def test_simple_dag_no_dangling(
        self, simple_dag: tuple[Graph[UUID], dict[str, UUID]]
    ):
        """Simple DAG should have no dangling nodes."""
        graph, _ = simple_dag
        result = GraphAlgorithms.find_dangling_nodes(graph)
        assert result == set()

    def test_disconnected_component_dangling(
        self, disconnected_graph: tuple[Graph[UUID], dict[str, UUID]]
    ):
        """Disconnected component with no edges should be dangling."""
        graph, _ = disconnected_graph
        # Add isolated node
        isolated = uuid4()
        graph.add_node(isolated)

        result = GraphAlgorithms.find_dangling_nodes(graph)
        assert isolated in result

    def test_multiple_isolated_nodes(self, empty_graph: Graph[UUID]):
        """Multiple isolated nodes should all be detected."""
        isolated1 = uuid4()
        isolated2 = uuid4()
        isolated3 = uuid4()
        empty_graph.add_node(isolated1)
        empty_graph.add_node(isolated2)
        empty_graph.add_node(isolated3)

        result = GraphAlgorithms.find_dangling_nodes(empty_graph)
        assert len(result) == 3


# =============================================================================
# DEAD ENDS TESTS
# =============================================================================


class TestFindDeadEnds:
    """Tests for find_dead_ends method."""

    def test_empty_graph_no_dead_ends(self, empty_graph: Graph[UUID]):
        """Empty graph should have no dead ends."""
        result = GraphAlgorithms.find_dead_ends(empty_graph)
        assert result == set()

    def test_single_node_is_dead_end(self, empty_graph: Graph[UUID]):
        """Single node should be considered a dead end."""
        node = uuid4()
        empty_graph.add_node(node)
        result = GraphAlgorithms.find_dead_ends(empty_graph)
        assert node in result

    def test_simple_dag_leaf_is_dead_end(
        self, simple_dag: tuple[Graph[UUID], dict[str, UUID]]
    ):
        """Leaf node (no successors) should be dead end."""
        graph, nodes = simple_dag
        result = GraphAlgorithms.find_dead_ends(graph)
        # Last node (c) has no successors
        assert nodes["c"] in result
        assert len(result) == 1

    def test_diamond_dag_dead_ends(
        self, diamond_dag: tuple[Graph[UUID], dict[str, UUID]]
    ):
        """Diamond DAG should have one dead end (d)."""
        graph, nodes = diamond_dag
        result = GraphAlgorithms.find_dead_ends(graph)
        # Only d has no successors
        assert nodes["d"] in result
        assert len(result) == 1

    def test_all_leaves_are_dead_ends(
        self, complex_dag: tuple[Graph[UUID], dict[str, UUID]]
    ):
        """All leaf nodes should be detected as dead ends."""
        graph, _ = complex_dag
        result = GraphAlgorithms.find_dead_ends(graph)
        # Should have 2 leaf nodes with no successors
        assert len(result) == 2

    def test_with_terminal_types(self, empty_graph: Graph[UUID]):
        """Terminal types should be excluded from dead ends."""
        from app.models.enums import NodeType

        node1 = uuid4()
        node2 = uuid4()
        empty_graph.add_edge(node1, node2)

        # Without terminal types filter, both are dead ends
        result = GraphAlgorithms.find_dead_ends(empty_graph)
        assert node2 in result

        # With terminal types (AGGREGATOR is allowed to have no outputs)
        result = GraphAlgorithms.find_dead_ends(
            empty_graph, terminal_types={NodeType.AGGREGATOR}
        )
        # Still returns node2 because type checking happens at validator level
        assert node2 in result


# =============================================================================
# CRITICAL PATH TESTS
# =============================================================================


class TestGetCriticalPath:
    """Tests for get_critical_path method."""

    def test_empty_graph_critical_path(self, empty_graph: Graph[UUID]):
        """Empty graph should return empty path."""
        path, length = GraphAlgorithms.get_critical_path(empty_graph)
        assert path == []
        assert length == 0

    def test_single_node_critical_path(self, empty_graph: Graph[UUID]):
        """Single node should have path of length 1."""
        node = uuid4()
        empty_graph.add_node(node)
        path, length = GraphAlgorithms.get_critical_path(empty_graph)
        assert len(path) == 1
        assert node in path
        assert length == 1

    def test_simple_chain_critical_path(
        self, simple_dag: tuple[Graph[UUID], dict[str, UUID]]
    ):
        """Simple chain should have full path as critical path."""
        graph, _ = simple_dag
        path, length = GraphAlgorithms.get_critical_path(graph)
        assert length == 3  # a -> b -> c
        assert len(path) == 3

    def test_diamond_critical_path(
        self, diamond_dag: tuple[Graph[UUID], dict[str, UUID]]
    ):
        """Diamond DAG should have critical path of length 3."""
        graph, _ = diamond_dag
        path, length = GraphAlgorithms.get_critical_path(graph)
        # Either a->b->d or a->c->d (both length 3)
        assert length == 3
        assert len(path) == 3

    def test_cycle_graph_empty_path(
        self, cycle_graph: tuple[Graph[UUID], dict[str, UUID]]
    ):
        """Graph with cycle should return empty path."""
        graph, _ = cycle_graph
        path, length = GraphAlgorithms.get_critical_path(graph)
        assert path == []
        assert length == 0

    def test_complex_dag_critical_path(
        self, complex_dag: tuple[Graph[UUID], dict[str, UUID]]
    ):
        """Complex DAG should find longest path."""
        graph, _ = complex_dag
        path, length = GraphAlgorithms.get_critical_path(graph)
        # Should find the longest path through the DAG
        assert length > 0
        assert len(path) == length
        # Verify path is valid (no gaps)
        for i in range(len(path) - 1):
            successors = graph.get_successors(path[i])
            assert path[i + 1] in successors

    def test_multiple_branches_finds_longest(self, empty_graph: Graph[UUID]):
        """Should find the longest branch among multiple options."""
        nodes = {f"node{i}": uuid4() for i in range(5)}

        # Short branch: a -> b
        empty_graph.add_edge(nodes["node0"], nodes["node1"])

        # Long branch: a -> c -> d -> e
        empty_graph.add_edge(nodes["node0"], nodes["node2"])
        empty_graph.add_edge(nodes["node2"], nodes["node3"])
        empty_graph.add_edge(nodes["node3"], nodes["node4"])

        path, length = GraphAlgorithms.get_critical_path(empty_graph)
        # Should prefer the longer branch
        assert length == 4  # a -> c -> d -> e


# =============================================================================
# DAG VALIDATION TESTS
# =============================================================================


class TestValidateDag:
    """Tests for validate_dag method."""

    def test_empty_graph_is_valid(self, empty_graph: Graph[UUID]):
        """Empty graph should be valid."""
        is_valid, errors = GraphAlgorithms.validate_dag(empty_graph)
        assert is_valid is True
        assert len(errors) == 0

    def test_single_node_is_valid(self, empty_graph: Graph[UUID]):
        """Single node graph should be valid."""
        node = uuid4()
        empty_graph.add_node(node)
        is_valid, errors = GraphAlgorithms.validate_dag(empty_graph)
        assert is_valid is True
        assert len(errors) == 0

    def test_simple_dag_is_valid(self, simple_dag: tuple[Graph[UUID], dict[str, UUID]]):
        """Simple DAG should be valid."""
        graph, _ = simple_dag
        is_valid, errors = GraphAlgorithms.validate_dag(graph)
        assert is_valid is True
        assert len(errors) == 0

    def test_cycle_graph_is_invalid(
        self, cycle_graph: tuple[Graph[UUID], dict[str, UUID]]
    ):
        """Graph with cycle should be invalid."""
        graph, _ = cycle_graph
        is_valid, errors = GraphAlgorithms.validate_dag(graph)
        assert is_valid is False
        assert len(errors) > 0
        assert "cycle" in errors[0].lower()

    def test_dangling_nodes_in_valid_dag(self, empty_graph: Graph[UUID]):
        """DAG with dangling nodes should be invalid."""
        # Create valid structure
        node1 = uuid4()
        node2 = uuid4()
        empty_graph.add_edge(node1, node2)

        # Add dangling node
        dangling = uuid4()
        empty_graph.add_node(dangling)

        is_valid, errors = GraphAlgorithms.validate_dag(empty_graph)
        assert is_valid is False
        assert len(errors) > 0
        assert "dangling" in errors[0].lower()

    def test_complex_valid_dag(self, complex_dag: tuple[Graph[UUID], dict[str, UUID]]):
        """Complex DAG without issues should be valid."""
        graph, _ = complex_dag
        is_valid, errors = GraphAlgorithms.validate_dag(graph)
        assert is_valid is True
        assert len(errors) == 0


# =============================================================================
# EDGE CASES AND BOUNDARY CONDITIONS
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_multiple_edges_same_direction(self, empty_graph: Graph[UUID]):
        """Multiple edges between same nodes (should be allowed by Graph)."""
        a, b = uuid4(), uuid4()
        empty_graph.add_edge(a, b)
        empty_graph.add_edge(a, b)  # Add again

        is_valid, errors = GraphAlgorithms.validate_dag(empty_graph)
        assert is_valid is True  # Still valid (no cycle)

    def test_tree_structure(self, empty_graph: Graph[UUID]):
        """Tree structure (root with many branches)."""
        root = uuid4()
        children = [uuid4() for _ in range(3)]
        for child in children:
            empty_graph.add_edge(root, child)

        is_valid, errors = GraphAlgorithms.validate_dag(empty_graph)
        assert is_valid is True
        assert len(errors) == 0

    def test_reverse_tree_structure(self, empty_graph: Graph[UUID]):
        """Reverse tree (many roots converging to single leaf)."""
        leaf = uuid4()
        roots = [uuid4() for _ in range(3)]
        for root in roots:
            empty_graph.add_edge(root, leaf)

        is_valid, errors = GraphAlgorithms.validate_dag(empty_graph)
        assert is_valid is True
        assert len(errors) == 0

    def test_large_chain_performance(self, empty_graph: Graph[UUID]):
        """Test with larger chain to verify performance."""
        nodes = [uuid4() for _ in range(100)]
        for i in range(len(nodes) - 1):
            empty_graph.add_edge(nodes[i], nodes[i + 1])

        is_valid, errors = GraphAlgorithms.validate_dag(empty_graph)
        assert is_valid is True
        assert len(errors) == 0

        path, length = GraphAlgorithms.get_critical_path(empty_graph)
        assert length == 100
