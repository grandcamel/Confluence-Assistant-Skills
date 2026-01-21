"""
Live integration tests for space statistics operations.

Usage:
    pytest test_space_stats_live.py --live -v
"""

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


@pytest.mark.integration
class TestSpaceStatsLive:
    """Live tests for space statistics operations."""

    def test_count_pages_in_space(self, confluence_client, test_space):
        """Test counting pages in a space."""
        pages = confluence_client.get(
            "/api/v2/pages", params={"space-id": test_space["id"], "limit": 250}
        )

        count = len(pages.get("results", []))
        assert count >= 0

    def test_count_blogposts_in_space(self, confluence_client, test_space):
        """Test counting blog posts in a space."""
        posts = confluence_client.get(
            "/api/v2/blogposts", params={"space-id": test_space["id"], "limit": 250}
        )

        count = len(posts.get("results", []))
        assert count >= 0

    def test_get_space_activity(self, confluence_client, test_space):
        """Test getting recent activity in space."""
        results = confluence_client.get(
            "/rest/api/search",
            params={
                "cql": f'space = "{test_space["key"]}" ORDER BY lastModified DESC',
                "limit": 20,
            },
        )

        assert "results" in results

    def test_get_space_contributors(self, confluence_client, test_space):
        """Test getting contributors in space by searching recent content."""
        results = confluence_client.get(
            "/rest/api/search",
            params={
                "cql": f'space = "{test_space["key"]}" ORDER BY created DESC',
                "expand": "content.history.createdBy",
                "limit": 20,
            },
        )

        assert "results" in results

    def test_compare_content_types(self, confluence_client, test_space):
        """Test comparing different content type counts."""
        pages = confluence_client.get(
            "/api/v2/pages", params={"space-id": test_space["id"], "limit": 250}
        )

        posts = confluence_client.get(
            "/api/v2/blogposts", params={"space-id": test_space["id"], "limit": 250}
        )

        page_count = len(pages.get("results", []))
        post_count = len(posts.get("results", []))

        # Just verify we got counts
        assert page_count >= 0
        assert post_count >= 0
