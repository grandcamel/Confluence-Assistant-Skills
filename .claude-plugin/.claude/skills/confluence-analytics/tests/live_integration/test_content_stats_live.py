"""
Live integration tests for content statistics operations.

Usage:
    pytest test_content_stats_live.py --live -v
"""

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


@pytest.mark.integration
class TestContentStatsLive:
    """Live tests for content statistics."""

    def test_get_space_content_summary(self, confluence_client, test_space):
        """Test getting content summary for a space."""
        # Count pages
        pages = confluence_client.get(
            "/api/v2/pages", params={"space-id": test_space["id"], "limit": 250}
        )

        # Count blog posts
        posts = confluence_client.get(
            "/api/v2/blogposts", params={"space-id": test_space["id"], "limit": 250}
        )

        page_count = len(pages.get("results", []))
        post_count = len(posts.get("results", []))

        assert page_count >= 0
        assert post_count >= 0

    def test_get_recent_activity(self, confluence_client, test_space):
        """Test getting recently modified content."""
        results = confluence_client.get(
            "/rest/api/search",
            params={
                "cql": f'space = "{test_space["key"]}" ORDER BY lastModified DESC',
                "limit": 10,
            },
        )

        assert "results" in results

    def test_get_content_by_user(self, confluence_client):
        """Test getting content created by current user."""
        results = confluence_client.get(
            "/rest/api/search",
            params={
                "cql": "creator = currentUser() AND type = page ORDER BY created DESC",
                "limit": 10,
            },
        )

        assert "results" in results

    def test_get_content_modified_today(self, confluence_client, test_space):
        """Test getting content modified today."""
        from datetime import datetime

        today = datetime.now().strftime("%Y-%m-%d")

        results = confluence_client.get(
            "/rest/api/search",
            params={
                "cql": f'space = "{test_space["key"]}" AND lastModified >= "{today}"',
                "limit": 25,
            },
        )

        assert "results" in results
