"""
Confluence Hierarchy Skill - Test Configuration
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
def sample_page():
    """Sample page data from API."""
    return {
        "id": "123456",
        "status": "current",
        "title": "Test Page",
        "spaceId": "789",
        "parentId": "111",
        "version": {"number": 1},
        "body": {
            "storage": {"value": "<p>Test content</p>", "representation": "storage"}
        },
        "_links": {"webui": "/wiki/spaces/TEST/pages/123456"},
    }


@pytest.fixture
def sample_page_with_ancestors():
    """Sample page with ancestors included."""
    return {
        "id": "123456",
        "status": "current",
        "title": "Child Page",
        "spaceId": "789",
        "parentId": "111",
        "version": {"number": 1},
        "ancestors": [
            {"id": "100", "title": "Root Page", "parentId": None},
            {"id": "111", "title": "Parent Page", "parentId": "100"},
        ],
        "_links": {"webui": "/wiki/spaces/TEST/pages/123456"},
    }


@pytest.fixture
def sample_children():
    """Sample children pages list."""
    return {
        "results": [
            {
                "id": "200",
                "title": "Child 1",
                "parentId": "123456",
                "status": "current",
            },
            {
                "id": "201",
                "title": "Child 2",
                "parentId": "123456",
                "status": "current",
            },
        ],
        "_links": {},
    }


@pytest.fixture
def sample_page_tree():
    """Sample page tree structure."""
    return {
        "id": "123456",
        "title": "Root Page",
        "status": "current",
        "children": [
            {
                "id": "200",
                "title": "Child 1",
                "children": [{"id": "300", "title": "Grandchild 1", "children": []}],
            },
            {"id": "201", "title": "Child 2", "children": []},
        ],
    }
