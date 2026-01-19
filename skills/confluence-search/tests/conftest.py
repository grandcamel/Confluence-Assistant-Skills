"""
Pytest fixtures for confluence-search skill tests.

Extends the shared fixtures with search-specific test data.
"""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest

# =============================================================================
# Mock Fixtures (from shared conftest)
# =============================================================================


@pytest.fixture
def mock_response():
    """Factory for creating mock HTTP responses."""

    def _create_response(
        status_code: int = 200,
        json_data=None,
        text: str = "",
        headers=None,
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

        # Create a mock session
        client.session = MagicMock()

        # Helper to set up responses
        def setup_response(method: str, response_data, status_code: int = 200):
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
def sample_search_results():
    """Sample search results from API."""
    return {
        "results": [
            {
                "content": {
                    "id": "123456",
                    "status": "current",
                    "title": "Test Page",
                    "spaceId": "789",
                },
                "excerpt": "This is a <em>test</em> page with content...",
                "lastModified": "2024-01-15T10:30:00.000Z",
            }
        ],
        "_links": {"next": "/rest/api/search?cql=space=TEST&cursor=abc123"},
        "limit": 25,
        "size": 1,
        "start": 0,
        "totalSize": 1,
    }


@pytest.fixture
def sample_cql_fields():
    """Sample CQL field suggestions."""
    return [
        {"name": "space", "type": "string", "description": "Space key"},
        {"name": "title", "type": "string", "description": "Page title"},
        {"name": "text", "type": "string", "description": "Full text search"},
        {
            "name": "type",
            "type": "enum",
            "description": "Content type",
            "values": ["page", "blogpost", "comment", "attachment"],
        },
        {"name": "label", "type": "string", "description": "Content label"},
        {"name": "creator", "type": "string", "description": "Content creator"},
        {"name": "created", "type": "date", "description": "Creation date"},
        {"name": "lastModified", "type": "date", "description": "Last modified date"},
        {"name": "ancestor", "type": "string", "description": "Ancestor page ID"},
        {"name": "parent", "type": "string", "description": "Parent page ID"},
    ]


@pytest.fixture
def sample_cql_operators():
    """Sample CQL operators."""
    return [
        {"operator": "=", "description": "Equals"},
        {"operator": "!=", "description": "Not equals"},
        {"operator": "~", "description": "Contains (text search)"},
        {"operator": "!~", "description": "Does not contain"},
        {"operator": ">", "description": "Greater than"},
        {"operator": "<", "description": "Less than"},
        {"operator": ">=", "description": "Greater than or equal"},
        {"operator": "<=", "description": "Less than or equal"},
        {"operator": "in", "description": "In list"},
        {"operator": "not in", "description": "Not in list"},
    ]


@pytest.fixture
def sample_cql_functions():
    """Sample CQL functions."""
    return [
        {"name": "currentUser()", "description": "Current logged in user"},
        {"name": "startOfDay()", "description": "Start of today"},
        {"name": "startOfWeek()", "description": "Start of this week"},
        {"name": "startOfMonth()", "description": "Start of this month"},
        {"name": "startOfYear()", "description": "Start of this year"},
        {"name": "endOfDay()", "description": "End of today"},
        {"name": "endOfWeek()", "description": "End of this week"},
        {"name": "endOfMonth()", "description": "End of this month"},
        {"name": "endOfYear()", "description": "End of this year"},
    ]


@pytest.fixture
def sample_query_history():
    """Sample query history entries."""
    return [
        {
            "query": "space = 'DOCS' AND type = page",
            "timestamp": "2024-01-15T10:30:00.000Z",
            "results_count": 42,
        },
        {
            "query": "label = 'api' AND creator = currentUser()",
            "timestamp": "2024-01-14T15:45:00.000Z",
            "results_count": 15,
        },
        {
            "query": "text ~ 'documentation' ORDER BY lastModified DESC",
            "timestamp": "2024-01-13T09:20:00.000Z",
            "results_count": 128,
        },
    ]


@pytest.fixture
def sample_spaces_for_suggestion():
    """Sample spaces for field value suggestions."""
    return {
        "results": [
            {"id": "1", "key": "DOCS", "name": "Documentation"},
            {"id": "2", "key": "KB", "name": "Knowledge Base"},
            {"id": "3", "key": "DEV", "name": "Development"},
        ]
    }


@pytest.fixture
def sample_labels_for_suggestion():
    """Sample labels for field value suggestions."""
    return {
        "results": [
            {"id": "1", "name": "documentation", "prefix": "global"},
            {"id": "2", "name": "api", "prefix": "global"},
            {"id": "3", "name": "tutorial", "prefix": "global"},
            {"id": "4", "name": "reference", "prefix": "global"},
        ]
    }
