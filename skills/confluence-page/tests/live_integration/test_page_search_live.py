"""
Live integration tests for page search operations.

Usage:
    pytest test_page_search_live.py --live -v
"""

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


@pytest.mark.integration
class TestPageSearchLive:
    """Live tests for page search operations."""

    def test_search_page_by_title(self, confluence_client, test_space):
        """Test searching for a page by title."""
        # Create a uniquely titled page
        unique = uuid.uuid4().hex[:8]
        title = f"SearchTest {unique}"

        page = confluence_client.post(
            "/api/v2/pages",
            json_data={
                "spaceId": test_space["id"],
                "status": "current",
                "title": title,
                "body": {"representation": "storage", "value": "<p>Searchable.</p>"},
            },
        )

        try:
            results = confluence_client.get(
                "/rest/api/search", params={"cql": f'title ~ "{unique}"', "limit": 10}
            )
            assert "results" in results
        finally:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")

    def test_search_page_by_content(self, confluence_client, test_space):
        """Test searching for a page by content."""
        unique = uuid.uuid4().hex[:8]

        page = confluence_client.post(
            "/api/v2/pages",
            json_data={
                "spaceId": test_space["id"],
                "status": "current",
                "title": f"Content Search {uuid.uuid4().hex[:8]}",
                "body": {
                    "representation": "storage",
                    "value": f"<p>UniqueContent{unique}</p>",
                },
            },
        )

        try:
            results = confluence_client.get(
                "/rest/api/search",
                params={"cql": f'text ~ "UniqueContent{unique}"', "limit": 10},
            )
            assert "results" in results
        finally:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")

    def test_search_recently_created(self, confluence_client, test_space):
        """Test searching for recently created pages."""
        from datetime import datetime

        today = datetime.now().strftime("%Y-%m-%d")

        results = confluence_client.get(
            "/rest/api/search",
            params={
                "cql": f'space = "{test_space["key"]}" AND created >= "{today}" AND type = page',
                "limit": 10,
            },
        )

        assert "results" in results
