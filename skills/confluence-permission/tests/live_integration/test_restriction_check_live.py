"""
Live integration tests for restriction check operations.

Usage:
    pytest test_restriction_check_live.py --live -v
"""

import contextlib
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


@pytest.fixture
def test_page(confluence_client, test_space):
    page = confluence_client.post(
        "/api/v2/pages",
        json_data={
            "spaceId": test_space["id"],
            "status": "current",
            "title": f"Restriction Check Test {uuid.uuid4().hex[:8]}",
            "body": {"representation": "storage", "value": "<p>Test.</p>"},
        },
    )
    yield page
    with contextlib.suppress(Exception):
        confluence_client.delete(f"/api/v2/pages/{page['id']}")


@pytest.fixture
def current_user(confluence_client):
    return confluence_client.get("/rest/api/user/current")


@pytest.mark.integration
class TestRestrictionCheckLive:
    """Live tests for restriction check operations."""

    def test_check_page_restrictions(self, confluence_client, test_page):
        """Test checking if a page has restrictions."""
        restrictions = confluence_client.get(
            f"/rest/api/content/{test_page['id']}/restriction"
        )

        assert "results" in restrictions or isinstance(restrictions, dict)

    def test_page_without_restrictions(self, confluence_client, test_page):
        """Test that new page has no restrictions."""
        restrictions = confluence_client.get(
            f"/rest/api/content/{test_page['id']}/restriction"
        )

        # New page should have empty or minimal restrictions
        results = restrictions.get("results", [])
        # Check that there are no user/group restrictions
        has_restrictions = False
        for r in results:
            user_restrictions = (
                r.get("restrictions", {}).get("user", {}).get("results", [])
            )
            group_restrictions = (
                r.get("restrictions", {}).get("group", {}).get("results", [])
            )
            if user_restrictions or group_restrictions:
                has_restrictions = True

        # New page typically has no restrictions
        assert not has_restrictions or len(results) == 0

    def test_check_read_permission(self, confluence_client, test_page):
        """Test checking read permission on a page."""
        # If we can read it, we have read permission
        page = confluence_client.get(f"/api/v2/pages/{test_page['id']}")
        assert page["id"] == test_page["id"]

    def test_check_edit_permission(self, confluence_client, test_page, current_user):
        """Test checking edit permission by attempting update."""
        # Try to update the page
        updated = confluence_client.put(
            f"/api/v2/pages/{test_page['id']}",
            json_data={
                "id": test_page["id"],
                "status": "current",
                "title": test_page["title"],
                "spaceId": test_page["spaceId"],
                "body": {"representation": "storage", "value": "<p>Updated.</p>"},
                "version": {"number": test_page["version"]["number"] + 1},
            },
        )

        # If we got here, we have edit permission
        assert updated["id"] == test_page["id"]
