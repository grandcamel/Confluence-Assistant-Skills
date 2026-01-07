"""
Live integration tests for confluence-page skill.

Tests page CRUD operations against a real Confluence instance.

Usage:
    pytest test_page_live.py --profile development -v
"""

import contextlib
import uuid

import pytest

from confluence_assistant_skills_lib import (
    get_confluence_client,
)


def pytest_addoption(parser):
    """Add custom command line option for profile."""
    try:
        parser.addoption(
            "--profile",
            action="store",
            default=None,
            help="Confluence profile to use for testing",
        )
    except ValueError:
        pass  # Option already added


@pytest.fixture(scope="session")
def confluence_client(request):
    """Get Confluence client using profile from command line."""
    profile = request.config.getoption("--profile", default=None)
    return get_confluence_client(profile=profile)


@pytest.fixture(scope="session")
def test_space(confluence_client):
    """Get first available space for testing."""
    spaces = confluence_client.get("/api/v2/spaces", params={"limit": 1})
    if not spaces.get("results"):
        pytest.skip("No spaces available for testing")
    return spaces["results"][0]


@pytest.fixture
def test_page(confluence_client, test_space):
    """Create a test page for each test."""
    page_data = {
        "spaceId": test_space["id"],
        "status": "current",
        "title": f"Test Page {uuid.uuid4().hex[:8]}",
        "body": {"representation": "storage", "value": "<p>Test page content.</p>"},
    }
    page = confluence_client.post("/api/v2/pages", json_data=page_data)

    yield page

    with contextlib.suppress(Exception):
        confluence_client.delete(f"/api/v2/pages/{page['id']}")


@pytest.mark.integration
class TestCreatePageLive:
    """Live tests for page creation."""

    def test_create_page_basic(self, confluence_client, test_space):
        """Test creating a basic page."""
        title = f"Live Test Page {uuid.uuid4().hex[:8]}"

        page = confluence_client.post(
            "/api/v2/pages",
            json_data={
                "spaceId": test_space["id"],
                "status": "current",
                "title": title,
                "body": {
                    "representation": "storage",
                    "value": "<p>Created by live test.</p>",
                },
            },
        )

        try:
            assert page["id"] is not None
            assert page["title"] == title
            assert page["spaceId"] == test_space["id"]
        finally:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")

    def test_create_page_with_parent(self, confluence_client, test_space, test_page):
        """Test creating a child page."""
        child_title = f"Child Page {uuid.uuid4().hex[:8]}"

        child = confluence_client.post(
            "/api/v2/pages",
            json_data={
                "spaceId": test_space["id"],
                "parentId": test_page["id"],
                "status": "current",
                "title": child_title,
                "body": {
                    "representation": "storage",
                    "value": "<p>Child page content.</p>",
                },
            },
        )

        try:
            assert child["parentId"] == test_page["id"]
        finally:
            confluence_client.delete(f"/api/v2/pages/{child['id']}")


@pytest.mark.integration
class TestGetPageLive:
    """Live tests for page retrieval."""

    def test_get_page_by_id(self, confluence_client, test_page):
        """Test getting a page by ID."""
        page = confluence_client.get(f"/api/v2/pages/{test_page['id']}")

        assert page["id"] == test_page["id"]
        assert page["title"] == test_page["title"]

    def test_get_page_with_body(self, confluence_client, test_page):
        """Test getting a page with body content."""
        page = confluence_client.get(
            f"/api/v2/pages/{test_page['id']}", params={"body-format": "storage"}
        )

        assert "body" in page
        assert "storage" in page["body"]

    def test_get_nonexistent_page(self, confluence_client):
        """Test getting a non-existent page."""
        from confluence_assistant_skills_lib import NotFoundError

        with pytest.raises(NotFoundError):
            confluence_client.get("/api/v2/pages/999999999999")


@pytest.mark.integration
class TestUpdatePageLive:
    """Live tests for page updates."""

    def test_update_page_title(self, confluence_client, test_page):
        """Test updating a page title."""
        new_title = f"Updated Title {uuid.uuid4().hex[:8]}"
        version = test_page["version"]["number"]

        updated = confluence_client.put(
            f"/api/v2/pages/{test_page['id']}",
            json_data={
                "id": test_page["id"],
                "status": "current",
                "title": new_title,
                "version": {"number": version + 1},
            },
        )

        assert updated["title"] == new_title
        assert updated["version"]["number"] == version + 1

    def test_update_page_content(self, confluence_client, test_page):
        """Test updating page content."""
        new_content = "<p>Updated content from live test.</p>"
        version = test_page["version"]["number"]

        updated = confluence_client.put(
            f"/api/v2/pages/{test_page['id']}",
            json_data={
                "id": test_page["id"],
                "status": "current",
                "title": test_page["title"],
                "version": {"number": version + 1},
                "body": {"representation": "storage", "value": new_content},
            },
        )

        assert updated["version"]["number"] == version + 1


@pytest.mark.integration
class TestDeletePageLive:
    """Live tests for page deletion."""

    def test_delete_page(self, confluence_client, test_space):
        """Test deleting a page."""
        # Create page to delete
        page = confluence_client.post(
            "/api/v2/pages",
            json_data={
                "spaceId": test_space["id"],
                "status": "current",
                "title": f"Delete Me {uuid.uuid4().hex[:8]}",
                "body": {"representation": "storage", "value": "<p>Delete me</p>"},
            },
        )

        page_id = page["id"]

        # Delete it
        confluence_client.delete(f"/api/v2/pages/{page_id}")

        # Verify deleted or trashed
        from confluence_assistant_skills_lib import NotFoundError

        try:
            result = confluence_client.get(f"/api/v2/pages/{page_id}")
            assert result.get("status") == "trashed"
        except NotFoundError:
            pass  # Also acceptable


@pytest.mark.integration
class TestListPagesLive:
    """Live tests for listing pages."""

    def test_list_pages_in_space(self, confluence_client, test_space, test_page):
        """Test listing pages in a space."""
        pages = confluence_client.get(
            "/api/v2/pages", params={"space-id": test_space["id"], "limit": 25}
        )

        assert "results" in pages
        assert len(pages["results"]) >= 1

    def test_list_pages_with_pagination(self, confluence_client, test_space):
        """Test listing pages with pagination."""
        pages = confluence_client.get(
            "/api/v2/pages", params={"space-id": test_space["id"], "limit": 5}
        )

        assert "results" in pages
        # _links may contain 'next' for pagination
        assert "_links" in pages
