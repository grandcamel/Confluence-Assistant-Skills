"""
Live integration tests for attachment download operations.

Usage:
    pytest test_attachment_download_live.py --profile development -v
"""

import contextlib
import os
import tempfile
import uuid
from pathlib import Path

import pytest

from confluence_assistant_skills_lib import (
    get_confluence_client,
)


def pytest_addoption(parser):
    with contextlib.suppress(ValueError):
        parser.addoption("--profile", action="store", default=None)


@pytest.fixture(scope="session")
def confluence_client(request):
    profile = request.config.getoption("--profile", default=None)
    return get_confluence_client(profile=profile)


@pytest.fixture(scope="session")
def test_space(confluence_client):
    spaces = confluence_client.get("/api/v2/spaces", params={"limit": 1})
    if not spaces.get("results"):
        pytest.skip("No spaces available")
    return spaces["results"][0]


@pytest.fixture
def test_page_with_attachment(confluence_client, test_space):
    """Create a page with an attachment."""
    page = confluence_client.post(
        "/api/v2/pages",
        json_data={
            "spaceId": test_space["id"],
            "status": "current",
            "title": f"Download Test {uuid.uuid4().hex[:8]}",
            "body": {"representation": "storage", "value": "<p>Test.</p>"},
        },
    )

    # Create temp file
    content = "Test content for download verification."
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        temp_path = Path(f.name)

    try:
        result = confluence_client.upload_file(
            f"/rest/api/content/{page['id']}/child/attachment", temp_path
        )
        attachment = result["results"][0]
        yield {"page": page, "attachment": attachment, "content": content}
    finally:
        os.unlink(temp_path)
        with contextlib.suppress(Exception):
            confluence_client.delete(f"/api/v2/pages/{page['id']}")


@pytest.mark.integration
class TestAttachmentDownloadLive:
    """Live tests for attachment download operations."""

    def test_get_download_link(self, confluence_client, test_page_with_attachment):
        """Test getting attachment download link."""
        attachment = test_page_with_attachment["attachment"]

        # Get attachment details using v2 API
        details = confluence_client.get(f"/api/v2/attachments/{attachment['id']}")

        assert "downloadLink" in details or "webuiLink" in details

    def test_attachment_exists(self, confluence_client, test_page_with_attachment):
        """Test that uploaded attachment exists."""
        attachment = test_page_with_attachment["attachment"]

        details = confluence_client.get(f"/api/v2/attachments/{attachment['id']}")

        assert details["id"] == attachment["id"]

    def test_list_page_attachments_for_download(
        self, confluence_client, test_page_with_attachment
    ):
        """Test listing attachments available for download."""
        page = test_page_with_attachment["page"]

        attachments = confluence_client.get(f"/api/v2/pages/{page['id']}/attachments")

        assert "results" in attachments
        assert len(attachments["results"]) >= 1

    def test_attachment_has_media_type(
        self, confluence_client, test_page_with_attachment
    ):
        """Test that attachment has media type for download handling."""
        attachment = test_page_with_attachment["attachment"]

        details = confluence_client.get(f"/api/v2/attachments/{attachment['id']}")

        assert "mediaType" in details
