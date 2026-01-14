"""Workflow validation package.

TAG: [SPEC-010] [DAG] [VALIDATION]

This package provides standalone DAG validation services for workflow graphs.
All components are designed for parallel development with no conflicts to
existing codebase.

Components:
- Graph: Generic directed graph data structure
- GraphAlgorithms: Graph algorithm collection (cycle detection, topology)
- DAGValidator: Main validation service
- Exceptions: Custom exception hierarchy

Example:
    >>> from app.services.workflow import DAGValidator, Graph
    >>> validator = DAGValidator(db_session)
    >>> result = await validator.validate_workflow(workflow_id)
"""

from app.services.workflow.algorithms import GraphAlgorithms
from app.services.workflow.exceptions import (
    DAGValidationError,
    CycleDetectedError,
    GraphTooLargeError,
    InvalidNodeReferenceError,
    ValidationTimeoutError,
)
from app.services.workflow.graph import Graph
from app.services.workflow.validator import DAGValidator

__all__ = [
    # Data structures
    "Graph",
    # Algorithms
    "GraphAlgorithms",
    # Validator
    "DAGValidator",
    # Exceptions
    "DAGValidationError",
    "CycleDetectedError",
    "InvalidNodeReferenceError",
    "GraphTooLargeError",
    "ValidationTimeoutError",
]
