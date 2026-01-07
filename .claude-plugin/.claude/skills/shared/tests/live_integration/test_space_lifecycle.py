"""
Live Integration Tests - Space Lifecycle

Tests for space CRUD operations against a real Confluence instance.

Usage:
    pytest test_space_lifecycle.py --profile development -v
"""

import contextlib
import time
import uuid

import pytest


def delete_space_v1(client, space_key: str) -> None:
    """Delete a space using v1 API (v2 doesn't support space deletion)."""
    response = client.session.delete(
        f"{client.base_url}/wiki/rest/api/space/{space_key}"
    )
    if response.status_code not in (202, 204, 404):
        raise Exception(
            f"Failed to delete space: {response.status_code} - {response.text}"
        )


@pytest.mark.integration
@pytest.mark.confluence
@pytest.mark.spaces
class TestSpaceCreate:
    """Tests for space creation."""

    def test_create_basic_space(self, confluence_client):
        """Test creating a basic space."""
        space_key = f"TST{uuid.uuid4().hex[:6].upper()}"
        space_name = f"Test Space {space_key}"

        space = confluence_client.post(
            "/api/v2/spaces",
            json_data={"key": space_key, "name": space_name},
            operation="create basic space",
        )

        try:
            assert space["key"] == space_key
            assert space["name"] == space_name
            assert "id" in space
        finally:
            # Use v1 API for space deletion (v2 doesn't support it)
            delete_space_v1(confluence_client, space_key)

    @pytest.mark.skip(
        reason="Description format may cause 500 errors in some Confluence configurations"
    )
    def test_create_space_with_description(self, confluence_client):
        """Test creating a space with description."""
        space_key = f"TST{uuid.uuid4().hex[:6].upper()}"
        description = "A test space with description"

        space = confluence_client.post(
            "/api/v2/spaces",
            json_data={
                "key": space_key,
                "name": f"Test Space {space_key}",
                "description": {
                    "plain": {"value": description, "representation": "plain"}
                },
            },
            operation="create space with description",
        )

        try:
            assert space["key"] == space_key
            # Check description if returned
            if "description" in space:
                desc = space["description"]
                if isinstance(desc, dict) and "plain" in desc:
                    assert desc["plain"]["value"] == description
        finally:
            # Use v1 API for space deletion (v2 doesn't support it)
            delete_space_v1(confluence_client, space_key)

    def test_create_duplicate_space_fails(self, confluence_client, test_space):
        """Test that creating a space with duplicate key fails."""
        from confluence_assistant_skills_lib import ConfluenceError

        with pytest.raises(ConfluenceError):
            confluence_client.post(
                "/api/v2/spaces",
                json_data={"key": test_space["key"], "name": "Duplicate Space"},
                operation="create duplicate space",
            )


@pytest.mark.integration
@pytest.mark.confluence
@pytest.mark.spaces
class TestSpaceRead:
    """Tests for reading spaces."""

    def test_get_space_by_key(self, confluence_client, test_space):
        """Test retrieving a space by key."""
        spaces = list(
            confluence_client.paginate(
                "/api/v2/spaces",
                params={"keys": test_space["key"]},
                operation="get space by key",
            )
        )

        assert len(spaces) == 1
        assert spaces[0]["key"] == test_space["key"]
        assert spaces[0]["id"] == test_space["id"]

    def test_list_spaces(self, confluence_client):
        """Test listing all spaces."""
        spaces = list(
            confluence_client.paginate(
                "/api/v2/spaces",
                params={"limit": 10},
                limit=10,
                operation="list spaces",
            )
        )

        assert len(spaces) >= 1
        for space in spaces:
            assert "id" in space
            assert "key" in space
            assert "name" in space

    def test_list_spaces_with_type_filter(self, confluence_client):
        """Test listing spaces filtered by type."""
        spaces = list(
            confluence_client.paginate(
                "/api/v2/spaces",
                params={"type": "global", "limit": 10},
                limit=10,
                operation="list global spaces",
            )
        )

        for space in spaces:
            assert space.get("type") == "global"

    def test_get_nonexistent_space(self, confluence_client):
        """Test that non-existent space returns empty results."""
        spaces = list(
            confluence_client.paginate(
                "/api/v2/spaces",
                params={"keys": "NONEXISTENT999"},
                operation="get nonexistent space",
            )
        )

        assert len(spaces) == 0


@pytest.mark.integration
@pytest.mark.confluence
@pytest.mark.spaces
class TestSpaceUpdate:
    """Tests for updating spaces.

    Note: The v2 API doesn't support PUT for spaces. Use v1 API for updates.
    """

    @pytest.mark.skip(reason="v2 API doesn't support PUT for spaces - use v1 API")
    def test_update_space_name(self, confluence_client, test_space):
        """Test updating a space name."""
        new_name = f"Updated Space Name {uuid.uuid4().hex[:8]}"

        updated = confluence_client.put(
            f"/api/v2/spaces/{test_space['id']}",
            json_data={"name": new_name},
            operation="update space name",
        )

        assert updated["name"] == new_name

    @pytest.mark.skip(reason="v2 API doesn't support PUT for spaces - use v1 API")
    def test_update_space_description(self, confluence_client, test_space):
        """Test updating a space description."""
        new_description = f"Updated description {uuid.uuid4().hex[:8]}"

        updated = confluence_client.put(
            f"/api/v2/spaces/{test_space['id']}",
            json_data={
                "description": {
                    "plain": {"value": new_description, "representation": "plain"}
                }
            },
            operation="update space description",
        )

        # Verify update
        if "description" in updated:
            desc = updated["description"]
            if isinstance(desc, dict) and "plain" in desc:
                assert desc["plain"]["value"] == new_description


@pytest.mark.integration
@pytest.mark.confluence
@pytest.mark.spaces
class TestSpaceContent:
    """Tests for space content operations."""

    def test_get_space_pages(self, confluence_client, test_space, test_page):
        """Test listing pages in a space."""
        pages = list(
            confluence_client.paginate(
                "/api/v2/pages",
                params={"space-id": test_space["id"]},
                operation="get space pages",
            )
        )

        assert len(pages) >= 1
        page_ids = [p["id"] for p in pages]
        assert test_page["id"] in page_ids

    def test_get_space_blogposts(self, confluence_client, test_space, test_blogpost):
        """Test listing blog posts in a space."""
        blogposts = list(
            confluence_client.paginate(
                "/api/v2/blogposts",
                params={"space-id": test_space["id"]},
                operation="get space blogposts",
            )
        )

        assert len(blogposts) >= 1
        post_ids = [p["id"] for p in blogposts]
        assert test_blogpost["id"] in post_ids

    def test_get_root_pages(self, confluence_client, test_space, test_page):
        """Test getting root-level pages in a space."""
        pages = list(
            confluence_client.paginate(
                "/api/v2/pages",
                params={"space-id": test_space["id"], "depth": "root"},
                operation="get root pages",
            )
        )

        # test_page should be at root level (no parent specified in fixture)
        page_ids = [p["id"] for p in pages]
        assert test_page["id"] in page_ids


@pytest.mark.integration
@pytest.mark.confluence
@pytest.mark.spaces
class TestSpaceDelete:
    """Tests for deleting spaces.

    Note: Space deletion is an async operation via v1 API.
    These tests are timing-dependent and may fail in some configurations.
    """

    @pytest.mark.skip(reason="Async space deletion timing is unpredictable")
    def test_delete_empty_space(self, confluence_client):
        """Test deleting an empty space."""
        # Create a space to delete
        space_key = f"DEL{uuid.uuid4().hex[:6].upper()}"

        confluence_client.post(
            "/api/v2/spaces",
            json_data={"key": space_key, "name": f"Space to Delete {space_key}"},
            operation="create space for deletion",
        )

        # Delete it using v1 API (v2 doesn't support space deletion)
        delete_space_v1(confluence_client, space_key)

        # Wait for async deletion to complete (space deletion is a long-running task)
        time.sleep(5)

        # Verify it's gone (may still be in trash, check for empty or deleted status)
        spaces = list(
            confluence_client.paginate(
                "/api/v2/spaces",
                params={"keys": space_key},
                operation="verify space deleted",
            )
        )
        # Space may still exist in trash state briefly
        if spaces:
            assert spaces[0].get("status") in ("deleted", None) or len(spaces) == 0

    @pytest.mark.skip(reason="Async space deletion timing is unpredictable")
    def test_delete_space_with_content(self, confluence_client):
        """Test deleting a space that contains pages."""
        # Create space
        space_key = f"DEL{uuid.uuid4().hex[:6].upper()}"

        space = confluence_client.post(
            "/api/v2/spaces",
            json_data={"key": space_key, "name": f"Space with Content {space_key}"},
            operation="create space with content",
        )

        # Create a page in it
        page = confluence_client.post(
            "/api/v2/pages",
            json_data={
                "spaceId": space["id"],
                "status": "current",
                "title": f"Page in {space_key}",
                "body": {"representation": "storage", "value": "<p>Content</p>"},
            },
            operation="create page in space",
        )

        try:
            # Delete page first
            confluence_client.delete(f"/api/v2/pages/{page['id']}")
            # Then delete space using v1 API
            delete_space_v1(confluence_client, space_key)
        except Exception:
            # Cleanup on failure
            with contextlib.suppress(Exception):
                confluence_client.delete(f"/api/v2/pages/{page['id']}")
            with contextlib.suppress(Exception):
                delete_space_v1(confluence_client, space_key)
            raise

        # Wait for async deletion to complete (space deletion is a long-running task)
        time.sleep(5)

        # Verify deletion (may still be in trash briefly)
        spaces = list(
            confluence_client.paginate(
                "/api/v2/spaces",
                params={"keys": space_key},
                operation="verify space with content deleted",
            )
        )
        # Space may still exist in trash state briefly
        if spaces:
            assert spaces[0].get("status") in ("deleted", None) or len(spaces) == 0
