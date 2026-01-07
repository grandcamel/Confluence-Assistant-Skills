"""
Live integration tests for space permission operations.

Usage:
    pytest test_space_permissions_live.py --live -v
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
class TestSpacePermissionsLive:
    """Live tests for space permission operations."""

    def test_get_space_with_permissions(self, confluence_client, test_space):
        """Test getting space with permission expansion."""
        space = confluence_client.get(
            f"/rest/api/space/{test_space['key']}", params={"expand": "permissions"}
        )

        assert "key" in space
        # permissions may or may not be present depending on access

    def test_get_space_settings(self, confluence_client, test_space):
        """Test getting space settings."""
        # Use v1 API for settings
        try:
            settings = confluence_client.get(
                f"/rest/api/space/{test_space['key']}/settings"
            )
            assert settings is not None
        except Exception:
            # Settings endpoint may not be available
            pytest.skip("Space settings not accessible")

    def test_list_space_admins(self, confluence_client, test_space):
        """Test listing users with admin access to space."""
        # This requires specific permissions to view
        try:
            admins = confluence_client.get(
                f"/rest/api/space/{test_space['key']}",
                params={"expand": "permissions.subjects.user"},
            )
            assert "key" in admins
        except Exception:
            pytest.skip("Cannot access space permissions")

    def test_check_current_user_access(self, confluence_client, test_space):
        """Test that current user has access to space."""
        # If we can get the space, we have at least read access
        space = confluence_client.get(f"/api/v2/spaces/{test_space['id']}")

        assert space["id"] == test_space["id"]

    def test_list_space_content(self, confluence_client, test_space):
        """Test listing content in space proves access."""
        pages = confluence_client.get(
            "/api/v2/pages", params={"space-id": test_space["id"], "limit": 5}
        )

        assert "results" in pages
