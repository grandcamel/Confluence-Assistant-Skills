"""
Confluence Permission Skill - Test Configuration
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
def sample_space_permissions():
    """Sample space permissions data from API."""
    return {
        "results": [
            {
                "principal": {
                    "type": "user",
                    "id": "user-123"
                },
                "operation": {
                    "key": "read",
                    "target": "space"
                }
            },
            {
                "principal": {
                    "type": "group",
                    "id": "group-456"
                },
                "operation": {
                    "key": "administer",
                    "target": "space"
                }
            }
        ],
        "_links": {}
    }


@pytest.fixture
def sample_page_restrictions():
    """Sample page restrictions data from v1 API."""
    return {
        "read": {
            "operation": "read",
            "restrictions": {
                "user": {
                    "results": [
                        {
                            "type": "known",
                            "username": "user1",
                            "userKey": "user-key-1",
                            "accountId": "account-id-1"
                        }
                    ],
                    "size": 1
                },
                "group": {
                    "results": [
                        {
                            "type": "group",
                            "name": "confluence-administrators",
                            "id": "group-id-1"
                        }
                    ],
                    "size": 1
                }
            }
        },
        "update": {
            "operation": "update",
            "restrictions": {
                "user": {"results": [], "size": 0},
                "group": {"results": [], "size": 0}
            }
        }
    }


@pytest.fixture
def sample_page_operations():
    """Sample page operations data from v2 API."""
    return {
        "results": [
            {
                "operation": "read",
                "targetType": "page"
            },
            {
                "operation": "update",
                "targetType": "page"
            },
            {
                "operation": "delete",
                "targetType": "page"
            }
        ],
        "_links": {}
    }
