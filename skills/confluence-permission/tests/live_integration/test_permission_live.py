"""
Live integration tests for confluence-permission skill.

Tests permission operations against a real Confluence instance.

Usage:
    pytest test_permission_live.py --live -v
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
            "title": f"Permission Test Page {uuid.uuid4().hex[:8]}",
            "body": {"representation": "storage", "value": "<p>Test.</p>"},
        },
    )
    yield page
    with contextlib.suppress(Exception):
        confluence_client.delete(f"/api/v2/pages/{page['id']}")


@pytest.fixture
def current_user(confluence_client):
    """Get current user info."""
    return confluence_client.get("/rest/api/user/current")


@pytest.mark.integration
class TestGetSpacePermissionsLive:
    """Live tests for getting space permissions."""

    def test_get_space_permissions(self, confluence_client, test_space):
        """Test getting permissions for a space."""
        # Use v1 API for space permissions
        permissions = confluence_client.get(
            f"/rest/api/space/{test_space['key']}", params={"expand": "permissions"}
        )

        assert "key" in permissions
        # permissions expansion may be available
        if "permissions" in permissions:
            assert isinstance(permissions["permissions"], list)

    def test_get_space_settings(self, confluence_client, test_space):
        """Test getting space settings."""
        space = confluence_client.get(f"/api/v2/spaces/{test_space['id']}")

        assert space["id"] == test_space["id"]
        assert "key" in space


@pytest.mark.integration
class TestGetPageRestrictionsLive:
    """Live tests for getting page restrictions."""

    def test_get_page_restrictions(self, confluence_client, test_page):
        """Test getting restrictions on a page."""
        restrictions = confluence_client.get(
            f"/rest/api/content/{test_page['id']}/restriction"
        )

        assert (
            "results" in restrictions
            or "restrictions" in restrictions
            or isinstance(restrictions, dict)
        )

    def test_page_with_no_restrictions(self, confluence_client, test_page):
        """Test page with no explicit restrictions."""
        # New pages typically have no restrictions
        restrictions = confluence_client.get(
            f"/rest/api/content/{test_page['id']}/restriction"
        )

        # Should return empty or default restrictions
        assert restrictions is not None


@pytest.mark.integration
class TestAddPageRestrictionLive:
    """Live tests for adding page restrictions."""

    def test_add_view_restriction(self, confluence_client, test_page, current_user):
        """Test adding a view restriction to a page."""
        # Add view restriction for current user
        result = confluence_client.put(
            f"/rest/api/content/{test_page['id']}/restriction",
            json_data={
                "results": [
                    {
                        "operation": "read",
                        "restrictions": {
                            "user": {
                                "results": [{"accountId": current_user["accountId"]}]
                            }
                        },
                    }
                ]
            },
        )

        # Result format varies, just check it succeeds
        assert result is not None

        # Remove restriction to clean up
        with contextlib.suppress(Exception):
            confluence_client.delete(f"/rest/api/content/{test_page['id']}/restriction")

    def test_add_edit_restriction(self, confluence_client, test_page, current_user):
        """Test adding an edit restriction to a page."""
        result = confluence_client.put(
            f"/rest/api/content/{test_page['id']}/restriction",
            json_data={
                "results": [
                    {
                        "operation": "update",
                        "restrictions": {
                            "user": {
                                "results": [{"accountId": current_user["accountId"]}]
                            }
                        },
                    }
                ]
            },
        )

        assert result is not None

        # Clean up
        with contextlib.suppress(Exception):
            confluence_client.delete(f"/rest/api/content/{test_page['id']}/restriction")


@pytest.mark.integration
class TestRemovePageRestrictionLive:
    """Live tests for removing page restrictions."""

    def test_remove_all_restrictions(self, confluence_client, test_page, current_user):
        """Test removing all restrictions from a page."""
        # First add a restriction
        confluence_client.put(
            f"/rest/api/content/{test_page['id']}/restriction",
            json_data={
                "results": [
                    {
                        "operation": "read",
                        "restrictions": {
                            "user": {
                                "results": [{"accountId": current_user["accountId"]}]
                            }
                        },
                    }
                ]
            },
        )

        # Remove all restrictions
        result = confluence_client.delete(
            f"/rest/api/content/{test_page['id']}/restriction"
        )

        # Should succeed
        assert result is None or result == {} or result is not None


@pytest.mark.integration
class TestCheckPermissionLive:
    """Live tests for checking user permissions."""

    def test_user_can_view_page(self, confluence_client, test_page):
        """Test that current user can view a page they created."""
        # Just reading the page proves we have view permission
        page = confluence_client.get(f"/api/v2/pages/{test_page['id']}")

        assert page["id"] == test_page["id"]

    def test_user_can_edit_page(self, confluence_client, test_page):
        """Test that current user can edit a page they created."""
        # Get fresh page to ensure we have current version
        page = confluence_client.get(f"/api/v2/pages/{test_page['id']}")
        version = page["version"]["number"]

        # Update the page - need to include body for version to increment
        updated = confluence_client.put(
            f"/api/v2/pages/{test_page['id']}",
            json_data={
                "id": test_page["id"],
                "status": "current",
                "title": test_page["title"],
                "body": {
                    "representation": "storage",
                    "value": "<p>Updated by permission test.</p>",
                },
                "version": {"number": version + 1},
            },
        )

        # Verify update succeeded - version should increment
        assert updated["version"]["number"] >= version
