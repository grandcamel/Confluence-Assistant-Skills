"""
Live integration tests for page version history operations.

Usage:
    pytest test_page_versions_live.py --live -v
"""

import contextlib
import time
import uuid

import pytest

from confluence_as import (
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


def _update_page_with_retry(client, page_id, title, version_num, max_retries=3):
    """Update page with retry logic for version conflicts."""
    from confluence_as.error_handler import ConflictError

    for attempt in range(max_retries):
        # Always re-fetch to get current version
        current = client.get(f"/api/v2/pages/{page_id}")
        current_version = current["version"]["number"]

        try:
            return client.put(
                f"/api/v2/pages/{page_id}",
                json_data={
                    "id": page_id,
                    "status": "current",
                    "title": title,
                    "version": {"number": current_version + 1, "message": f"Version {version_num}"},
                    "body": {"representation": "storage", "value": f"<p>Version {version_num}</p>"},
                },
            )
        except ConflictError:
            if attempt < max_retries - 1:
                time.sleep(1.0 * (attempt + 1))  # Exponential backoff
            else:
                raise

    return None  # Should not reach here


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

    # Create additional versions with retry logic
    for i in range(2, 5):
        time.sleep(0.5)
        page = _update_page_with_retry(
            confluence_client, page["id"], page["title"], i
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
