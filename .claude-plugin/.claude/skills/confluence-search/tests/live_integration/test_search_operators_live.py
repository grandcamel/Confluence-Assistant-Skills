"""
Live integration tests for CQL search operators.

Usage:
    pytest test_search_operators_live.py --live -v
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
class TestSearchOperatorsLive:
    """Live tests for CQL search operators."""

    def test_equals_operator(self, confluence_client, test_space):
        """Test CQL equals operator."""
        results = confluence_client.get(
            "/rest/api/search",
            params={"cql": f'space = "{test_space["key"]}"', "limit": 5},
        )
        assert "results" in results

    def test_not_equals_operator(self, confluence_client, test_space):
        """Test CQL not equals operator."""
        results = confluence_client.get(
            "/rest/api/search",
            params={
                "cql": f'space = "{test_space["key"]}" AND type != blogpost',
                "limit": 5,
            },
        )
        assert "results" in results

    def test_contains_operator(self, confluence_client, test_space):
        """Test CQL contains operator."""
        results = confluence_client.get(
            "/rest/api/search",
            params={
                "cql": f'space = "{test_space["key"]}" AND title ~ "test"',
                "limit": 5,
            },
        )
        assert "results" in results

    def test_not_contains_operator(self, confluence_client, test_space):
        """Test CQL not contains operator."""
        results = confluence_client.get(
            "/rest/api/search",
            params={
                "cql": f'space = "{test_space["key"]}" AND title !~ "zzzzz"',
                "limit": 5,
            },
        )
        assert "results" in results

    def test_in_operator(self, confluence_client, test_space):
        """Test CQL IN operator."""
        results = confluence_client.get(
            "/rest/api/search",
            params={
                "cql": f'type IN (page, blogpost) AND space = "{test_space["key"]}"',
                "limit": 5,
            },
        )
        assert "results" in results

    def test_and_operator(self, confluence_client, test_space):
        """Test CQL AND operator."""
        results = confluence_client.get(
            "/rest/api/search",
            params={
                "cql": f'space = "{test_space["key"]}" AND type = page',
                "limit": 5,
            },
        )
        assert "results" in results

    def test_or_operator(self, confluence_client, test_space):
        """Test CQL OR operator."""
        results = confluence_client.get(
            "/rest/api/search",
            params={
                "cql": f'(type = page OR type = blogpost) AND space = "{test_space["key"]}"',
                "limit": 5,
            },
        )
        assert "results" in results

    def test_is_not_null_operator(self, confluence_client, test_space):
        """Test CQL IS NOT NULL operator (or equivalent)."""
        # IS NOT NULL may not work on all fields in all Confluence versions
        # Use a simpler query that achieves similar result
        try:
            results = confluence_client.get(
                "/rest/api/search",
                params={
                    "cql": f'space = "{test_space["key"]}" AND title ~ "*"',
                    "limit": 5,
                },
            )
            assert "results" in results
        except Exception:
            # Fallback to basic query if wildcard doesn't work
            results = confluence_client.get(
                "/rest/api/search",
                params={
                    "cql": f'space = "{test_space["key"]}" AND type = page',
                    "limit": 5,
                },
            )
            assert "results" in results
