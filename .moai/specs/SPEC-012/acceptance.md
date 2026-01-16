# SPEC-012: Node Processor Framework - Acceptance Criteria

## Tags

`[SPEC-012]` `[PROCESSOR]` `[ACCEPTANCE]`

---

## Overview

This document defines the acceptance criteria for the Node Processor Framework (SPEC-012). All criteria are written in Given-When-Then format and must pass before the SPEC is considered complete.

---

## Acceptance Criteria

### AC-012-001: BaseProcessor Lifecycle Execution

**Requirement Reference:** REQ-012-001, REQ-012-002

**Scenario: Successful processing with all lifecycle hooks**

```gherkin
Given a ToolNodeProcessor with valid configuration
And the processor is initialized with a Node and ExecutionContext
And raw inputs contain valid tool_id and parameters

When the processor.execute(raw_inputs) method is called

Then pre_process should validate and transform inputs to ToolProcessorInput model
And process should execute the core tool logic
And post_process should serialize the output to a dictionary
And the returned dictionary should contain the tool execution result
And metrics should be recorded with success=True
```

**Scenario: Processing failure triggers error handling**

```gherkin
Given an AgentNodeProcessor with retry configuration enabled
And the AgentManager returns a timeout error on first attempt
And the AgentManager succeeds on second attempt

When the processor.execute(raw_inputs) method is called

Then the processor should retry the process method
And exponential backoff should be applied between retries
And the final result should be successful
And metrics should record retry_count=1
```

---

### AC-012-002: Input Validation with Pydantic

**Requirement Reference:** REQ-012-003

**Scenario: Valid input passes validation**

```gherkin
Given a ToolNodeProcessor
And raw inputs contain:
  | field            | value          |
  | tool_id          | "price_fetcher"|
  | parameters       | {"symbol": "AAPL"} |
  | timeout_seconds  | 30             |

When pre_process is called with the raw inputs

Then a ToolProcessorInput model should be returned
And the model should have tool_id = "price_fetcher"
And the model should have parameters = {"symbol": "AAPL"}
And the model should have timeout_seconds = 30
```

**Scenario: Invalid input raises validation error**

```gherkin
Given a ToolNodeProcessor
And raw inputs contain:
  | field            | value   |
  | tool_id          | ""      |
  | timeout_seconds  | -1      |

When pre_process is called with the raw inputs

Then a ProcessorValidationError should be raised
And the error should contain field-level validation messages
And the error.processor should be "ToolNodeProcessor"
```

---

### AC-012-003: Retry Logic with Exponential Backoff

**Requirement Reference:** REQ-012-005, REQ-012-010

**Scenario: Retry on transient error with backoff**

```gherkin
Given a processor with retry configuration:
  | setting                 | value              |
  | retry_enabled           | True               |
  | max_retries             | 3                  |
  | initial_delay_seconds   | 1.0                |
  | backoff_multiplier      | 2.0                |
  | retry_on_exceptions     | [TimeoutError]     |

And the process method raises TimeoutError on attempts 1 and 2
And the process method succeeds on attempt 3

When processor.execute(inputs) is called

Then attempt 1 should fail with TimeoutError
And there should be a 1.0 second delay before attempt 2
And attempt 2 should fail with TimeoutError
And there should be a 2.0 second delay before attempt 3
And attempt 3 should succeed
And metrics should show retry_count = 2
```

**Scenario: No retry on validation errors**

```gherkin
Given a processor with retry_enabled = True
And the pre_process method raises ProcessorValidationError

When processor.execute(invalid_inputs) is called

Then ProcessorValidationError should be raised immediately
And no retry attempts should be made
And metrics should show retry_count = 0
```

**Scenario: Max retries exceeded**

```gherkin
Given a processor with max_retries = 3
And the process method always raises ConnectionError

When processor.execute(inputs) is called

Then 4 total attempts should be made (initial + 3 retries)
And ProcessorExecutionError should be raised
And error.retry_count should equal 3
And metrics should show success = False
```

---

### AC-012-004: ProcessorRegistry Operations

**Requirement Reference:** REQ-012-016, REQ-012-017

**Scenario: Registry returns correct processor type**

```gherkin
Given a ProcessorRegistry with default registrations

When registry.get("tool") is called

Then ToolNodeProcessor class should be returned

When registry.get("agent") is called

Then AgentNodeProcessor class should be returned

When registry.get("condition") is called

Then ConditionNodeProcessor class should be returned
```

**Scenario: Registry creates processor instance**

```gherkin
Given a ProcessorRegistry with default registrations
And a Node with type = "tool"
And an ExecutionContext

When registry.create("tool", node, context) is called

Then a ToolNodeProcessor instance should be returned
And instance.node should equal the provided node
And instance.context should equal the provided context
```

**Scenario: Registry raises error for unknown type**

```gherkin
Given a ProcessorRegistry with default registrations

When registry.get("unknown_type") is called

Then ProcessorNotFoundError should be raised
And the error message should include "unknown_type"
```

---

### AC-012-005: Metrics Collection

**Requirement Reference:** REQ-012-008, REQ-012-009

**Scenario: Metrics recorded for successful processing**

```gherkin
Given a ToolNodeProcessor with config.collect_metrics = True
And an ExecutionContext with execution_id = "exec-123"

When processor.execute(valid_inputs) is called successfully

Then MetricsCollector should contain one ProcessorMetrics record
And metrics.execution_id should equal "exec-123"
And metrics.processor_type should equal "ToolNodeProcessor"
And metrics.success should equal True
And metrics.pre_process_duration_ms should be > 0
And metrics.process_duration_ms should be > 0
And metrics.post_process_duration_ms should be > 0
And metrics.total_duration_ms should equal sum of phase durations
```

**Scenario: Metrics summary aggregation**

```gherkin
Given a MetricsCollector with recorded metrics for execution "exec-123":
  | processor_type | success | duration_ms |
  | ToolNodeProcessor    | True    | 100         |
  | AgentNodeProcessor   | True    | 500         |
  | ToolNodeProcessor    | False   | 50          |

When collector.get_summary("exec-123") is called

Then summary.total_processors should equal 3
And summary.success_count should equal 2
And summary.failure_count should equal 1
And summary.success_rate should equal 0.666...
And summary.by_processor_type["ToolNodeProcessor"].count should equal 2
And summary.by_processor_type["AgentNodeProcessor"].count should equal 1
```

---

### AC-012-006: ToolNodeProcessor

**Requirement Reference:** REQ-012-010

**Scenario: Tool execution with valid parameters**

```gherkin
Given a ToolNodeProcessor
And ToolRegistry contains a tool with id = "price_fetcher"
And the tool expects parameters {"symbol": str}

When processor.execute({
  "tool_id": "price_fetcher",
  "parameters": {"symbol": "AAPL"},
  "timeout_seconds": 30
}) is called

Then the tool should be retrieved from ToolRegistry
And tool.execute should be called with {"symbol": "AAPL"}
And the output should contain the tool's result
And execution_duration_ms should be recorded
```

---

### AC-012-007: ConditionNodeProcessor

**Requirement Reference:** REQ-012-012

**Scenario: Condition evaluation selects correct branch**

```gherkin
Given a ConditionNodeProcessor
And conditions:
  | name       | expression      | target_node    |
  | oversold   | rsi < 30        | buy_analyzer   |
  | overbought | rsi > 70        | sell_analyzer  |
  | neutral    | else            | hold_analyzer  |

And evaluation_context contains {"rsi": 25}

When processor.execute(inputs) is called

Then selected_branch should equal "oversold"
And target_node should equal "buy_analyzer"
And evaluated_conditions should show which conditions were checked
```

**Scenario: Condition defaults to else branch**

```gherkin
Given a ConditionNodeProcessor with same conditions as above
And evaluation_context contains {"rsi": 50}

When processor.execute(inputs) is called

Then selected_branch should equal "neutral"
And target_node should equal "hold_analyzer"
```

---

### AC-012-008: AggregatorNodeProcessor

**Requirement Reference:** REQ-012-015

**Scenario: Merge strategy combines outputs**

```gherkin
Given an AggregatorNodeProcessor
And input_sources:
  | source_node | output           |
  | node_a      | {"price": 100}   |
  | node_b      | {"volume": 5000} |

And strategy = "merge"

When processor.execute(inputs) is called

Then aggregated_result should equal {"price": 100, "volume": 5000}
And source_count should equal 2
And strategy_used should equal "merge"
```

**Scenario: List strategy collects outputs**

```gherkin
Given an AggregatorNodeProcessor
And input_sources:
  | source_node | output           |
  | node_a      | {"price": 100}   |
  | node_b      | {"price": 200}   |

And strategy = "list"

When processor.execute(inputs) is called

Then aggregated_result should equal [{"price": 100}, {"price": 200}]
And source_count should equal 2
```

---

### AC-012-009: Context Propagation

**Requirement Reference:** REQ-012-018, REQ-012-019

**Scenario: Processor accesses context variables**

```gherkin
Given a processor initialized with ExecutionContext
And context.variables contains {"rsi_threshold": 30}

When processor.get_variable("rsi_threshold") is called

Then the returned value should equal 30
```

**Scenario: Processor accesses upstream node output**

```gherkin
Given a processor initialized with ExecutionContext
And context.node_outputs contains:
  | node_id   | outputs              |
  | fetcher_1 | {"price": 150.5}     |

When processor.get_node_output("fetcher_1", "price") is called

Then the returned value should equal 150.5
```

---

### AC-012-010: Error Hierarchy

**Requirement Reference:** REQ-012-006, REQ-012-007

**Scenario: Validation error contains field details**

```gherkin
Given a ProcessorValidationError created with:
  | processor           | errors                                    |
  | ToolNodeProcessor   | [{"loc": ["tool_id"], "msg": "required"}] |

When str(error) is called

Then the message should contain "ToolNodeProcessor"
And the message should contain validation error details
```

**Scenario: Execution error contains retry information**

```gherkin
Given a ProcessorExecutionError created with:
  | processor         | node_id    | message      | retry_count |
  | AgentNodeProcessor| node-123   | API timeout  | 3           |

When str(error) is called

Then the message should contain "AgentNodeProcessor"
And the message should contain "node-123"
And the message should contain "retries: 3"
```

---

## Quality Gates

### Code Quality

- [ ] All processor classes have complete type hints
- [ ] All public methods have docstrings with TAG comments
- [ ] No linter warnings from ruff
- [ ] Type checking passes with mypy

### Test Coverage

- [ ] Unit test coverage >= 85% for processor module
- [ ] All acceptance scenarios have corresponding tests
- [ ] Integration tests for ProcessorRegistry
- [ ] Retry logic tested with mocked delays

### Performance

- [ ] Pre-process validation completes in < 10ms
- [ ] Metrics collection overhead < 1ms per invocation
- [ ] ProcessorRegistry lookup is O(1)

### Documentation

- [ ] All error types documented with examples
- [ ] ProcessorRegistry usage documented
- [ ] Integration with SPEC-011 documented

---

## Definition of Done

1. All acceptance criteria scenarios pass
2. Test coverage meets quality gate (>= 85%)
3. No critical or high-severity issues open
4. Code review completed and approved
5. Integration with SPEC-011 verified
6. Documentation complete

---

## Related Documents

- [SPEC-012 Specification](spec.md)
- [SPEC-012 Implementation Plan](plan.md)
- [SPEC-011 Workflow Execution Engine](../SPEC-011/spec.md)

---

## HISTORY

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-16 | binee | Initial acceptance criteria |
