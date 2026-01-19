"""
Confluence Attachment Skill - Test Configuration
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
            method_upper = method.upper()
            # POST/PUT/PATCH use session.request(), GET/DELETE use direct methods
            if method_upper in ("POST", "PUT", "PATCH"):
                client.session.request.return_value = response
            else:
                getattr(client.session, method.lower()).return_value = response

        client.setup_response = setup_response
        yield client


@pytest.fixture
def sample_attachment():
    """Sample attachment data from API."""
    return {
        "id": "att123456",
        "status": "current",
        "title": "test-file.pdf",
        "fileId": "file123",
        "fileSize": 1024,
        "webuiLink": "/wiki/download/attachments/123456/test-file.pdf",
        "downloadLink": "/wiki/download/attachments/123456/test-file.pdf",
        "mediaType": "application/pdf",
        "version": {"number": 1, "createdAt": "2024-01-01T00:00:00.000Z"},
        "pageId": "123456",
    }


@pytest.fixture
def sample_page():
    """Sample page data from API."""
    return {
        "id": "123456",
        "status": "current",
        "title": "Test Page",
        "spaceId": "789",
        "_links": {"webui": "/wiki/spaces/TEST/pages/123456"},
    }


@pytest.fixture
def test_file(tmp_path):
    """Create a temporary test file."""
    test_file = tmp_path / "test_upload.txt"
    test_file.write_text("This is a test file for attachment upload")
    return test_file


@pytest.fixture
def test_pdf_file(tmp_path):
    """Create a temporary test PDF file (mock)."""
    test_file = tmp_path / "test_document.pdf"
    test_file.write_bytes(b"%PDF-1.4 mock pdf content")
    return test_file


@pytest.fixture
def test_image_file(tmp_path):
    """Create a temporary test image file (mock)."""
    test_file = tmp_path / "test_image.png"
    test_file.write_bytes(b"\x89PNG\r\n\x1a\n mock png content")
    return test_file
