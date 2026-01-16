"""Tests for HttpToolExecutor."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.executors.http_executor import HttpToolExecutor


class TestHttpToolExecutor:
    """Test HttpToolExecutor class."""

    @pytest.mark.asyncio
    async def test_execute_get_request_success(self):
        """Test successful GET request execution."""
        executor = HttpToolExecutor()

        # Create mock response
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"result": "success"}
        mock_response.text = '{"result": "success"}'
        mock_response.url = "https://api.example.com/test"

        # Create mock client
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)

        with patch.object(HttpToolExecutor, "_get_client", return_value=mock_client):
            result = await executor.execute(
                config={
                    "url": "https://api.example.com/test",
                    "method": "GET",
                },
                input_data={},
                auth_config=None,
            )

        assert result.success is True
        assert result.output["status_code"] == 200
        assert result.output["body"]["result"] == "success"
        assert result.error is None

    @pytest.mark.asyncio
    async def test_validate_config_success(self):
        """Test successful configuration validation."""
        executor = HttpToolExecutor()

        # Valid configuration
        assert executor.validate_config({
            "url": "https://api.example.com/test",
            "method": "GET",
        }) is True

    @pytest.mark.asyncio
    async def test_validate_config_missing_url(self):
        """Test validation fails when URL is missing."""
        executor = HttpToolExecutor()

        with pytest.raises(ValueError, match="must include 'url'"):
            executor.validate_config({"method": "GET"})
