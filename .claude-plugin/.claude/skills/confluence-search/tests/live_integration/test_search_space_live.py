"""
Live integration tests for space-specific search operations.

Usage:
    pytest test_search_space_live.py --profile development -v
"""

import contextlib

import pytest

from confluence_assistant_skills_lib import (
    get_confluence_client,
)


def pytest_addoption(parser):
    with contextlib.suppress(ValueError):
        parser.addoption("--profile", action="store", default=None)


@pytest.fixture(scope="session")
def confluence_client(request):
    profile = request.config.getoption("--profile", default=None)
    return get_confluence_client(profile=profile)


@pytest.fixture(scope="session")
def test_space(confluence_client):
    spaces = confluence_client.get("/api/v2/spaces", params={"limit": 1})
    if not spaces.get("results"):
        pytest.skip("No spaces available")
    return spaces["results"][0]


@pytest.mark.integration
class TestSearchSpaceLive:
    """Live tests for space-specific search operations."""

    def test_search_within_space(self, confluence_client, test_space):
        """Test searching within a specific space."""
        results = confluence_client.get(
            "/rest/api/search",
            params={"cql": f'space = "{test_space["key"]}"', "limit": 10},
        )

        assert "results" in results

    def test_search_across_multiple_spaces(self, confluence_client):
        """Test searching across all spaces."""
        results = confluence_client.get(
            "/rest/api/search", params={"cql": "type = page", "limit": 10}
        )

        assert "results" in results

    def test_exclude_space_from_search(self, confluence_client, test_space):
        """Test excluding a space from search."""
        results = confluence_client.get(
            "/rest/api/search",
            params={
                "cql": f'type = page AND space != "{test_space["key"]}"',
                "limit": 10,
            },
        )

        assert "results" in results

    def test_search_space_by_key(self, confluence_client, test_space):
        """Test finding a specific space by key."""
        spaces = confluence_client.get(
            "/api/v2/spaces", params={"keys": test_space["key"]}
        )

        assert "results" in spaces
        keys = [s["key"] for s in spaces["results"]]
        assert test_space["key"] in keys
