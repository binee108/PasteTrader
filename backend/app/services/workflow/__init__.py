"""Workflow validation and execution package.

TAG: [SPEC-010] [DAG] [VALIDATION]
TAG: [SPEC-011] [EXECUTION] [EXECUTOR]

This package provides DAG validation services and workflow execution
for workflow graphs. All components are designed for parallel development
with no conflicts to existing codebase.

Components:
Validation (SPEC-010):
- Graph: Generic directed graph data structure
- GraphAlgorithms: Graph algorithm collection (cycle detection, topology)
- DAGValidator: Main validation service
- DAG Exceptions: Custom exception hierarchy for validation

Execution (SPEC-011):
- WorkflowExecutor: DAG-based workflow execution engine
- ExecutionContext: Thread-safe context for node data passing
- Execution Exceptions: Custom exception hierarchy for execution

Example:
    >>> from app.services.workflow import DAGValidator, WorkflowExecutor
    >>> validator = DAGValidator(db_session)
    >>> result = await validator.validate_workflow(workflow_id)
    >>> executor = WorkflowExecutor(db_session)
    >>> exec_result = await executor.execute(workflow_id, input_data)
"""

# ============================================================================
# SPEC-010: DAG Validation Components
# ============================================================================

from app.services.workflow.algorithms import GraphAlgorithms
from app.services.workflow.exceptions import (
    CycleDetectedError,
    DAGValidationError,
    GraphTooLargeError,
    InvalidNodeReferenceError,
    ValidationTimeoutError,
)
from app.services.workflow.graph import Graph
from app.services.workflow.validator import DAGValidator

# ============================================================================
# SPEC-011: Workflow Execution Components
# ============================================================================

from app.services.workflow.context import ExecutionContext
from app.services.workflow.exceptions import (
    ConditionEvaluationError,
    ExecutionCancelledError,
    ExecutionError,
    NodeExecutionError,
    NodeTimeoutError,
)
from app.services.workflow.executor import ExecutionResult, WorkflowExecutor

__all__ = [
    # ============================================================================
    # SPEC-010: DAG Validation
    # ============================================================================
    # Data structures
    "Graph",
    # Algorithms
    "GraphAlgorithms",
    # Validator
    "DAGValidator",
    # DAG Exceptions
    "CycleDetectedError",
    "DAGValidationError",
    "GraphTooLargeError",
    "InvalidNodeReferenceError",
    "ValidationTimeoutError",
    # ============================================================================
    # SPEC-011: Workflow Execution
    # ============================================================================
    # Executor
    "WorkflowExecutor",
    "ExecutionResult",
    # Context
    "ExecutionContext",
    # Execution Exceptions
    "ConditionEvaluationError",
    "ExecutionCancelledError",
    "ExecutionError",
    "NodeExecutionError",
    "NodeTimeoutError",
]
