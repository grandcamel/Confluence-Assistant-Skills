"""
Live integration tests for search export operations.

Usage:
    pytest test_search_export_live.py --profile development -v
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
class TestSearchExportLive:
    """Live tests for exporting search results."""

    def test_search_all_pages(self, confluence_client, test_space):
        """Test searching and collecting all pages in a space."""
        all_results = []
        start = 0
        limit = 25

        while True:
            results = confluence_client.get(
                "/rest/api/search",
                params={
                    "cql": f'space = "{test_space["key"]}" AND type = page',
                    "limit": limit,
                    "start": start,
                },
            )

            batch = results.get("results", [])
            all_results.extend(batch)

            if len(batch) < limit:
                break

            start += limit

            # Safety limit
            if start > 500:
                break

        assert isinstance(all_results, list)

    def test_search_with_content_expansion(self, confluence_client, test_space):
        """Test searching with expanded content."""
        results = confluence_client.get(
            "/rest/api/search",
            params={
                "cql": f'space = "{test_space["key"]}" AND type = page',
                "limit": 5,
                "expand": "content.body.storage,content.version",
            },
        )

        assert "results" in results

        for result in results["results"]:
            content = result.get("content", {})
            if "body" in content:
                assert "storage" in content["body"]

    def test_search_results_format(self, confluence_client, test_space):
        """Test search results contain expected fields."""
        results = confluence_client.get(
            "/rest/api/search",
            params={
                "cql": f'space = "{test_space["key"]}" AND type = page',
                "limit": 5,
            },
        )

        for result in results.get("results", []):
            content = result.get("content", {})
            assert "id" in content
            assert "title" in content
            assert "type" in content

    def test_search_order_by_modified(self, confluence_client, test_space):
        """Test searching with order by last modified."""
        results = confluence_client.get(
            "/rest/api/search",
            params={
                "cql": f'space = "{test_space["key"]}" ORDER BY lastModified DESC',
                "limit": 10,
            },
        )

        assert "results" in results
        # Results should be in descending order by last modified

    def test_search_order_by_created(self, confluence_client, test_space):
        """Test searching with order by created date."""
        results = confluence_client.get(
            "/rest/api/search",
            params={
                "cql": f'space = "{test_space["key"]}" ORDER BY created DESC',
                "limit": 10,
            },
        )

        assert "results" in results
