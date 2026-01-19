"""
Confluence Property Skill - Test Configuration
"""

import json
from typing import Optional
from unittest.mock import MagicMock, Mock, patch

import pytest


@pytest.fixture
def mock_response():
    """Factory for creating mock HTTP responses."""

    def _create_response(
        status_code: int = 200,
        json_data: Optional[dict] = None,
        text: str = "",
        headers: Optional[dict] = None,
    ):
        response = Mock()
        response.status_code = status_code
        response.ok = 200 <= status_code < 300
        response.text = text or json.dumps(json_data or {})
        response.headers = headers or {}

        if json_data is not None:
            response.json.return_value = json_data
        else:
            response.json.side_effect = ValueError("No JSON")

        return response

    return _create_response


@pytest.fixture
def mock_client(mock_response):
    """Create a mock Confluence client."""
    from confluence_assistant_skills_lib import ConfluenceClient

    with patch.object(ConfluenceClient, "_create_session"):
        client = ConfluenceClient(
            base_url="https://test.atlassian.net",
            email="test@example.com",
            api_token="test-token",
        )

        client.session = MagicMock()

        def setup_response(method: str, response_data: dict, status_code: int = 200):
            response = mock_response(status_code=status_code, json_data=response_data)
            getattr(client.session, method.lower()).return_value = response

        client.setup_response = setup_response
        yield client


@pytest.fixture
def sample_property():
    """Sample property data from API."""
    return {
        "id": "prop-123",
        "key": "my-property",
        "value": {"data": "test value", "metadata": {"example": "data"}},
        "version": {"number": 1},
    }


@pytest.fixture
def sample_properties():
    """Sample properties list from API."""
    return {
        "results": [
            {
                "id": "prop-1",
                "key": "property-one",
                "value": {"data": "value one"},
                "version": {"number": 1},
            },
            {
                "id": "prop-2",
                "key": "property-two",
                "value": {"data": "value two"},
                "version": {"number": 2},
            },
        ],
        "_links": {},
    }
