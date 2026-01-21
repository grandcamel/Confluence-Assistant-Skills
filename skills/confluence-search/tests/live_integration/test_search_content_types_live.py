"""
Live integration tests for searching different content types.

Usage:
    pytest test_search_content_types_live.py --live -v
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
class TestSearchContentTypesLive:
    """Live tests for searching different content types."""

    def test_search_pages_only(self, confluence_client, test_space):
        """Test searching for pages only."""
        results = confluence_client.get(
            "/rest/api/search",
            params={
                "cql": f'space = "{test_space["key"]}" AND type = page',
                "limit": 10,
            },
        )

        assert "results" in results
        for r in results.get("results", []):
            assert r.get("content", {}).get("type") == "page"

    def test_search_blogposts_only(self, confluence_client, test_space):
        """Test searching for blog posts only."""
        results = confluence_client.get(
            "/rest/api/search",
            params={
                "cql": f'space = "{test_space["key"]}" AND type = blogpost',
                "limit": 10,
            },
        )

        assert "results" in results

    def test_search_attachments(self, confluence_client, test_space):
        """Test searching for attachments."""
        results = confluence_client.get(
            "/rest/api/search",
            params={
                "cql": f'space = "{test_space["key"]}" AND type = attachment',
                "limit": 10,
            },
        )

        assert "results" in results

    def test_search_comments(self, confluence_client, test_space):
        """Test searching for comments."""
        results = confluence_client.get(
            "/rest/api/search",
            params={
                "cql": f'space = "{test_space["key"]}" AND type = comment',
                "limit": 10,
            },
        )

        assert "results" in results

    def test_search_multiple_types(self, confluence_client, test_space):
        """Test searching for multiple content types."""
        results = confluence_client.get(
            "/rest/api/search",
            params={
                "cql": f'space = "{test_space["key"]}" AND type in (page, blogpost)',
                "limit": 10,
            },
        )

        assert "results" in results

    def test_search_all_content(self, confluence_client, test_space):
        """Test searching all content types."""
        results = confluence_client.get(
            "/rest/api/search",
            params={"cql": f'space = "{test_space["key"]}"', "limit": 10},
        )

        assert "results" in results
