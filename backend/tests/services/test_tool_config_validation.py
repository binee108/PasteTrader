"""Tool configuration validation tests.

TAG: [SPEC-009] [TESTS] [SERVICE] [TOOL] [VALIDATION]
REQ: REQ-005 - Tool Type Required Field Validation

This module tests tool configuration validation by type.
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.exceptions import InvalidToolConfigError
from app.models.tool import Tool
from app.schemas.tool import ToolCreate
from app.services.tool_service import ToolService


class TestToolConfigValidation:
    """Test tool configuration validation by type."""

    # ===== HTTP 타입 검증 테스트 =====

    @pytest.mark.asyncio
    async def test_http_tool_with_valid_config(self, db_session):
        """Test HTTP tool creation with valid config."""
        data = ToolCreate(
            name="Valid HTTP Tool",
            tool_type="http",
            config={"url": "https://api.example.com"},
            input_schema={"type": "object"},
        )

        # Schema validation should pass
        assert data.config["url"] == "https://api.example.com"

    def test_http_tool_missing_url_raises_validation_error(self):
        """Test HTTP tool without url field raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ToolCreate(
                name="Invalid HTTP Tool",
                tool_type="http",
                config={},  # url 누락
                input_schema={"type": "object"},
            )

        error_msg = str(exc_info.value)
        assert "http" in error_msg
        assert "url" in error_msg
        assert ("누락" in error_msg or "missing" in error_msg.lower())

    def test_http_tool_with_null_url_raises_validation_error(self):
        """Test HTTP tool with null url field raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ToolCreate(
                name="Invalid HTTP Tool",
                tool_type="http",
                config={"url": None},  # url이 null
                input_schema={"type": "object"},
            )

        error_msg = str(exc_info.value)
        assert "http" in error_msg
        assert "url" in error_msg

    # ===== Python 타입 검증 테스트 =====

    def test_python_tool_missing_code_raises_validation_error(self):
        """Test Python tool without code field raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ToolCreate(
                name="Invalid Python Tool",
                tool_type="python",
                config={},  # code 누락
                input_schema={"type": "object"},
            )

        error_msg = str(exc_info.value)
        assert "python" in error_msg
        assert "code" in error_msg

    @pytest.mark.asyncio
    async def test_python_tool_with_valid_config(self, db_session):
        """Test Python tool creation with valid config."""
        data = ToolCreate(
            name="Valid Python Tool",
            tool_type="python",
            config={"code": "print('hello')"},
            input_schema={"type": "object"},
        )

        # Schema validation should pass
        assert data.config["code"] == "print('hello')"

    # ===== Shell 타입 검증 테스트 =====

    def test_shell_tool_missing_command_raises_validation_error(self):
        """Test Shell tool without command field raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ToolCreate(
                name="Invalid Shell Tool",
                tool_type="shell",
                config={},  # command 누락
                input_schema={"type": "object"},
            )

        error_msg = str(exc_info.value)
        assert "shell" in error_msg
        assert "command" in error_msg

    @pytest.mark.asyncio
    async def test_shell_tool_with_valid_config(self, db_session):
        """Test Shell tool creation with valid config."""
        data = ToolCreate(
            name="Valid Shell Tool",
            tool_type="shell",
            config={"command": "ls -la"},
            input_schema={"type": "object"},
        )

        # Schema validation should pass
        assert data.config["command"] == "ls -la"

    # ===== MCP 타입 검증 테스트 =====

    def test_mcp_tool_missing_server_url_raises_validation_error(self):
        """Test MCP tool without server_url field raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ToolCreate(
                name="Invalid MCP Tool",
                tool_type="mcp",
                config={},  # server_url 누락
                input_schema={"type": "object"},
            )

        error_msg = str(exc_info.value)
        assert "mcp" in error_msg
        assert "server_url" in error_msg

    @pytest.mark.asyncio
    async def test_mcp_tool_with_valid_config(self, db_session):
        """Test MCP tool creation with valid config."""
        data = ToolCreate(
            name="Valid MCP Tool",
            tool_type="mcp",
            config={"server_url": "https://mcp.example.com"},
            input_schema={"type": "object"},
        )

        # Schema validation should pass
        assert data.config["server_url"] == "https://mcp.example.com"

    # ===== Builtin 타입 검증 테스트 (config 검증 없음) =====

    @pytest.mark.asyncio
    async def test_builtin_tool_without_config_succeeds(self, db_session):
        """Test builtin tool creation without config succeeds."""
        data = ToolCreate(
            name="Builtin Tool",
            tool_type="builtin",
            config={},  # builtin은 config 검증 없음
            input_schema={"type": "object"},
        )

        service = ToolService(db_session)
        tool = await service.create(uuid4(), data)

        assert tool.tool_type == "builtin"

    # ===== Service-level validation tests (bypass schema validation) =====

    @pytest.mark.asyncio
    async def test_service_validates_http_tool_config(self, db_session):
        """Test service validates HTTP tool config (bypass schema)."""
        # Create Tool object directly to bypass schema validation
        tool = Tool(
            owner_id=uuid4(),
            name="Invalid HTTP Tool",
            tool_type="http",
            config={},  # url 누락
            input_schema={"type": "object"},
        )

        service = ToolService(db_session)

        # Service-level validation should catch this
        with pytest.raises(InvalidToolConfigError) as exc_info:
            service._validate_tool_config(tool.tool_type, tool.config)

        assert exc_info.value.tool_type == "http"
        assert "url" in exc_info.value.missing_fields

    @pytest.mark.asyncio
    async def test_service_validates_python_tool_config(self, db_session):
        """Test service validates Python tool config."""
        tool = Tool(
            owner_id=uuid4(),
            name="Invalid Python Tool",
            tool_type="python",
            config={},  # code 누락
            input_schema={"type": "object"},
        )

        service = ToolService(db_session)

        with pytest.raises(InvalidToolConfigError) as exc_info:
            service._validate_tool_config(tool.tool_type, tool.config)

        assert exc_info.value.tool_type == "python"
        assert "code" in exc_info.value.missing_fields

    @pytest.mark.asyncio
    async def test_service_validates_shell_tool_config(self, db_session):
        """Test service validates Shell tool config."""
        tool = Tool(
            owner_id=uuid4(),
            name="Invalid Shell Tool",
            tool_type="shell",
            config={},  # command 누락
            input_schema={"type": "object"},
        )

        service = ToolService(db_session)

        with pytest.raises(InvalidToolConfigError) as exc_info:
            service._validate_tool_config(tool.tool_type, tool.config)

        assert exc_info.value.tool_type == "shell"
        assert "command" in exc_info.value.missing_fields

    @pytest.mark.asyncio
    async def test_service_validates_mcp_tool_config(self, db_session):
        """Test service validates MCP tool config."""
        tool = Tool(
            owner_id=uuid4(),
            name="Invalid MCP Tool",
            tool_type="mcp",
            config={},  # server_url 누락
            input_schema={"type": "object"},
        )

        service = ToolService(db_session)

        with pytest.raises(InvalidToolConfigError) as exc_info:
            service._validate_tool_config(tool.tool_type, tool.config)

        assert exc_info.value.tool_type == "mcp"
        assert "server_url" in exc_info.value.missing_fields

    @pytest.mark.asyncio
    async def test_service_allows_builtin_tool_without_config(self, db_session):
        """Test service allows builtin tool without config validation."""
        service = ToolService(db_session)

        # Should not raise any error
        service._validate_tool_config("builtin", {})
