# SPEC-011: Workflow Execution Engine - Acceptance Criteria

## Metadata

| Field | Value |
|-------|-------|
| SPEC ID | SPEC-011 |
| Document Type | Acceptance Criteria |
| Created | 2026-01-16 |
| Status | Draft |

---

## Overview

This document defines the acceptance criteria for the Workflow Execution Engine. All criteria are written in Given-When-Then (Gherkin) format and must be verified before the SPEC can be marked as completed.

---

## Quality Gates

### TRUST 5 Compliance

| Pillar | Criteria | Status |
|--------|----------|--------|
| **Test-first** | Minimum 85% test coverage | [ ] Pending |
| **Readable** | Ruff linting passes with no warnings | [ ] Pending |
| **Unified** | Black formatting applied | [ ] Pending |
| **Secured** | No SQL injection, input validation on all inputs | [ ] Pending |
| **Trackable** | All requirements have traceability tags | [ ] Pending |

---

## Test Scenarios

### Scenario Group 1: DAG Execution Order

#### Scenario 1.1: Sequential Execution

**Given** a workflow with 3 nodes in sequence (A -> B -> C)
**When** the workflow is executed
**Then** nodes execute in order A, then B, then C
**And** each node waits for previous node completion before starting

**Tags:** `[SPEC-011]` `[REQ-011-001]` `[EXEC]` `[ORDER]`

---

#### Scenario 1.2: Parallel Execution

**Given** a workflow with 2 parallel nodes at same level (A -> [B, C] -> D)
**When** the workflow is executed
**Then** B and C execute concurrently after A completes
**And** D waits for both B and C to complete before starting

**Tags:** `[SPEC-011]` `[REQ-011-001]` `[REQ-011-002]` `[EXEC]` `[PARALLEL]`

---

#### Scenario 1.3: Dependency Resolution

**Given** a node C depends on outputs from nodes A and B
**When** node C executes
**Then** node C has access to outputs from both A and B
**And** execution fails if either A or B fails

**Tags:** `[SPEC-011]` `[REQ-011-003]` `[EXEC]` `[DEPENDENCY]`

---

### Scenario Group 2: Execution State Management

#### Scenario 2.1: State Transitions

**Given** a node in PENDING state
**When** the node starts execution
**Then** state transitions to RUNNING
**When** execution completes successfully
**Then** state transitions to COMPLETED

**Tags:** `[SPEC-011]` `[REQ-011-004]` `[STATE]`

---

#### Scenario 2.2: Failure State

**Given** a node in RUNNING state
**When** execution fails
**Then** state transitions to FAILED
**And** error information is captured

**Tags:** `[SPEC-011]` `[REQ-011-004]` `[REQ-011-005]` `[STATE]` `[ERROR]`

---

#### Scenario 2.3: Skip State

**Given** a node with failed dependency
**When** graceful degradation is disabled
**Then** node state transitions to SKIPPED
**And** node is not executed

**Tags:** `[SPEC-011]` `[REQ-011-004]` `[STATE]` `[SKIP]`

---

### Scenario Group 3: Error Handling

#### Scenario 3.1: Per-Node Error Capture

**Given** a node that fails with exception
**When** the failure occurs
**Then** exception type is captured
**And** exception message is captured
**And** stack trace is captured
**And** node inputs at failure time are captured

**Tags:** `[SPEC-011]` `[REQ-011-005]` `[ERROR]` `[CAPTURE]`

---

#### Scenario 3.2: Stop on Failure

**Given** a workflow with `on_node_failure: stop`
**When** any node fails
**Then** workflow execution halts immediately
**And** remaining nodes are not executed
**And** workflow status is FAILED

**Tags:** `[SPEC-011]` `[REQ-011-006]` `[ERROR]` `[STOP]`

---

#### Scenario 3.3: Continue on Failure

**Given** a workflow with `on_node_failure: continue`
**When** a node fails
**Then** workflow execution continues
**And** dependent nodes are skipped
**And** independent nodes execute normally
**And** workflow status is PARTIAL

**Tags:** `[SPEC-011]` `[REQ-011-006]` `[ERROR]` `[CONTINUE]`

---

#### Scenario 3.4: Error Context Propagation

**Given** a node A that fails
**And** a dependent node B with error handling
**When** node B executes
**Then** node B can access error from node A via `{{ errors.node_a }}`
**And** node B can execute conditional logic based on error

**Tags:** `[SPEC-011]` `[REQ-011-007]` `[ERROR]` `[PROPAGATION]`

---

### Scenario Group 4: Retry Logic

#### Scenario 4.1: Successful Retry

**Given** a node with `max_retries: 3`
**And** the node fails on first attempt
**And** the node succeeds on second attempt
**When** the node executes
**Then** execution is marked as COMPLETED
**And** retry_count is 1

**Tags:** `[SPEC-011]` `[REQ-011-009]` `[RETRY]` `[SUCCESS]`

---

#### Scenario 4.2: Exhausted Retries

**Given** a node with `max_retries: 3`
**And** the node fails on all attempts
**When** the node executes
**Then** execution is marked as FAILED
**And** retry_count is 3
**And** no further retries are attempted

**Tags:** `[SPEC-011]` `[REQ-011-009]` `[REQ-011-012]` `[RETRY]` `[EXHAUSTED]`

---

#### Scenario 4.3: Exponential Backoff

**Given** a node with `initial_delay: 1`, `backoff_multiplier: 2`
**When** the node fails and retries
**Then** first retry waits ~1 second
**And** second retry waits ~2 seconds
**And** third retry waits ~4 seconds

**Tags:** `[SPEC-011]` `[REQ-011-010]` `[RETRY]` `[BACKOFF]`

---

#### Scenario 4.4: Conditional Retry

**Given** a node with `retry_on: ["TimeoutError", "ConnectionError"]`
**When** the node fails with `ValueError`
**Then** no retry is attempted
**And** node is marked as FAILED immediately

**Tags:** `[SPEC-011]` `[REQ-011-011]` `[RETRY]` `[CONDITIONAL]`

---

### Scenario Group 5: Execution Context

#### Scenario 5.1: Variable Substitution

**Given** a workflow with variable `rsi_period: 14`
**And** a node config containing `{{ variables.rsi_period }}`
**When** the node executes
**Then** the variable reference is replaced with `14`
**And** the node receives the substituted value

**Tags:** `[SPEC-011]` `[REQ-011-015]` `[CONTEXT]` `[VARIABLE]`

---

#### Scenario 5.2: Node Output Reference

**Given** a node A that outputs `{"symbol": "AAPL"}`
**And** a node B config containing `{{ nodes.node-a.outputs.symbol }}`
**When** node B executes
**Then** the reference is replaced with `"AAPL"`
**And** node B receives the substituted value

**Tags:** `[SPEC-011]` `[REQ-011-015]` `[CONTEXT]` `[REFERENCE]`

---

#### Scenario 5.3: Context Isolation

**Given** two concurrent executions of the same workflow
**And** execution 1 sets a context variable
**When** execution 2 runs
**Then** execution 2 does not see execution 1's context variables
**And** executions are fully isolated

**Tags:** `[SPEC-011]` `[REQ-011-016]` `[CONTEXT]` `[ISOLATION]`

---

#### Scenario 5.4: Output Storage

**Given** a node that completes successfully
**When** the node outputs `{"result": "success"}`
**Then** the output is stored in `context.node_outputs[node_id]`
**And** the output is retrievable by dependent nodes

**Tags:** `[SPEC-011]` `[REQ-011-014]` `[CONTEXT]` `[STORAGE]`

---

### Scenario Group 6: Node Execution

#### Scenario 6.1: Tool Node Execution

**Given** a tool node with `tool_id: price_fetcher`
**And** the tool is registered in ToolRegistry
**When** the node executes
**Then** ToolRegistry.get() is called with the tool_id
**And** the tool's execute() method is called with validated inputs
**And** outputs are stored in context

**Tags:** `[SPEC-011]` `[REQ-011-017]` `[NODE]` `[TOOL]`

---

#### Scenario 6.2: Agent Node Execution

**Given** an agent node with `agent_id: analyzer`
**And** the agent is registered in AgentManager
**When** the node executes
**Then** AgentManager.get() is called with the agent_id
**And** the agent's execute() method is called
**And** LLM response is parsed and stored

**Tags:** `[SPEC-011]` `[REQ-011-018]` `[NODE]` `[AGENT]`

---

#### Scenario 6.3: Condition Node Evaluation

**Given** a condition node with conditions:
```
- rsi < 30 → oversold branch
- rsi > 70 → overbought branch
- else → neutral branch
```
**And** input rsi = 25
**When** the node evaluates
**Then** the oversold branch is selected
**And** output contains `selected_branch: oversold`

**Tags:** `[SPEC-011]` `[REQ-011-019]` `[NODE]` `[CONDITION]`

---

#### Scenario 6.4: Adapter Node Transformation

**Given** an adapter node with transformation type `json_to_dataframe`
**And** input is a list of JSON objects
**When** the node executes
**Then** the input is converted to DataFrame format
**And** the DataFrame is converted back to JSON-serializable output

**Tags:** `[SPEC-011]` `[REQ-011-020]` `[NODE]` `[ADAPTER]`

---

#### Scenario 6.5: Aggregator Node Collection

**Given** an aggregator node with strategy `merge`
**And** inputs from 3 nodes with outputs `[A1, A2]`, `[B1]`, `[C1, C2, C3]`
**When** the node executes
**Then** outputs are merged into `[A1, A2, B1, C1, C2, C3]`
**And** the merged result is stored as output

**Tags:** `[SPEC-011]` `[REQ-011-021]` `[NODE]` `[AGGREGATOR]`

---

### Scenario Group 7: Scheduler Integration

#### Scenario 7.1: Cron-Based Scheduling

**Given** a workflow with schedule `cron: "30 9 * * 1-5"`
**When** the scheduler processes the schedule
**Then** the workflow is registered with APScheduler
**And** the workflow executes at 9:30 AM on weekdays

**Tags:** `[SPEC-011]` `[REQ-011-022]` `[REQ-011-023]` `[SCHEDULER]` `[CRON]`

---

#### Scenario 7.2: Manual Execution

**Given** a workflow configured for scheduled execution
**When** a manual execution request is received via API
**Then** the workflow executes immediately
**And** the schedule is not affected

**Tags:** `[SPEC-011]` `[REQ-011-024]` `[SCHEDULER]` `[MANUAL]`

---

#### Scenario 7.3: Scheduler Lifecycle

**Given** a running WorkflowScheduler
**When** shutdown() is called
**Then** all scheduled jobs are halted
**And** running executions complete before shutdown

**Tags:** `[SPEC-011]` `[REQ-011-022]` `[SCHEDULER]` `[LIFECYCLE]`

---

### Scenario Group 8: Execution History

#### Scenario 8.1: Execution Record Creation

**Given** a workflow execution starts
**When** execution begins
**Then** a WorkflowExecution record is created
**And** execution_id is generated
**And** status is RUNNING
**And** started_at is set

**Tags:** `[SPEC-011]` `[REQ-011-025]` `[HISTORY]` `[CREATE]`

---

#### Scenario 8.2: Node Execution Tracking

**Given** a workflow with 5 nodes
**When** the workflow executes
**Then** a NodeExecution record is created for each node
**And** each record tracks node_id, status, started_at, completed_at

**Tags:** `[SPEC-011]` `[REQ-011-025]` `[HISTORY]` `[NODE]`

---

#### Scenario 8.3: Execution Completion

**Given** a workflow execution in RUNNING state
**When** all nodes complete
**Then** WorkflowExecution status is COMPLETED
**And** completed_at is set
**And** final outputs are stored
**And** duration_ms is calculated

**Tags:** `[SPEC-011]` `[REQ-011-025]` `[HISTORY]` `[COMPLETE]`

---

#### Scenario 8.4: Execution Query

**Given** multiple workflow executions
**When** querying executions by workflow_id
**Then** all executions for that workflow are returned
**And** results are ordered by started_at DESC
**And** pagination is supported

**Tags:** `[SPEC-011]` `[REQ-011-025]` `[HISTORY]` `[QUERY]`

---

### Scenario Group 9: API Endpoints

#### Scenario 9.1: Execute Workflow API

**Given** an authenticated user
**And** a workflow ID
**When** POST /api/v1/executions/workflows/{id} is called
**Then** response status is 202 Accepted
**And** response contains execution_id
**And** workflow executes in background
**And** response status is "running"

**Tags:** `[SPEC-011]` `[API]` `[EXECUTE]`

---

#### Scenario 9.2: Get Execution Status API

**Given** a running workflow execution
**When** GET /api/v1/executions/{execution_id} is called
**Then** response contains current status
**And** response contains node results
**And** response contains error summary if any

**Tags:** `[SPEC-011]` `[API]` `[STATUS]`

---

#### Scenario 9.3: Cancel Execution API

**Given** a running workflow execution
**When** POST /api/v1/executions/{execution_id}/cancel is called
**Then** execution is marked as CANCELLED
**And** running nodes complete current work
**And** pending nodes are not executed
**And** response confirms cancellation

**Tags:** `[SPEC-011]` `[API]` `[CANCEL]`

---

## Performance Criteria

### Response Time

| Operation | Target | Measurement |
|-----------|--------|-------------|
| Workflow execution start | <100ms | API response time |
| Node execution (simple) | <1s | Per-node duration |
| Context variable lookup | <1ms | Per-access time |
| Execution history query | <500ms | API response time |

### Concurrency

| Metric | Target | Measurement |
|--------|--------|-------------|
| Parallel nodes per level | Up to 10 | Configurable limit |
| Concurrent executions | Up to 50 | System capacity |
| Scheduled workflows | Up to 1000 | Scheduler capacity |

### Reliability

| Metric | Target | Measurement |
|--------|--------|-------------|
| Execution success rate | >99% | Excluding user errors |
| Scheduler uptime | >99.9% | APScheduler availability |
| Context isolation | 100% | No cross-execution leakage |

---

## Security Criteria

### Input Validation

| Input | Validation |
|-------|------------|
| workflow_id | UUID format, user ownership |
| execution_id | UUID format, user ownership |
| inputs JSONSchema | Per-workflow schema validation |
| cron expression | Valid cron syntax |

### Access Control

| Operation | Requirement |
|-----------|-------------|
| Execute workflow | User must own workflow or have execution permission |
| View execution | User must own execution or workflow |
| Cancel execution | User must own execution |

### Resource Limits

| Resource | Limit |
|----------|-------|
| Context size | 100MB per execution |
| Execution duration | 1 hour (configurable) |
| Node timeout | 5 minutes (per node) |

---

## Integration Points

### SPEC-010 Integration

- **Dependency:** Use `TopologyResult.execution_order` from DAG Validator
- **Verification:** Execute workflows with various topologies
- **Test:** Single path, parallel paths, complex DAG structures

### SPEC-009 Integration

- **Dependency:** Use `ToolRegistry` and `AgentManager`
- **Verification:** Execute tool and agent nodes
- **Test:** Mock tools/agents for isolated testing

### SPEC-005 Integration

- **Dependency:** Create `WorkflowExecution` and `NodeExecution` records
- **Verification:** Records created and updated correctly
- **Test:** Query execution history

---

## Change History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-16 | workflow-spec | Initial acceptance criteria |
