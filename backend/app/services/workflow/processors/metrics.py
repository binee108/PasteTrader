"""Processor Metrics Collection.

TAG: [SPEC-012] [PROCESSOR] [METRICS]
REQ: REQ-012-008, REQ-012-009 - Processing Metrics and Aggregation
"""

import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class ProcessorMetrics:
    """Metrics collected for a single processor invocation.

    TAG: [SPEC-012] [METRICS]

    Attributes:
        processor_type: Type of processor (e.g., "ToolProcessor")
        node_id: ID of the node being processed
        execution_id: ID of the workflow execution
        pre_process_duration_ms: Duration of pre_process in milliseconds
        process_duration_ms: Duration of process in milliseconds
        post_process_duration_ms: Duration of post_process in milliseconds
        total_duration_ms: Total processing duration in milliseconds
        success: Whether processing succeeded
        retry_count: Number of retry attempts
        error_type: Type of error if failed
        input_size_bytes: Size of input data in bytes
        output_size_bytes: Size of output data in bytes
        started_at: When processing started
        completed_at: When processing completed
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

    Provides thread-safe recording, querying, and aggregation of processor metrics.
    """

    def __init__(self) -> None:
        self._metrics: list[ProcessorMetrics] = []
        self._lock = threading.Lock()

    def record(self, metrics: ProcessorMetrics) -> None:
        """Record processor metrics in a thread-safe manner.

        TAG: [SPEC-012] [METRICS] [RECORD]

        Args:
            metrics: The metrics to record
        """
        with self._lock:
            self._metrics.append(metrics)

    def get_metrics(
        self,
        execution_id: str | None = None,
        processor_type: str | None = None,
    ) -> list[ProcessorMetrics]:
        """Get recorded metrics with optional filters.

        TAG: [SPEC-012] [METRICS] [GET]

        Args:
            execution_id: Filter by execution ID
            processor_type: Filter by processor type

        Returns:
            List of metrics matching the filter criteria
        """
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

        Args:
            execution_id: The execution ID to summarize

        Returns:
            Dictionary with summary statistics or empty dict if no metrics
        """
        metrics = self.get_metrics(execution_id=execution_id)

        if not metrics:
            return {}

        total_duration = sum(m.total_duration_ms for m in metrics)
        success_count = sum(1 for m in metrics if m.success)
        failure_count = len(metrics) - success_count

        # Group by processor type
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
                    "avg_duration_ms": (
                        sum(m.total_duration_ms for m in pmetrics) / len(pmetrics)
                    ),
                    "success_rate": (
                        sum(1 for m in pmetrics if m.success) / len(pmetrics)
                    ),
                }
                for ptype, pmetrics in by_type.items()
            },
        }

    def clear(self, execution_id: str | None = None) -> None:
        """Clear recorded metrics.

        TAG: [SPEC-012] [METRICS] [CLEAR]

        Args:
            execution_id: If provided, only clear metrics for this execution.
                        If None, clear all metrics.
        """
        with self._lock:
            if execution_id:
                self._metrics = [
                    m for m in self._metrics if m.execution_id != execution_id
                ]
            else:
                self._metrics.clear()
