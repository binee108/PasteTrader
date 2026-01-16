# SPEC-011: Acceptance Criteria

TAG: [SPEC-011] [WORKFLOW] [EXECUTION] [ASYNCIO] [PARALLEL]
STATUS: Planned
CREATED: 2026-01-15

## Test Scenarios

### Feature: Workflow Execution Engine (E-001)

```gherkin
Feature: DAG-based Workflow Execution
  As a workflow system
  I want to execute workflows based on DAG topological order
  So that nodes are executed in correct dependency order

  Background:
    Given a workflow with trigger -> tool -> agent nodes exists
    And all nodes are connected with edges

  Scenario: Successful linear workflow execution
    When I execute the workflow with input data {"key": "value"}
    Then the WorkflowExecution status should be COMPLETED
    And all NodeExecutions should be COMPLETED
    And the execution order should be [trigger, tool, agent]
    And the output_data should contain results from all nodes

  Scenario: Workflow with parallel nodes
    Given a workflow with trigger -> [tool_1, tool_2] -> aggregator
    When I execute the workflow
    Then tool_1 and tool_2 should execute in parallel
    And aggregator should execute after both tools complete
    And duration should be less than sequential execution

  Scenario: Workflow not found
    When I execute a workflow with non-existent ID
    Then an error should be raised
    And the error message should contain "Workflow not found"

  Scenario: Empty workflow (no nodes)
    Given a workflow with no nodes
    When I execute the workflow
    Then an error should be raised
    And the error message should contain "No nodes in workflow"
```

### Feature: ExecutionContext Data Passing (E-002)

```gherkin
Feature: ExecutionContext for Node Data Passing
  As a workflow execution engine
  I want to pass data between nodes using ExecutionContext
  So that nodes can access predecessor outputs

  Background:
    Given an ExecutionContext with workflow_execution_id
    And initial input_data {"input": "value"}

  Scenario: Store and retrieve node output
    When node_1 sets output {"result": 42}
    Then get_output(node_1) should return {"result": 42}

  Scenario: Get input from single predecessor
    Given node_1 has output {"data": "from_node_1"}
    And edge exists from node_1 to node_2
    When I call get_input for node_2
    Then the input should contain {"data": "from_node_1"}

  Scenario: Get input from multiple predecessors
    Given node_1 has output {"a": 1}
    And node_2 has output {"b": 2}
    And edges exist from node_1 and node_2 to node_3
    When I call get_input for node_3
    Then the input should contain {"a": 1, "b": 2}

  Scenario: Workflow variables are accessible in input
    Given workflow variable "api_key" is set to "secret"
    When I call get_input for any node
    Then the input should contain {"api_key": "secret"}

  Scenario: Concurrent access is thread-safe
    When 10 coroutines simultaneously call set_output
    Then all outputs should be stored correctly
    And no data corruption should occur
```

### Feature: Parallel Node Execution (E-003)

```gherkin
Feature: Parallel Node Execution with asyncio.TaskGroup
  As a workflow execution engine
  I want to execute same-level nodes in parallel
  So that workflow execution is efficient

  Background:
    Given a workflow with trigger -> [tool_1, tool_2, tool_3] -> aggregator
    And each tool node takes 100ms to execute

  Scenario: Nodes in same level execute concurrently
    When I execute the workflow
    Then tool_1, tool_2, and tool_3 should start at approximately the same time
    And total execution time should be less than 150ms (not 300ms)

  Scenario: Semaphore limits concurrent executions
    Given max_parallel_nodes is set to 2
    When I execute the workflow
    Then at most 2 tools should run simultaneously
    And execution should complete successfully

  Scenario: One node failure doesn't stop parallel nodes
    Given tool_2 is configured to fail
    When I execute the workflow
    Then tool_1 and tool_3 should still complete
    And their outputs should be stored in context
```

### Feature: Error Handling and Retry (E-004)

```gherkin
Feature: Error Handling and Exponential Backoff Retry
  As a workflow execution engine
  I want to retry failed nodes with exponential backoff
  So that transient failures are handled gracefully

  Background:
    Given a workflow with a tool node
    And retry_config is {"max_retries": 3, "delay": 1}

  Scenario: Successful retry after transient failure
    Given the tool fails on first 2 attempts
    And succeeds on 3rd attempt
    When I execute the workflow
    Then NodeExecution.retry_count should be 2
    And NodeExecution.status should be COMPLETED
    And workflow should complete successfully

  Scenario: Max retries exceeded
    Given the tool fails on all attempts
    When I execute the workflow
    Then NodeExecution.retry_count should be 3
    And NodeExecution.status should be FAILED
    And NodeExecution.error_message should contain failure reason
    And WorkflowExecution.status should be FAILED

  Scenario: Exponential backoff timing
    Given the tool fails on first 2 attempts
    When I execute the workflow
    Then retry delays should be approximately [1s, 2s, 4s]

  Scenario: Downstream nodes are blocked on failure
    Given workflow trigger -> tool_1 -> tool_2 -> tool_3
    And tool_1 fails after max retries
    When I execute the workflow
    Then tool_2 and tool_3 should be SKIPPED
    And skip reason should mention upstream failure
```

### Feature: Condition Node Branching (E-005)

```gherkin
Feature: Condition Node Evaluation and Branching
  As a workflow execution engine
  I want to evaluate conditions and follow matching branches
  So that workflows can have dynamic execution paths

  Background:
    Given a workflow with condition node
    And condition node has edges to "true" and "false" branches

  Scenario: Condition evaluates to true
    Given context variable "value" is 50
    And condition expression is "value > 30"
    When I execute the condition node
    Then only "true" branch should be followed
    And "false" branch nodes should be SKIPPED

  Scenario: Condition evaluates to false
    Given context variable "value" is 20
    And condition expression is "value > 30"
    When I execute the condition node
    Then only "false" branch should be followed
    And "true" branch nodes should be SKIPPED

  Scenario: Priority-based edge selection
    Given condition has edges with priorities [1, 2, 3]
    And multiple conditions could match
    When I execute the condition node
    Then edge with lowest priority number should be selected first

  Scenario: No matching condition (default path)
    Given condition expressions don't match any context values
    And a default edge exists
    When I execute the condition node
    Then default edge should be followed
```

### Feature: Timeout Handling (E-006)

```gherkin
Feature: Node Timeout Handling
  As a workflow execution engine
  I want to enforce node execution timeouts
  So that long-running nodes don't block workflow

  Background:
    Given a workflow with a tool node
    And timeout_seconds is set to 5

  Scenario: Node completes within timeout
    Given node execution takes 2 seconds
    When I execute the workflow
    Then NodeExecution.status should be COMPLETED
    And no timeout error should occur

  Scenario: Node exceeds timeout
    Given node execution takes 10 seconds
    When I execute the workflow
    Then NodeExecution.status should be FAILED
    And error_message should contain "timed out"
    And NodeTimeoutError should be raised

  Scenario: Custom timeout per node
    Given node_1 has timeout_seconds = 10
    And node_2 has timeout_seconds = 2
    When I execute the workflow
    Then each node should respect its own timeout
```

### Feature: Workflow Cancellation (E-007)

```gherkin
Feature: Workflow Cancellation Support
  As a workflow execution engine
  I want to cancel running workflows gracefully
  So that resources are not wasted on unwanted executions

  Background:
    Given a workflow with multiple long-running nodes

  Scenario: Cancel pending workflow
    Given WorkflowExecution is in PENDING status
    When I call cancel(execution_id)
    Then WorkflowExecution.status should be CANCELLED
    And no nodes should be executed

  Scenario: Cancel running workflow
    Given WorkflowExecution is in RUNNING status
    And some nodes are still executing
    When I call cancel(execution_id)
    Then running nodes should stop gracefully
    And pending nodes should be marked CANCELLED
    And completed nodes should remain COMPLETED
    And WorkflowExecution.status should be CANCELLED

  Scenario: Cannot cancel completed workflow
    Given WorkflowExecution is in COMPLETED status
    When I call cancel(execution_id)
    Then an error should be raised
    And error message should indicate workflow already completed
```

### Feature: ExecutionLog Integration (E-008)

```gherkin
Feature: Execution Logging
  As a workflow execution engine
  I want to log all execution events
  So that execution can be traced and debugged

  Background:
    Given a workflow with trigger -> tool -> agent

  Scenario: Workflow start and end logged
    When I execute the workflow
    Then ExecutionLog should contain INFO log for workflow start
    And ExecutionLog should contain INFO log for workflow completion
    And logs should include workflow_execution_id

  Scenario: Node execution logged
    When I execute the workflow
    Then ExecutionLog should contain INFO log for each node start
    And ExecutionLog should contain INFO log for each node completion
    And logs should include node_execution_id

  Scenario: Errors logged with ERROR level
    Given tool node is configured to fail
    When I execute the workflow
    Then ExecutionLog should contain ERROR log for failure
    And error log should include error message and stack trace

  Scenario: Retries logged with WARN level
    Given tool node fails on first attempt
    When I execute the workflow
    Then ExecutionLog should contain WARN log for retry
    And log message should include retry count
```

### Feature: State Transitions (E-009)

```gherkin
Feature: Execution State Transitions
  As a workflow execution engine
  I want to enforce correct state transitions
  So that execution state is always consistent

  Scenario: WorkflowExecution state transitions
    Given a new workflow execution
    Then initial status should be PENDING
    When execution starts
    Then status should transition to RUNNING
    When execution completes successfully
    Then status should transition to COMPLETED
    And ended_at should be set

  Scenario: WorkflowExecution failure transition
    Given a running workflow execution
    When a critical error occurs
    Then status should transition to FAILED
    And ended_at should be set
    And error_message should be populated

  Scenario: NodeExecution state transitions
    Given a new node execution
    Then initial status should be PENDING
    When node starts
    Then status should transition to RUNNING
    When node completes successfully
    Then status should transition to COMPLETED

  Scenario: Invalid state transition rejected
    Given a workflow execution in COMPLETED status
    When I try to transition to RUNNING
    Then an error should be raised
    And status should remain COMPLETED
```

### Feature: Full Workflow Execution (E-010)

```gherkin
Feature: End-to-End Workflow Execution
  As a workflow execution engine
  I want to execute complete workflows
  So that all features work together correctly

  Scenario: Complex DAG with all node types
    Given a workflow with:
      | Node Type   | Name        | Config                    |
      | trigger     | start       | manual trigger            |
      | tool        | fetch_data  | fetch market data         |
      | condition   | check_rsi   | rsi < 30 or rsi > 70      |
      | agent       | analyzer    | analyze signals           |
      | aggregator  | combine     | combine results           |
    And edges connecting all nodes appropriately
    When I execute the workflow with input {"symbol": "AAPL"}
    Then all nodes should execute in correct order
    And condition should branch correctly
    And final output should contain combined results
    And all logs should be recorded
    And duration should be measured

  Scenario: Performance under load
    Given a workflow with 50 nodes and 100 edges
    When I execute the workflow
    Then execution overhead should be less than 500ms
    And memory usage should be reasonable
    And all nodes should complete successfully
```

---

## Performance Tests

### Benchmark: Parallel Execution

```python
@pytest.mark.benchmark
async def test_parallel_execution_performance(benchmark, db_session, parallel_workflow):
    """Parallel execution should be faster than sequential."""
    executor = WorkflowExecutor(db_session)

    # Sequential execution time (simulated)
    sequential_time = len(parallel_workflow.nodes) * 0.1  # 100ms per node

    result = benchmark(
        lambda: asyncio.run(
            executor.execute(parallel_workflow.id, {})
        )
    )

    # Parallel should be significantly faster
    assert result.duration_seconds < sequential_time * 0.5
```

### Benchmark: Large Workflow

```python
@pytest.mark.benchmark
async def test_large_workflow_performance(benchmark, db_session, large_workflow):
    """Large workflow should complete within reasonable time."""
    executor = WorkflowExecutor(db_session)

    result = benchmark(
        lambda: asyncio.run(
            executor.execute(large_workflow.id, {})
        )
    )

    assert result.duration_seconds < 10  # 10 seconds for 100 nodes
```

---

## Quality Gate Criteria

### Coverage Requirements
- [ ] Line coverage >= 85%
- [ ] Branch coverage >= 80%
- [ ] All public methods have tests
- [ ] Edge cases covered

### Performance Requirements
- [ ] Parallel execution: faster than sequential
- [ ] 100 nodes: < 10s total execution
- [ ] Execution overhead: < 500ms for 50 nodes
- [ ] Memory: < 3x graph size

### Code Quality Requirements
- [ ] Zero ruff errors
- [ ] Zero basedpyright errors
- [ ] All docstrings present
- [ ] Type hints complete

---

## Verification Methods

### Unit Tests
- Test ExecutionContext operations independently
- Test WorkflowExecutor methods with mocked dependencies
- Test error handling scenarios

### Integration Tests
- Test with real database
- Test complete workflow execution flow
- Test with various workflow patterns

### Performance Tests
- Benchmark parallel execution
- Benchmark large workflows
- Profile memory usage

---

## Definition of Done

### Functional Completeness
- [ ] All scenarios in this document pass
- [ ] All error conditions are handled
- [ ] Edge cases are covered

### Documentation
- [ ] API documented with examples
- [ ] Error messages are clear
- [ ] Integration guide complete

### Integration
- [ ] Works with SPEC-010 DAG Validator
- [ ] Works with existing execution models
- [ ] No breaking changes to existing code

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-15 | workflow-spec | Initial acceptance criteria |
