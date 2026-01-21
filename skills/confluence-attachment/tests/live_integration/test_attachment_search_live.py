"""
Live integration tests for attachment search operations.

Usage:
    pytest test_attachment_search_live.py --live -v
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
class TestAttachmentSearchLive:
    """Live tests for attachment search operations."""

    def test_search_attachments_in_space(self, confluence_client, test_space):
        """Test searching for attachments in a space."""
        results = confluence_client.get(
            "/rest/api/search",
            params={
                "cql": f'space = "{test_space["key"]}" AND type = attachment',
                "limit": 10,
            },
        )

        assert "results" in results

    def test_search_attachments_by_filename(self, confluence_client, test_space):
        """Test searching attachments by filename pattern."""
        results = confluence_client.get(
            "/rest/api/search",
            params={
                "cql": f'space = "{test_space["key"]}" AND type = attachment AND title ~ ".txt"',
                "limit": 10,
            },
        )

        assert "results" in results

    def test_search_attachments_by_date(self, confluence_client, test_space):
        """Test searching attachments by date."""
        from datetime import datetime, timedelta

        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        results = confluence_client.get(
            "/rest/api/search",
            params={
                "cql": f'space = "{test_space["key"]}" AND type = attachment AND created >= "{week_ago}"',
                "limit": 10,
            },
        )

        assert "results" in results
