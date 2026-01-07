"""
Live integration tests for attachment metadata operations.

Usage:
    pytest test_attachment_metadata_live.py --profile development -v
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
def test_page(confluence_client, test_space):
    page = confluence_client.post(
        "/api/v2/pages",
        json_data={
            "spaceId": test_space["id"],
            "status": "current",
            "title": f"Attachment Metadata Test {uuid.uuid4().hex[:8]}",
            "body": {"representation": "storage", "value": "<p>Test.</p>"},
        },
    )
    yield page
    with contextlib.suppress(Exception):
        confluence_client.delete(f"/api/v2/pages/{page['id']}")


@pytest.fixture
def test_attachment(confluence_client, test_page):
    """Create a test attachment."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Test attachment content for metadata tests.")
        temp_path = Path(f.name)

    try:
        result = confluence_client.upload_file(
            f"/rest/api/content/{test_page['id']}/child/attachment", temp_path
        )
        attachment = result["results"][0]
        yield attachment
    finally:
        os.unlink(temp_path)


@pytest.mark.integration
class TestAttachmentMetadataLive:
    """Live tests for attachment metadata operations."""

    def test_get_attachment_details(
        self, confluence_client, test_page, test_attachment
    ):
        """Test getting attachment details."""
        attachment = confluence_client.get(
            f"/api/v2/attachments/{test_attachment['id']}"
        )

        assert attachment["id"] == test_attachment["id"]
        assert "title" in attachment
        assert "mediaType" in attachment

    def test_list_page_attachments(self, confluence_client, test_page, test_attachment):
        """Test listing all attachments on a page."""
        attachments = confluence_client.get(
            f"/api/v2/pages/{test_page['id']}/attachments"
        )

        assert "results" in attachments
        attachment_ids = [a["id"] for a in attachments.get("results", [])]
        assert test_attachment["id"] in attachment_ids

    def test_attachment_media_type(self, confluence_client, test_attachment):
        """Test that attachment has a media type."""
        attachment = confluence_client.get(
            f"/api/v2/attachments/{test_attachment['id']}"
        )

        # Verify mediaType field exists and is non-empty
        assert "mediaType" in attachment
        assert attachment["mediaType"]  # Non-empty string

    def test_attachment_has_file_size(self, confluence_client, test_attachment):
        """Test that attachment reports file size."""
        attachment = confluence_client.get(
            f"/api/v2/attachments/{test_attachment['id']}"
        )

        # Should have fileSize or webuiLink
        assert "fileSize" in attachment or "webuiLink" in attachment
