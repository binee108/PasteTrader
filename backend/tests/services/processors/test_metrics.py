"""Tests for processor metrics collection.

TAG: [SPEC-012] [PROCESSOR] [TEST] [METRICS]
REQ: REQ-012-008, REQ-012-009 - Processing Metrics and Aggregation
"""

import pytest
import threading
import time
from datetime import datetime, UTC
from concurrent.futures import ThreadPoolExecutor


class TestProcessorMetricsDataclass:
    """Test ProcessorMetrics dataclass structure."""

    def test_metrics_dataclass_creation(self):
        """Test ProcessorMetrics can be created with required fields."""
        from app.services.workflow.processors.metrics import ProcessorMetrics

        metrics = ProcessorMetrics(
            processor_type="ToolProcessor",
            node_id="node-123",
            execution_id="exec-456",
        )

        assert metrics.processor_type == "ToolProcessor"
        assert metrics.node_id == "node-123"
        assert metrics.execution_id == "exec-456"
        assert metrics.started_at is not None
        assert isinstance(metrics.started_at, datetime)

    def test_metrics_dataclass_default_values(self):
        """Test ProcessorMetrics has correct default values."""
        from app.services.workflow.processors.metrics import ProcessorMetrics

        metrics = ProcessorMetrics(
            processor_type="AgentProcessor",
            node_id="node-789",
            execution_id="exec-101",
        )

        # Timing defaults
        assert metrics.pre_process_duration_ms == 0.0
        assert metrics.process_duration_ms == 0.0
        assert metrics.post_process_duration_ms == 0.0
        assert metrics.total_duration_ms == 0.0

        # Status defaults
        assert metrics.success is False
        assert metrics.retry_count == 0
        assert metrics.error_type is None

        # Resource defaults
        assert metrics.input_size_bytes == 0
        assert metrics.output_size_bytes == 0

        # Timestamp defaults
        assert metrics.completed_at is None

    def test_metrics_dataclass_with_all_fields(self):
        """Test ProcessorMetrics with all fields set."""
        from app.services.workflow.processors.metrics import ProcessorMetrics

        started = datetime.now(UTC)
        completed = datetime.now(UTC)

        metrics = ProcessorMetrics(
            processor_type="ConditionProcessor",
            node_id="node-202",
            execution_id="exec-303",
            pre_process_duration_ms=1.5,
            process_duration_ms=10.2,
            post_process_duration_ms=0.8,
            total_duration_ms=12.5,
            success=True,
            retry_count=0,
            error_type=None,
            input_size_bytes=1024,
            output_size_bytes=2048,
            started_at=started,
            completed_at=completed,
        )

        assert metrics.pre_process_duration_ms == 1.5
        assert metrics.process_duration_ms == 10.2
        assert metrics.post_process_duration_ms == 0.8
        assert metrics.total_duration_ms == 12.5
        assert metrics.success is True
        assert metrics.input_size_bytes == 1024
        assert metrics.output_size_bytes == 2048


class TestMetricsCollector:
    """Test MetricsCollector functionality."""

    def test_collector_initialization(self):
        """Test MetricsCollector initializes with empty metrics list."""
        from app.services.workflow.processors.metrics import MetricsCollector

        collector = MetricsCollector()

        assert collector._metrics == []
        assert len(collector._metrics) == 0

    def test_record_single_metric(self):
        """Test recording a single metric."""
        from app.services.workflow.processors.metrics import (
            MetricsCollector,
            ProcessorMetrics,
        )

        collector = MetricsCollector()
        metrics = ProcessorMetrics(
            processor_type="ToolProcessor",
            node_id="node-1",
            execution_id="exec-1",
        )

        collector.record(metrics)

        assert len(collector._metrics) == 1
        assert collector._metrics[0] is metrics

    def test_record_multiple_metrics(self):
        """Test recording multiple metrics."""
        from app.services.workflow.processors.metrics import (
            MetricsCollector,
            ProcessorMetrics,
        )

        collector = MetricsCollector()

        for i in range(5):
            metrics = ProcessorMetrics(
                processor_type=f"Processor{i}",
                node_id=f"node-{i}",
                execution_id="exec-1",
            )
            collector.record(metrics)

        assert len(collector._metrics) == 5

    def test_get_metrics_without_filters(self):
        """Test getting all metrics without filters."""
        from app.services.workflow.processors.metrics import (
            MetricsCollector,
            ProcessorMetrics,
        )

        collector = MetricsCollector()

        # Record 3 metrics for same execution
        for i in range(3):
            metrics = ProcessorMetrics(
                processor_type="ToolProcessor",
                node_id=f"node-{i}",
                execution_id="exec-123",
            )
            collector.record(metrics)

        all_metrics = collector.get_metrics()

        assert len(all_metrics) == 3

    def test_get_metrics_with_execution_id_filter(self):
        """Test filtering metrics by execution_id."""
        from app.services.workflow.processors.metrics import (
            MetricsCollector,
            ProcessorMetrics,
        )

        collector = MetricsCollector()

        # Record metrics for different executions
        collector.record(
            ProcessorMetrics(
                processor_type="ToolProcessor",
                node_id="node-1",
                execution_id="exec-1",
            )
        )
        collector.record(
            ProcessorMetrics(
                processor_type="AgentProcessor",
                node_id="node-2",
                execution_id="exec-2",
            )
        )
        collector.record(
            ProcessorMetrics(
                processor_type="ToolProcessor",
                node_id="node-3",
                execution_id="exec-1",
            )
        )

        # Filter by execution_id
        exec1_metrics = collector.get_metrics(execution_id="exec-1")

        assert len(exec1_metrics) == 2
        assert all(m.execution_id == "exec-1" for m in exec1_metrics)

    def test_get_metrics_with_processor_type_filter(self):
        """Test filtering metrics by processor_type."""
        from app.services.workflow.processors.metrics import (
            MetricsCollector,
            ProcessorMetrics,
        )

        collector = MetricsCollector()

        # Record different processor types
        collector.record(
            ProcessorMetrics(
                processor_type="ToolProcessor",
                node_id="node-1",
                execution_id="exec-1",
            )
        )
        collector.record(
            ProcessorMetrics(
                processor_type="AgentProcessor",
                node_id="node-2",
                execution_id="exec-1",
            )
        )
        collector.record(
            ProcessorMetrics(
                processor_type="ToolProcessor",
                node_id="node-3",
                execution_id="exec-2",
            )
        )

        # Filter by processor_type
        tool_metrics = collector.get_metrics(processor_type="ToolProcessor")

        assert len(tool_metrics) == 2
        assert all(m.processor_type == "ToolProcessor" for m in tool_metrics)

    def test_get_metrics_with_both_filters(self):
        """Test filtering metrics by both execution_id and processor_type."""
        from app.services.workflow.processors.metrics import (
            MetricsCollector,
            ProcessorMetrics,
        )

        collector = MetricsCollector()

        # Record various metrics
        collector.record(
            ProcessorMetrics(
                processor_type="ToolProcessor",
                node_id="node-1",
                execution_id="exec-1",
            )
        )
        collector.record(
            ProcessorMetrics(
                processor_type="AgentProcessor",
                node_id="node-2",
                execution_id="exec-1",
            )
        )
        collector.record(
            ProcessorMetrics(
                processor_type="ToolProcessor",
                node_id="node-3",
                execution_id="exec-2",
            )
        )

        # Filter by both
        filtered = collector.get_metrics(
            execution_id="exec-1", processor_type="ToolProcessor"
        )

        assert len(filtered) == 1
        assert filtered[0].processor_type == "ToolProcessor"
        assert filtered[0].execution_id == "exec-1"

    def test_get_summary_for_execution(self):
        """Test getting aggregated summary for an execution."""
        from app.services.workflow.processors.metrics import (
            MetricsCollector,
            ProcessorMetrics,
        )

        collector = MetricsCollector()

        # Record successful metrics
        for i in range(3):
            metrics = ProcessorMetrics(
                processor_type="ToolProcessor",
                node_id=f"node-{i}",
                execution_id="exec-test",
                success=True,
                total_duration_ms=10.0 + i * 5.0,
            )
            collector.record(metrics)

        # Record one failed metric
        collector.record(
            ProcessorMetrics(
                processor_type="ToolProcessor",
                node_id="node-4",
                execution_id="exec-test",
                success=False,
                total_duration_ms=5.0,
                error_type="TimeoutError",
            )
        )

        summary = collector.get_summary("exec-test")

        assert summary["execution_id"] == "exec-test"
        assert summary["total_processors"] == 4
        assert summary["success_count"] == 3
        assert summary["failure_count"] == 1
        assert summary["success_rate"] == 0.75
        # Total: 10.0 + 15.0 + 20.0 + 5.0 = 50.0
        assert summary["total_duration_ms"] == 50.0
        assert "by_processor_type" in summary

    def test_get_summary_for_empty_execution(self):
        """Test getting summary for execution with no metrics."""
        from app.services.workflow.processors.metrics import MetricsCollector

        collector = MetricsCollector()

        summary = collector.get_summary("nonexistent-exec")

        assert summary == {}

    def test_clear_all_metrics(self):
        """Test clearing all metrics."""
        from app.services.workflow.processors.metrics import (
            MetricsCollector,
            ProcessorMetrics,
        )

        collector = MetricsCollector()

        # Record some metrics
        for i in range(3):
            metrics = ProcessorMetrics(
                processor_type="ToolProcessor",
                node_id=f"node-{i}",
                execution_id="exec-1",
            )
            collector.record(metrics)

        assert len(collector._metrics) == 3

        # Clear all
        collector.clear()

        assert len(collector._metrics) == 0

    def test_clear_metrics_by_execution_id(self):
        """Test clearing metrics for specific execution_id."""
        from app.services.workflow.processors.metrics import (
            MetricsCollector,
            ProcessorMetrics,
        )

        collector = MetricsCollector()

        # Record metrics for different executions
        collector.record(
            ProcessorMetrics(
                processor_type="ToolProcessor",
                node_id="node-1",
                execution_id="exec-1",
            )
        )
        collector.record(
            ProcessorMetrics(
                processor_type="AgentProcessor",
                node_id="node-2",
                execution_id="exec-2",
            )
        )
        collector.record(
            ProcessorMetrics(
                processor_type="ToolProcessor",
                node_id="node-3",
                execution_id="exec-1",
            )
        )

        assert len(collector._metrics) == 3

        # Clear only exec-1
        collector.clear(execution_id="exec-1")

        assert len(collector._metrics) == 1
        assert collector._metrics[0].execution_id == "exec-2"


class TestMetricsCollectorThreadSafety:
    """Test thread-safe operations of MetricsCollector."""

    def test_concurrent_record_safety(self):
        """Test that concurrent record operations are thread-safe."""
        from app.services.workflow.processors.metrics import (
            MetricsCollector,
            ProcessorMetrics,
        )

        collector = MetricsCollector()
        num_threads = 10
        records_per_thread = 100

        def record_metrics(thread_id: int):
            for i in range(records_per_thread):
                metrics = ProcessorMetrics(
                    processor_type=f"Processor{thread_id}",
                    node_id=f"node-{thread_id}-{i}",
                    execution_id=f"exec-{thread_id}",
                )
                collector.record(metrics)

        # Run threads concurrently
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=record_metrics, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify all metrics were recorded
        expected_count = num_threads * records_per_thread
        assert len(collector._metrics) == expected_count

    def test_concurrent_read_write_safety(self):
        """Test that concurrent reads and writes are safe."""
        from app.services.workflow.processors.metrics import (
            MetricsCollector,
            ProcessorMetrics,
        )

        collector = MetricsCollector()

        def write_metrics():
            for i in range(50):
                metrics = ProcessorMetrics(
                    processor_type="Writer",
                    node_id=f"node-{i}",
                    execution_id="exec-write",
                )
                collector.record(metrics)
                time.sleep(0.001)

        def read_metrics():
            for _ in range(50):
                try:
                    collector.get_metrics()
                except Exception:
                    pytest.fail("get_metrics raised exception during concurrent access")
                time.sleep(0.001)

        # Start threads
        write_thread = threading.Thread(target=write_metrics)
        read_thread = threading.Thread(target=read_metrics)

        write_thread.start()
        read_thread.start()

        write_thread.join()
        read_thread.join()

        # Verify no data corruption
        assert len(collector._metrics) == 50

    def test_concurrent_clear_safety(self):
        """Test that concurrent clear operations are safe."""
        from app.services.workflow.processors.metrics import (
            MetricsCollector,
            ProcessorMetrics,
        )

        collector = MetricsCollector()

        # Populate metrics
        for i in range(100):
            metrics = ProcessorMetrics(
                processor_type="TestProcessor",
                node_id=f"node-{i}",
                execution_id=f"exec-{i % 5}",  # 5 different executions
            )
            collector.record(metrics)

        def clear_specific_execution(exec_id: str):
            collector.clear(execution_id=exec_id)

        # Clear different executions concurrently
        threads = []
        for i in range(5):
            thread = threading.Thread(target=clear_specific_execution, args=(f"exec-{i}",))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All should be cleared
        assert len(collector._metrics) == 0
