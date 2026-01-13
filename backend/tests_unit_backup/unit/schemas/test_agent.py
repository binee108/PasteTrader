"""Tests for Agent Pydantic schemas.

TAG: [SPEC-009] [TEST] [AGENT_SCHEMAS]
REQ: REQ-001 - Agent Schema Validation Tests
REQ: REQ-002 - Provider Pattern Validation
REQ: REQ-003 - Field Constraint Validation

This module contains comprehensive tests for all Agent-related Pydantic schemas
following TDD RED-GREEN-REFACTOR cycle.
"""

from datetime import datetime
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.schemas.agent import (
    AgentCreate,
    AgentResponse,
    AgentTestRequest,
    AgentTestResponse,
    AgentToolsUpdate,
    AgentUpdate,
    ModelConfig,
)


# =============================================================================
# ModelConfig Tests
# =============================================================================


class TestModelConfig:
    """Test suite for ModelConfig schema."""

    def test_valid_model_config_anthropic(self):
        """Test ModelConfig with valid anthropic provider."""
        config = ModelConfig(
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            temperature=0.7,
            max_tokens=4096,
        )
        assert config.provider == "anthropic"
        assert config.model == "claude-3-5-sonnet-20241022"
        assert config.temperature == 0.7
        assert config.max_tokens == 4096

    def test_valid_model_config_openai(self):
        """Test ModelConfig with valid openai provider."""
        config = ModelConfig(
            provider="openai",
            model="gpt-4o",
            temperature=0.5,
            max_tokens=8192,
        )
        assert config.provider == "openai"
        assert config.model == "gpt-4o"
        assert config.temperature == 0.5
        assert config.max_tokens == 8192

    def test_valid_model_config_glm(self):
        """Test ModelConfig with valid glm provider."""
        config = ModelConfig(
            provider="glm",
            model="glm-4-plus",
            temperature=0.8,
            max_tokens=2048,
        )
        assert config.provider == "glm"
        assert config.model == "glm-4-plus"
        assert config.temperature == 0.8
        assert config.max_tokens == 2048

    def test_default_values(self):
        """Test ModelConfig default values."""
        config = ModelConfig(
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
        )
        assert config.temperature == 0.7
        assert config.max_tokens == 4096

    def test_invalid_provider_pattern(self):
        """Test ModelConfig rejects invalid provider patterns."""
        invalid_providers = [
            "invalid",
            "ANTHROPIC",
            "Anthropic",
            "open_ai",
            "gpt",
            "",
            "openai-extra",
        ]

        for provider in invalid_providers:
            with pytest.raises(ValidationError) as exc_info:
                ModelConfig(provider=provider, model="test-model")
            assert "provider" in str(exc_info.value).lower()

    def test_temperature_minimum_boundary(self):
        """Test ModelConfig temperature minimum boundary (ge=0)."""
        # Valid: temperature = 0
        config = ModelConfig(
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            temperature=0,
        )
        assert config.temperature == 0

        # Invalid: temperature < 0
        with pytest.raises(ValidationError) as exc_info:
            ModelConfig(
                provider="anthropic",
                model="claude-3-5-sonnet-20241022",
                temperature=-0.1,
            )
        assert "temperature" in str(exc_info.value).lower()

    def test_temperature_maximum_boundary(self):
        """Test ModelConfig temperature maximum boundary (le=2)."""
        # Valid: temperature = 2
        config = ModelConfig(
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            temperature=2,
        )
        assert config.temperature == 2

        # Invalid: temperature > 2
        with pytest.raises(ValidationError) as exc_info:
            ModelConfig(
                provider="anthropic",
                model="claude-3-5-sonnet-20241022",
                temperature=2.1,
            )
        assert "temperature" in str(exc_info.value).lower()

    def test_max_tokens_minimum_boundary(self):
        """Test ModelConfig max_tokens minimum boundary (ge=1)."""
        # Valid: max_tokens = 1
        config = ModelConfig(
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            max_tokens=1,
        )
        assert config.max_tokens == 1

        # Invalid: max_tokens < 1
        with pytest.raises(ValidationError) as exc_info:
            ModelConfig(
                provider="anthropic",
                model="claude-3-5-sonnet-20241022",
                max_tokens=0,
            )
        assert "max_tokens" in str(exc_info.value).lower()

    def test_max_tokens_maximum_boundary(self):
        """Test ModelConfig max_tokens maximum boundary (le=128000)."""
        # Valid: max_tokens = 128000
        config = ModelConfig(
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            max_tokens=128000,
        )
        assert config.max_tokens == 128000

        # Invalid: max_tokens > 128000
        with pytest.raises(ValidationError) as exc_info:
            ModelConfig(
                provider="anthropic",
                model="claude-3-5-sonnet-20241022",
                max_tokens=128001,
            )
        assert "max_tokens" in str(exc_info.value).lower()


# =============================================================================
# AgentCreate Tests
# =============================================================================


class TestAgentCreate:
    """Test suite for AgentCreate schema."""

    def test_valid_agent_create(self):
        """Test AgentCreate with valid data."""
        tool_id = uuid4()
        data = {
            "name": "Test Agent",
            "description": "A test agent",
            "system_prompt": "You are a helpful assistant",
            "model_config": {
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-20241022",
                "temperature": 0.7,
                "max_tokens": 4096,
            },
            "tool_ids": [tool_id],
        }

        agent = AgentCreate(**data)
        assert agent.name == "Test Agent"
        assert agent.description == "A test agent"
        assert agent.system_prompt == "You are a helpful assistant"
        assert agent.model_config.provider == "anthropic"
        assert agent.model_config.model == "claude-3-5-sonnet-20241022"
        assert len(agent.tool_ids) == 1
        assert tool_id in agent.tool_ids

    def test_agent_create_without_description(self):
        """Test AgentCreate without optional description."""
        data = {
            "name": "Test Agent",
            "system_prompt": "You are a helpful assistant",
            "model_config": {
                "provider": "openai",
                "model": "gpt-4o",
            },
            "tool_ids": [],
        }

        agent = AgentCreate(**data)
        assert agent.name == "Test Agent"
        assert agent.description is None
        assert agent.tool_ids == []

    def test_agent_create_name_min_length(self):
        """Test AgentCreate name minimum length constraint."""
        # Valid: name with 1 character
        agent = AgentCreate(
            name="A",
            system_prompt="Prompt",
            model_config={
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-20241022",
            },
        )
        assert agent.name == "A"

        # Invalid: empty name
        with pytest.raises(ValidationError) as exc_info:
            AgentCreate(
                name="",
                system_prompt="Prompt",
                model_config={
                    "provider": "anthropic",
                    "model": "claude-3-5-sonnet-20241022",
                },
            )
        assert "name" in str(exc_info.value).lower()

    def test_agent_create_name_max_length(self):
        """Test AgentCreate name maximum length constraint."""
        # Valid: name with 255 characters
        long_name = "A" * 255
        agent = AgentCreate(
            name=long_name,
            system_prompt="Prompt",
            model_config={
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-20241022",
            },
        )
        assert len(agent.name) == 255

        # Invalid: name with 256 characters
        with pytest.raises(ValidationError) as exc_info:
            AgentCreate(
                name="A" * 256,
                system_prompt="Prompt",
                model_config={
                    "provider": "anthropic",
                    "model": "claude-3-5-sonnet-20241022",
                },
            )
        assert "name" in str(exc_info.value).lower()

    def test_agent_create_system_prompt_min_length(self):
        """Test AgentCreate system_prompt minimum length constraint."""
        # Valid: system_prompt with 1 character
        agent = AgentCreate(
            name="Test",
            system_prompt="P",
            model_config={
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-20241022",
            },
        )
        assert agent.system_prompt == "P"

        # Invalid: empty system_prompt
        with pytest.raises(ValidationError) as exc_info:
            AgentCreate(
                name="Test",
                system_prompt="",
                model_config={
                    "provider": "anthropic",
                    "model": "claude-3-5-sonnet-20241022",
                },
            )
        assert "system_prompt" in str(exc_info.value).lower()

    def test_agent_create_multiple_tool_ids(self):
        """Test AgentCreate with multiple tool IDs."""
        tool_ids = [uuid4() for _ in range(5)]
        agent = AgentCreate(
            name="Test",
            system_prompt="Prompt",
            model_config={
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-20241022",
            },
            tool_ids=tool_ids,
        )
        assert len(agent.tool_ids) == 5
        for tool_id in tool_ids:
            assert tool_id in agent.tool_ids


# =============================================================================
# AgentUpdate Tests
# =============================================================================


class TestAgentUpdate:
    """Test suite for AgentUpdate schema."""

    def test_valid_agent_update_all_fields(self):
        """Test AgentUpdate with all optional fields."""
        data = {
            "description": "Updated description",
            "system_prompt": "Updated prompt",
            "model_config": {
                "provider": "openai",
                "model": "gpt-4o",
                "temperature": 0.5,
            },
            "is_active": False,
        }

        update = AgentUpdate(**data)
        assert update.description == "Updated description"
        assert update.system_prompt == "Updated prompt"
        assert update.model_config.provider == "openai"
        assert update.is_active is False

    def test_agent_update_partial_fields(self):
        """Test AgentUpdate with partial fields."""
        # Only description
        update = AgentUpdate(description="New description")
        assert update.description == "New description"
        assert update.system_prompt is None
        assert update.model_config is None
        assert update.is_active is None

        # Only is_active
        update = AgentUpdate(is_active=True)
        assert update.description is None
        assert update.is_active is True

    def test_agent_update_empty_object(self):
        """Test AgentUpdate with no fields provided."""
        update = AgentUpdate()
        assert update.description is None
        assert update.system_prompt is None
        assert update.model_config is None
        assert update.is_active is None


# =============================================================================
# AgentResponse Tests
# =============================================================================


class TestAgentResponse:
    """Test suite for AgentResponse schema."""

    def test_valid_agent_response(self):
        """Test AgentResponse with valid data."""
        tool_id = uuid4()
        agent_id = uuid4()
        created_at = datetime.now()
        updated_at = datetime.now()

        data = {
            "id": agent_id,
            "name": "Test Agent",
            "description": "A test agent",
            "system_prompt": "You are a helpful assistant",
            "model_config": {
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-20241022",
            },
            "tool_ids": [tool_id],
            "is_active": True,
            "created_at": created_at,
            "updated_at": updated_at,
        }

        response = AgentResponse(**data)
        assert response.id == agent_id
        assert response.name == "Test Agent"
        assert response.tool_ids == [tool_id]
        assert response.is_active is True
        assert response.created_at == created_at
        assert response.updated_at == updated_at

    def test_agent_response_from_attributes(self):
        """Test AgentResponse from_attributes (ORM mode)."""
        # Mock SQLAlchemy model
        mock_agent = MagicMock()
        mock_agent.id = uuid4()
        mock_agent.name = "Test Agent"
        mock_agent.description = "Test description"
        mock_agent.system_prompt = "You are helpful"
        mock_agent.model_provider = "anthropic"
        mock_agent.model_name = "claude-3-5-sonnet-20241022"
        mock_agent.config = {"temperature": 0.7, "max_tokens": 4096}
        mock_agent.tools = [str(uuid4()), str(uuid4())]
        mock_agent.is_active = True
        mock_agent.created_at = datetime.now()
        mock_agent.updated_at = datetime.now()

        # Note: This test expects from_attributes to work
        # Actual implementation will need to handle model_config mapping
        # This test documents the expected behavior
        pass  # Implementation will validate this

    def test_agent_response_optional_updated_at(self):
        """Test AgentResponse with optional updated_at."""
        agent_id = uuid4()
        created_at = datetime.now()

        data = {
            "id": agent_id,
            "name": "Test",
            "description": None,
            "system_prompt": "Prompt",
            "model_config": {
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-20241022",
            },
            "tool_ids": [],
            "is_active": True,
            "created_at": created_at,
            "updated_at": None,
        }

        response = AgentResponse(**data)
        assert response.updated_at is None


# =============================================================================
# AgentToolsUpdate Tests
# =============================================================================


class TestAgentToolsUpdate:
    """Test suite for AgentToolsUpdate schema."""

    def test_valid_tools_update(self):
        """Test AgentToolsUpdate with tool IDs."""
        tool_ids = [uuid4() for _ in range(3)]
        update = AgentToolsUpdate(tool_ids=tool_ids)
        assert update.tool_ids == tool_ids
        assert len(update.tool_ids) == 3

    def test_tools_update_empty_list(self):
        """Test AgentToolsUpdate with empty tool list (removes all tools)."""
        update = AgentToolsUpdate(tool_ids=[])
        assert update.tool_ids == []

    def test_tools_update_single_tool(self):
        """Test AgentToolsUpdate with single tool ID."""
        tool_id = uuid4()
        update = AgentToolsUpdate(tool_ids=[tool_id])
        assert len(update.tool_ids) == 1
        assert tool_id in update.tool_ids


# =============================================================================
# AgentTestRequest Tests
# =============================================================================


class TestAgentTestRequest:
    """Test suite for AgentTestRequest schema."""

    def test_valid_test_request(self):
        """Test AgentTestRequest with valid data."""
        request = AgentTestRequest(
            test_prompt="Hello, how are you?",
            timeout=60,
        )
        assert request.test_prompt == "Hello, how are you?"
        assert request.timeout == 60

    def test_test_request_default_timeout(self):
        """Test AgentTestRequest uses default timeout."""
        request = AgentTestRequest(test_prompt="Test")
        assert request.timeout == 60

    def test_test_request_timeout_min_boundary(self):
        """Test AgentTestRequest timeout minimum boundary (ge=1)."""
        # Valid: timeout = 1
        request = AgentTestRequest(test_prompt="Test", timeout=1)
        assert request.timeout == 1

        # Invalid: timeout < 1
        with pytest.raises(ValidationError) as exc_info:
            AgentTestRequest(test_prompt="Test", timeout=0)
        assert "timeout" in str(exc_info.value).lower()

    def test_test_request_timeout_max_boundary(self):
        """Test AgentTestRequest timeout maximum boundary (le=300)."""
        # Valid: timeout = 300
        request = AgentTestRequest(test_prompt="Test", timeout=300)
        assert request.timeout == 300

        # Invalid: timeout > 300
        with pytest.raises(ValidationError) as exc_info:
            AgentTestRequest(test_prompt="Test", timeout=301)
        assert "timeout" in str(exc_info.value).lower()

    def test_test_request_min_length(self):
        """Test AgentTestRequest test_prompt minimum length."""
        # Valid: 1 character
        request = AgentTestRequest(test_prompt="A")
        assert request.test_prompt == "A"

        # Invalid: empty string
        with pytest.raises(ValidationError) as exc_info:
            AgentTestRequest(test_prompt="")
        assert "test_prompt" in str(exc_info.value).lower()


# =============================================================================
# AgentTestResponse Tests
# =============================================================================


class TestAgentTestResponse:
    """Test suite for AgentTestResponse schema."""

    def test_successful_test_response(self):
        """Test AgentTestResponse for successful execution."""
        response = AgentTestResponse(
            success=True,
            response="Hello! I'm doing well, thank you!",
            error=None,
            tool_calls=[{"name": "search", "args": {"query": "test"}}],
            execution_time_ms=1234,
            tokens_used={"prompt": 10, "completion": 20, "total": 30},
        )

        assert response.success is True
        assert response.response == "Hello! I'm doing well, thank you!"
        assert response.error is None
        assert len(response.tool_calls) == 1
        assert response.execution_time_ms == 1234
        assert response.tokens_used["total"] == 30

    def test_failed_test_response(self):
        """Test AgentTestResponse for failed execution."""
        response = AgentTestResponse(
            success=False,
            response=None,
            error="Timeout exceeded",
            tool_calls=[],
            execution_time_ms=5000,
            tokens_used=None,
        )

        assert response.success is False
        assert response.response is None
        assert response.error == "Timeout exceeded"
        assert response.tool_calls == []
        assert response.execution_time_ms == 5000
        assert response.tokens_used is None

    def test_test_response_default_tool_calls(self):
        """Test AgentTestResponse default empty tool_calls list."""
        response = AgentTestResponse(
            success=True,
            response="Response",
            error=None,
            execution_time_ms=100,
        )
        assert response.tool_calls == []

    def test_test_response_multiple_tool_calls(self):
        """Test AgentTestResponse with multiple tool calls."""
        tool_calls = [
            {"name": "search", "args": {"query": "weather"}},
            {"name": "calculator", "args": {"expression": "2+2"}},
            {"name": "database", "args": {"table": "users"}},
        ]

        response = AgentTestResponse(
            success=True,
            response="Done",
            error=None,
            tool_calls=tool_calls,
            execution_time_ms=2500,
        )

        assert len(response.tool_calls) == 3
        assert response.tool_calls[0]["name"] == "search"
        assert response.tool_calls[1]["name"] == "calculator"
        assert response.tool_calls[2]["name"] == "database"


# =============================================================================
# Integration Tests
# =============================================================================


class TestAgentSchemasIntegration:
    """Integration tests for Agent schemas."""

    def test_agent_create_to_response_flow(self):
        """Test data flow from AgentCreate to AgentResponse."""
        tool_id = uuid4()
        agent_id = uuid4()
        created_at = datetime.now()
        updated_at = datetime.now()

        # Create request
        create_data = {
            "name": "Test Agent",
            "description": "Test",
            "system_prompt": "Prompt",
            "model_config": {
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-20241022",
            },
            "tool_ids": [tool_id],
        }
        create = AgentCreate(**create_data)

        # Simulated response (from database)
        response_data = {
            "id": agent_id,
            "name": create.name,
            "description": create.description,
            "system_prompt": create.system_prompt,
            "model_config": create.model_config,
            "tool_ids": create.tool_ids,
            "is_active": True,
            "created_at": created_at,
            "updated_at": updated_at,
        }
        response = AgentResponse(**response_data)

        assert response.id == agent_id
        assert response.name == create.name
        assert response.model_config.provider == create.model_config.provider

    def test_agent_update_partial_flow(self):
        """Test partial update scenario."""
        # Original agent
        original = AgentResponse(
            id=uuid4(),
            name="Original Name",
            description="Original description",
            system_prompt="Original prompt",
            model_config={
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-20241022",
            },
            tool_ids=[],
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Update request (only description and is_active)
        update = AgentUpdate(
            description="Updated description",
            is_active=False,
        )

        # Verify update only contains specified fields
        assert update.description == "Updated description"
        assert update.is_active is False
        assert update.system_prompt is None
        assert update.model_config is None

    def test_agent_test_request_response_flow(self):
        """Test complete test execution flow."""
        # Test request
        request = AgentTestRequest(
            test_prompt="What is 2+2?",
            timeout=30,
        )

        # Simulated test execution
        success = True
        response = "The answer is 4."
        tool_calls = [
            {"name": "calculator", "args": {"expression": "2+2"}},
        ]
        execution_time_ms = 523
        tokens_used = {"prompt": 15, "completion": 8, "total": 23}

        # Test response
        test_response = AgentTestResponse(
            success=success,
            response=response,
            error=None,
            tool_calls=tool_calls,
            execution_time_ms=execution_time_ms,
            tokens_used=tokens_used,
        )

        assert test_response.success is True
        assert test_response.response == "The answer is 4."
        assert test_response.execution_time_ms == 523
        assert test_response.tokens_used["total"] == 23
