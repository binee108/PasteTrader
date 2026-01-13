"""Tool Pydantic schemas for API operations.

TAG: [SPEC-009] [TOOL] [SCHEMAS]
REQ: REQ-T001 - Tool CRUD Operations
REQ: REQ-T002 - JSON Schema Validation for Parameters
REQ: REQ-T003 - Tool Test Execution

This module provides Pydantic schemas for Tool-related operations
including creation, updates, responses, and test execution.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.base import BaseResponse, BaseSchema


class ToolCreate(BaseSchema):
    """Schema for tool creation.

    Attributes:
        name: Tool unique identifier name
        description: Optional tool description
        parameters: JSON Schema for tool parameters validation
        implementation_path: Optional path to tool implementation file
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Tool unique name identifier",
        examples=["http_request", "data_transform"],
    )
    description: str | None = Field(
        default=None,
        max_length=5000,
        description="Tool functionality description",
        examples=["Executes HTTP requests with retry logic"],
    )
    parameters: dict[str, Any] = Field(
        ...,
        description="JSON Schema for parameter validation",
        examples=[
            {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "format": "uri"},
                    "timeout": {"type": "integer", "minimum": 1},
                },
            }
        ],
    )
    implementation_path: str | None = Field(
        default=None,
        max_length=500,
        description="Path to tool implementation file",
        examples=["tools/http_request.py"],
    )


class ToolUpdate(BaseSchema):
    """Schema for tool updates.

    All fields are optional to support partial updates.
    """

    description: str | None = Field(
        default=None,
        max_length=5000,
        description="Updated tool description",
    )
    parameters: dict[str, Any] | None = Field(
        default=None,
        description="Updated JSON Schema for parameters",
    )
    implementation_path: str | None = Field(
        default=None,
        max_length=500,
        description="Updated implementation path",
    )
    is_active: bool | None = Field(
        default=None,
        description="Tool active status flag",
        examples=[True, False],
    )


class ToolResponse(BaseResponse):
    """Schema for tool API responses.

    Includes all tool fields with timestamps.
    """

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(
        ...,
        description="Tool unique name identifier",
        examples=["http_request"],
    )
    description: str | None = Field(
        default=None,
        description="Tool functionality description",
    )
    parameters: dict[str, Any] = Field(
        ...,
        description="JSON Schema for parameter validation",
    )
    implementation_path: str | None = Field(
        default=None,
        description="Path to tool implementation file",
    )
    is_active: bool = Field(
        ...,
        description="Whether the tool is currently active",
        examples=[True],
    )
    # Override to make Optional for newly created tools
    updated_at: datetime | None = Field(
        default=None,
        description="Timestamp when the resource was last updated",
    )


class ToolDetailResponse(ToolResponse):
    """Schema for tool detail responses with relationships.

    Extends ToolResponse with usage information.
    """

    used_by_agents: list[UUID] = Field(
        default_factory=list,
        description="List of agent IDs that use this tool",
        examples=[["550e8400-e29b-41d4-a716-446655440000"]],
    )
    used_in_workflows: list[UUID] = Field(
        default_factory=list,
        description="List of workflow IDs that include this tool",
        examples=[
            [
                "550e8400-e29b-41d4-a716-446655440001",
                "550e8400-e29b-41d4-a716-446655440002",
            ]
        ],
    )


class ToolTestRequest(BaseSchema):
    """Schema for tool test execution requests.

    Validates test parameters and timeout constraints.
    """

    params: dict[str, Any] = Field(
        ...,
        description="Test parameters matching tool's JSON Schema",
        examples=[{"url": "https://api.example.com", "timeout": 30}],
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=120,
        description="Test execution timeout in seconds",
        examples=[30, 60, 120],
    )


class ToolTestResponse(BaseSchema):
    """Schema for tool test execution responses.

    Returns test results with execution metrics.
    """

    success: bool = Field(
        ...,
        description="Whether the test execution succeeded",
        examples=[True, False],
    )
    result: Any | None = Field(
        default=None,
        description="Test result data if successful",
        examples=[{"status": "ok", "data": "response"}],
    )
    error: str | None = Field(
        default=None,
        description="Error message if test failed",
        examples=["Connection timeout after 30s"],
    )
    execution_time_ms: int = Field(
        ...,
        ge=0,
        description="Execution time in milliseconds",
        examples=[150, 500, 1000],
    )
    logs: list[str] = Field(
        default_factory=list,
        description="Execution log messages",
        examples=[["Starting test...", "Executing request...", "Test completed"]],
    )


__all__ = [
    "ToolCreate",
    "ToolDetailResponse",
    "ToolResponse",
    "ToolTestRequest",
    "ToolTestResponse",
    "ToolUpdate",
]
