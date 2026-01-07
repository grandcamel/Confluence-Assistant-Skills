"""
Live integration tests for page version history operations.

Usage:
    pytest test_page_versions_live.py --live -v
"""

import contextlib
import time
import uuid

import pytest

from confluence_assistant_skills_lib import (
    get_confluence_client,
)


@pytest.fixture(scope="session")
def confluence_client():
    return get_confluence_client()


@pytest.fixture(scope="session")
def test_space(confluence_client):
    spaces = confluence_client.get("/api/v2/spaces", params={"limit": 1})
    if not spaces.get("results"):
        pytest.skip("No spaces available")
    return spaces["results"][0]


@pytest.fixture
def versioned_page(confluence_client, test_space):
    """Create a page with multiple versions."""
    page = confluence_client.post(
        "/api/v2/pages",
        json_data={
            "spaceId": test_space["id"],
            "status": "current",
            "title": f"Version Test {uuid.uuid4().hex[:8]}",
            "body": {"representation": "storage", "value": "<p>Version 1</p>"},
        },
    )

    # Create additional versions
    for i in range(2, 5):
        time.sleep(0.3)
        page = confluence_client.put(
            f"/api/v2/pages/{page['id']}",
            json_data={
                "id": page["id"],
                "status": "current",
                "title": page["title"],
                "version": {"number": i, "message": f"Version {i}"},
                "body": {"representation": "storage", "value": f"<p>Version {i}</p>"},
            },
        )

    yield page

    with contextlib.suppress(Exception):
        confluence_client.delete(f"/api/v2/pages/{page['id']}")


@pytest.mark.integration
class TestPageVersionsLive:
    """Live tests for page version history."""

    def test_get_version_history(self, confluence_client, versioned_page):
        """Test getting version history."""
        versions = confluence_client.get(
            f"/rest/api/content/{versioned_page['id']}/version"
        )

        assert "results" in versions
        assert len(versions["results"]) >= 4

    def test_get_specific_version(self, confluence_client, versioned_page):
        """Test getting a specific version."""
        version = confluence_client.get(
            f"/rest/api/content/{versioned_page['id']}/version/1"
        )

        assert version["number"] == 1

    def test_version_messages(self, confluence_client, versioned_page):
        """Test that version messages are preserved."""
        versions = confluence_client.get(
            f"/rest/api/content/{versioned_page['id']}/version"
        )

        # Check that version messages exist
        for v in versions["results"]:
            if v["number"] > 1:
                assert "message" in v

    def test_compare_versions(self, confluence_client, versioned_page):
        """Test getting content at different versions."""
        # Get version 1 content
        v1 = confluence_client.get(
            f"/rest/api/content/{versioned_page['id']}",
            params={"version": 1, "expand": "body.storage"},
        )

        # Get latest version
        latest = confluence_client.get(
            f"/rest/api/content/{versioned_page['id']}",
            params={"expand": "body.storage"},
        )

        assert "Version 1" in v1["body"]["storage"]["value"]
        assert "Version 4" in latest["body"]["storage"]["value"]
