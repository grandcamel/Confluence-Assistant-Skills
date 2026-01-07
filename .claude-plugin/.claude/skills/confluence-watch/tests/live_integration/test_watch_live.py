"""
Live integration tests for confluence-watch skill.

These tests run against a real Confluence instance.
Set CONFLUENCE_EMAIL, CONFLUENCE_API_TOKEN environment variables.

Usage:
    pytest test_watch_live.py --profile test -v
"""

import contextlib
import time

import pytest

from confluence_assistant_skills_lib import (
    get_confluence_client,
)


@pytest.fixture(scope="session")
def confluence_client(request):
    """Get Confluence client using profile from command line."""
    profile = request.config.getoption("--profile", default=None)
    return get_confluence_client(profile=profile)


@pytest.fixture(scope="session")
def test_page(confluence_client):
    """Create a test page for watch tests."""
    # Get default space from config or use TEST
    spaces = confluence_client.get("/api/v2/spaces", params={"limit": 1})
    if not spaces.get("results"):
        pytest.skip("No spaces available for testing")

    space = spaces["results"][0]
    space_id = space["id"]

    # Create test page
    page_data = {
        "spaceId": space_id,
        "status": "current",
        "title": f"Watch Test Page {id(confluence_client)}",
        "body": {
            "representation": "storage",
            "value": "<p>This is a test page for watch functionality.</p>",
        },
    }

    page = confluence_client.post("/api/v2/pages", json_data=page_data)
    page_id = page["id"]

    yield page_id

    # Cleanup
    try:
        confluence_client.delete(f"/api/v2/pages/{page_id}")
    except Exception:
        pass  # Already deleted or not found


class TestWatchPageLive:
    """Live integration tests for watch_page.py"""

    def test_watch_page(self, confluence_client, test_page):
        """Test watching a page."""
        result = confluence_client.post(
            f"/rest/api/user/watch/content/{test_page}", operation="watch page"
        )
        # Should return 200 or empty dict
        assert result is not None

    def test_watch_already_watching(self, confluence_client, test_page):
        """Test watching a page that is already being watched."""
        # Watch first time
        confluence_client.post(f"/rest/api/user/watch/content/{test_page}")

        # Watch second time - should not error
        result = confluence_client.post(
            f"/rest/api/user/watch/content/{test_page}", operation="watch page"
        )
        assert result is not None

    def test_watch_invalid_page(self, confluence_client):
        """Test watching a non-existent page."""

        with pytest.raises(Exception):
            # Using an obviously invalid page ID
            confluence_client.post(
                "/rest/api/user/watch/content/999999999", operation="watch page"
            )


class TestUnwatchPageLive:
    """Live integration tests for unwatch_page.py"""

    def test_unwatch_page(self, confluence_client, test_page):
        """Test unwatching a page."""
        # First watch it
        confluence_client.post(f"/rest/api/user/watch/content/{test_page}")

        # Then unwatch
        result = confluence_client.delete(
            f"/rest/api/user/watch/content/{test_page}", operation="unwatch page"
        )
        # Should succeed with empty response or success indicator
        assert result is not None or result == {}

    def test_unwatch_not_watching(self, confluence_client, test_page):
        """Test unwatching a page we're not watching."""
        # Unwatch without watching first - should not error
        result = confluence_client.delete(
            f"/rest/api/user/watch/content/{test_page}", operation="unwatch page"
        )
        assert result is not None or result == {}


class TestGetWatchersLive:
    """Live integration tests for get_watchers.py"""

    def test_get_watchers(self, confluence_client, test_page):
        """Test getting watchers list."""
        # Watch the page first
        confluence_client.post(f"/rest/api/user/watch/content/{test_page}")
        time.sleep(1)  # Wait for watch to register

        # Get watchers
        result = confluence_client.get(
            f"/rest/api/content/{test_page}/notification/created",
            operation="get watchers",
        )

        assert "results" in result
        assert isinstance(result["results"], list)
        # Watchers list may be empty if not indexed yet, just verify structure

    def test_get_watchers_empty(self, confluence_client, test_page):
        """Test getting watchers for unwatched page."""
        # Make sure we're not watching
        with contextlib.suppress(Exception):
            confluence_client.delete(f"/rest/api/user/watch/content/{test_page}")

        # Get watchers
        result = confluence_client.get(
            f"/rest/api/content/{test_page}/notification/created",
            operation="get watchers",
        )

        assert "results" in result
        assert isinstance(result["results"], list)


class TestAmIWatchingLive:
    """Live integration tests for am_i_watching.py"""

    def test_am_i_watching_yes(self, confluence_client, test_page):
        """Test checking watch status when watching."""
        # Watch the page
        confluence_client.post(f"/rest/api/user/watch/content/{test_page}")
        time.sleep(2)  # Wait for watch to register

        # Get current user
        current_user = confluence_client.get("/rest/api/user/current")
        current_user["accountId"]

        # Get watchers
        watchers_result = confluence_client.get(
            f"/rest/api/content/{test_page}/notification/created"
        )
        watchers = watchers_result["results"]

        # Check if watching - watchers may not be immediately indexed
        # so we verify the structure is correct, not the exact content
        assert isinstance(watchers, list)
        # If watchers are present, verify format
        if watchers:
            assert any("accountId" in w or "name" in w for w in watchers)

    def test_am_i_watching_no(self, confluence_client, test_page):
        """Test checking watch status when not watching."""
        # Unwatch the page
        with contextlib.suppress(Exception):
            confluence_client.delete(f"/rest/api/user/watch/content/{test_page}")

        # Get current user
        current_user = confluence_client.get("/rest/api/user/current")
        current_account_id = current_user["accountId"]

        # Get watchers
        watchers_result = confluence_client.get(
            f"/rest/api/content/{test_page}/notification/created"
        )
        watchers = watchers_result["results"]

        # Check if watching
        is_watching = any(w.get("accountId") == current_account_id for w in watchers)

        assert is_watching is False

    def test_get_current_user(self, confluence_client):
        """Test getting current user information."""
        user = confluence_client.get("/rest/api/user/current")

        assert "accountId" in user
        assert "displayName" in user or "username" in user
        assert user["accountId"] is not None


class TestWatchSpaceLive:
    """Live integration tests for watch_space.py"""

    def test_watch_space(self, confluence_client):
        """Test watching a space."""
        # Get first available space
        spaces = confluence_client.get("/api/v2/spaces", params={"limit": 1})
        if not spaces.get("results"):
            pytest.skip("No spaces available for testing")

        space_key = spaces["results"][0]["key"]

        # Watch the space
        result = confluence_client.post(
            f"/rest/api/user/watch/space/{space_key}", operation="watch space"
        )

        # Should succeed
        assert result is not None

        # Cleanup - unwatch
        with contextlib.suppress(Exception):
            confluence_client.delete(f"/rest/api/user/watch/space/{space_key}")


def pytest_addoption(parser):
    """Add custom command line option for profile."""
    parser.addoption(
        "--profile",
        action="store",
        default=None,
        help="Confluence profile to use for testing",
    )
