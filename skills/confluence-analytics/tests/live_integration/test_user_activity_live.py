"""
Live integration tests for user activity analytics.

Usage:
    pytest test_user_activity_live.py --live -v
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


@pytest.fixture
def current_user(confluence_client):
    return confluence_client.get("/rest/api/user/current")


@pytest.mark.integration
class TestUserActivityLive:
    """Live tests for user activity analytics."""

    def test_get_user_created_content(self, confluence_client, current_user):
        """Test getting content created by current user."""
        results = confluence_client.get(
            "/rest/api/search",
            params={
                "cql": "creator = currentUser() AND type = page ORDER BY created DESC",
                "limit": 10,
            },
        )

        assert "results" in results

    def test_get_user_modified_content(self, confluence_client, current_user):
        """Test getting content modified by current user."""
        results = confluence_client.get(
            "/rest/api/search",
            params={
                "cql": "contributor = currentUser() ORDER BY lastModified DESC",
                "limit": 10,
            },
        )

        assert "results" in results

    def test_get_recent_user_activity(self, confluence_client, current_user):
        """Test getting recent activity by current user."""
        from datetime import datetime, timedelta

        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        results = confluence_client.get(
            "/rest/api/search",
            params={
                "cql": f'contributor = currentUser() AND lastModified >= "{week_ago}"',
                "limit": 20,
            },
        )

        assert "results" in results

    def test_get_user_details(self, confluence_client, current_user):
        """Test getting current user details."""
        assert "accountId" in current_user or "username" in current_user
        assert "displayName" in current_user or "publicName" in current_user

    def test_user_content_count(self, confluence_client, current_user):
        """Test counting content by current user."""
        results = confluence_client.get(
            "/rest/api/search",
            params={"cql": "creator = currentUser() AND type = page", "limit": 250},
        )

        count = len(results.get("results", []))
        assert count >= 0
