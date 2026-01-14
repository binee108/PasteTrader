"""Pydantic schemas for request/response validation.

TAG: [SPEC-007] [SCHEMAS]
REQ: REQ-001 - Schema Package Exports

This package contains all Pydantic models for API validation.
Exports all schemas for convenient importing.
"""

# Base schemas and utilities
# Agent schemas
from app.schemas.agent import (
    AgentBase,
    AgentCreate,
    AgentListResponse,
    AgentResponse,
    AgentToolAdd,
    AgentUpdate,
)
from app.schemas.base import (
    BaseResponse,
    BaseSchema,
    ConfigField,
    DescriptionField,
    ErrorResponse,
    MessageResponse,
    NameField,
    OptionalNameField,
    PaginatedResponse,
    PaginationParams,
    SuccessResponse,
    VersionField,
)

# Execution schemas
from app.schemas.execution import (
    ExecutionCancel,
    ExecutionContext,
    ExecutionLogBase,
    ExecutionLogCreate,
    ExecutionLogPaginatedResponse,
    ExecutionLogResponse,
    ExecutionMetadata,
    ExecutionResume,
    ExecutionRetry,
    ExecutionStatistics,
    NodeExecutionBase,
    NodeExecutionCreate,
    NodeExecutionPaginatedResponse,
    NodeExecutionResponse,
    NodeExecutionUpdate,
    NodeExecutionWithLogs,
    WorkflowExecutionBase,
    WorkflowExecutionCreate,
    WorkflowExecutionDetail,
    WorkflowExecutionListResponse,
    WorkflowExecutionPaginatedResponse,
    WorkflowExecutionResponse,
    WorkflowExecutionStatistics,
    WorkflowExecutionWithNodes,
)

# Tool schemas
from app.schemas.tool import (
    ToolBase,
    ToolCreate,
    ToolListResponse,
    ToolResponse,
    ToolTestRequest,
    ToolTestResponse,
    ToolUpdate,
)

# Workflow schemas
from app.schemas.workflow import (
    EdgeBase,
    EdgeBatchCreate,
    EdgeCreate,
    EdgePaginatedResponse,
    EdgeResponse,
    NodeBase,
    NodeBatchCreate,
    NodeCreate,
    NodePaginatedResponse,
    NodeResponse,
    NodeUpdate,
    RetryConfig,
    WorkflowBase,
    WorkflowCreate,
    WorkflowExportData,
    WorkflowGraphUpdate,
    WorkflowImport,
    WorkflowListResponse,
    WorkflowPaginatedResponse,
    WorkflowResponse,
    WorkflowUpdate,
    WorkflowWithNodes,
)

__all__ = [
    # Agent schemas
    "AgentBase",
    "AgentCreate",
    "AgentListResponse",
    "AgentResponse",
    "AgentToolAdd",
    "AgentUpdate",
    # Base schemas
    "BaseResponse",
    "BaseSchema",
    "ConfigField",
    "DescriptionField",
    # Workflow schemas
    "EdgeBase",
    "EdgeBatchCreate",
    "EdgeCreate",
    "EdgePaginatedResponse",
    "EdgeResponse",
    "ErrorResponse",
    # Execution schemas
    "ExecutionCancel",
    "ExecutionContext",
    "ExecutionLogBase",
    "ExecutionLogCreate",
    "ExecutionLogPaginatedResponse",
    "ExecutionLogResponse",
    "ExecutionMetadata",
    "ExecutionResume",
    "ExecutionRetry",
    "ExecutionStatistics",
    "MessageResponse",
    "NameField",
    "NodeBase",
    "NodeBatchCreate",
    "NodeCreate",
    "NodeExecutionBase",
    "NodeExecutionCreate",
    "NodeExecutionPaginatedResponse",
    "NodeExecutionResponse",
    "NodeExecutionUpdate",
    "NodeExecutionWithLogs",
    "NodePaginatedResponse",
    "NodeResponse",
    "NodeUpdate",
    "OptionalNameField",
    "PaginatedResponse",
    "PaginationParams",
    "RetryConfig",
    "SuccessResponse",
    # Tool schemas
    "ToolBase",
    "ToolCreate",
    "ToolListResponse",
    "ToolResponse",
    "ToolTestRequest",
    "ToolTestResponse",
    "ToolUpdate",
    "VersionField",
    "WorkflowBase",
    "WorkflowCreate",
    "WorkflowExecutionBase",
    "WorkflowExecutionCreate",
    "WorkflowExecutionDetail",
    "WorkflowExecutionListResponse",
    "WorkflowExecutionPaginatedResponse",
    "WorkflowExecutionResponse",
    "WorkflowExecutionStatistics",
    "WorkflowExecutionWithNodes",
    "WorkflowExportData",
    "WorkflowGraphUpdate",
    "WorkflowImport",
    "WorkflowListResponse",
    "WorkflowPaginatedResponse",
    "WorkflowResponse",
    "WorkflowUpdate",
    "WorkflowWithNodes",
]
