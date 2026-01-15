"""HTTP tool executor for API requests."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import httpx

from app.services.executors.base import ToolExecutionResult, ToolExecutor

if TYPE_CHECKING:
    from app.models.tool import Tool


class HttpToolExecutor(ToolExecutor):
    """Executor for HTTP-type tools."""

    # Security limits
    DEFAULT_TIMEOUT: float = 30.0  # seconds
    MAX_TIMEOUT: float = 300.0  # 5 minutes
    DEFAULT_MAX_RESPONSE_SIZE: int = 10 * 1024 * 1024  # 10MB
    MAX_RESPONSE_SIZE: int = 100 * 1024 * 1024  # 100MB

    # Supported HTTP methods
    SUPPORTED_METHODS = {
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "HEAD",
        "OPTIONS",
    }

    def __init__(self) -> None:
        """Initialize HTTP executor."""
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.DEFAULT_TIMEOUT),
                follow_redirects=True,
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
            )
        return self._client

    async def execute(
        self,
        config: dict[str, Any],
        input_data: dict[str, Any],
        auth_config: dict[str, Any] | None = None,
    ) -> ToolExecutionResult:
        """Execute HTTP request."""
        start_time = time.time()

        try:
            # Validate configuration
            self.validate_config(config)

            # Extract request parameters
            url = config["url"]
            method = config.get("method", "POST").upper()

            # Build request
            headers = config.get("headers", {}).copy()
            params = config.get("params", {})
            body = self._prepare_body(method, config, input_data)

            # Apply authentication
            self._apply_auth(headers, params, body, auth_config)

            # Enforce timeout
            timeout = self._get_timeout(config)

            # Execute request
            client = await self._get_client()

            # Build request parameters
            request_kwargs: dict[str, Any] = {
                "method": method,
                "url": url,
                "headers": headers,
                "params": params,
                "timeout": timeout,
            }

            # Set body based on content type
            if headers.get("content-type", "").startswith("application/json"):
                request_kwargs["json"] = body
            elif body is not None:
                # For non-JSON content, convert body to bytes or string
                if isinstance(body, dict):
                    import json
                    request_kwargs["content"] = json.dumps(body).encode("utf-8")
                elif isinstance(body, str):
                    request_kwargs["content"] = body.encode("utf-8")
                else:
                    request_kwargs["content"] = body

            response = await client.request(**request_kwargs)

            # Check response size limit
            max_size = self._get_max_response_size(config)
            response_content = await self._get_response_content(response, max_size)

            execution_time_ms = (time.time() - start_time) * 1000

            # Build result
            return ToolExecutionResult(
                success=response.is_success,
                output={
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": response_content,
                    "url": str(response.url),
                },
                error=None if response.is_success else f"HTTP {response.status_code}: {response.text}",
                execution_time_ms=execution_time_ms,
                metadata={
                    "method": method,
                    "url": url,
                    "response_size": len(response_content),
                },
            )

        except httpx.TimeoutException as e:
            execution_time_ms = (time.time() - start_time) * 1000
            return ToolExecutionResult(
                success=False,
                output=None,
                error=f"Request timeout after {execution_time_ms:.0f}ms: {e}",
                execution_time_ms=execution_time_ms,
            )

        except httpx.HTTPStatusError as e:
            execution_time_ms = (time.time() - start_time) * 1000
            return ToolExecutionResult(
                success=False,
                output={
                    "status_code": e.response.status_code,
                    "body": e.response.text[:1000],
                },
                error=f"HTTP error: {e.response.status_code}",
                execution_time_ms=execution_time_ms,
            )

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            return ToolExecutionResult(
                success=False,
                output=None,
                error=f"Request failed: {type(e).__name__}: {e}",
                execution_time_ms=execution_time_ms,
            )

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate HTTP tool configuration."""
        if "url" not in config:
            raise ValueError("HTTP configuration must include 'url'")

        url = config["url"]
        if not url or not isinstance(url, str):
            raise ValueError("HTTP 'url' must be a non-empty string")

        # Validate URL scheme
        if not url.startswith(("http://", "https://")):
            raise ValueError("HTTP 'url' must use http:// or https:// scheme")

        # Validate method
        method = config.get("method", "POST").upper()
        if method not in self.SUPPORTED_METHODS:
            raise ValueError(
                f"Unsupported HTTP method: {method}. "
                f"Supported: {', '.join(self.SUPPORTED_METHODS)}"
            )

        # Validate timeout
        timeout = self._get_timeout(config)
        if timeout > self.MAX_TIMEOUT:
            raise ValueError(f"Timeout exceeds maximum: {timeout}s > {self.MAX_TIMEOUT}s")

        # Validate response size limit
        max_size = self._get_max_response_size(config)
        if max_size > self.MAX_RESPONSE_SIZE:
            raise ValueError(
                f"Response size limit exceeds maximum: {max_size} > {self.MAX_RESPONSE_SIZE}"
            )

        return True

    def _prepare_body(
        self,
        method: str,
        config: dict[str, Any],
        input_data: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Prepare request body based on method and configuration."""
        if method in ("GET", "HEAD", "OPTIONS", "DELETE"):
            return None

        # Merge config body with input data
        body = config.get("body", {})
        if input_data:
            body = {**body, **input_data}

        return body if body else None

    def _apply_auth(
        self,
        headers: dict[str, str],
        params: dict[str, Any],
        body: dict[str, Any] | None,
        auth_config: dict[str, Any] | None,
    ) -> None:
        """Apply authentication to request."""
        if not auth_config:
            return

        auth_type = auth_config.get("type")

        if auth_type == "bearer":
            token = auth_config.get("token")
            if token:
                headers["Authorization"] = f"Bearer {token}"

        elif auth_type == "api_key":
            key = auth_config.get("api_key")
            location = auth_config.get("location", "header")
            name = auth_config.get("name", "X-API-Key")

            if key:
                if location == "header":
                    headers[name] = key
                elif location == "query":
                    params[name] = key

        elif auth_type == "custom":
            # Custom headers from auth_config
            custom_headers = auth_config.get("headers", {})
            headers.update(custom_headers)

    def _get_timeout(self, config: dict[str, Any]) -> float:
        """Get request timeout from config."""
        timeout = config.get("timeout", self.DEFAULT_TIMEOUT)

        if isinstance(timeout, (int, float)):
            return float(min(timeout, self.MAX_TIMEOUT))

        return self.DEFAULT_TIMEOUT

    def _get_max_response_size(self, config: dict[str, Any]) -> int:
        """Get maximum response size from config."""
        max_size = config.get("max_response_size", self.DEFAULT_MAX_RESPONSE_SIZE)

        if isinstance(max_size, int):
            return min(max_size, self.MAX_RESPONSE_SIZE)

        return self.DEFAULT_MAX_RESPONSE_SIZE

    async def _get_response_content(
        self,
        response: httpx.Response,
        max_size: int,
    ) -> str | dict[str, Any]:
        """Get response content with size limit enforcement."""
        content_type = response.headers.get("content-type", "")

        if "application/json" in content_type:
            # Parse JSON response
            response_data: Any = response.json()

            # Cast to dict for type checking
            json_content: dict[str, Any] = response_data if isinstance(response_data, dict) else {}

            # Check size
            if len(str(response_data)) > max_size:
                return {
                    "_truncated": True,
                    "_size": len(str(response_data)),
                    "_limit": max_size,
                    "message": "Response too large, truncated",
                }

            return json_content

        else:
            # Text response
            text_content: str = response.text

            if len(text_content) > max_size:
                return text_content[:max_size] + f"\n... [truncated at {max_size} bytes]"

            return text_content

    async def __aenter__(self) -> "HttpToolExecutor":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit with cleanup."""
        if self._client:
            await self._client.aclose()
            self._client = None


__all__ = ["HttpToolExecutor"]
