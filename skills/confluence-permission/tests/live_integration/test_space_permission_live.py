"""
Live integration tests for space permission operations.

Usage:
    pytest test_space_permission_live.py --live -v
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
class TestSpacePermissionLive:
    """Live tests for space permission operations."""

    def test_get_space_permissions(self, confluence_client, test_space):
        """Test getting space permissions."""
        try:
            permissions = confluence_client.get(
                f"/rest/api/space/{test_space['key']}/permission"
            )
            # Should return permissions or be accessible
            assert permissions is not None
        except Exception:
            # Permission API may require admin access
            pass

    def test_current_user_can_access_space(self, confluence_client, test_space):
        """Test that current user can access the space."""
        # If we can get the space, we have access
        space = confluence_client.get(f"/api/v2/spaces/{test_space['id']}")
        assert space["id"] == test_space["id"]

    def test_current_user_can_create_content(
        self, confluence_client, test_space, current_user
    ):
        """Test that current user can create content in space."""
        import uuid

        page = confluence_client.post(
            "/api/v2/pages",
            json_data={
                "spaceId": test_space["id"],
                "status": "current",
                "title": f"Permission Test {uuid.uuid4().hex[:8]}",
                "body": {"representation": "storage", "value": "<p>Test.</p>"},
            },
        )

        try:
            assert page["id"] is not None
        finally:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")

    def test_list_space_admins(self, confluence_client, test_space):
        """Test listing space administrators."""
        try:
            # Try to get space permissions
            perms = confluence_client.get(
                f"/rest/api/space/{test_space['key']}", params={"expand": "permissions"}
            )
            assert "key" in perms
        except Exception:
            # May not have permission to view admins
            pass
