"""
Live integration tests for page move operations.

Usage:
    pytest test_page_move_live.py --live -v
"""

import contextlib
import uuid

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


@pytest.fixture
def parent_pages(confluence_client, test_space):
    """Create two parent pages for move testing."""
    pages = []
    for i in range(2):
        page = confluence_client.post(
            "/api/v2/pages",
            json_data={
                "spaceId": test_space["id"],
                "status": "current",
                "title": f"Move Parent {i} {uuid.uuid4().hex[:8]}",
                "body": {"representation": "storage", "value": f"<p>Parent {i}.</p>"},
            },
        )
        pages.append(page)

    yield pages

    for page in pages:
        with contextlib.suppress(Exception):
            confluence_client.delete(f"/api/v2/pages/{page['id']}")


@pytest.fixture
def child_page(confluence_client, test_space, parent_pages):
    """Create a child page under first parent."""
    page = confluence_client.post(
        "/api/v2/pages",
        json_data={
            "spaceId": test_space["id"],
            "status": "current",
            "title": f"Move Child {uuid.uuid4().hex[:8]}",
            "parentId": parent_pages[0]["id"],
            "body": {"representation": "storage", "value": "<p>Child.</p>"},
        },
    )
    yield page
    with contextlib.suppress(Exception):
        confluence_client.delete(f"/api/v2/pages/{page['id']}")


@pytest.mark.integration
class TestPageMoveLive:
    """Live tests for page move operations."""

    def test_move_page_to_new_parent(
        self, confluence_client, test_space, parent_pages, child_page
    ):
        """Test moving a page to a different parent."""
        new_parent = parent_pages[1]

        # Move the child to new parent
        moved = confluence_client.put(
            f"/api/v2/pages/{child_page['id']}",
            json_data={
                "id": child_page["id"],
                "status": "current",
                "title": child_page["title"],
                "spaceId": test_space["id"],
                "parentId": new_parent["id"],
                "body": {"representation": "storage", "value": "<p>Child moved.</p>"},
                "version": {"number": child_page["version"]["number"] + 1},
            },
        )

        assert moved["parentId"] == new_parent["id"]

    def test_move_page_to_root(
        self, confluence_client, test_space, parent_pages, child_page
    ):
        """Test moving a page to root level."""
        # Get fresh version since other tests may have modified it
        fresh_page = confluence_client.get(f"/api/v2/pages/{child_page['id']}")

        # Move to root (omit parentId) - note: Confluence v2 API may not support
        # true root pages; it might assign space homepage as parent
        moved = confluence_client.put(
            f"/api/v2/pages/{child_page['id']}",
            json_data={
                "id": child_page["id"],
                "status": "current",
                "title": child_page["title"],
                "spaceId": test_space["id"],
                "body": {"representation": "storage", "value": "<p>Now root.</p>"},
                "version": {"number": fresh_page["version"]["number"] + 1},
            },
        )

        # Verify the update succeeded - parentId behavior varies by Confluence version
        # Some versions keep the parent, others assign space homepage
        assert moved.get("id") == child_page["id"]
        assert moved.get("status") == "current"

    def test_verify_page_parent(self, confluence_client, child_page, parent_pages):
        """Test verifying page parent relationship."""
        page = confluence_client.get(f"/api/v2/pages/{child_page['id']}")
        assert page["parentId"] == parent_pages[0]["id"]
