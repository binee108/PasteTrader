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

    All fields are optional to support partial updates.
    """

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
    )


class ToolTestResponse(BaseSchema):
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
    )


__all__ = [
    "ToolBase",
    "ToolCreate",
    "ToolListResponse",
    "ToolResponse",
    "ToolTestRequest",
    "ToolTestResponse",
    "ToolUpdate",
]
