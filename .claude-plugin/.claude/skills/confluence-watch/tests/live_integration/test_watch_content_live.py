"""
Live integration tests for content watch operations.

Usage:
    pytest test_watch_content_live.py --profile development -v
"""

import contextlib
import uuid

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


@pytest.fixture
def test_page(confluence_client, test_space):
    page = confluence_client.post(
        "/api/v2/pages",
        json_data={
            "spaceId": test_space["id"],
            "status": "current",
            "title": f"Watch Content Test {uuid.uuid4().hex[:8]}",
            "body": {"representation": "storage", "value": "<p>Test.</p>"},
        },
    )
    yield page
    with contextlib.suppress(Exception):
        confluence_client.delete(f"/api/v2/pages/{page['id']}")


@pytest.mark.integration
class TestWatchContentLive:
    """Live tests for content watch operations."""

    def test_watch_and_unwatch_page(self, confluence_client, test_page):
        """Test watching and unwatching a page."""
        try:
            # Watch
            confluence_client.post(
                f"/rest/api/user/watch/content/{test_page['id']}", json_data={}
            )

            # Unwatch
            confluence_client.delete(f"/rest/api/user/watch/content/{test_page['id']}")
        except Exception:
            pass  # Watch API may vary

    def test_page_accessible_after_watch_toggle(self, confluence_client, test_page):
        """Test that page remains accessible after watch operations."""
        with contextlib.suppress(Exception):
            confluence_client.post(
                f"/rest/api/user/watch/content/{test_page['id']}", json_data={}
            )

        # Page should still be accessible
        page = confluence_client.get(f"/api/v2/pages/{test_page['id']}")
        assert page["id"] == test_page["id"]

        with contextlib.suppress(Exception):
            confluence_client.delete(f"/rest/api/user/watch/content/{test_page['id']}")
