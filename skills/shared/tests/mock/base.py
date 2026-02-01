"""
Base Mock Confluence Client

Provides the foundation for mock client behavior.
Mixins extend this base to add domain-specific mock functionality.
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable
from unittest.mock import MagicMock


class MockConfluenceClientBase:
    """
    Base class for mock Confluence client.

    Provides:
    - Basic HTTP method mocking (get, post, put, delete)
    - Response recording and playback
    - Error simulation
    - Request history tracking
    """

    def __init__(
        self,
        base_url: str = "https://test.atlassian.net",
        email: str = "test@example.com",
        api_token: str = "test-token",
    ):
        self.base_url = base_url
        self.email = email
        self.api_token = api_token

        # Request history
        self._requests: list[dict[str, Any]] = []

        # Response registry (endpoint pattern -> response data)
        self._responses: dict[str, list[dict[str, Any]]] = defaultdict(list)

        # Error simulation
        self._errors: dict[str, Exception] = {}

        # Callback registry for dynamic responses
        self._callbacks: dict[str, Callable] = {}

        # Mock session for compatibility
        self.session = MagicMock()

    # =========================================================================
    # HTTP Methods
    # =========================================================================

    def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        operation: str = "GET request",
    ) -> dict[str, Any]:
        """Mock GET request."""
        return self._handle_request("GET", endpoint, params=params, operation=operation)

    def post(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        operation: str = "POST request",
    ) -> dict[str, Any]:
        """Mock POST request."""
        payload = json_data if json_data is not None else data
        return self._handle_request(
            "POST", endpoint, params=params, data=payload, operation=operation
        )

    def put(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        operation: str = "PUT request",
    ) -> dict[str, Any]:
        """Mock PUT request."""
        payload = json_data if json_data is not None else data
        return self._handle_request(
            "PUT", endpoint, params=params, data=payload, operation=operation
        )

    def delete(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        operation: str = "DELETE request",
    ) -> dict[str, Any]:
        """Mock DELETE request."""
        return self._handle_request(
            "DELETE", endpoint, params=params, operation=operation
        )

    def paginate(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        operation: str = "paginated request",
        limit: int | None = None,
        results_key: str = "results",
    ):
        """Mock paginated request."""
        response = self.get(endpoint, params=params, operation=operation)
        results = response.get(results_key, [])

        for count, item in enumerate(results, 1):
            yield item
            if limit and count >= limit:
                return

    def test_connection(self) -> dict[str, Any]:
        """Mock connection test."""
        return {
            "success": True,
            "user": "Mock User",
            "email": self.email,
            "type": "known",
        }

    # =========================================================================
    # Request Handling
    # =========================================================================

    def _handle_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        operation: str = "",
    ) -> dict[str, Any]:
        """
        Handle a mock request.

        Order of precedence:
        1. Check for simulated error
        2. Check for registered callback
        3. Check for registered response
        4. Call mixin handler if available
        5. Return empty response
        """
        # Record request
        request = {
            "method": method,
            "endpoint": endpoint,
            "params": params,
            "data": data,
            "operation": operation,
            "timestamp": datetime.now().isoformat(),
        }
        self._requests.append(request)

        # Check for simulated error
        error = self._find_matching_error(endpoint)
        if error:
            raise error

        # Check for callback
        callback = self._find_matching_callback(endpoint)
        if callback:
            return callback(method, endpoint, params, data)

        # Check for registered response
        response = self._find_matching_response(endpoint)
        if response is not None:
            return response

        # Try mixin handlers
        handler = self._find_mixin_handler(method, endpoint)
        if handler:
            return handler(endpoint, params, data)

        # Default empty response
        return {}

    def _find_matching_error(self, endpoint: str) -> Exception | None:
        """Find a matching error for the endpoint."""
        for pattern, error in self._errors.items():
            if re.match(pattern, endpoint):
                return error
        return None

    def _find_matching_callback(self, endpoint: str) -> Callable | None:
        """Find a matching callback for the endpoint."""
        for pattern, callback in self._callbacks.items():
            if re.match(pattern, endpoint):
                return callback
        return None

    def _find_matching_response(self, endpoint: str) -> dict[str, Any] | None:
        """Find a matching registered response for the endpoint."""
        for pattern, responses in self._responses.items():
            if re.match(pattern, endpoint) and responses:
                # Return and remove first response (FIFO)
                return responses.pop(0)
        return None

    def _find_mixin_handler(
        self,
        method: str,
        endpoint: str,
    ) -> Callable | None:
        """Find a mixin handler for the endpoint."""
        # Mixins implement _handle_<method>_<domain> methods
        # e.g., _handle_get_pages, _handle_post_pages
        handler_name = f"_handle_{method.lower()}"

        if hasattr(self, handler_name):
            return getattr(self, handler_name)

        return None

    # =========================================================================
    # Response Registration
    # =========================================================================

    def register_response(
        self,
        endpoint_pattern: str,
        response: dict[str, Any],
    ) -> MockConfluenceClientBase:
        """
        Register a response for an endpoint pattern.

        Args:
            endpoint_pattern: Regex pattern to match endpoints
            response: Response data to return

        Returns:
            self for chaining
        """
        self._responses[endpoint_pattern].append(response)
        return self

    def register_callback(
        self,
        endpoint_pattern: str,
        callback: Callable[[str, str, dict | None, dict | None], dict],
    ) -> MockConfluenceClientBase:
        """
        Register a dynamic callback for an endpoint pattern.

        Args:
            endpoint_pattern: Regex pattern to match endpoints
            callback: Function(method, endpoint, params, data) -> response

        Returns:
            self for chaining
        """
        self._callbacks[endpoint_pattern] = callback
        return self

    def simulate_error(
        self,
        endpoint_pattern: str,
        error: Exception,
    ) -> MockConfluenceClientBase:
        """
        Simulate an error for an endpoint pattern.

        Args:
            endpoint_pattern: Regex pattern to match endpoints
            error: Exception to raise

        Returns:
            self for chaining
        """
        self._errors[endpoint_pattern] = error
        return self

    def clear_error(self, endpoint_pattern: str) -> MockConfluenceClientBase:
        """Remove error simulation for an endpoint pattern."""
        self._errors.pop(endpoint_pattern, None)
        return self

    # =========================================================================
    # Request History
    # =========================================================================

    @property
    def requests(self) -> list[dict[str, Any]]:
        """Get all recorded requests."""
        return self._requests.copy()

    def get_requests(
        self,
        method: str | None = None,
        endpoint_pattern: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get filtered requests."""
        result = self._requests

        if method:
            result = [r for r in result if r["method"] == method]

        if endpoint_pattern:
            result = [r for r in result if re.match(endpoint_pattern, r["endpoint"])]

        return result

    def clear_requests(self) -> MockConfluenceClientBase:
        """Clear request history."""
        self._requests.clear()
        return self

    def assert_called_with(
        self,
        method: str,
        endpoint_pattern: str,
        times: int | None = None,
    ) -> None:
        """Assert that an endpoint was called."""
        matches = self.get_requests(method=method, endpoint_pattern=endpoint_pattern)

        if times is not None and len(matches) != times:
            raise AssertionError(
                f"Expected {times} calls to {method} {endpoint_pattern}, got {len(matches)}"
            )
        elif not matches:
            raise AssertionError(
                f"Expected call to {method} {endpoint_pattern}, but none found"
            )

    def assert_not_called(
        self,
        method: str,
        endpoint_pattern: str,
    ) -> None:
        """Assert that an endpoint was not called."""
        matches = self.get_requests(method=method, endpoint_pattern=endpoint_pattern)

        if matches:
            raise AssertionError(
                f"Expected no calls to {method} {endpoint_pattern}, but found {len(matches)}"
            )

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def reset(self) -> MockConfluenceClientBase:
        """Reset all mock state."""
        self._requests.clear()
        self._responses.clear()
        self._errors.clear()
        self._callbacks.clear()
        return self

    @staticmethod
    def generate_id() -> str:
        """Generate a random ID."""
        import uuid

        return str(uuid.uuid4().int)[:18]

    @staticmethod
    def generate_timestamp() -> str:
        """Generate current timestamp in Confluence format."""
        return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
