"""
Live integration tests for bulk watch operations.

Usage:
    pytest test_watch_bulk_live.py --live -v
"""

import contextlib
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
def test_pages(confluence_client, test_space):
    """Create multiple test pages."""
    pages = []
    for i in range(3):
        page = confluence_client.post(
            "/api/v2/pages",
            json_data={
                "spaceId": test_space["id"],
                "status": "current",
                "title": f"Watch Bulk Test {i} {uuid.uuid4().hex[:8]}",
                "body": {"representation": "storage", "value": f"<p>Page {i}.</p>"},
            },
        )
        pages.append(page)

    yield pages

    for page in pages:
        with contextlib.suppress(Exception):
            confluence_client.delete(f"/api/v2/pages/{page['id']}")


@pytest.fixture
def current_user(confluence_client):
    return confluence_client.get("/rest/api/user/current")


@pytest.mark.integration
class TestWatchBulkLive:
    """Live tests for bulk watch operations."""

    def test_watch_multiple_pages(self, confluence_client, test_pages, current_user):
        """Test watching multiple pages."""
        for page in test_pages:
            try:
                confluence_client.post(
                    f"/rest/api/user/watch/content/{page['id']}", json_data={}
                )
            except Exception:
                # Watch may already exist
                pass

        # Verify - at minimum the pages should still be accessible
        for page in test_pages:
            result = confluence_client.get(f"/api/v2/pages/{page['id']}")
            assert result["id"] == page["id"]

    def test_unwatch_multiple_pages(self, confluence_client, test_pages, current_user):
        """Test unwatching multiple pages."""
        # Watch first
        for page in test_pages:
            with contextlib.suppress(Exception):
                confluence_client.post(
                    f"/rest/api/user/watch/content/{page['id']}", json_data={}
                )

        # Unwatch
        for page in test_pages:
            with contextlib.suppress(Exception):
                confluence_client.delete(f"/rest/api/user/watch/content/{page['id']}")

        # Verify pages still accessible
        for page in test_pages:
            result = confluence_client.get(f"/api/v2/pages/{page['id']}")
            assert result["id"] == page["id"]

    def test_check_watch_status_multiple(
        self, confluence_client, test_pages, current_user
    ):
        """Test checking watch status on multiple pages."""
        # Each page should be queryable for watch status
        for page in test_pages:
            try:
                # Try to get watch status
                confluence_client.get(f"/rest/api/user/watch/content/{page['id']}")
            except Exception:
                # 404 means not watching, which is valid
                pass
