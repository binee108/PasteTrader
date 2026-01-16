# SPEC-012: Node Processor Framework

## Metadata

| Field | Value |
|-------|-------|
| SPEC ID | SPEC-012 |
| Title | Node Processor Framework |
| Created | 2026-01-16 |
| Updated | 2026-01-16 |
| Status | Draft |
| Priority | High (P0) |
| Lifecycle | spec-anchored |
| Author | binee |
| Phase | Phase 4 - Engine Core |

## Tags

`[SPEC-012]` `[PROCESSOR]` `[DATA]` `[VALIDATION]` `[TRANSFORMATION]` `[ASYNCIO]` `[BACKEND]`

---

## Overview

This SPEC defines the Node Processor Framework that provides a processing abstraction layer for workflow nodes. While SPEC-011 (Workflow Execution Engine) handles execution orchestration with BaseNodeExecutor, this SPEC implements BaseProcessor for data transformation, input/output validation, error handling with retry logic, and metrics collection.

### Scope

- BaseProcessor abstract class with lifecycle hooks (pre_process, process, post_process)
- Input/Output validation using Pydantic schemas
- Error handling with configurable retry logic
- Processing metrics collection (duration, success rate, error count)
- Six processor type implementations for different node types
- ProcessorRegistry for dynamic processor lookup and instantiation
- Async execution support with asyncio
- Context propagation between processors

### Out of Scope

- DAG execution orchestration (covered by SPEC-011)
- Node type definitions and models (covered by SPEC-003)
- Tool/Agent definitions and registry (covered by SPEC-009)
- Workflow CRUD operations (covered by SPEC-007)
- DAG validation (covered by SPEC-010)

---

## Environment

### Technology Stack (Constitution Reference)

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.13.x | Runtime environment |
| asyncio | builtin | Async processing support |
| FastAPI | 0.115.x | API framework integration |
| Pydantic | 2.10.x | Input/Output validation |
| SQLAlchemy | 2.0.x | Metrics persistence |

### Configuration Dependencies

- SPEC-001: Base models, Mixins, Enums
- SPEC-003: Workflow, Node, Edge models (node type definitions)
- SPEC-009: ToolRegistry, AgentManager (external service access)
- SPEC-011: ExecutionContext, NodeExecutionResult (execution layer)

---

## Assumptions

### Technical Assumptions

| Assumption | Confidence | Evidence | Risk if Wrong |
|------------|------------|----------|---------------|
| Pydantic v2 validation is fast enough for hot path | High | Benchmarks show <1ms overhead | Need schema caching |
| Context propagation via dict is thread-safe | High | Python GIL protects dict operations | Need explicit locks |
| Processor instances can be reused across executions | Medium | Stateless design principle | Need instance pooling |
| Metrics collection overhead is negligible | Medium | Timing operations are cheap | Need sampling |

### Design Assumptions

| Assumption | Confidence | Risk if Wrong |
|------------|------------|---------------|
| Lifecycle hooks (pre/process/post) cover all use cases | High | May need additional hooks |
| Single processor per node type is sufficient | High | May need processor chains |
| Validation errors should not be retried | High | Users may want retry on transient errors |
| Metrics are stored in-memory initially | Medium | Need persistence for long-running workflows |

---

## Requirements

### BaseProcessor Requirements

#### REQ-012-001: Abstract BaseProcessor Class

**Ubiquitous Requirement**

The system shall **always** provide an abstract BaseProcessor class that defines the processing contract for all node processors.

**Interface:**
```python
from abc import ABC, abstractmethod
from typing import Any, TypeVar, Generic
from pydantic import BaseModel

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)

class BaseProcessor(ABC, Generic[InputT, OutputT]):
    """Base class for all node processors.

    TAG: [SPEC-012] [PROCESSOR] [BASE]
    """

    @abstractmethod
    async def pre_process(self, inputs: dict[str, Any]) -> InputT:
        """Validate and transform raw inputs into typed input model."""
        pass

    @abstractmethod
    async def process(self, validated_input: InputT) -> OutputT:
        """Execute the core processing logic."""
        pass

    @abstractmethod
    async def post_process(self, output: OutputT) -> dict[str, Any]:
        """Transform typed output into serializable dict."""
        pass
```

#### REQ-012-002: Lifecycle Hook Execution Order

**Event-Driven Requirement**

**WHEN** a processor is invoked with raw inputs, **THEN** the system shall execute lifecycle hooks in order: pre_process -> process -> post_process.

**Execution Flow:**
1. `pre_process`: Validate inputs, transform to typed model
2. `process`: Execute core logic, return typed output
3. `post_process`: Serialize output, add metadata

**Example:**
```python
async def execute(self, raw_inputs: dict[str, Any]) -> dict[str, Any]:
    """Full processing lifecycle."""
    # Step 1: Pre-process (validation + transformation)
    validated = await self.pre_process(raw_inputs)

    # Step 2: Process (core logic)
    result = await self.process(validated)

    # Step 3: Post-process (serialization)
    return await self.post_process(result)
```

#### REQ-012-003: Input Validation with Pydantic

**Ubiquitous Requirement**

The system shall **always** validate processor inputs using Pydantic models before processing.

**Validation Rules:**
- Input schema defined per processor type
- Validation errors raised as `ProcessorValidationError`
- Invalid inputs never reach the `process()` method
- Detailed error messages with field-level information

**Example:**
```python
class ToolProcessorInput(BaseModel):
    model_config = ConfigDict(strict=True)

    tool_id: str
    parameters: dict[str, Any]
    timeout_seconds: int = Field(default=30, ge=1, le=300)


async def pre_process(self, inputs: dict[str, Any]) -> ToolProcessorInput:
    try:
        return ToolProcessorInput.model_validate(inputs)
    except ValidationError as e:
        raise ProcessorValidationError(
            processor=self.__class__.__name__,
            errors=e.errors(),
        )
```

#### REQ-012-004: Output Validation

**Event-Driven Requirement**

**WHEN** the `process()` method returns output, **THEN** the system shall validate the output against the output schema.

**Validation Rules:**
- Output schema defined per processor type
- Invalid outputs raise `ProcessorOutputError`
- Output validated before `post_process()`
- Type coercion allowed for compatible types

---

### Error Handling Requirements

#### REQ-012-005: Configurable Retry Logic

**State-Driven Requirement**

**IF** a processor has `retry_config.enabled = True`, **THEN** the system shall retry failed processing up to `max_retries` times.

**Retry Configuration:**
```python
@dataclass
class ProcessorRetryConfig:
    enabled: bool = True
    max_retries: int = 3
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    backoff_multiplier: float = 2.0
    retry_on_exceptions: list[type[Exception]] = field(
        default_factory=lambda: [TimeoutError, ConnectionError]
    )
```

**Retry Behavior:**
- Only retry on configured exception types
- Validation errors (`ProcessorValidationError`) are never retried
- Exponential backoff between retries
- All retry attempts logged with attempt number

#### REQ-012-006: Error Context Capture

**Ubiquitous Requirement**

The system shall **always** capture detailed error context when processing fails.

**Captured Information:**
```python
@dataclass
class ProcessorError:
    processor_type: str
    node_id: str
    error_type: str
    message: str
    stack_trace: str
    inputs: dict[str, Any]  # Sanitized (no secrets)
    occurred_at: datetime
    retry_count: int
    is_retryable: bool
```

#### REQ-012-007: Graceful Error Propagation

**Event-Driven Requirement**

**WHEN** a processor fails after all retries, **THEN** the system shall wrap the error in `ProcessorExecutionError` and propagate to the execution layer.

**Error Hierarchy:**
```
ProcessorError (base)
├── ProcessorValidationError (input/output validation)
├── ProcessorTimeoutError (execution timeout)
├── ProcessorExecutionError (processing failure)
└── ProcessorConfigurationError (invalid configuration)
```

---

### Metrics Collection Requirements

#### REQ-012-008: Processing Metrics

**Ubiquitous Requirement**

The system shall **always** collect processing metrics for each processor invocation.

**Metrics Schema:**
```python
@dataclass
class ProcessorMetrics:
    processor_type: str
    node_id: str
    execution_id: str

    # Timing
    pre_process_duration_ms: float
    process_duration_ms: float
    post_process_duration_ms: float
    total_duration_ms: float

    # Status
    success: bool
    retry_count: int
    error_type: str | None

    # Resource usage
    input_size_bytes: int
    output_size_bytes: int

    # Timestamp
    started_at: datetime
    completed_at: datetime
```

#### REQ-012-009: Metrics Aggregation

**Event-Driven Requirement**

**WHEN** workflow execution completes, **THEN** the system shall aggregate processor metrics and provide summary statistics.

**Aggregated Metrics:**
- Total processing time by processor type
- Success/failure rate by processor type
- Average duration percentiles (P50, P95, P99)
- Error distribution by type

---

### Processor Type Requirements

#### REQ-012-010: ToolNodeProcessor

**Event-Driven Requirement**

**WHEN** a tool node is processed, **THEN** the system shall execute the tool with validated parameters and handle tool-specific errors.

**Processing Flow:**
1. Validate tool_id exists in ToolRegistry
2. Validate parameters against tool's input schema
3. Execute tool with timeout enforcement
4. Validate tool output against output schema
5. Transform output for downstream nodes

**Input Schema:**
```python
class ToolProcessorInput(BaseModel):
    tool_id: str
    parameters: dict[str, Any]
    timeout_seconds: int = 30
```

**Output Schema:**
```python
class ToolProcessorOutput(BaseModel):
    result: Any
    execution_duration_ms: float
    tool_metadata: dict[str, Any] = Field(default_factory=dict)
```

#### REQ-012-011: AgentNodeProcessor

**Event-Driven Requirement**

**WHEN** an agent node is processed, **THEN** the system shall execute the AI agent with the constructed prompt and parse structured output.

**Processing Flow:**
1. Retrieve agent configuration from AgentManager
2. Build prompt from template with variable substitution
3. Execute agent with configured LLM provider
4. Parse structured output (JSON/Pydantic model if defined)
5. Validate output against expected schema

**Input Schema:**
```python
class AgentProcessorInput(BaseModel):
    agent_id: str
    prompt_variables: dict[str, Any] = Field(default_factory=dict)
    max_tokens: int = 4096
    temperature: float = 0.7
```

**Output Schema:**
```python
class AgentProcessorOutput(BaseModel):
    response: str
    structured_output: dict[str, Any] | None = None
    token_usage: dict[str, int]
    model_used: str
```

#### REQ-012-012: ConditionNodeProcessor

**Event-Driven Requirement**

**WHEN** a condition node is processed, **THEN** the system shall evaluate condition expressions and determine the output branch.

**Processing Flow:**
1. Validate condition expressions
2. Evaluate conditions in sequence with input data
3. Return first matching condition branch
4. Default to "else" branch if no match

**Input Schema:**
```python
class ConditionProcessorInput(BaseModel):
    conditions: list[ConditionExpression]
    evaluation_context: dict[str, Any]

class ConditionExpression(BaseModel):
    name: str
    expression: str  # Python expression or simple comparison
    target_node: str
```

**Output Schema:**
```python
class ConditionProcessorOutput(BaseModel):
    selected_branch: str
    target_node: str
    evaluated_conditions: list[dict[str, bool]]
```

#### REQ-012-013: AdapterNodeProcessor

**Event-Driven Requirement**

**WHEN** an adapter node is processed, **THEN** the system shall transform input data according to the configured transformation rules.

**Transformation Types:**
- `field_mapping`: Rename and restructure fields
- `type_conversion`: Convert between data types
- `aggregation`: Group and aggregate data
- `filtering`: Filter data based on conditions
- `custom`: User-defined transformation function

**Input Schema:**
```python
class AdapterProcessorInput(BaseModel):
    transformation_type: str
    source_data: Any
    transformation_config: dict[str, Any]
```

**Output Schema:**
```python
class AdapterProcessorOutput(BaseModel):
    transformed_data: Any
    transformation_applied: str
    records_processed: int
```

#### REQ-012-014: TriggerNodeProcessor

**Event-Driven Requirement**

**WHEN** a trigger node is processed, **THEN** the system shall initialize the workflow execution context with trigger data.

**Processing Flow:**
1. Validate trigger source (schedule, webhook, manual)
2. Extract trigger payload and metadata
3. Initialize execution context variables
4. Prepare initial data for downstream nodes

**Input Schema:**
```python
class TriggerProcessorInput(BaseModel):
    trigger_type: str  # "schedule" | "webhook" | "manual"
    trigger_payload: dict[str, Any] = Field(default_factory=dict)
    trigger_metadata: dict[str, Any] = Field(default_factory=dict)
```

**Output Schema:**
```python
class TriggerProcessorOutput(BaseModel):
    initialized: bool
    context_variables: dict[str, Any]
    trigger_timestamp: datetime
```

#### REQ-012-015: AggregatorNodeProcessor

**Event-Driven Requirement**

**WHEN** an aggregator node is processed, **THEN** the system shall collect and aggregate outputs from multiple input sources.

**Aggregation Strategies:**
- `merge`: Combine all outputs into single dictionary
- `list`: Collect all outputs into a list
- `reduce`: Apply reduction function (sum, count, avg)
- `custom`: User-defined aggregation function

**Input Schema:**
```python
class AggregatorProcessorInput(BaseModel):
    strategy: str
    input_sources: dict[str, Any]  # {source_node_id: output_data}
    aggregation_config: dict[str, Any] = Field(default_factory=dict)
```

**Output Schema:**
```python
class AggregatorProcessorOutput(BaseModel):
    aggregated_result: Any
    source_count: int
    strategy_used: str
```

---

### ProcessorRegistry Requirements

#### REQ-012-016: Dynamic Processor Registration

**Ubiquitous Requirement**

The system shall **always** maintain a ProcessorRegistry for dynamic processor lookup and instantiation.

**Registry Interface:**
```python
class ProcessorRegistry:
    """Registry for processor type lookup and instantiation.

    TAG: [SPEC-012] [REGISTRY]
    """

    def register(
        self,
        node_type: str,
        processor_class: type[BaseProcessor],
    ) -> None:
        """Register a processor class for a node type."""
        pass

    def get(self, node_type: str) -> type[BaseProcessor]:
        """Get processor class for node type."""
        pass

    def create(
        self,
        node_type: str,
        config: ProcessorConfig,
    ) -> BaseProcessor:
        """Create processor instance with configuration."""
        pass

    def list_registered(self) -> list[str]:
        """List all registered processor types."""
        pass
```

#### REQ-012-017: Default Processor Registration

**Event-Driven Requirement**

**WHEN** the application starts, **THEN** the system shall register all default processor types.

**Default Registrations:**
```python
# Default processor mappings
DEFAULT_PROCESSORS = {
    "tool": ToolNodeProcessor,
    "agent": AgentNodeProcessor,
    "condition": ConditionNodeProcessor,
    "adapter": AdapterNodeProcessor,
    "trigger": TriggerNodeProcessor,
    "aggregator": AggregatorNodeProcessor,
}
```

---

### Context Propagation Requirements

#### REQ-012-018: Context Access in Processors

**State-Driven Requirement**

**IF** a processor needs access to execution context, **THEN** the system shall inject the ExecutionContext via processor initialization.

**Context Access:**
```python
class BaseProcessor(ABC, Generic[InputT, OutputT]):
    def __init__(
        self,
        node: Node,
        context: ExecutionContext,
        config: ProcessorConfig,
    ):
        self.node = node
        self.context = context
        self.config = config

    def get_variable(self, path: str) -> Any:
        """Get variable from execution context."""
        return self.context.get_variable(path)

    def get_node_output(self, node_id: str, key: str = None) -> Any:
        """Get output from another node."""
        return self.context.get_node_output(node_id, key)
```

#### REQ-012-019: Context Update After Processing

**Event-Driven Requirement**

**WHEN** a processor completes successfully, **THEN** the system shall update the execution context with the processor output.

**Context Update:**
```python
async def execute_with_context_update(
    self,
    processor: BaseProcessor,
    inputs: dict[str, Any],
) -> dict[str, Any]:
    """Execute processor and update context."""
    result = await processor.execute(inputs)

    # Update context with output
    self.context.set_node_output(
        node_id=processor.node.id,
        outputs=result,
    )

    return result
```

---

## Specifications

### SPEC-012-A: File Structure

```
backend/
  app/
    services/
      workflow/
        processors/
          __init__.py           # ProcessorRegistry, exports
          base.py               # BaseProcessor, ProcessorConfig
          tool.py               # ToolNodeProcessor
          agent.py              # AgentNodeProcessor
          condition.py          # ConditionNodeProcessor
          adapter.py            # AdapterNodeProcessor
          trigger.py            # TriggerNodeProcessor
          aggregator.py         # AggregatorNodeProcessor
          errors.py             # Processor exceptions
          metrics.py            # ProcessorMetrics, MetricsCollector
    schemas/
      processors.py             # Processor input/output schemas
```

### SPEC-012-B: BaseProcessor Implementation

```python
# services/workflow/processors/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Generic, TypeVar
import asyncio
import time

from pydantic import BaseModel, ConfigDict

from app.models.workflow import Node
from app.services.workflow.context import ExecutionContext
from .errors import ProcessorValidationError, ProcessorExecutionError
from .metrics import ProcessorMetrics, MetricsCollector

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


@dataclass
class ProcessorConfig:
    """Configuration for processor behavior."""
    timeout_seconds: int = 60
    retry_enabled: bool = True
    max_retries: int = 3
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    backoff_multiplier: float = 2.0
    retry_on_exceptions: list[type[Exception]] = field(
        default_factory=lambda: [TimeoutError, ConnectionError]
    )
    collect_metrics: bool = True


class BaseProcessor(ABC, Generic[InputT, OutputT]):
    """Abstract base class for all node processors.

    TAG: [SPEC-012] [PROCESSOR] [BASE]

    Provides:
    - Lifecycle hooks (pre_process, process, post_process)
    - Input/output validation
    - Error handling with retry logic
    - Metrics collection
    """

    # Subclasses define input/output schema types
    input_schema: type[InputT]
    output_schema: type[OutputT]

    def __init__(
        self,
        node: Node,
        context: ExecutionContext,
        config: ProcessorConfig | None = None,
    ):
        self.node = node
        self.context = context
        self.config = config or ProcessorConfig()
        self.metrics_collector = MetricsCollector()

    async def execute(self, raw_inputs: dict[str, Any]) -> dict[str, Any]:
        """Execute the full processing lifecycle with error handling.

        TAG: [SPEC-012] [PROCESSOR] [EXECUTE]
        """
        metrics = ProcessorMetrics(
            processor_type=self.__class__.__name__,
            node_id=str(self.node.id),
            execution_id=str(self.context.execution_id),
            started_at=datetime.now(UTC),
        )

        try:
            # Step 1: Pre-process (validation + transformation)
            start = time.perf_counter()
            validated_input = await self.pre_process(raw_inputs)
            metrics.pre_process_duration_ms = (time.perf_counter() - start) * 1000

            # Step 2: Process with retry logic
            start = time.perf_counter()
            result = await self._execute_with_retry(validated_input)
            metrics.process_duration_ms = (time.perf_counter() - start) * 1000

            # Step 3: Post-process (serialization)
            start = time.perf_counter()
            output = await self.post_process(result)
            metrics.post_process_duration_ms = (time.perf_counter() - start) * 1000

            metrics.success = True
            return output

        except Exception as e:
            metrics.success = False
            metrics.error_type = type(e).__name__
            raise

        finally:
            metrics.completed_at = datetime.now(UTC)
            metrics.total_duration_ms = (
                metrics.pre_process_duration_ms +
                metrics.process_duration_ms +
                metrics.post_process_duration_ms
            )
            if self.config.collect_metrics:
                self.metrics_collector.record(metrics)

    @abstractmethod
    async def pre_process(self, inputs: dict[str, Any]) -> InputT:
        """Validate and transform raw inputs.

        TAG: [SPEC-012] [PROCESSOR] [PRE]

        Raises:
            ProcessorValidationError: If validation fails
        """
        pass

    @abstractmethod
    async def process(self, validated_input: InputT) -> OutputT:
        """Execute the core processing logic.

        TAG: [SPEC-012] [PROCESSOR] [CORE]
        """
        pass

    @abstractmethod
    async def post_process(self, output: OutputT) -> dict[str, Any]:
        """Transform output to serializable dict.

        TAG: [SPEC-012] [PROCESSOR] [POST]
        """
        pass

    async def _execute_with_retry(self, validated_input: InputT) -> OutputT:
        """Execute process() with retry logic.

        TAG: [SPEC-012] [PROCESSOR] [RETRY]
        """
        last_exception = None
        retry_count = 0

        for attempt in range(self.config.max_retries + 1):
            try:
                return await asyncio.wait_for(
                    self.process(validated_input),
                    timeout=self.config.timeout_seconds,
                )
            except tuple(self.config.retry_on_exceptions) as e:
                last_exception = e
                retry_count = attempt + 1

                if not self.config.retry_enabled:
                    raise ProcessorExecutionError(
                        processor=self.__class__.__name__,
                        node_id=str(self.node.id),
                        message=str(e),
                        retry_count=0,
                    ) from e

                if attempt < self.config.max_retries:
                    delay = min(
                        self.config.initial_delay_seconds * (
                            self.config.backoff_multiplier ** attempt
                        ),
                        self.config.max_delay_seconds,
                    )
                    await asyncio.sleep(delay)

        raise ProcessorExecutionError(
            processor=self.__class__.__name__,
            node_id=str(self.node.id),
            message=str(last_exception),
            retry_count=retry_count,
        ) from last_exception

    # Helper methods for context access
    def get_variable(self, path: str, default: Any = None) -> Any:
        """Get variable from execution context."""
        return self.context.get_variable(path, default)

    def get_node_output(self, node_id: str, key: str | None = None) -> Any:
        """Get output from another node."""
        return self.context.get_node_output(node_id, key)
```

### SPEC-012-C: ProcessorRegistry Implementation

```python
# services/workflow/processors/__init__.py
from typing import Type

from app.models.workflow import Node
from app.services.workflow.context import ExecutionContext
from .base import BaseProcessor, ProcessorConfig
from .tool import ToolNodeProcessor
from .agent import AgentNodeProcessor
from .condition import ConditionNodeProcessor
from .adapter import AdapterNodeProcessor
from .trigger import TriggerNodeProcessor
from .aggregator import AggregatorNodeProcessor
from .errors import ProcessorNotFoundError


class ProcessorRegistry:
    """Registry for dynamic processor lookup and instantiation.

    TAG: [SPEC-012] [REGISTRY]

    Example:
        registry = ProcessorRegistry()
        processor = registry.create("tool", node, context)
        result = await processor.execute(inputs)
    """

    def __init__(self):
        self._processors: dict[str, type[BaseProcessor]] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register default processor types."""
        defaults = {
            "tool": ToolNodeProcessor,
            "agent": AgentNodeProcessor,
            "condition": ConditionNodeProcessor,
            "adapter": AdapterNodeProcessor,
            "trigger": TriggerNodeProcessor,
            "aggregator": AggregatorNodeProcessor,
        }
        for node_type, processor_class in defaults.items():
            self.register(node_type, processor_class)

    def register(
        self,
        node_type: str,
        processor_class: type[BaseProcessor],
    ) -> None:
        """Register a processor class for a node type.

        TAG: [SPEC-012] [REGISTRY] [REGISTER]

        Args:
            node_type: The node type identifier
            processor_class: The processor class to register
        """
        self._processors[node_type] = processor_class

    def get(self, node_type: str) -> type[BaseProcessor]:
        """Get processor class for node type.

        TAG: [SPEC-012] [REGISTRY] [GET]

        Raises:
            ProcessorNotFoundError: If no processor registered for type
        """
        if node_type not in self._processors:
            raise ProcessorNotFoundError(
                f"No processor registered for node type: {node_type}"
            )
        return self._processors[node_type]

    def create(
        self,
        node_type: str,
        node: Node,
        context: ExecutionContext,
        config: ProcessorConfig | None = None,
    ) -> BaseProcessor:
        """Create processor instance with configuration.

        TAG: [SPEC-012] [REGISTRY] [CREATE]
        """
        processor_class = self.get(node_type)
        return processor_class(node=node, context=context, config=config)

    def list_registered(self) -> list[str]:
        """List all registered processor types."""
        return list(self._processors.keys())


# Module-level singleton for convenience
_registry: ProcessorRegistry | None = None


def get_registry() -> ProcessorRegistry:
    """Get the global processor registry singleton."""
    global _registry
    if _registry is None:
        _registry = ProcessorRegistry()
    return _registry
```

### SPEC-012-D: Processor Schemas

```python
# schemas/processors.py
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, ConfigDict


# Tool Processor Schemas
class ToolProcessorInput(BaseModel):
    model_config = ConfigDict(strict=True)

    tool_id: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = Field(default=30, ge=1, le=300)


class ToolProcessorOutput(BaseModel):
    result: Any
    execution_duration_ms: float
    tool_metadata: dict[str, Any] = Field(default_factory=dict)


# Agent Processor Schemas
class AgentProcessorInput(BaseModel):
    model_config = ConfigDict(strict=True)

    agent_id: str
    prompt_variables: dict[str, Any] = Field(default_factory=dict)
    max_tokens: int = Field(default=4096, ge=1, le=128000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)


class AgentProcessorOutput(BaseModel):
    response: str
    structured_output: dict[str, Any] | None = None
    token_usage: dict[str, int] = Field(default_factory=dict)
    model_used: str


# Condition Processor Schemas
class ConditionExpression(BaseModel):
    name: str
    expression: str
    target_node: str


class ConditionProcessorInput(BaseModel):
    conditions: list[ConditionExpression]
    evaluation_context: dict[str, Any] = Field(default_factory=dict)


class ConditionProcessorOutput(BaseModel):
    selected_branch: str
    target_node: str
    evaluated_conditions: list[dict[str, Any]] = Field(default_factory=list)


# Adapter Processor Schemas
class AdapterProcessorInput(BaseModel):
    transformation_type: str
    source_data: Any
    transformation_config: dict[str, Any] = Field(default_factory=dict)


class AdapterProcessorOutput(BaseModel):
    transformed_data: Any
    transformation_applied: str
    records_processed: int = 0


# Trigger Processor Schemas
class TriggerProcessorInput(BaseModel):
    trigger_type: str  # "schedule" | "webhook" | "manual"
    trigger_payload: dict[str, Any] = Field(default_factory=dict)
    trigger_metadata: dict[str, Any] = Field(default_factory=dict)


class TriggerProcessorOutput(BaseModel):
    initialized: bool = True
    context_variables: dict[str, Any] = Field(default_factory=dict)
    trigger_timestamp: datetime


# Aggregator Processor Schemas
class AggregatorProcessorInput(BaseModel):
    strategy: str  # "merge" | "list" | "reduce" | "custom"
    input_sources: dict[str, Any]
    aggregation_config: dict[str, Any] = Field(default_factory=dict)


class AggregatorProcessorOutput(BaseModel):
    aggregated_result: Any
    source_count: int
    strategy_used: str
```

### SPEC-012-E: Processor Errors

```python
# services/workflow/processors/errors.py
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any


class ProcessorError(Exception):
    """Base exception for processor errors.

    TAG: [SPEC-012] [ERROR] [BASE]
    """
    pass


@dataclass
class ProcessorValidationError(ProcessorError):
    """Raised when input/output validation fails.

    TAG: [SPEC-012] [ERROR] [VALIDATION]
    """
    processor: str
    errors: list[dict[str, Any]]

    def __str__(self) -> str:
        return f"Validation failed in {self.processor}: {self.errors}"


@dataclass
class ProcessorExecutionError(ProcessorError):
    """Raised when processing fails after retries.

    TAG: [SPEC-012] [ERROR] [EXECUTION]
    """
    processor: str
    node_id: str
    message: str
    retry_count: int = 0

    def __str__(self) -> str:
        return (
            f"Execution failed in {self.processor} "
            f"(node: {self.node_id}, retries: {self.retry_count}): {self.message}"
        )


@dataclass
class ProcessorTimeoutError(ProcessorError):
    """Raised when processing exceeds timeout.

    TAG: [SPEC-012] [ERROR] [TIMEOUT]
    """
    processor: str
    node_id: str
    timeout_seconds: int

    def __str__(self) -> str:
        return (
            f"Timeout in {self.processor} "
            f"(node: {self.node_id}) after {self.timeout_seconds}s"
        )


@dataclass
class ProcessorConfigurationError(ProcessorError):
    """Raised when processor configuration is invalid.

    TAG: [SPEC-012] [ERROR] [CONFIG]
    """
    processor: str
    message: str

    def __str__(self) -> str:
        return f"Configuration error in {self.processor}: {self.message}"


class ProcessorNotFoundError(ProcessorError):
    """Raised when requested processor type is not registered.

    TAG: [SPEC-012] [ERROR] [NOT_FOUND]
    """
    pass
```

### SPEC-012-F: Metrics Collection

```python
# services/workflow/processors/metrics.py
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any
import threading


@dataclass
class ProcessorMetrics:
    """Metrics collected for a single processor invocation.

    TAG: [SPEC-012] [METRICS]
    """
    processor_type: str
    node_id: str
    execution_id: str

    # Timing
    pre_process_duration_ms: float = 0.0
    process_duration_ms: float = 0.0
    post_process_duration_ms: float = 0.0
    total_duration_ms: float = 0.0

    # Status
    success: bool = False
    retry_count: int = 0
    error_type: str | None = None

    # Resource usage
    input_size_bytes: int = 0
    output_size_bytes: int = 0

    # Timestamps
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None


class MetricsCollector:
    """Thread-safe metrics collector for processors.

    TAG: [SPEC-012] [METRICS] [COLLECTOR]
    """

    def __init__(self):
        self._metrics: list[ProcessorMetrics] = []
        self._lock = threading.Lock()

    def record(self, metrics: ProcessorMetrics) -> None:
        """Record processor metrics."""
        with self._lock:
            self._metrics.append(metrics)

    def get_metrics(
        self,
        execution_id: str | None = None,
        processor_type: str | None = None,
    ) -> list[ProcessorMetrics]:
        """Get recorded metrics with optional filters."""
        with self._lock:
            result = self._metrics.copy()

        if execution_id:
            result = [m for m in result if m.execution_id == execution_id]
        if processor_type:
            result = [m for m in result if m.processor_type == processor_type]

        return result

    def get_summary(self, execution_id: str) -> dict[str, Any]:
        """Get aggregated summary for an execution.

        TAG: [SPEC-012] [METRICS] [SUMMARY]
        """
        metrics = self.get_metrics(execution_id=execution_id)

        if not metrics:
            return {}

        total_duration = sum(m.total_duration_ms for m in metrics)
        success_count = sum(1 for m in metrics if m.success)
        failure_count = len(metrics) - success_count

        by_type: dict[str, list[ProcessorMetrics]] = {}
        for m in metrics:
            by_type.setdefault(m.processor_type, []).append(m)

        return {
            "execution_id": execution_id,
            "total_processors": len(metrics),
            "success_count": success_count,
            "failure_count": failure_count,
            "success_rate": success_count / len(metrics) if metrics else 0,
            "total_duration_ms": total_duration,
            "by_processor_type": {
                ptype: {
                    "count": len(pmetrics),
                    "avg_duration_ms": sum(m.total_duration_ms for m in pmetrics) / len(pmetrics),
                    "success_rate": sum(1 for m in pmetrics if m.success) / len(pmetrics),
                }
                for ptype, pmetrics in by_type.items()
            },
        }

    def clear(self, execution_id: str | None = None) -> None:
        """Clear recorded metrics."""
        with self._lock:
            if execution_id:
                self._metrics = [
                    m for m in self._metrics if m.execution_id != execution_id
                ]
            else:
                self._metrics.clear()
```

---

## Constraints

### Technical Constraints

- All processor methods must be async/await compatible
- Input/output validation must use Pydantic v2 with `model_config = ConfigDict()`
- Retry logic must not retry validation errors
- Metrics collection must be thread-safe

### Performance Constraints

- Pre-process validation should complete in < 10ms
- Metrics collection overhead should be < 1ms per invocation
- ProcessorRegistry lookup should be O(1)
- Memory usage per processor instance should be < 1MB

### Security Constraints

- Sensitive data must be sanitized before logging/metrics
- User-defined transformations (adapter) must be sandboxed
- No arbitrary code execution in condition expressions

---

## Dependencies

### Internal Dependencies

- SPEC-001: Base models and mixins (BaseTimestampMixin, BaseUUIDMixin)
- SPEC-003: Node model definition (Node, NodeType)
- SPEC-009: ToolRegistry, AgentManager (external service access)
- SPEC-011: ExecutionContext, ExecutionConfig (execution layer)

### External Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| pydantic | >=2.10.0 | Input/output validation |
| asyncio | builtin | Async processing |

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Validation overhead in hot path | Medium | Medium | Schema caching, optional strict mode |
| Memory leak from metrics accumulation | Low | High | Periodic cleanup, max metrics limit |
| Retry storms from misconfiguration | Medium | Medium | Global retry budget, circuit breaker |
| Type confusion between processors | Low | Medium | Strong typing, registry validation |

---

## Related SPECs

- **SPEC-001**: Base Models (mixins, enums used by processors)
- **SPEC-003**: Workflow Domain Models (Node, NodeType definitions)
- **SPEC-009**: Tool/Agent API (ToolRegistry, AgentManager integration)
- **SPEC-010**: DAG Validation (pre-execution validation)
- **SPEC-011**: Workflow Execution Engine (BaseNodeExecutor, ExecutionContext)

---

## HISTORY

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-16 | binee | Initial SPEC creation |
