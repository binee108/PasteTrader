# SPEC-010: Acceptance Criteria

TAG: [SPEC-010] [WORKFLOW] [VALIDATION] [DAG] [PARALLEL-SAFE]
STATUS: Planned
CREATED: 2025-01-14

## Test Scenarios

### Feature: Cycle Detection (E-001)

```gherkin
Feature: DAG Cycle Detection
  As a workflow system
  I want to detect cycles before adding edges
  So that workflow execution order remains deterministic

  Background:
    Given a workflow with nodes A, B, and C exists
    And edges A -> B and B -> C exist

  Scenario: Valid edge does not create cycle
    When I validate adding edge from A to C
    Then the validation should pass
    And is_valid should be true
    And issues should be empty

  Scenario: Invalid edge creates direct cycle
    When I validate adding edge from C to A
    Then the validation should fail
    And is_valid should be false
    And issues should contain "CYCLE_DETECTED"
    And the issue severity should be "error"

  Scenario: Invalid edge creates self-loop
    When I validate adding edge from B to B
    Then the validation should fail
    And is_valid should be false
    And issues should contain "SELF_LOOP"

  Scenario: Parallel paths do not create cycle
    Given an additional edge A -> C exists
    When I validate the workflow structure
    Then the validation should pass
    And no cycle should be detected

  Scenario: Complex graph with multiple paths
    Given nodes D and E exist
    And edges C -> D and C -> E exist
    And edge D -> E exists
    When I validate adding edge from E to B
    Then the validation should fail
    And issues should contain "CYCLE_DETECTED"
```

### Feature: Node Type Validation (S-001 to S-005)

```gherkin
Feature: Node Type Validation
  As a workflow system
  I want to validate node type requirements
  So that workflows have correct structure

  Scenario: Trigger node has no incoming edges
    Given a workflow with a trigger node
    And the trigger node has no incoming edges
    When I validate the nodes
    Then the validation should pass

  Scenario: Trigger node with incoming edge is invalid
    Given a workflow with a trigger node
    And the trigger node has an incoming edge
    When I validate the nodes
    Then the validation should fail
    And issues should contain error for trigger node

  Scenario: Aggregator node has sufficient inputs
    Given a workflow with an aggregator node
    And the aggregator node has 2 incoming edges
    When I validate the nodes
    Then the validation should pass

  Scenario: Aggregator node with single input is invalid
    Given a workflow with an aggregator node
    And the aggregator node has only 1 incoming edge
    When I validate the nodes
    Then the validation should fail
    And issues should contain warning for aggregator node

  Scenario: Condition node has multiple outputs
    Given a workflow with a condition node
    And the condition node has edges to "true" and "false" handles
    When I validate the nodes
    Then the validation should pass

  Scenario: Condition node with single output is invalid
    Given a workflow with a condition node
    And the condition node has only 1 outgoing edge
    When I validate the nodes
    Then the validation should fail
    And issues should contain warning for condition node

  Scenario: Tool node with valid tool_id
    Given a workflow with a tool node
    And the tool node references an existing tool
    When I validate the nodes
    Then the validation should pass

  Scenario: Tool node with invalid tool_id
    Given a workflow with a tool node
    And the tool node references a non-existent tool
    When I validate the nodes
    Then the validation should fail
    And issues should contain "INVALID_TOOL_REF"

  Scenario: Agent node with valid agent_id
    Given a workflow with an agent node
    And the agent node references an existing agent
    When I validate the nodes
    Then the validation should pass

  Scenario: Agent node with invalid agent_id
    Given a workflow with an agent node
    And the agent node references a non-existent agent
    When I validate the nodes
    Then the validation should fail
    And issues should contain "INVALID_AGENT_REF"
```

### Feature: Handle Validation (E-003)

```gherkin
Feature: Edge Handle Validation
  As a workflow system
  I want to validate edge handles
  So that connections are valid for node types

  Scenario: Valid source handle for condition node
    Given a condition node with outgoing edge
    And the edge uses source_handle "true"
    When I validate the handles
    Then the validation should pass

  Scenario: Invalid source handle for condition node
    Given a condition node with outgoing edge
    And the edge uses source_handle "invalid_handle"
    When I validate the handles
    Then the validation should fail
    And issues should contain "INVALID_HANDLE"

  Scenario: Null handles are valid for default nodes
    Given a tool node with outgoing edge
    And the edge uses null source_handle
    When I validate the handles
    Then the validation should pass

  Scenario: Custom handles for condition branches
    Given a condition node with custom branches
    And edges use handles "branch_1", "branch_2", "branch_3"
    When I validate the handles
    Then the validation should pass
```

### Feature: Structure Validation (N-001 to N-004)

```gherkin
Feature: Workflow Structure Validation
  As a workflow system
  I want to validate workflow structure
  So that workflows are complete and executable

  Scenario: Valid connected workflow
    Given a workflow with trigger -> tool -> agent
    And all nodes are connected
    When I validate the structure
    Then the validation should pass
    And no warnings should be present

  Scenario: Workflow with orphan node
    Given a workflow with trigger -> tool
    And an additional agent node with no connections
    When I validate the structure
    Then the validation should produce warning
    And issues should contain "ORPHAN_NODE"

  Scenario: Workflow with unreachable node
    Given a workflow with trigger -> tool
    And a separate chain condition -> agent
    When I validate the structure
    Then the validation should produce warning
    And issues should contain "UNREACHABLE_NODE"

  Scenario: Workflow with no trigger
    Given a workflow with tool -> agent
    And no trigger node exists
    When I validate the structure
    Then the validation should produce warning
    And issues should contain "MISSING_TRIGGER"

  Scenario: Duplicate edge detection
    Given a workflow with edge A -> B
    When I try to add another edge A -> B with same handles
    Then the validation should fail
    And issues should contain "DUPLICATE_EDGE"
```

### Feature: Data Flow Validation (E-004)

```gherkin
Feature: Data Flow Schema Validation
  As a workflow system
  I want to validate data flow compatibility
  So that nodes can process each other's output

  Scenario: Compatible schemas
    Given a source node with output_schema {"type": "object", "properties": {"value": {"type": "number"}}}
    And a target node with input_schema {"type": "object", "properties": {"value": {"type": "number"}}}
    When I validate the data flow
    Then the validation should pass

  Scenario: Incompatible schemas type mismatch
    Given a source node with output_schema {"type": "string"}
    And a target node with input_schema {"type": "number"}
    When I validate the data flow
    Then the validation should produce warning
    And issues should contain "SCHEMA_MISMATCH"

  Scenario: Null schemas are always compatible
    Given a source node with null output_schema
    And a target node with null input_schema
    When I validate the data flow
    Then the validation should pass

  Scenario: Missing required field
    Given a source node with output_schema {"type": "object", "properties": {"a": {"type": "string"}}}
    And a target node with input_schema requiring field "b"
    When I validate the data flow
    Then the validation should produce warning
    And issues should contain "SCHEMA_MISMATCH"
```

### Feature: Topological Sort (E-005)

```gherkin
Feature: Topological Sort and Execution Order
  As a workflow execution engine
  I want to get execution order
  So that I can execute nodes in correct sequence

  Scenario: Simple linear workflow
    Given a workflow trigger -> tool -> agent
    When I request execution order
    Then level 0 should contain [trigger]
    And level 1 should contain [tool]
    And level 2 should contain [agent]

  Scenario: Parallel paths
    Given a workflow with trigger -> [tool_1, tool_2] -> agent
    When I request execution order
    Then level 0 should contain [trigger]
    And level 1 should contain [tool_1, tool_2] in any order
    And level 2 should contain [agent]
    And parallel_paths should include [[tool_1, tool_2]]

  Scenario: Diamond pattern
    Given a workflow trigger -> [A, B] -> C
    And A -> C and B -> C
    When I request execution order
    Then A and B should be at same level
    And C should be at the next level

  Scenario: Complex DAG
    Given a workflow with multiple branches and merges
    When I request execution order
    Then all nodes should be included
    And parent nodes should always precede children
    And execution should be deterministic
```

### Feature: Full Validation (C-001)

```gherkin
Feature: Full Workflow Validation
  As a workflow system
  I want to run complete validation
  So that all issues are detected at once

  Scenario: Valid workflow passes all checks
    Given a complete valid workflow
    And all nodes have valid references
    And all schemas are compatible
    When I run full validation
    Then is_valid should be true
    And issues should be empty or contain only INFO level
    And execution_order should be populated
    And duration_ms should be less than 100

  Scenario: Multiple issues are all reported
    Given a workflow with cycle risk
    And orphan nodes
    And schema mismatches
    When I run full validation
    Then all issues should be reported
    And issues should be grouped by severity
    And ERROR issues should be listed first

  Scenario: Performance under load
    Given a workflow with 50 nodes and 100 edges
    When I run full validation
    Then duration_ms should be less than 100

  Scenario: Large workflow validation
    Given a workflow with 100 nodes and 200 edges
    When I run full validation
    Then duration_ms should be less than 100
    And memory usage should be reasonable
```

---

## Performance Tests

### Benchmark: Cycle Detection

```python
@pytest.mark.benchmark
async def test_cycle_detection_performance(benchmark, db_session, large_workflow):
    """Cycle detection should complete in <10ms for 100 nodes."""
    validator = DAGValidator(db_session)

    result = benchmark(
        lambda: asyncio.run(
            validator.validate_cycle(
                large_workflow.id,
                large_workflow.nodes[0].id,
                large_workflow.nodes[-1].id,
            )
        )
    )

    assert result.duration_ms < 10
```

### Benchmark: Full Validation

```python
@pytest.mark.benchmark
async def test_full_validation_performance(benchmark, db_session, large_workflow):
    """Full validation should complete in <100ms for 100 nodes."""
    validator = DAGValidator(db_session)

    result = benchmark(
        lambda: asyncio.run(validator.validate_full(large_workflow.id))
    )

    assert result.duration_ms < 100
```

---

## Quality Gate Criteria

### Coverage Requirements
- [ ] Line coverage >= 85%
- [ ] Branch coverage >= 80%
- [ ] All public methods have tests
- [ ] Edge cases covered

### Performance Requirements
- [ ] Cycle detection: <10ms (100 nodes)
- [ ] Structure validation: <50ms (100 nodes)
- [ ] Node validation: <30ms (100 nodes)
- [ ] Data flow validation: <20ms (100 nodes)
- [ ] Topological sort: <10ms (100 nodes)
- [ ] Full validation: <100ms (100 nodes)

### Code Quality Requirements
- [ ] Zero ruff errors
- [ ] Zero mypy errors
- [ ] All docstrings present
- [ ] Type hints complete

---

## Verification Methods

### Unit Tests
- Test each validation method independently
- Mock database for isolation
- Cover all error codes

### Integration Tests
- Test with real database
- Test complete validation flow
- Test with complex workflows

### Performance Tests
- Benchmark with varying workflow sizes
- Profile memory usage
- Detect performance regressions

---

## Definition of Done

### Functional Completeness
- [ ] All scenarios in this document pass
- [ ] All error codes are testable
- [ ] Edge cases are handled

### Documentation
- [ ] API documented with examples
- [ ] Error messages are clear
- [ ] Integration guide complete

### Integration
- [ ] Can be imported from app.services.workflow
- [ ] Works with existing models
- [ ] No breaking changes to existing code

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-01-14 | manager-spec | Initial acceptance criteria |
