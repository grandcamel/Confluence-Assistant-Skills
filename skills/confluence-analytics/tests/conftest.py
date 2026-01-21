"""
Confluence Analytics Skill - Test Configuration
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
    from confluence_as import ConfluenceClient

    with patch.object(ConfluenceClient, "_create_session"):
        client = ConfluenceClient(
            base_url="https://test.atlassian.net",
            email="test@example.com",
            api_token="test-token",
        )

        client.session = MagicMock()

        def setup_response(method: str, response_data: dict, status_code: int = 200):
            response = mock_response(status_code=status_code, json_data=response_data)
            method_upper = method.upper()
            # POST/PUT/PATCH use session.request(), GET/DELETE use direct methods
            if method_upper in ("POST", "PUT", "PATCH"):
                client.session.request.return_value = response
            else:
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
        "type": "page",
        "space": {"key": "TEST"},
        "version": {"number": 5, "when": "2024-01-15T10:30:00.000Z"},
        "history": {
            "latest": True,
            "createdBy": {"displayName": "John Doe"},
            "createdDate": "2024-01-01T10:00:00.000Z",
        },
        "_links": {"webui": "/wiki/spaces/TEST/pages/123456"},
    }


@pytest.fixture
def sample_page_history():
    """Sample page history data from v1 API."""
    return {
        "id": "123456",
        "type": "page",
        "title": "Test Page",
        "version": {
            "number": 5,
            "when": "2024-01-15T10:30:00.000Z",
            "by": {"displayName": "John Doe"},
        },
        "history": {
            "latest": True,
            "createdBy": {"displayName": "John Doe"},
            "createdDate": "2024-01-01T10:00:00.000Z",
            "contributors": {
                "publishers": {
                    "users": [
                        {"displayName": "John Doe", "username": "jdoe"},
                        {"displayName": "Jane Smith", "username": "jsmith"},
                    ]
                }
            },
        },
    }


@pytest.fixture
def sample_search_results():
    """Sample CQL search results."""
    return {
        "results": [
            {
                "content": {
                    "id": "123456",
                    "type": "page",
                    "title": "Popular Page 1",
                    "space": {"key": "TEST"},
                    "_links": {"webui": "/wiki/spaces/TEST/pages/123456"},
                }
            },
            {
                "content": {
                    "id": "123457",
                    "type": "page",
                    "title": "Popular Page 2",
                    "space": {"key": "TEST"},
                    "_links": {"webui": "/wiki/spaces/TEST/pages/123457"},
                }
            },
        ],
        "start": 0,
        "limit": 25,
        "size": 2,
        "_links": {},
    }


@pytest.fixture
def sample_watchers():
    """Sample watchers data."""
    return {
        "results": [
            {
                "type": "known",
                "watcher": {
                    "type": "known",
                    "accountId": "user1",
                    "email": "user1@example.com",
                    "displayName": "User One",
                },
            },
            {
                "type": "known",
                "watcher": {
                    "type": "known",
                    "accountId": "user2",
                    "email": "user2@example.com",
                    "displayName": "User Two",
                },
            },
        ],
        "start": 0,
        "limit": 25,
        "size": 2,
    }
