# SPEC-011: Workflow Execution Engine - Implementation Plan

## Metadata

| Field | Value |
|-------|-------|
| SPEC ID | SPEC-011 |
| Document Type | Implementation Plan |
| Created | 2026-01-16 |
| Status | Draft |

---

## Overview

This document outlines the implementation plan for the Workflow Execution Engine. The plan is organized by priority with clear task decomposition, technical approach, and dependency mapping.

---

## Milestones

### Priority: Primary (P0)

Core DAG execution functionality required for MVP workflow execution.

| Milestone | Description |
|-----------|-------------|
| M1: Execution Context | Shared context management with variable substitution |
| M2: DAG Executor Core | Topological sort-based execution with parallel async |
| M3: Node Executors | Tool and Agent node execution with retry logic |
| M4: Error Handling | Per-node error capture and graceful degradation |
| M5: Execution Storage | Database persistence of execution records |

### Priority: Secondary (P1)

Enhanced features for production readiness.

| Milestone | Description |
|-----------|-------------|
| M6: Advanced Node Executors | Condition, Adapter, Aggregator nodes |
| M7: Scheduler Integration | APScheduler integration for scheduled workflows |
| M8: Execution API | REST API endpoints for execution control |
| M9: Execution History | Query and monitoring capabilities |

### Priority: Optional (P2)

Future enhancements.

| Milestone | Description |
|-----------|-------------|
| M10: Fallback Execution | Fallback node support on failure |
| M11: Streaming Results | Real-time execution status updates |
| M12: Distributed Execution | Multi-worker execution support |

---

## Task Breakdown

### Phase 1: Foundation (M1, M2)

#### Task 1.1: Execution Context Module

**File:** `backend/app/services/workflow/context.py`

**Subtasks:**
- [ ] Define `ExecutionContext` dataclass
- [ ] Implement `get_variable()` for dot-notation variable access
- [ ] Implement `get_node_output()` for retrieving node outputs
- [ ] Implement `set_node_output()` for storing node outputs
- [ ] Implement `substitute_variables()` for template variable substitution
- [ ] Add context isolation tests

**Dependencies:** SPEC-003 models

**Estimated Complexity:** Medium

---

#### Task 1.2: Retry Logic Module

**File:** `backend/app/services/workflow/retry.py`

**Subtasks:**
- [ ] Define `RetryConfig` dataclass
- [ ] Implement `RetryExecutor` class
- [ ] Implement exponential backoff calculation
- [ ] Implement exception type filtering
- [ ] Add retry logic unit tests

**Dependencies:** None (standalone module)

**Estimated Complexity:** Low

---

#### Task 1.3: DAG Executor Core

**File:** `backend/app/services/workflow/executor.py`

**Subtasks:**
- [ ] Define `DAGExecutor` class with constructor
- [ ] Implement `execute_workflow()` main orchestration
- [ ] Implement `_execute_level()` for parallel level execution
- [ ] Implement `_execute_with_semaphore()` for concurrency control
- [ ] Implement `_gather_inputs()` for dependency resolution
- [ ] Add integration tests with mock workflows

**Dependencies:** Task 1.1, Task 1.2, SPEC-010 (DAGValidator)

**Estimated Complexity:** High

---

### Phase 2: Node Executors (M3, M6)

#### Task 2.1: Base Node Executor

**File:** `backend/app/services/workflow/node_executors.py`

**Subtasks:**
- [ ] Define `BaseNodeExecutor` abstract class
- [ ] Define common executor interface
- [ ] Implement input preparation logic
- [ ] Add executor factory for node type routing

**Dependencies:** Task 1.1

**Estimated Complexity:** Low

---

#### Task 2.2: Tool Node Executor

**Subtasks:**
- [ ] Implement `ToolNodeExecutor` class
- [ ] Integrate with ToolRegistry from SPEC-009
- [ ] Add input validation against tool schema
- [ ] Add output validation against tool schema
- [ ] Add timeout enforcement
- [ ] Add retry integration

**Dependencies:** Task 2.1, SPEC-009 (ToolRegistry)

**Estimated Complexity:** Medium

---

#### Task 2.3: Agent Node Executor

**Subtasks:**
- [ ] Implement `AgentNodeExecutor` class
- [ ] Integrate with AgentManager from SPEC-009
- [ ] Add prompt template building
- [ ] Add LLM response parsing
- [ ] Add streaming response support (optional)

**Dependencies:** Task 2.1, SPEC-009 (AgentManager)

**Estimated Complexity:** Medium

---

#### Task 2.4: Condition Node Executor

**Subtasks:**
- [ ] Implement `ConditionNodeExecutor` class
- [ ] Add condition expression parser
- [ ] Implement safe expression evaluation
- [ ] Add branch selection logic
- [ ] Support else/default branch

**Dependencies:** Task 2.1

**Estimated Complexity:** Medium

---

#### Task 2.5: Adapter Node Executor

**Subtasks:**
- [ ] Implement `AdapterNodeExecutor` class
- [ ] Add JSON to DataFrame transformation
- [ ] Add DataFrame to JSON transformation
- [ ] Add field mapping transformation
- [ ] Add filter transformation
- [ ] Implement sandboxed code execution

**Dependencies:** Task 2.1

**Estimated Complexity:** Medium

---

#### Task 2.6: Aggregator Node Executor

**Subtasks:**
- [ ] Implement `AggregatorNodeExecutor` class
- [ ] Add merge strategy
- [ ] Add concatenate strategy
- [ ] Add numeric aggregation (sum, avg, count)
- [ ] Add custom aggregation support

**Dependencies:** Task 2.1

**Estimated Complexity:** Low

---

### Phase 3: Error Handling (M4)

#### Task 3.1: Error Capture Module

**Subtasks:**
- [ ] Define `NodeExecutionError` dataclass
- [ ] Implement error capture in node executors
- [ ] Add stack trace capture
- [ ] Add input snapshot on error
- [ ] Add error storage in context

**Dependencies:** Task 2.2, Task 2.3

**Estimated Complexity:** Low

---

#### Task 3.2: Graceful Degradation

**Subtasks:**
- [ ] Implement `on_node_failure: continue` logic
- [ ] Implement `on_node_failure: stop` logic
- [ ] Add failure threshold checking
- [ ] Add error context propagation
- [ ] Add downstream dependency handling

**Dependencies:** Task 3.1, Task 1.3

**Estimated Complexity:** Medium

---

### Phase 4: Storage Integration (M5, M9)

#### Task 4.1: Execution Models Integration

**Subtasks:**
- [ ] Create `WorkflowExecution` records on start
- [ ] Create `NodeExecution` records on node start
- [ ] Update `NodeExecution` records on completion
- [ ] Update `WorkflowExecution` records on completion
- [ ] Add execution context persistence (optional)

**Dependencies:** SPEC-005 models

**Estimated Complexity:** Medium

---

#### Task 4.2: Execution History Queries

**Subtasks:**
- [ ] Implement `get_execution_result()` query
- [ ] Implement `get_workflow_executions()` list query
- [ ] Implement `get_node_executions()` by execution
- [ ] Add pagination support
- [ ] Add filtering by status, date range

**Dependencies:** Task 4.1

**Estimated Complexity:** Low

---

### Phase 5: Scheduler Integration (M7)

#### Task 5.1: Scheduler Wrapper

**File:** `backend/app/services/workflow/scheduler.py`

**Subtasks:**
- [ ] Implement `WorkflowScheduler` class
- [ ] Integrate APScheduler
- [ ] Implement `schedule_workflow()` method
- [ ] Implement `unschedule_workflow()` method
- [ ] Add lifecycle management (start, shutdown)

**Dependencies:** Task 1.3

**Estimated Complexity:** Medium

---

#### Task 5.2: Schedule Configuration

**Subtasks:**
- [ ] Add schedule config to Workflow model
- [ ] Parse cron expressions from workflow config
- [ ] Add timezone handling
- [ ] Validate cron syntax
- [ ] Add schedule persistence

**Dependencies:** Task 5.1, SPEC-003

**Estimated Complexity:** Low

---

### Phase 6: API Layer (M8)

#### Task 6.1: Execution Schemas

**File:** `backend/app/schemas/execution.py`

**Subtasks:**
- [ ] Define `ExecutionStatus` enum
- [ ] Define `NodeExecutionStatus` enum
- [ ] Define `ExecutionResult` schema
- [ ] Define `NodeExecutionResult` schema
- [ ] Define `ExecuteWorkflowRequest` schema
- [ ] Define `ExecuteWorkflowResponse` schema

**Dependencies:** None

**Estimated Complexity:** Low

---

#### Task 6.2: Execution API Endpoints

**File:** `backend/app/api/v1/executions.py`

**Subtasks:**
- [ ] Implement `POST /workflows/{id}/execute` endpoint
- [ ] Implement `GET /executions/{id}` endpoint
- [ ] Implement `POST /executions/{id}/cancel` endpoint
- [ ] Implement `GET /workflows/{id}/executions` endpoint
- [ ] Add authentication/authorization
- [ ] Add rate limiting

**Dependencies:** Task 6.1, Task 1.3, Task 5.1

**Estimated Complexity:** Medium

---

## Technical Approach

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Execution API Layer                          │
│  POST /workflows/{id}/execute                                   │
│  GET  /executions/{id}                                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    WorkflowScheduler                            │
│  - APScheduler integration                                      │
│  - Cron-based scheduling                                        │
│  - Job management                                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       DAGExecutor                               │
│  - Topological sort from SPEC-010                               │
│  - Parallel async execution (asyncio.gather)                    │
│  - Context management                                           │
│  - Error handling                                               │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  ToolExecutor   │ │  AgentExecutor  │ │ConditionExecutor│
│  + RetryLogic   │ │  + RetryLogic   │ │AdapterExecutor  │
└─────────────────┘ └─────────────────┘ └─────────────────┘
              │               │               │
              └───────────────┼───────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   ExecutionContext                             │
│  - variables                                                   │
│  - node_outputs                                                │
│  - node_errors                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Concurrency Strategy

1. **Level-based Parallelism**: Nodes within same topological level execute in parallel
2. **Semaphore Limiting**: Configurable max parallel nodes (default: 10)
3. **Async/Await**: All operations non-blocking
4. **Exception Isolation**: `return_exceptions=True` in `asyncio.gather()`

### Error Handling Strategy

1. **Per-Node Capture**: Each node execution wraps in try/except
2. **Retry Logic**: Configurable retries with exponential backoff
3. **Degradation Mode**: Continue on failure vs. stop immediately
4. **Error Propagation**: Optional error context to downstream nodes

### Context Management

1. **Isolation**: Each execution has unique context
2. **Immutability**: Node outputs never modified after storage
3. **Variable Substitution**: Template-based `{{ variable }}` references
4. **Memory Management**: Context cleanup after execution

---

## Implementation Sequence

### Sprint 1: Foundation
- Task 1.1: Execution Context Module
- Task 1.2: Retry Logic Module
- Task 2.1: Base Node Executor

### Sprint 2: Core Execution
- Task 1.3: DAG Executor Core
- Task 2.2: Tool Node Executor
- Task 3.1: Error Capture Module

### Sprint 3: Node Executors
- Task 2.3: Agent Node Executor
- Task 2.4: Condition Node Executor
- Task 3.2: Graceful Degradation

### Sprint 4: Advanced Features
- Task 2.5: Adapter Node Executor
- Task 2.6: Aggregator Node Executor
- Task 4.1: Execution Models Integration

### Sprint 5: Scheduler & API
- Task 5.1: Scheduler Wrapper
- Task 5.2: Schedule Configuration
- Task 6.1: Execution Schemas
- Task 6.2: Execution API Endpoints

### Sprint 6: Polish
- Task 4.2: Execution History Queries
- Integration testing
- Performance optimization
- Documentation

---

## Testing Strategy

### Unit Tests

| Module | Test Coverage Target |
|--------|---------------------|
| Context | 90% |
| Retry Logic | 95% |
| DAG Executor | 85% |
| Node Executors | 80% each |

### Integration Tests

- Full workflow execution with mock tools/agents
- Error handling and retry scenarios
- Parallel execution verification
- Context isolation between executions

### End-to-End Tests

- Scheduled workflow execution
- Manual on-demand execution
- Cancellation scenarios
- Multi-execution concurrency

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Circular dependency with SPEC-010 | Use dependency injection, clear interfaces |
| ToolRegistry/AgentManager not thread-safe | Add async locks in executor |
| Memory growth with large contexts | Add size limits, periodic cleanup |
| Retry storms on API failures | Configurable backoff, max retry caps |
| Orphaned executions on shutdown | Implement graceful shutdown with cleanup |

---

## Dependencies

### Internal SPEC Dependencies

| SPEC | Dependency Type | Purpose |
|------|-----------------|---------|
| SPEC-001 | Hard | Base models, mixins |
| SPEC-003 | Hard | Workflow, Node, Edge models |
| SPEC-005 | Hard | Execution record storage |
| SPEC-009 | Hard | ToolRegistry, AgentManager |
| SPEC-010 | Hard | DAGValidator, topological sort |

### Implementation Dependencies

| Component | Required By |
|-----------|-------------|
| Execution Context | All executors |
| DAG Executor | Scheduler, API |
| Node Executors | DAG Executor |
| Retry Logic | Tool/Agent executors |

---

## Change History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-16 | workflow-spec | Initial implementation plan |
