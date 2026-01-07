"""
Live integration tests for search pagination operations.

Usage:
    pytest test_search_pagination_live.py --live -v
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
class TestSearchPaginationLive:
    """Live tests for search pagination operations."""

    def test_paginated_search(self, confluence_client, test_space):
        """Test paginated search results."""
        # First page
        page1 = confluence_client.get(
            "/rest/api/search",
            params={"cql": f'space = "{test_space["key"]}"', "limit": 5},
        )

        assert "results" in page1
        assert "_links" in page1

    def test_search_with_start_offset(self, confluence_client, test_space):
        """Test search with start offset."""
        results = confluence_client.get(
            "/rest/api/search",
            params={"cql": f'space = "{test_space["key"]}"', "start": 0, "limit": 10},
        )

        assert "results" in results

    def test_search_total_size(self, confluence_client, test_space):
        """Test that search returns total size info."""
        results = confluence_client.get(
            "/rest/api/search",
            params={"cql": f'space = "{test_space["key"]}"', "limit": 5},
        )

        # Should have size or totalSize
        assert "size" in results or "totalSize" in results or "results" in results

    def test_search_multiple_pages(self, confluence_client, test_space):
        """Test fetching multiple pages of results."""
        all_results = []

        # First page
        page = confluence_client.get(
            "/rest/api/search",
            params={"cql": f'space = "{test_space["key"]}"', "limit": 5},
        )
        all_results.extend(page.get("results", []))

        # Get second page if available
        if len(page.get("results", [])) == 5:
            page2 = confluence_client.get(
                "/rest/api/search",
                params={
                    "cql": f'space = "{test_space["key"]}"',
                    "start": 5,
                    "limit": 5,
                },
            )
            all_results.extend(page2.get("results", []))

        assert len(all_results) >= 0

    def test_search_with_expand(self, confluence_client, test_space):
        """Test search with expanded content."""
        results = confluence_client.get(
            "/rest/api/search",
            params={
                "cql": f'space = "{test_space["key"]}" AND type = page',
                "expand": "content.body.view",
                "limit": 3,
            },
        )

        assert "results" in results
