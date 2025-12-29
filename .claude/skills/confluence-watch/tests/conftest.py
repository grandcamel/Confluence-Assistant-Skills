"""
Confluence Watch Skill - Test Configuration
"""

import sys
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# Add shared lib to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'shared' / 'scripts' / 'lib'))


@pytest.fixture
def mock_response():
    """Factory for creating mock HTTP responses."""
    def _create_response(
        status_code: int = 200,
        json_data: dict = None,
        text: str = "",
        headers: dict = None,
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
    from confluence_client import ConfluenceClient

    with patch.object(ConfluenceClient, '_create_session'):
        client = ConfluenceClient(
            base_url="https://test.atlassian.net",
            email="test@example.com",
            api_token="test-token"
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
        "_links": {"webui": "/wiki/spaces/TEST/pages/123456"}
    }


@pytest.fixture
def sample_space():
    """Sample space data from API."""
    return {
        "id": "789",
        "key": "TEST",
        "name": "Test Space",
        "type": "global",
        "status": "current"
    }


@pytest.fixture
def sample_watcher():
    """Sample watcher/user data from API."""
    return {
        "type": "known",
        "accountId": "user-123",
        "email": "test@example.com",
        "displayName": "Test User",
        "publicName": "Test User"
    }


@pytest.fixture
def sample_watch_response():
    """Sample watch response from API."""
    return {
        "success": True,
        "status_code": 200
    }
