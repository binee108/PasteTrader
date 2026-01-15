<<<<<<< HEAD
"""Tool schemas for API request/response validation.

TAG: [SPEC-009] [SCHEMAS] [TOOL]
REQ: REQ-001 - Tool CRUD Schemas
REQ: REQ-002 - Tool Type Enum Schemas
REQ: REQ-003 - Tool Test Execution Schema

This module defines Pydantic schemas for Tool API validation.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID  # noqa: TC003 - Required at runtime for Pydantic v2

from pydantic import Field, model_validator

from app.schemas.base import (
    BaseResponse,
    BaseSchema,
    DescriptionField,
    NameField,
    OptionalNameField,
)

# =============================================================================
# Base Schemas
# =============================================================================


class ToolBase(BaseSchema):
    """Base tool schema with common fields."""

    name: str = NameField
    description: str | None = DescriptionField
    tool_type: str = Field(
        ...,
        description="Type of tool (http, mcp, python, shell, builtin)",
        examples=["http"],
    )
    config: dict[str, Any] = Field(
        ...,
        description="Tool-specific configuration (JSON)",
        examples=[{"url": "https://api.example.com", "method": "POST"}],
    )
    input_schema: dict[str, Any] = Field(
        ...,
        description="JSON Schema for tool input validation",
        examples=[{"type": "object", "properties": {"url": {"type": "string"}}}],
    )
    output_schema: dict[str, Any] | None = Field(
        default=None,
        description="JSON Schema for tool output validation",
    )
    auth_config: dict[str, Any] | None = Field(
        default=None,
        description="Authentication configuration (encrypted at rest)",
    )
    rate_limit: dict[str, Any] | None = Field(
        default=None,
        description="Rate limiting configuration",
    )
    is_active: bool = Field(
        default=True,
        description="Whether the tool is active and usable",
    )
    is_public: bool = Field(
        default=False,
        description="Whether the tool is publicly accessible",
    )


# =============================================================================
# Create Schemas
# =============================================================================


class ToolCreate(ToolBase):
    """Schema for creating a new tool."""

    @model_validator(mode="after")
    def validate_tool_config(self) -> "ToolCreate":
        """도구 타입별 필수 필드를 검증합니다.

        각 도구 타입에 필요한 필드가 config에 포함되어 있는지 확인합니다.

        Raises:
            ValueError: 필수 필드가 누락된 경우

        Returns:
            검증된 ToolCreate 인스턴스
        """
        # 도구 타입별 필수 필드 매핑
        required_fields_by_type: dict[str, list[str]] = {
            "http": ["url"],
            "python": ["code"],
            "shell": ["command"],
            "mcp": ["server_url"],
        }

        # 해당 타입의 필수 필드 목록 가져오기
        required_fields = required_fields_by_type.get(self.tool_type, [])

        # 누락된 필드 확인
        missing_fields: list[str] = []
        for field in required_fields:
            if field not in self.config or self.config[field] is None:
                missing_fields.append(field)

        # 필수 필드가 누락된 경우 에러 발생
        if missing_fields:
            raise ValueError(
                f"'{self.tool_type}' 타입의 도구 설정에 필수 필드가 누락되었습니다: "
                f"{', '.join(f"'{field}'" for field in missing_fields)}"
            )

        return self





# =============================================================================
# Update Schemas
# =============================================================================


class ToolUpdate(BaseSchema):
    """Schema for updating a tool.
=======
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

from pydantic import ConfigDict, Field

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
>>>>>>> origin/main

    All fields are optional to support partial updates.
    """

<<<<<<< HEAD
    name: str | None = OptionalNameField
    description: str | None = Field(default=None, max_length=2000)
    tool_type: str | None = Field(default=None, description="Tool type")
    config: dict[str, Any] | None = Field(
        default=None, description="Tool configuration"
    )
    input_schema: dict[str, Any] | None = Field(
        default=None, description="Input JSON Schema"
    )
    output_schema: dict[str, Any] | None = Field(
        default=None, description="Output JSON Schema"
    )
    auth_config: dict[str, Any] | None = Field(
        default=None, description="Authentication configuration"
    )
    rate_limit: dict[str, Any] | None = Field(
        default=None, description="Rate limit config"
    )
    is_active: bool | None = Field(default=None, description="Active status")
    is_public: bool | None = Field(default=None, description="Public status")


# =============================================================================
# Response Schemas
# =============================================================================


class ToolResponse(ToolBase, BaseResponse):
    """Schema for tool response."""

    owner_id: UUID = Field(
        ...,
        description="UUID of the tool owner",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )


class ToolListResponse(BaseSchema):
    """Schema for tool list items (summary view)."""

    id: UUID = Field(..., description="Tool ID")
    name: str = Field(..., description="Tool name")
    tool_type: str = Field(..., description="Tool type")
    is_active: bool = Field(..., description="Active status")
    is_public: bool = Field(..., description="Public status")
    created_at: str = Field(..., description="Creation timestamp")


# =============================================================================
# Tool Test Execution Schemas
# =============================================================================


class ToolTestRequest(BaseSchema):
    """Schema for tool test execution request."""

    input_data: dict[str, Any] = Field(
        ...,
        description="Input data to test the tool with",
        examples=[{"url": "https://api.example.com", "query": "test"}],
=======
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
>>>>>>> origin/main
    )


class ToolTestResponse(BaseSchema):
<<<<<<< HEAD
    """Schema for tool test execution response."""

    success: bool = Field(
        ...,
        description="Whether the tool execution was successful",
    )
    output: dict[str, Any] | None = Field(
        default=None,
        description="Tool output data",
    )
    error: str | None = Field(
        default=None,
        description="Error message if execution failed",
    )
    execution_time_ms: float = Field(
        ...,
        description="Tool execution time in milliseconds",
        examples=[150.5],
=======
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
>>>>>>> origin/main
    )


__all__ = [
<<<<<<< HEAD
    "ToolBase",
    "ToolCreate",
    "ToolListResponse",
=======
    "ToolCreate",
    "ToolDetailResponse",
>>>>>>> origin/main
    "ToolResponse",
    "ToolTestRequest",
    "ToolTestResponse",
    "ToolUpdate",
]
