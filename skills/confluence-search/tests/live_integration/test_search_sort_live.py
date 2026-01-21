"""
Live integration tests for search sorting operations.

Usage:
    pytest test_search_sort_live.py --live -v
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
class TestSearchSortLive:
    """Live tests for search sorting operations."""

    def test_sort_by_last_modified_desc(self, confluence_client, test_space):
        """Test sorting by last modified descending."""
        results = confluence_client.get(
            "/rest/api/search",
            params={
                "cql": f'space = "{test_space["key"]}" ORDER BY lastModified DESC',
                "limit": 10,
            },
        )

        assert "results" in results

    def test_sort_by_last_modified_asc(self, confluence_client, test_space):
        """Test sorting by last modified ascending."""
        results = confluence_client.get(
            "/rest/api/search",
            params={
                "cql": f'space = "{test_space["key"]}" ORDER BY lastModified ASC',
                "limit": 10,
            },
        )

        assert "results" in results

    def test_sort_by_created(self, confluence_client, test_space):
        """Test sorting by created date."""
        results = confluence_client.get(
            "/rest/api/search",
            params={
                "cql": f'space = "{test_space["key"]}" ORDER BY created DESC',
                "limit": 10,
            },
        )

        assert "results" in results

    def test_sort_by_title(self, confluence_client, test_space):
        """Test sorting by title."""
        results = confluence_client.get(
            "/rest/api/search",
            params={
                "cql": f'space = "{test_space["key"]}" ORDER BY title ASC',
                "limit": 10,
            },
        )

        assert "results" in results

    def test_default_sort(self, confluence_client, test_space):
        """Test search with default sorting."""
        results = confluence_client.get(
            "/rest/api/search",
            params={"cql": f'space = "{test_space["key"]}"', "limit": 10},
        )

        assert "results" in results
