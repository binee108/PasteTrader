# SPEC-012: Node Processor Framework - Implementation Plan

## Tags

`[SPEC-012]` `[PROCESSOR]` `[PLAN]`

---

## Overview

This document outlines the implementation plan for the Node Processor Framework defined in SPEC-012. The framework provides the processing abstraction layer for workflow nodes with lifecycle hooks, validation, error handling, and metrics collection.

---

## Task Decomposition

### Milestone 1: Core Infrastructure (Primary Goal)

#### Task 1.1: Create Processor Directory Structure

**Priority:** P0 (Critical)

Create the directory structure for processor modules:

```
backend/app/services/workflow/processors/
├── __init__.py           # ProcessorRegistry, exports
├── base.py               # BaseProcessor, ProcessorConfig
├── errors.py             # Processor exceptions
├── metrics.py            # ProcessorMetrics, MetricsCollector
├── tool.py               # ToolNodeProcessor
├── agent.py              # AgentNodeProcessor
├── condition.py          # ConditionNodeProcessor
├── adapter.py            # AdapterNodeProcessor
├── trigger.py            # TriggerNodeProcessor
└── aggregator.py         # AggregatorNodeProcessor
```

**Dependencies:** None
**Verification:** Directory structure exists with empty `__init__.py` files

---

#### Task 1.2: Implement Processor Errors Module

**Priority:** P0 (Critical)

Implement custom exceptions for processor error handling:

- `ProcessorError` (base)
- `ProcessorValidationError` (input/output validation failures)
- `ProcessorExecutionError` (processing failures after retries)
- `ProcessorTimeoutError` (timeout exceeded)
- `ProcessorConfigurationError` (invalid configuration)
- `ProcessorNotFoundError` (registry lookup failure)

**Dependencies:** Task 1.1
**Verification:** All exception classes properly inherit and have meaningful `__str__`

---

#### Task 1.3: Implement Metrics Collection Module

**Priority:** P0 (Critical)

Implement metrics collection infrastructure:

- `ProcessorMetrics` dataclass with timing, status, and resource fields
- `MetricsCollector` with thread-safe recording and querying
- Summary aggregation by execution_id and processor_type
- Cleanup mechanism for memory management

**Dependencies:** Task 1.1
**Verification:** Thread-safe metrics recording confirmed with concurrent tests

---

#### Task 1.4: Implement BaseProcessor Abstract Class

**Priority:** P0 (Critical)

Implement the abstract base class with:

- Generic type parameters `InputT` and `OutputT`
- Lifecycle hooks (`pre_process`, `process`, `post_process`)
- `execute()` method orchestrating the lifecycle
- Retry logic with exponential backoff
- Metrics integration
- Context access helper methods

**Dependencies:** Tasks 1.2, 1.3
**Verification:** Abstract class properly enforces interface contract

---

#### Task 1.5: Implement ProcessorRegistry

**Priority:** P0 (Critical)

Implement the processor registry:

- Registration of processor classes by node type
- Lookup and instantiation methods
- Default processor registration on initialization
- Module-level singleton accessor

**Dependencies:** Task 1.4
**Verification:** Registry correctly creates processor instances

---

### Milestone 2: Processor Implementations (Secondary Goal)

#### Task 2.1: Create Processor Schema Definitions

**Priority:** P1 (High)

Create Pydantic schemas in `schemas/processors.py`:

- `ToolProcessorInput` / `ToolProcessorOutput`
- `AgentProcessorInput` / `AgentProcessorOutput`
- `ConditionProcessorInput` / `ConditionProcessorOutput`
- `AdapterProcessorInput` / `AdapterProcessorOutput`
- `TriggerProcessorInput` / `TriggerProcessorOutput`
- `AggregatorProcessorInput` / `AggregatorProcessorOutput`

**Dependencies:** Task 1.4
**Verification:** All schemas validate correctly with test data

---

#### Task 2.2: Implement ToolNodeProcessor

**Priority:** P1 (High)

Implement tool node processing:

- Validate tool_id exists in ToolRegistry
- Validate parameters against tool's input schema
- Execute tool with timeout enforcement
- Capture execution metrics

**Dependencies:** Tasks 1.4, 2.1, SPEC-009
**Verification:** Tool execution with validation and error handling works

---

#### Task 2.3: Implement AgentNodeProcessor

**Priority:** P1 (High)

Implement agent node processing:

- Retrieve agent from AgentManager
- Build prompt with variable substitution
- Execute agent with LLM provider
- Parse structured output if schema defined

**Dependencies:** Tasks 1.4, 2.1, SPEC-009
**Verification:** Agent execution with prompt building works

---

#### Task 2.4: Implement ConditionNodeProcessor

**Priority:** P1 (High)

Implement condition evaluation:

- Parse condition expressions safely
- Evaluate conditions with input data
- Determine target branch
- Return evaluated conditions for debugging

**Dependencies:** Tasks 1.4, 2.1
**Verification:** Condition evaluation routes correctly

---

#### Task 2.5: Implement AdapterNodeProcessor

**Priority:** P1 (High)

Implement data transformation:

- Support `field_mapping` transformation
- Support `type_conversion` transformation
- Support `filtering` transformation
- Support `aggregation` transformation

**Dependencies:** Tasks 1.4, 2.1
**Verification:** Data transformations produce expected outputs

---

#### Task 2.6: Implement TriggerNodeProcessor

**Priority:** P1 (High)

Implement trigger processing:

- Handle schedule triggers
- Handle webhook triggers
- Handle manual triggers
- Initialize context variables

**Dependencies:** Tasks 1.4, 2.1
**Verification:** Trigger types initialize context correctly

---

#### Task 2.7: Implement AggregatorNodeProcessor

**Priority:** P1 (High)

Implement output aggregation:

- Support `merge` strategy
- Support `list` strategy
- Support `reduce` strategy
- Track source count in output

**Dependencies:** Tasks 1.4, 2.1
**Verification:** Aggregation strategies combine inputs correctly

---

### Milestone 3: Integration (Final Goal)

#### Task 3.1: Integration with SPEC-011 ExecutionContext

**Priority:** P2 (Medium)

Integrate processors with execution layer:

- Inject ExecutionContext into processor initialization
- Update context after successful processing
- Propagate processor errors to execution layer

**Dependencies:** Tasks 1.4, 2.x, SPEC-011
**Verification:** Processors work within execution flow

---

#### Task 3.2: Integration with SPEC-009 Tool/Agent Services

**Priority:** P2 (Medium)

Connect processors to existing services:

- ToolNodeProcessor uses ToolRegistry from SPEC-009
- AgentNodeProcessor uses AgentManager from SPEC-009
- Handle service unavailability gracefully

**Dependencies:** Tasks 2.2, 2.3, SPEC-009
**Verification:** Processors correctly invoke external services

---

#### Task 3.3: Add Processor Tests

**Priority:** P2 (Medium)

Create comprehensive test suite:

- Unit tests for each processor type
- Integration tests for ProcessorRegistry
- Error handling tests
- Metrics collection tests
- Retry logic tests

**Dependencies:** Tasks 1.x, 2.x
**Verification:** Test coverage >= 85% for processor module

---

### Milestone 4: Documentation & Polish (Optional Goal)

#### Task 4.1: Add Docstrings and Type Hints

**Priority:** P3 (Low)

Ensure all public methods have:

- Comprehensive docstrings with examples
- Complete type hints
- TAG comments for traceability

**Dependencies:** All previous tasks
**Verification:** Documentation coverage complete

---

#### Task 4.2: Performance Optimization

**Priority:** P3 (Low)

Optimize critical paths:

- Schema caching for repeated validation
- Metrics collection sampling for high-frequency use
- Registry lookup optimization

**Dependencies:** Task 3.3
**Verification:** Performance benchmarks meet constraints

---

## Technical Approach

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Processor Layer (SPEC-012)                   │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                   ProcessorRegistry                        │ │
│  │  - register(node_type, processor_class)                   │ │
│  │  - create(node_type, node, context) -> BaseProcessor      │ │
│  └───────────────────────────────────────────────────────────┘ │
│                            │                                    │
│                            ▼                                    │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                    BaseProcessor<I, O>                     │ │
│  │  + pre_process(inputs) -> InputT                          │ │
│  │  + process(validated) -> OutputT                          │ │
│  │  + post_process(output) -> dict                           │ │
│  │  + execute(raw_inputs) -> dict                            │ │
│  └───────────────────────────────────────────────────────────┘ │
│            │         │         │         │         │           │
│            ▼         ▼         ▼         ▼         ▼           │
│  ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐  │
│  │ Tool  │ │ Agent │ │Condit.│ │Adapter│ │Trigger│ │Aggreg.│  │
│  │Proces.│ │Proces.│ │Proces.│ │Proces.│ │Proces.│ │Proces.│  │
│  └───────┘ └───────┘ └───────┘ └───────┘ └───────┘ └───────┘  │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Execution Layer (SPEC-011)                     │
│  DAGExecutor, ExecutionContext, BaseNodeExecutor               │
└─────────────────────────────────────────────────────────────────┘
```

### Processing Flow

```
raw_inputs (dict)
       │
       ▼
┌──────────────────┐
│   pre_process()  │  ← Validation + Type Conversion
│   InputT model   │
└──────────────────┘
       │
       ▼
┌──────────────────┐
│    process()     │  ← Core Logic + Retry
│   OutputT model  │
└──────────────────┘
       │
       ▼
┌──────────────────┐
│  post_process()  │  ← Serialization
│   dict output    │
└──────────────────┘
       │
       ▼
context.set_node_output()
```

### Error Handling Strategy

1. **Validation Errors**: Never retried, immediately propagated
2. **Timeout Errors**: Retried according to configuration
3. **Connection Errors**: Retried with exponential backoff
4. **Configuration Errors**: Fail-fast, no retry

### Metrics Strategy

1. **Collection**: Record every invocation with timing breakdown
2. **Storage**: In-memory with periodic cleanup
3. **Aggregation**: Summary statistics per execution
4. **Export**: Available via MetricsCollector API

---

## Risk Mitigation

| Risk | Mitigation Strategy |
|------|---------------------|
| Validation overhead | Cache compiled schemas, benchmark hot paths |
| Memory leaks | Implement max metrics limit, periodic cleanup |
| Retry storms | Global retry budget, circuit breaker pattern |
| Type confusion | Strong typing, comprehensive tests |

---

## Dependencies

### Upstream Dependencies (Must Complete First)

- **SPEC-001**: Base models (UUIDMixin, TimestampMixin)
- **SPEC-003**: Node model definition
- **SPEC-009**: ToolRegistry, AgentManager (for integration)
- **SPEC-011**: ExecutionContext (for integration)

### Downstream Consumers

- **SPEC-011**: DAGExecutor will use processors via registry
- Future SPECs: Any new node types will implement BaseProcessor

---

## Testing Strategy

### Unit Tests

- Each processor type with valid/invalid inputs
- ProcessorRegistry registration and lookup
- Error class instantiation and string representation
- MetricsCollector thread-safety

### Integration Tests

- Full processor lifecycle with mock context
- Registry with all default processors
- Metrics aggregation across multiple processors

### Performance Tests

- Validation latency benchmarks
- Metrics collection overhead
- Concurrent processor execution

---

## Related Documents

- [SPEC-012 Specification](spec.md)
- [SPEC-012 Acceptance Criteria](acceptance.md)
- [SPEC-011 Workflow Execution Engine](../SPEC-011/spec.md)
- [SPEC-009 Tool/Agent API](../SPEC-009/spec.md)

---

## HISTORY

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-16 | binee | Initial plan creation |
