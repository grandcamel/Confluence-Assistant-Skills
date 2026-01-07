"""
Live integration tests for ancestor operations.

Usage:
    pytest test_ancestor_live.py --profile development -v
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
def nested_pages(confluence_client, test_space):
    """Create a hierarchy of pages: grandparent -> parent -> child."""
    pages = []

    # Create grandparent
    grandparent = confluence_client.post(
        "/api/v2/pages",
        json_data={
            "spaceId": test_space["id"],
            "status": "current",
            "title": f"Grandparent {uuid.uuid4().hex[:8]}",
            "body": {"representation": "storage", "value": "<p>Grandparent.</p>"},
        },
    )
    pages.append(grandparent)

    # Create parent under grandparent
    parent = confluence_client.post(
        "/api/v2/pages",
        json_data={
            "spaceId": test_space["id"],
            "status": "current",
            "title": f"Parent {uuid.uuid4().hex[:8]}",
            "parentId": grandparent["id"],
            "body": {"representation": "storage", "value": "<p>Parent.</p>"},
        },
    )
    pages.append(parent)

    # Create child under parent
    child = confluence_client.post(
        "/api/v2/pages",
        json_data={
            "spaceId": test_space["id"],
            "status": "current",
            "title": f"Child {uuid.uuid4().hex[:8]}",
            "parentId": parent["id"],
            "body": {"representation": "storage", "value": "<p>Child.</p>"},
        },
    )
    pages.append(child)

    yield {"grandparent": grandparent, "parent": parent, "child": child}

    # Cleanup in reverse order
    for page in reversed(pages):
        with contextlib.suppress(Exception):
            confluence_client.delete(f"/api/v2/pages/{page['id']}")


@pytest.mark.integration
class TestAncestorLive:
    """Live tests for ancestor operations."""

    def test_get_page_ancestors(self, confluence_client, nested_pages):
        """Test getting ancestors of a page."""
        child = nested_pages["child"]

        # Get page with ancestors
        page = confluence_client.get(
            f"/rest/api/content/{child['id']}", params={"expand": "ancestors"}
        )

        ancestors = page.get("ancestors", [])
        assert len(ancestors) >= 2

        ancestor_ids = [a["id"] for a in ancestors]
        assert nested_pages["parent"]["id"] in ancestor_ids
        assert nested_pages["grandparent"]["id"] in ancestor_ids

    def test_get_immediate_parent(self, confluence_client, nested_pages):
        """Test getting immediate parent of a page."""
        child = nested_pages["child"]
        parent = nested_pages["parent"]

        page = confluence_client.get(f"/api/v2/pages/{child['id']}")

        assert page.get("parentId") == parent["id"]

    def test_top_level_page_parent(self, confluence_client, nested_pages):
        """Test that a top-level page's parent is either None or the space homepage."""
        grandparent = nested_pages["grandparent"]

        page = confluence_client.get(f"/api/v2/pages/{grandparent['id']}")

        # A page created without explicit parent may have:
        # - No parentId (None or absent)
        # - The space homepage as parent
        parent_id = page.get("parentId")
        # Verify we can retrieve the page - the parent might be space homepage
        assert page.get("id") == grandparent["id"]
        # If there's a parent, verify it exists
        if parent_id:
            parent_page = confluence_client.get(f"/api/v2/pages/{parent_id}")
            assert parent_page.get("id") == parent_id

    def test_ancestor_chain_order(self, confluence_client, nested_pages):
        """Test that ancestors are returned in correct order."""
        child = nested_pages["child"]

        page = confluence_client.get(
            f"/rest/api/content/{child['id']}", params={"expand": "ancestors"}
        )

        ancestors = page.get("ancestors", [])
        # Ancestors should be ordered from root to immediate parent
        # Last ancestor should be the immediate parent
        if ancestors:
            assert ancestors[-1]["id"] == nested_pages["parent"]["id"]
