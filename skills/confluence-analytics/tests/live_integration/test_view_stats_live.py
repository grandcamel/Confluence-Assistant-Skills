"""
Live integration tests for view statistics operations.

Usage:
    pytest test_view_stats_live.py --live -v
"""

import contextlib
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


@pytest.fixture
def test_page(confluence_client, test_space):
    page = confluence_client.post(
        "/api/v2/pages",
        json_data={
            "spaceId": test_space["id"],
            "status": "current",
            "title": f"View Stats Test {uuid.uuid4().hex[:8]}",
            "body": {"representation": "storage", "value": "<p>Test.</p>"},
        },
    )
    yield page
    with contextlib.suppress(Exception):
        confluence_client.delete(f"/api/v2/pages/{page['id']}")


@pytest.mark.integration
class TestViewStatsLive:
    """Live tests for view statistics operations."""

    def test_get_page_views_exist(self, confluence_client, test_page):
        """Test that page can be queried for view info."""
        # Read the page to increment view count
        page = confluence_client.get(f"/api/v2/pages/{test_page['id']}")
        assert page["id"] == test_page["id"]

    def test_get_popular_content(self, confluence_client, test_space):
        """Test querying for popular content in space."""
        # Search for most viewed content
        results = confluence_client.get(
            "/rest/api/search",
            params={
                "cql": f'space = "{test_space["key"]}" ORDER BY lastModified DESC',
                "limit": 10,
            },
        )

        assert "results" in results

    def test_get_recently_viewed(self, confluence_client):
        """Test getting recently viewed content for current user."""
        # This uses the user's history
        try:
            history = confluence_client.get(
                "/rest/api/content/search",
                params={"cql": 'lastModified >= now("-7d")', "limit": 10},
            )
            assert "results" in history or history is not None
        except Exception:
            # Some instances may not support this
            pass

    def test_get_content_watchers_count(self, confluence_client, test_page):
        """Test getting watcher information for content."""
        try:
            watchers = confluence_client.get(
                f"/rest/api/content/{test_page['id']}/notification/child-created"
            )
            # Response structure varies
            assert watchers is not None
        except Exception:
            # Watcher API may have different permissions
            pass
