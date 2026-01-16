"""Base Processor Abstract Class.

TAG: [SPEC-012] [PROCESSOR] [BASE]
REQ: REQ-012-001, REQ-012-002, REQ-012-003, REQ-012-004, REQ-012-005
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Generic, TypeVar
import asyncio
import time

from pydantic import BaseModel
from pydantic import ValidationError

from app.models.workflow import Node
from app.services.workflow.context import ExecutionContext
from .errors import (
    ProcessorValidationError,
    ProcessorExecutionError,
    ProcessorTimeoutError,
)
from .metrics import ProcessorMetrics, MetricsCollector

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


@dataclass
class ProcessorConfig:
    """Configuration for processor behavior.

    TAG: [SPEC-012] [PROCESSOR] [CONFIG]

    Attributes:
        timeout_seconds: Maximum execution time in seconds
        retry_enabled: Whether to retry on failures
        max_retries: Maximum number of retry attempts
        initial_delay_seconds: Initial retry delay in seconds
        max_delay_seconds: Maximum retry delay in seconds
        backoff_multiplier: Multiplier for exponential backoff
        retry_on_exceptions: Exception types that trigger retries
        collect_metrics: Whether to collect execution metrics
    """

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
    - Context access helpers

    Type Parameters:
        InputT: Input Pydantic model type
        OutputT: Output Pydantic model type
    """

    # Subclasses must define these
    input_schema: type[InputT]
    output_schema: type[OutputT]

    def __init__(
        self,
        node: Node,
        context: ExecutionContext,
        config: ProcessorConfig | None = None,
    ):
        """Initialize processor.

        Args:
            node: The workflow node being processed
            context: Execution context for variable/output access
            config: Processor configuration (uses defaults if None)
        """
        self.node = node
        self.context = context
        self.config = config or ProcessorConfig()
        self.metrics_collector = MetricsCollector()

    async def execute(self, raw_inputs: dict[str, Any]) -> dict[str, Any]:
        """Execute the full processing lifecycle with error handling.

        TAG: [SPEC-012] [PROCESSOR] [EXECUTE]

        This method orchestrates the complete processing lifecycle:
        1. Pre-process: Validate and transform inputs
        2. Process: Execute core logic with retry
        3. Post-process: Serialize output
        4. Collect metrics throughout

        Args:
            raw_inputs: Raw input data from previous node or trigger

        Returns:
            Serialized output dictionary for downstream nodes

        Raises:
            ProcessorValidationError: If input/output validation fails
            ProcessorExecutionError: If processing fails after retries
            ProcessorTimeoutError: If execution exceeds timeout
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
                metrics.pre_process_duration_ms
                + metrics.process_duration_ms
                + metrics.post_process_duration_ms
            )
            if self.config.collect_metrics:
                self.metrics_collector.record(metrics)

    @abstractmethod
    async def pre_process(self, inputs: dict[str, Any]) -> InputT:
        """Validate and transform raw inputs into typed input model.

        TAG: [SPEC-012] [PROCESSOR] [PRE]

        This method should:
        - Validate inputs against input_schema
        - Transform raw data into typed model
        - Raise ProcessorValidationError on validation failure

        Args:
            inputs: Raw input dictionary

        Returns:
            Validated and typed input model

        Raises:
            ProcessorValidationError: If validation fails
        """
        pass

    @abstractmethod
    async def process(self, validated_input: InputT) -> OutputT:
        """Execute the core processing logic.

        TAG: [SPEC-012] [PROCESSOR] [CORE]

        This method contains the main processing logic for the node type.
        It receives validated input and should return validated output.

        Args:
            validated_input: Validated input model from pre_process

        Returns:
            Validated output model

        Raises:
            Any processor-specific exceptions (will be retried if configured)
        """
        pass

    @abstractmethod
    async def post_process(self, output: OutputT) -> dict[str, Any]:
        """Transform output model into serializable dictionary.

        TAG: [SPEC-012] [PROCESSOR] [POST]

        This method should:
        - Convert output model to dictionary
        - Add any metadata or formatting
        - Return data suitable for downstream nodes

        Args:
            output: Validated output model from process

        Returns:
            Serializable dictionary for downstream consumption
        """
        pass

    async def _execute_with_retry(self, validated_input: InputT) -> OutputT:
        """Execute process() with retry logic.

        TAG: [SPEC-012] [PROCESSOR] [RETRY]

        Implements exponential backoff retry for configured exception types.

        Args:
            validated_input: Validated input to pass to process()

        Returns:
            Output from process()

        Raises:
            ProcessorExecutionError: If all retries exhausted
            ProcessorTimeoutError: If execution exceeds timeout
        """
        last_exception = None
        retry_count = 0

        for attempt in range(self.config.max_retries + 1):
            try:
                # Execute with timeout
                return await asyncio.wait_for(
                    self.process(validated_input),
                    timeout=self.config.timeout_seconds,
                )
            except asyncio.TimeoutError:
                # Timeout is NOT retriable - raise immediately
                raise ProcessorTimeoutError(
                    processor=self.__class__.__name__,
                    node_id=str(self.node.id),
                    timeout_seconds=self.config.timeout_seconds,
                )
            except tuple(self.config.retry_on_exceptions) as e:
                last_exception = e
                retry_count = attempt + 1

                # Don't retry if retry is disabled
                if not self.config.retry_enabled:
                    raise ProcessorExecutionError(
                        processor=self.__class__.__name__,
                        node_id=str(self.node.id),
                        message=str(e),
                        retry_count=0,
                    ) from e

                # Don't delay after last attempt
                if attempt < self.config.max_retries:
                    # Calculate exponential backoff delay
                    delay = min(
                        self.config.initial_delay_seconds
                        * (self.config.backoff_multiplier**attempt),
                        self.config.max_delay_seconds,
                    )
                    await asyncio.sleep(delay)
            except Exception as e:
                # Non-retriable exception - fail immediately
                raise ProcessorExecutionError(
                    processor=self.__class__.__name__,
                    node_id=str(self.node.id),
                    message=str(e),
                    retry_count=0,
                ) from e

        # All retries exhausted
        raise ProcessorExecutionError(
            processor=self.__class__.__name__,
            node_id=str(self.node.id),
            message=str(last_exception),
            retry_count=retry_count,
        ) from last_exception

    # Context helper methods
    def get_variable(self, path: str, default: Any = None) -> Any:
        """Get variable from execution context.

        TAG: [SPEC-012] [PROCESSOR] [CONTEXT] [GET_VARIABLE]

        Convenience method for accessing execution variables with dot notation.

        Args:
            path: Variable path (e.g., "user.id" or "api_key")
            default: Default value if variable not found

        Returns:
            Variable value or default
        """
        return self.context.get_variable(path, default)

    def get_node_output(self, node_id: str, key: str | None = None) -> Any:
        """Get output from a previously executed node.

        TAG: [SPEC-012] [PROCESSOR] [CONTEXT] [GET_NODE_OUTPUT]

        Convenience method for accessing outputs from other nodes.

        Args:
            node_id: ID of the node to get output from
            key: Optional key within the node output

        Returns:
            Node output value or entire output dict if key is None

        Raises:
            KeyError: If node_id or key not found
        """
        return self.context.get_node_output(node_id, key)
