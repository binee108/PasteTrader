# SPEC-011: Workflow Execution Engine

## Metadata

| Field | Value |
|-------|-------|
| SPEC ID | SPEC-011 |
| Title | Workflow Execution Engine |
| Created | 2026-01-16 |
| Status | Draft |
| Priority | High (P0) |
| Lifecycle | spec-anchored |
| Author | workflow-spec |
| Phase | Phase 4 - Engine Core |

## Tags

`[SPEC-011]` `[EXEC]` `[DAG]` `[WORKFLOW]` `[EXECUTION]` `[ASYNCIO]` `[RETRY]` `[BACKEND]`

---

## Overview

This SPEC defines the Workflow Execution Engine that provides runtime execution of validated DAG workflows. While SPEC-010 (DAG Validation Service) ensures workflow structural validity, this SPEC implements the actual execution runtime with async parallel execution, error handling, retry logic, and execution context management.

### Scope

- DAG Executor Core: Topological sort-based execution ordering
- Parallel async execution using asyncio.gather
- Execution state management (pending, running, completed, failed)
- Error handling with graceful degradation options
- Configurable retry logic with exponential backoff
- Shared execution context management
- Node type executors (Tool, Agent, Condition, Adapter, Aggregator)
- Scheduler integration (APScheduler)
- Execution history tracking

### Out of Scope

- Workflow DAG validation (covered by SPEC-010)
- Tool/Agent definition and management (covered by SPEC-009)
- Workflow CRUD operations (covered by SPEC-007)
- Frontend workflow editor (covered by separate SPEC)

---

## Environment

### Technology Stack (Constitution Reference)

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.13.x | Runtime environment |
| asyncio | builtin | Async parallel execution |
| FastAPI | 0.115.x | API framework for execution triggers |
| Pydantic | 2.10.x | Schema validation |
| SQLAlchemy | 2.0.x | ORM for execution records |
| APScheduler | 3.11.x | Scheduled workflow execution |
| asyncpg | 0.30.x | PostgreSQL async driver |

### Configuration Dependencies

- SPEC-001: Base models, Mixins, Enums
- SPEC-003: Workflow, Node, Edge models (execution targets)
- SPEC-009: ToolRegistry, AgentManager (node execution dependencies)
- SPEC-010: DAGValidator, topological sort (execution ordering)

---

## Assumptions

### Technical Assumptions

| Assumption | Confidence | Evidence | Risk if Wrong |
|------------|------------|----------|---------------|
| asyncio.gather scales to 50+ parallel nodes | High | Python 3.13 proven scalability | Need semaphore limiting |
| Topological sort from SPEC-010 is correct | High | Validated before execution | Stale validation requires re-check |
| ToolRegistry/AgentManager are thread-safe | Medium | SPEC-009 implementation | Need async locks |
| Context isolation per execution | High | Dict-based context proven safe | Memory leak risk with large contexts |

### Design Assumptions

| Assumption | Confidence | Risk if Wrong |
|------------|------------|---------------|
| Fail-fast default behavior is appropriate | Medium | Users may want continue-on-error |
| Exponential backoff prevents API throttling | High | Some APIs need custom backoff |
| In-memory context is sufficient | Medium | Long workflows may need persistence |
| Single-process execution is MVP | High | Multi-worker requires distributed state |

---

## Requirements

### DAG Executor Core Requirements

#### REQ-011-001: Topological Sort Execution Order

**Event-Driven Requirement**

**WHEN** a workflow execution is initiated, **THEN** the system shall execute nodes in topological order as provided by the DAG Validator.

**Details:**

- Use `TopologyResult.execution_order` from SPEC-010
- Execute nodes level-by-level respecting dependencies
- Within each level, execute independent nodes in parallel

**Example:**
```python
# Given execution_order from validator:
[
    ["trigger-1"],                    # Level 0
    ["tool-1", "tool-2"],             # Level 1 (parallel)
    ["condition-1"],                  # Level 2
    ["agent-1", "agent-2"],           # Level 3 (parallel)
    ["aggregator-1"]                  # Level 4
]
```

#### REQ-011-002: Parallel Async Execution

**Event-Driven Requirement**

**WHEN** multiple nodes at the same topological level have no interdependencies, **THEN** the system shall execute them concurrently using asyncio.gather.

**Details:**

- Use `asyncio.gather(*tasks, return_exceptions=True)`
- Configurable concurrency limit via semaphore
- Respect node-level timeout_seconds

**Example:**
```python
async def execute_level(self, level: list[str]):
    semaphore = asyncio.Semaphore(self.max_parallel_nodes)
    tasks = [self._execute_with_semaphore(node_id, semaphore)
             for node_id in level]
    return await asyncio.gather(*tasks, return_exceptions=True)
```

#### REQ-011-003: Dependency Resolution

**State-Driven Requirement**

**IF** a node depends on outputs from parent nodes, **THEN** the system shall gather all required inputs before executing the node.

**Details:**

- Check all dependencies are in COMPLETED state
- Gather outputs from execution context
- Skip node if any dependency failed (configurable)

**Example:**
```python
def _gather_inputs(self, node: Node) -> dict[str, Any]:
    inputs = {}
    for edge in self.incoming_edges[node.id]:
        source_output = self.context[edge.source_node_id]
        if edge.source_handle:
            inputs[edge.source_handle] = source_output[edge.source_handle]
        else:
            inputs[edge.source_node_id] = source_output
    return inputs
```

#### REQ-011-004: Execution State Management

**Ubiquitous Requirement**

The system shall **always** maintain execution state for each node throughout the workflow execution lifecycle.

**States:**
- `PENDING`: Node not yet started
- `RUNNING`: Node currently executing
- `COMPLETED`: Node finished successfully
- `FAILED`: Node execution failed
- `SKIPPED`: Node skipped due to dependency failure or condition evaluation
- `RETRYING`: Node being retried after failure

**State Transitions:**
```
PENDING → RUNNING → COMPLETED
    ↓         ↓
SKIPPED   FAILED → RETRYING → RUNNING → COMPLETED/FAILED
```

---

### Error Handling Requirements

#### REQ-011-005: Per-Node Error Capture

**Ubiquitous Requirement**

The system shall **always** capture detailed error information when a node execution fails.

**Captured Information:**
- Exception type and message
- Stack trace
- Node inputs at time of failure
- Timestamp of failure
- Retry attempt number

**Error Storage Format:**
```python
@dataclass
class NodeExecutionError:
    node_id: str
    exception_type: str
    message: str
    stack_trace: str
    inputs: dict[str, Any]
    occurred_at: datetime
    retry_count: int
```

#### REQ-011-006: Graceful Degradation Strategy

**State-Driven Requirement**

**IF** `error_handling.on_node_failure` is `"continue"`, **THEN** the system shall continue executing remaining nodes after a node failure.

**IF** `error_handling.on_node_failure` is `"stop"`, **THEN** the system shall halt execution immediately after a node failure.

**Configuration:**
```yaml
error_handling:
  on_node_failure: continue  # | stop
  propagate_errors: true
  failure_threshold: null    # Stop after N failures
```

#### REQ-011-007: Error Context Propagation

**Event-Driven Requirement**

**WHEN** a node fails, **THEN** the system shall propagate error context to dependent nodes if configured.

**Details:**

- Downstream nodes can access upstream errors via `{{ errors.parent_node_id }}`
- Enables conditional logic based on parent failures
- Error context available in `context['_errors']` dictionary

#### REQ-011-008: Fallback Node Execution

**Optional Requirement**

**Where possible**, the system shall support fallback node execution when primary node fails.

**Configuration:**
```yaml
nodes:
  - id: price-fetcher-primary
    type: tool
    fallback_to: price-fetcher-backup

  - id: price-fetcher-backup
    type: tool
    config:
      api_endpoint: "https://backup-api.example.com"
```

---

### Retry Logic Requirements

#### REQ-011-009: Configurable Retry Attempts

**State-Driven Requirement**

**IF** a node has `retry_config.max_retries > 0`, **THEN** the system shall retry failed node execution up to the configured limit.

**Retry Configuration:**
```yaml
nodes:
  - id: unstable-tool
    retry_config:
      max_retries: 3
      initial_delay_seconds: 1
      max_delay_seconds: 60
      backoff_multiplier: 2.0
      retry_on: ["TimeoutError", "ConnectionError"]
```

#### REQ-011-010: Exponential Backoff

**Event-Driven Requirement**

**WHEN** retrying a failed node, **THEN** the system shall apply exponential backoff between retry attempts.

**Backoff Formula:**
```
delay = min(initial_delay * (backoff_multiplier ^ attempt), max_delay)
```

**Example:**
- Attempt 1: delay = 1s
- Attempt 2: delay = 2s
- Attempt 3: delay = 4s
- Capped at max_delay (e.g., 60s)

#### REQ-011-011: Retry Condition Evaluation

**State-Driven Requirement**

**IF** `retry_config.retry_on` is specified, **THEN** the system shall only retry on listed exception types.

**IF** `retry_config.retry_on` is `null`, **THEN** the system shall retry on all exceptions.

**Valid Exception Types:**
- Built-in: `TimeoutError`, `ConnectionError`, `HTTPError`
- Custom: `APIThrottledError`, `TemporaryFailure`
- Wildcard: `"*"` for all exceptions

#### REQ-011-012: Maximum Retry Limit

**Unwanted Behavior Requirement**

The system **shall not** retry a node more than `retry_config.max_retries` times.

**Behavior:**
- After max retries exceeded, mark node as FAILED
- Do not attempt additional retries
- Proceed based on `error_handling.on_node_failure` setting

---

### Execution Context Requirements

#### REQ-011-013: Shared Context Management

**Ubiquitous Requirement**

The system shall **always** maintain a shared execution context throughout the workflow execution.

**Context Structure:**
```python
@dataclass
class ExecutionContext:
    execution_id: str
    workflow_id: str
    variables: dict[str, Any]        # Workflow-level variables
    node_outputs: dict[str, Any]     # {node_id: output_data}
    errors: dict[str, Any]           # {node_id: error_info}
    metadata: dict[str, Any]         # timestamps, counts, etc.
```

#### REQ-011-014: Node Output Storage

**Event-Driven Requirement**

**WHEN** a node completes successfully, **THEN** the system shall store its outputs in the execution context under the node ID.

**Storage Format:**
```python
context.node_outputs[node_id] = {
    "output_1": value1,
    "output_2": value2,
    "_meta": {
        "executed_at": "2026-01-16T09:30:05Z",
        "duration_ms": 150
    }
}
```

#### REQ-011-015: Variable Binding and Substitution

**State-Driven Requirement**

**IF** a node configuration contains variable references, **THEN** the system shall substitute them with actual values before execution.

**Variable Reference Patterns:**
- `{{ variables.rsi_period }}` → Workflow variable
- `{{ nodes.node-1.outputs.stock_list }}` → Node output reference
- `{{ inputs.symbol }}` → Runtime input parameter

**Example:**
```yaml
nodes:
  - id: fetch-price
    config:
      symbol: "{{ variables.default_symbol }}"
      period: "{{ nodes.configurator.outputs.period }}"
```

#### REQ-011-016: Context Isolation Between Executions

**Ubiquitous Requirement**

The system shall **always** isolate execution contexts between different workflow executions.

**Isolation Guarantees:**
- Each execution has unique `execution_id`
- Context never shared between executions
- Concurrent executions maintain separate contexts
- No cross-execution variable leakage

---

### Node Execution Requirements

#### REQ-011-017: Tool Node Execution

**Event-Driven Requirement**

**WHEN** a tool node is executed, **THEN** the system shall invoke the corresponding tool from ToolRegistry with validated inputs.

**Execution Flow:**
1. Retrieve tool from `ToolRegistry.get(tool_id)`
2. Validate inputs against tool's `input_schema`
3. Execute tool with timeout enforcement
4. Validate outputs against tool's `output_schema` (if defined)
5. Store outputs in context

**Error Handling:**
- Timeout: mark as FAILED, apply retry logic
- Invalid input: mark as FAILED, do not retry (input error)
- Tool error: mark as FAILED, apply retry logic

#### REQ-011-018: Agent Node Execution

**Event-Driven Requirement**

**WHEN** an agent node is executed, **THEN** the system shall invoke the corresponding agent from AgentManager with the configured prompt and inputs.

**Execution Flow:**
1. Retrieve agent from `AgentManager.get(agent_id)`
2. Build execution context for agent
3. Execute agent with LLM provider
4. Parse structured output (if schema defined)
5. Store outputs in context

**Configuration:**
```yaml
nodes:
  - id: analyzer
    type: agent
    agent_id: buy_signal_analyzer
    config:
      prompt_template: |
        Analyze the following stock data:
        {{ inputs.stock_data }}

        Provide a buy/sell recommendation.
      max_tokens: 4096
      temperature: 0.3
```

#### REQ-011-019: Condition Node Evaluation

**Event-Driven Requirement**

**WHEN** a condition node is evaluated, **THEN** the system shall evaluate the condition expression and route to the appropriate output branch.

**Condition Evaluation:**
```python
# Condition configuration
conditions:
  - name: oversold
    expression: "rsi < variables.oversold_threshold"
    target_node: buy-analyzer
  - name: overbought
    expression: "rsi > variables.overbought_threshold"
    target_node: sell-analyzer
  - name: neutral
    expression: "else"
    target_node: hold-analyzer
```

**Evaluation Order:**
1. Evaluate conditions in sequence
2. First matching condition determines output
3. `else` condition matches if no prior match
4. Store selected branch in context for routing

#### REQ-011-020: Adapter Node Transformation

**Event-Driven Requirement**

**WHEN** an adapter node is executed, **THEN** the system shall transform input data according to the configured transformation rules.

**Transformation Types:**
- `json_to_dataframe`: Convert JSON to pandas DataFrame
- `dataframe_to_json`: Convert DataFrame to JSON-serializable dict
- `map_fields`: Rename/restructure fields
- `filter`: Filter data based on conditions
- `aggregate`: Group and aggregate data

**Example:**
```yaml
nodes:
  - id: adapter-1
    type: adapter
    config:
      transformation: |
        def transform(inputs):
            df = pd.DataFrame(inputs['stock_list'])
            df['rsi_normalized'] = df['rsi'] / 100
            return df.to_dict('records')
```

#### REQ-011-021: Aggregator Node Collection

**Event-Driven Requirement**

**WHEN** an aggregator node is executed, **THEN** the system shall collect outputs from all input nodes and apply the configured aggregation strategy.

**Aggregation Strategies:**
- `merge`: Combine all outputs into single list
- `concatenate`: Join sequences
- `sum/count/avg`: Numeric aggregation
- `custom`: Python function for custom aggregation

**Example:**
```yaml
nodes:
  - id: aggregate-signals
    type: aggregator
    config:
      strategy: merge
      sort_by: confidence
      limit: 10
```

---

### Scheduler Integration Requirements

#### REQ-011-022: APScheduler Integration

**Ubiquitous Requirement**

The system shall **always** integrate with APScheduler for scheduled workflow execution.

**Scheduler Configuration:**
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

class WorkflowScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.executor = WorkflowExecutor()
```

#### REQ-011-023: Cron-Based Trigger Support

**Event-Driven Requirement**

**WHEN** a workflow has a schedule configuration, **THEN** the system shall register it with APScheduler using cron expression.

**Configuration:**
```yaml
workflow:
  schedule:
    cron: "30 9,15 * * 1-5"  # 9:30 and 15:00, weekdays only
    timezone: "Asia/Seoul"
```

#### REQ-011-024: Manual/Ondemand Execution

**Event-Driven Requirement**

**WHEN** a manual execution request is received, **THEN** the system shall execute the workflow immediately without scheduling.

**API Endpoint:**
```python
@router.post("/workflows/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: UUID,
    inputs: dict[str, Any] | None = None
) -> ExecutionResponse:
    """Execute workflow immediately on demand."""
```

#### REQ-011-025: Execution History Tracking

**Ubiquitous Requirement**

The system shall **always** record execution history for every workflow execution.

**Tracked Information:**
- Execution ID, Workflow ID
- Start time, End time, Duration
- Final status (completed/failed/partial)
- Node execution details (status, outputs, errors)
- Execution context snapshot (configurable)

**Storage:**
- `workflow_executions` table (from SPEC-005)
- `node_executions` table (from SPEC-005)

---

## Specifications

### SPEC-011-A: File Structure

```
backend/
  app/
    services/
      workflow/
        executor.py              # Main DAG Executor (NEW)
        node_executors.py        # Node type executors (NEW)
        context.py               # Execution context management (NEW)
        retry.py                 # Retry logic with backoff (NEW)
        scheduler.py             # Scheduler wrapper (NEW)
    schemas/
      execution.py               # Execution schemas (NEW)
    api/
      v1/
        executions.py            # Execution API endpoints (NEW)
```

### SPEC-011-B: DAG Executor Interface

```python
# services/workflow/executor.py
from uuid import UUID
from typing import Any, Optional
import asyncio
from dataclasses import dataclass, field

from app.models.workflow import Workflow, Node, Edge
from app.schemas.execution import (
    ExecutionContext,
    ExecutionResult,
    NodeExecutionResult,
    ExecutionConfig,
)
from app.services.workflow.validator import DAGValidator


@dataclass
class ExecutionConfig:
    """Configuration for workflow execution."""
    on_node_failure: str = "stop"  # "stop" | "continue"
    max_parallel_nodes: int = 10
    enable_retry: bool = True
    persist_context: bool = False
    timeout_seconds: int = 3600


class DAGExecutor:
    """Execute validated DAG workflows with parallel async execution.

    TAG: [SPEC-011] [EXEC] [DAG]

    This executor takes a validated workflow DAG and executes it
    according to the topological sort provided by DAGValidator.
    """

    def __init__(
        self,
        db: AsyncSession,
        tool_registry: ToolRegistry,
        agent_manager: AgentManager,
    ):
        self.db = db
        self.tools = tool_registry
        self.agents = agent_manager
        self.validator = DAGValidator(db)

    async def execute_workflow(
        self,
        workflow_id: UUID,
        inputs: dict[str, Any] | None = None,
        config: ExecutionConfig | None = None,
    ) -> ExecutionResult:
        """Execute a complete workflow DAG.

        TAG: [SPEC-011] [EXEC] [MAIN]

        Args:
            workflow_id: Workflow to execute
            inputs: Runtime input parameters
            config: Execution configuration

        Returns:
            ExecutionResult with status, outputs, and node results
        """
        ...

    async def execute_node(
        self,
        node: Node,
        context: ExecutionContext,
    ) -> NodeExecutionResult:
        """Execute a single node with its specific executor.

        TAG: [SPEC-011] [EXEC] [NODE]

        Routes to appropriate executor based on node_type.
        """
        ...

    async def _execute_level(
        self,
        node_ids: list[str],
        context: ExecutionContext,
    ) -> list[NodeExecutionResult]:
        """Execute all nodes in a topological level in parallel.

        TAG: [SPEC-011] [EXEC] [PARALLEL]

        Uses asyncio.gather with semaphore for concurrency control.
        """
        ...
```

### SPEC-011-C: Execution Context Management

```python
# services/workflow/context.py
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4
from typing import Any


@dataclass
class ExecutionContext:
    """Shared execution context for a workflow run.

    TAG: [SPEC-011] [CONTEXT]

    Provides isolation between executions while maintaining
    shared state for all nodes within an execution.
    """

    execution_id: UUID = field(default_factory=uuid4)
    workflow_id: UUID | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Workflow-level variables (from workflow.variables)
    variables: dict[str, Any] = field(default_factory=dict)

    # Node outputs keyed by node_id
    node_outputs: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Node errors keyed by node_id
    node_errors: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Runtime inputs passed to execution
    inputs: dict[str, Any] = field(default_factory=dict)

    # Metadata (counts, timestamps, etc.)
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_variable(self, path: str, default: Any = None) -> Any:
        """Get variable value by dot-notation path.

        Example: get_variable("config.rsi_period")
        """
        ...

    def get_node_output(
        self,
        node_id: str,
        output_key: str | None = None
    ) -> Any:
        """Get output from a specific node.

        If output_key is None, returns entire output dict.
        """
        ...

    def set_node_output(
        self,
        node_id: str,
        outputs: dict[str, Any]
    ) -> None:
        """Store node outputs in context."""
        ...

    def substitute_variables(
        self,
        template: str,
        local_vars: dict[str, Any] | None = None
    ) -> Any:
        """Substitute variable references in template string.

        Supports: {{ variables.* }}, {{ nodes.*.outputs.* }}, {{ inputs.* }}
        """
        ...
```

### SPEC-011-D: Retry Logic

```python
# services/workflow/retry.py
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable


@dataclass
class RetryConfig:
    """Retry configuration for node execution."""
    max_retries: int = 3
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    backoff_multiplier: float = 2.0
    retry_on: list[str] | None = None  # None = all exceptions


class RetryExecutor:
    """Handle retry logic with exponential backoff.

    TAG: [SPEC-011] [RETRY]
    """

    def __init__(self, config: RetryConfig):
        self.config = config

    async def execute_with_retry(
        self,
        func: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute function with retry logic.

        TAG: [SPEC-011] [RETRY] [EXECUTE]

        Applies exponential backoff between retries.
        Only retries on configured exception types.
        """
        last_exception = None

        for attempt in range(self.config.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                # Check if we should retry this exception
                if not self._should_retry(e, attempt):
                    raise

                # Wait before retry (exponential backoff)
                if attempt < self.config.max_retries:
                    delay = self._calculate_delay(attempt)
                    await asyncio.sleep(delay)

        # All retries exhausted
        raise last_exception

    def _should_retry(self, exception: Exception, attempt: int) -> bool:
        """Check if exception should trigger retry."""
        if attempt >= self.config.max_retries:
            return False

        if self.config.retry_on is None:
            return True  # Retry all exceptions

        exception_type = type(exception).__name__
        return exception_type in self.config.retry_on

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff."""
        delay = self.config.initial_delay_seconds * (
            self.config.backoff_multiplier ** attempt
        )
        return min(delay, self.config.max_delay_seconds)
```

### SPEC-011-E: Node Executors

```python
# services/workflow/node_executors.py
from abc import ABC, abstractmethod
from typing import Any

from app.services.workflow.context import ExecutionContext
from app.services.workflow.retry import RetryExecutor
from app.models.workflow import Node


class BaseNodeExecutor(ABC):
    """Base class for node type executors.

    TAG: [SPEC-011] [NODE] [BASE]
    """

    def __init__(self, node: Node, context: ExecutionContext):
        self.node = node
        self.context = context

    @abstractmethod
    async def execute(self) -> dict[str, Any]:
        """Execute the node and return outputs."""
        pass


class ToolNodeExecutor(BaseNodeExecutor):
    """Execute tool nodes via ToolRegistry.

    TAG: [SPEC-011] [NODE] [TOOL]
    """

    def __init__(
        self,
        node: Node,
        context: ExecutionContext,
        tool_registry: ToolRegistry,
    ):
        super().__init__(node, context)
        self.tools = tool_registry

    async def execute(self) -> dict[str, Any]:
        """Execute tool with retry logic."""
        tool = self.tools.get(self.node.config["tool_id"])

        # Substitute variables in tool inputs
        inputs = self._prepare_inputs()

        # Create retry executor
        retry_config = RetryConfig(**self.node.retry_config)
        retry_executor = RetryExecutor(retry_config)

        # Execute with retry
        async def _execute():
            return await tool.execute(inputs)

        result = await retry_executor.execute_with_retry(_execute)
        return {"output": result}


class AgentNodeExecutor(BaseNodeExecutor):
    """Execute agent nodes via AgentManager.

    TAG: [SPEC-011] [NODE] [AGENT]
    """

    def __init__(
        self,
        node: Node,
        context: ExecutionContext,
        agent_manager: AgentManager,
    ):
        super().__init__(node, context)
        self.agents = agent_manager

    async def execute(self) -> dict[str, Any]:
        """Execute agent with LLM call."""
        agent = self.agents.get(self.node.config["agent_id"])

        # Build prompt from template
        prompt = self._build_prompt()

        # Execute agent
        response = await agent.execute(prompt)
        return {"response": response}


class ConditionNodeExecutor(BaseNodeExecutor):
    """Evaluate condition nodes and determine output branch.

    TAG: [SPEC-011] [NODE] [CONDITION]
    """

    async def execute(self) -> dict[str, Any]:
        """Evaluate conditions and return selected branch."""
        conditions = self.node.config.get("conditions", [])
        inputs = self._get_inputs()

        for condition in conditions:
            if self._evaluate_condition(condition, inputs):
                return {
                    "selected_branch": condition["name"],
                    "target_node": condition["target_node"],
                }

        # Default to else condition
        return {"selected_branch": "default"}


class AdapterNodeExecutor(BaseNodeExecutor):
    """Execute adapter nodes for data transformation.

    TAG: [SPEC-011] [NODE] [ADAPTER]
    """

    async def execute(self) -> dict[str, Any]:
        """Apply data transformation."""
        transformation = self.node.config.get("transformation")
        inputs = self._get_inputs()

        # Execute transformation (in sandboxed env)
        result = self._apply_transformation(transformation, inputs)
        return {"output": result}


class AggregatorNodeExecutor(BaseNodeExecutor):
    """Execute aggregator nodes for collecting outputs.

    TAG: [SPEC-011] [NODE] [AGGREGATOR]
    """

    async def execute(self) -> dict[str, Any]:
        """Aggregate outputs from multiple input nodes."""
        strategy = self.node.config.get("strategy", "merge")

        # Gather outputs from all incoming edges
        inputs = self._get_inputs()

        if strategy == "merge":
            result = self._merge_outputs(inputs)
        elif strategy == "concatenate":
            result = self._concatenate_outputs(inputs)
        # ... other strategies

        return {"output": result}
```

### SPEC-011-F: Scheduler Integration

```python
# services/workflow/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from uuid import UUID
from typing import Callable, Optional

from app.services.workflow.executor import DAGExecutor


class WorkflowScheduler:
    """APScheduler wrapper for workflow scheduling.

    TAG: [SPEC-011] [SCHEDULER]
    """

    def __init__(self, executor: DAGExecutor):
        self.scheduler = AsyncIOScheduler()
        self.executor = executor
        self._jobs: dict[UUID, str] = {}

    def start(self) -> None:
        """Start the scheduler."""
        self.scheduler.start()

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the scheduler."""
        self.scheduler.shutdown(wait=wait)

    def schedule_workflow(
        self,
        workflow_id: UUID,
        cron: str,
        timezone: str = "Asia/Seoul",
        inputs: dict[str, Any] | None = None,
    ) -> str:
        """Schedule a workflow for cron-based execution.

        TAG: [SPEC-011] [SCHEDULER] [SCHEDULE]

        Args:
            workflow_id: Workflow to schedule
            cron: Cron expression (e.g., "30 9,15 * * 1-5")
            timezone: Timezone for cron schedule
            inputs: Default inputs for scheduled executions

        Returns:
            Job ID for the scheduled job
        """
        trigger = CronTrigger.from_crontab(cron, timezone=timezone)

        async def _execute():
            await self.executor.execute_workflow(workflow_id, inputs)

        job = self.scheduler.add_job(
            _execute,
            trigger=trigger,
            id=f"workflow-{workflow_id}",
            name=f"Workflow {workflow_id}",
        )

        self._jobs[workflow_id] = job.id
        return job.id

    def unschedule_workflow(self, workflow_id: UUID) -> None:
        """Remove workflow from schedule."""
        if workflow_id in self._jobs:
            self.scheduler.remove_job(self._jobs[workflow_id])
            del self._jobs[workflow_id]

    def get_next_run_time(self, workflow_id: UUID) -> Optional[datetime]:
        """Get next scheduled run time for workflow."""
        if workflow_id in self._jobs:
            job = self.scheduler.get_job(self._jobs[workflow_id])
            return job.next_run_time if job else None
        return None
```

### SPEC-011-G: Execution Schemas

```python
# schemas/execution.py
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class ExecutionStatus(str, Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some nodes failed
    CANCELLED = "cancelled"


class NodeExecutionStatus(str, Enum):
    """Node execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class NodeExecutionResult(BaseModel):
    """Result of a single node execution."""
    model_config = ConfigDict(from_attributes=True)

    node_id: UUID
    status: NodeExecutionStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: float = 0.0
    outputs: dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    retry_count: int = 0


class ExecutionResult(BaseModel):
    """Result of workflow execution."""
    model_config = ConfigDict(from_attributes=True)

    execution_id: UUID
    workflow_id: UUID
    status: ExecutionStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: float = 0.0

    # Node results
    node_results: list[NodeExecutionResult] = Field(default_factory=list)

    # Final outputs (from terminal nodes)
    outputs: dict[str, Any] = Field(default_factory=dict)

    # Error summary
    errors: list[str] = Field(default_factory=list)

    # Metadata
    nodes_completed: int = 0
    nodes_failed: int = 0
    nodes_skipped: int = 0


class ExecuteWorkflowRequest(BaseModel):
    """Request to execute a workflow."""
    inputs: dict[str, Any] = Field(default_factory=dict)
    config: ExecutionConfig = None


class ExecuteWorkflowResponse(BaseModel):
    """Response from workflow execution."""
    execution_id: UUID
    status: ExecutionStatus
    message: str
```

### SPEC-011-H: Execution API Endpoints

```python
# api/v1/executions.py
from uuid import UUID
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DBSession, CurrentUser
from app.schemas.execution import (
    ExecuteWorkflowRequest,
    ExecuteWorkflowResponse,
    ExecutionResult,
)
from app.services.workflow.executor import DAGExecutor

router = APIRouter(prefix="/executions", tags=["executions"])


@router.post(
    "/workflows/{workflow_id}",
    response_model=ExecuteWorkflowResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Execute Workflow",
    description="Execute a workflow immediately (on-demand).",
)
async def execute_workflow(
    workflow_id: UUID,
    request: ExecuteWorkflowRequest,
    background_tasks: BackgroundTasks,
    db: DBSession,
    current_user: CurrentUser,
) -> ExecuteWorkflowResponse:
    """Execute workflow on-demand.

    TAG: [SPEC-011] [API] [EXECUTE]

    Starts workflow execution in background.
    Returns immediately with execution_id.
    """
    executor = DAGExecutor(db)

    # Generate execution ID
    execution_id = await executor.create_execution(workflow_id, request.inputs)

    # Schedule background execution
    background_tasks.add_task(
        executor.execute_workflow,
        workflow_id,
        request.inputs,
        request.config,
    )

    return ExecuteWorkflowResponse(
        execution_id=execution_id,
        status="running",
        message="Workflow execution started",
    )


@router.get(
    "/{execution_id}",
    response_model=ExecutionResult,
    summary="Get Execution Status",
    description="Get the current status and results of a workflow execution.",
)
async def get_execution(
    execution_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> ExecutionResult:
    """Get execution status and results.

    TAG: [SPEC-011] [API] [STATUS]
    """
    executor = DAGExecutor(db)
    result = await executor.get_execution_result(execution_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found",
        )

    return result


@router.post(
    "/{execution_id}/cancel",
    status_code=status.HTTP_200_OK,
    summary="Cancel Execution",
    description="Cancel a running workflow execution.",
)
async def cancel_execution(
    execution_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """Cancel a running execution.

    TAG: [SPEC-011] [API] [CANCEL]
    """
    executor = DAGExecutor(db)
    cancelled = await executor.cancel_execution(execution_id)

    return {
        "execution_id": execution_id,
        "cancelled": cancelled,
        "message": "Execution cancelled" if cancelled else "Execution not found or already completed",
    }
```

---

## Constraints

### Technical Constraints

- All execution functions must be async/await compatible
- Must use topological sort from SPEC-010 for execution order
- Must respect node timeout_seconds
- Must use Pydantic v2 `model_config = ConfigDict(from_attributes=True)`

### Performance Constraints

- Parallel node execution limited by configurable semaphore (default: 10)
- Total workflow execution timeout: 3600 seconds (1 hour) by default
- Context size limited to 100MB per execution (configurable)
- Memory cleanup after execution completion

### Security Constraints

- Node execution sandboxed where possible
- Input validation before node execution
- No arbitrary code execution (adapter nodes use restricted eval)
- Audit logging for all executions

---

## Dependencies

### Internal Dependencies

- SPEC-001: Base models and mixins
- SPEC-003: Workflow, Node, Edge models (execution targets)
- SPEC-005: WorkflowExecution, NodeExecution models (tracking)
- SPEC-009: ToolRegistry, AgentManager (node dependencies)
- SPEC-010: DAGValidator, topological sort (execution ordering)

### External Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| asyncio | builtin | Parallel async execution |
| apscheduler | >=3.11.0 | Scheduled execution |
| sqlalchemy[asyncio] | >=2.0.0 | Execution record storage |

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Memory leak in long-running workflows | Medium | High | Context size limits, periodic cleanup |
| Race conditions in parallel execution | Medium | Medium | Proper context locking |
| Retry storms causing API throttling | Medium | High | Configurable backoff, max retries |
| Orphaned executions on cancellation | Low | Medium | Cleanup tasks, timeout enforcement |

---

## Related SPECs

- **SPEC-003**: Workflow Domain Models (Workflow, Node, Edge)
- **SPEC-005**: Execution Tracking Models (storage layer)
- **SPEC-009**: Tool/Agent API Endpoints (ToolRegistry, AgentManager)
- **SPEC-010**: DAG Validation Service (pre-execution validation)

---

## Change History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-16 | workflow-spec | Initial SPEC creation |
