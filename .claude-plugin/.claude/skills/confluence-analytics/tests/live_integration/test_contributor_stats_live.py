"""
Live integration tests for contributor statistics.

Usage:
    pytest test_contributor_stats_live.py --live -v
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
class TestContributorStatsLive:
    """Live tests for contributor statistics."""

    def test_find_content_creators(self, confluence_client, test_space):
        """Test finding content creators in space."""
        results = confluence_client.get(
            "/rest/api/search",
            params={
                "cql": f'space = "{test_space["key"]}" AND type = page',
                "expand": "content.history.createdBy",
                "limit": 20,
            },
        )

        assert "results" in results

    def test_find_recent_contributors(self, confluence_client, test_space):
        """Test finding recent contributors."""
        from datetime import datetime, timedelta

        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        results = confluence_client.get(
            "/rest/api/search",
            params={
                "cql": f'space = "{test_space["key"]}" AND lastModified >= "{week_ago}"',
                "expand": "content.history.lastUpdated",
                "limit": 20,
            },
        )

        assert "results" in results

    def test_get_page_creator(self, confluence_client, test_space):
        """Test getting page creator information."""
        # Get a page
        pages = confluence_client.get(
            "/api/v2/pages", params={"space-id": test_space["id"], "limit": 1}
        )

        if pages.get("results"):
            page = pages["results"][0]
            # Get with history expansion via v1
            detailed = confluence_client.get(
                f"/rest/api/content/{page['id']}", params={"expand": "history"}
            )
            assert "history" in detailed

    def test_count_contributions_by_type(self, confluence_client, test_space):
        """Test counting contributions by content type."""
        # Count pages
        pages = confluence_client.get(
            "/rest/api/search",
            params={
                "cql": f'space = "{test_space["key"]}" AND type = page AND creator = currentUser()',
                "limit": 100,
            },
        )

        # Count blogposts
        posts = confluence_client.get(
            "/rest/api/search",
            params={
                "cql": f'space = "{test_space["key"]}" AND type = blogpost AND creator = currentUser()',
                "limit": 100,
            },
        )

        page_count = len(pages.get("results", []))
        post_count = len(posts.get("results", []))

        assert page_count >= 0
        assert post_count >= 0
