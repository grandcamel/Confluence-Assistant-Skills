"""
Shared pytest fixtures for Confluence Assistant Skills tests.

This conftest.py provides common fixtures used across all skill tests:
- Mock Confluence client
- Test configuration
- Sample data generators
- Live integration fixtures (when --profile is provided)

Usage:
    # In your test file
    def test_something(mock_client, sample_page):
        result = mock_client.get('/api/v2/pages/123')
        assert result['id'] == '123'
"""

import os
import sys
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any, Optional

# Add shared lib to path
lib_path = Path(__file__).parent.parent / 'scripts' / 'lib'
sys.path.insert(0, str(lib_path))


def pytest_addoption(parser):
    """Add custom command-line options."""
    try:
        parser.addoption(
            "--profile",
            action="store",
            default=None,
            help="Confluence profile for live integration tests"
        )
    except ValueError:
        pass  # Option already added
    try:
        parser.addoption(
            "--live",
            action="store_true",
            default=False,
            help="Run live integration tests"
        )
    except ValueError:
        pass  # Option already added


def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line(
        "markers", "live: mark test as requiring live Confluence connection"
    )
    config.addinivalue_line(
        "markers", "destructive: mark test as making destructive changes"
    )


def pytest_collection_modifyitems(config, items):
    """Skip live tests unless --profile or --live is provided."""
    if not config.getoption("--profile") and not config.getoption("--live"):
        skip_live = pytest.mark.skip(reason="Need --profile or --live to run")
        for item in items:
            if "live" in item.keywords:
                item.add_marker(skip_live)


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_response():
    """Factory for creating mock HTTP responses."""
    def _create_response(
        status_code: int = 200,
        json_data: Optional[Dict] = None,
        text: str = "",
        headers: Optional[Dict] = None,
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

        # Create a mock session
        client.session = MagicMock()

        # Helper to set up responses
        def setup_response(method: str, response_data: Dict, status_code: int = 200):
            response = mock_response(status_code=status_code, json_data=response_data)
            getattr(client.session, method.lower()).return_value = response

        client.setup_response = setup_response

        yield client


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    return {
        "default_profile": "test",
        "profiles": {
            "test": {
                "url": "https://test.atlassian.net",
                "email": "test@example.com",
                "api_token": "test-token",
                "default_space": "TEST",
            }
        },
        "api": {
            "timeout": 30,
            "max_retries": 3,
            "retry_backoff": 2.0,
        }
    }


# ============================================================================
# Sample Data Fixtures
# ============================================================================

@pytest.fixture
def sample_page():
    """Sample page data from API."""
    return {
        "id": "123456",
        "status": "current",
        "title": "Test Page",
        "spaceId": "789",
        "parentId": "111",
        "parentType": "page",
        "position": 0,
        "authorId": "user123",
        "ownerId": "user123",
        "lastOwnerId": "user123",
        "createdAt": "2024-01-15T10:30:00.000Z",
        "version": {
            "number": 1,
            "message": "Initial version",
            "minorEdit": False,
            "authorId": "user123",
            "createdAt": "2024-01-15T10:30:00.000Z"
        },
        "body": {
            "storage": {
                "value": "<p>Test content</p>",
                "representation": "storage"
            },
            "atlas_doc_format": {
                "value": json.dumps({
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "Test content"}]
                        }
                    ]
                }),
                "representation": "atlas_doc_format"
            }
        },
        "_links": {
            "webui": "/wiki/spaces/TEST/pages/123456/Test+Page",
            "editui": "/wiki/pages/resumedraft.action?draftId=123456",
            "tinyui": "/wiki/x/abc123"
        }
    }


@pytest.fixture
def sample_space():
    """Sample space data from API."""
    return {
        "id": "789",
        "key": "TEST",
        "name": "Test Space",
        "type": "global",
        "status": "current",
        "homepageId": "123456",
        "description": {
            "plain": {
                "value": "A test space for unit tests",
                "representation": "plain"
            }
        },
        "_links": {
            "webui": "/wiki/spaces/TEST"
        }
    }


@pytest.fixture
def sample_comment():
    """Sample comment data from API."""
    return {
        "id": "comment123",
        "status": "current",
        "title": "Re: Test Page",
        "pageId": "123456",
        "authorId": "user456",
        "createdAt": "2024-01-16T14:00:00.000Z",
        "version": {
            "number": 1,
            "createdAt": "2024-01-16T14:00:00.000Z"
        },
        "body": {
            "storage": {
                "value": "<p>This is a test comment</p>",
                "representation": "storage"
            }
        }
    }


@pytest.fixture
def sample_attachment():
    """Sample attachment data from API."""
    return {
        "id": "att123",
        "status": "current",
        "title": "document.pdf",
        "mediaType": "application/pdf",
        "mediaTypeDescription": "PDF Document",
        "fileSize": 102400,
        "webuiLink": "/wiki/download/attachments/123456/document.pdf",
        "downloadLink": "/wiki/download/attachments/123456/document.pdf",
        "pageId": "123456",
        "version": {
            "number": 1,
            "createdAt": "2024-01-17T09:00:00.000Z"
        },
        "_links": {
            "download": "/wiki/download/attachments/123456/document.pdf"
        }
    }


@pytest.fixture
def sample_label():
    """Sample label data from API."""
    return {
        "id": "label123",
        "name": "documentation",
        "prefix": "global"
    }


@pytest.fixture
def sample_search_results(sample_page):
    """Sample search results from API."""
    return {
        "results": [
            {
                "content": sample_page,
                "excerpt": "This is a <em>test</em> page with content...",
                "lastModified": "2024-01-15T10:30:00.000Z"
            }
        ],
        "_links": {
            "next": "/rest/api/search?cql=space=TEST&cursor=abc123"
        },
        "limit": 25,
        "size": 1,
        "start": 0,
        "totalSize": 1
    }


@pytest.fixture
def sample_adf():
    """Sample ADF document."""
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "heading",
                "attrs": {"level": 1},
                "content": [{"type": "text", "text": "Test Heading"}]
            },
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "This is "},
                    {"type": "text", "text": "bold", "marks": [{"type": "strong"}]},
                    {"type": "text", "text": " text."}
                ]
            }
        ]
    }


# ============================================================================
# Live Integration Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def live_profile(request):
    """Get the profile name for live tests."""
    profile = request.config.getoption("--profile")
    if not profile:
        pytest.skip("No --profile provided for live tests")
    return profile


@pytest.fixture(scope="session")
def live_client(live_profile):
    """Create a real Confluence client for live tests."""
    from config_manager import get_confluence_client
    return get_confluence_client(profile=live_profile)


@pytest.fixture(scope="session")
def live_test_space(live_client):
    """
    Get or create a test space for live integration tests.

    Uses existing space if CONFLUENCE_TEST_SPACE env var is set,
    otherwise creates a temporary space.
    """
    existing_space = os.environ.get("CONFLUENCE_TEST_SPACE")

    if existing_space:
        # Use existing space
        spaces = list(live_client.paginate(
            '/api/v2/spaces',
            params={'keys': existing_space}
        ))
        if spaces:
            yield spaces[0]
            return

    # Create temporary test space
    import uuid
    space_key = f"CASTEST{uuid.uuid4().hex[:6].upper()}"

    space = live_client.post('/api/v2/spaces', json_data={
        'key': space_key,
        'name': f'CAS Test Space {space_key}',
        'description': {
            'plain': {
                'value': 'Temporary space for Confluence Assistant Skills integration tests',
                'representation': 'plain'
            }
        }
    }, operation='create test space')

    yield space

    # Cleanup - delete the test space
    try:
        live_client.delete(f"/api/v2/spaces/{space['id']}", operation='delete test space')
    except Exception as e:
        print(f"Warning: Failed to cleanup test space: {e}")


@pytest.fixture
def live_test_page(live_client, live_test_space):
    """Create a test page for a single test."""
    import uuid

    page = live_client.post('/api/v2/pages', json_data={
        'spaceId': live_test_space['id'],
        'status': 'current',
        'title': f'Test Page {uuid.uuid4().hex[:8]}',
        'body': {
            'representation': 'storage',
            'value': '<p>Test content for integration test</p>'
        }
    }, operation='create test page')

    yield page

    # Cleanup
    try:
        live_client.delete(f"/api/v2/pages/{page['id']}", operation='delete test page')
    except Exception:
        pass


# ============================================================================
# Utility Fixtures
# ============================================================================

@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary file for upload tests."""
    def _create_file(name: str = "test.txt", content: str = "Test content"):
        file_path = tmp_path / name
        file_path.write_text(content)
        return file_path

    return _create_file


@pytest.fixture
def capture_output(capsys):
    """Helper to capture and return stdout/stderr."""
    def _capture():
        captured = capsys.readouterr()
        return captured.out, captured.err

    return _capture
