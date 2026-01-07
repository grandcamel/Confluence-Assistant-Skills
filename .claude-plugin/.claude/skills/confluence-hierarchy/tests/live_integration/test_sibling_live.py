"""
Live integration tests for sibling page operations.

Usage:
    pytest test_sibling_live.py --profile development -v
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
def sibling_pages(confluence_client, test_space):
    """Create a parent with multiple sibling children."""
    pages = []

    parent = confluence_client.post(
        "/api/v2/pages",
        json_data={
            "spaceId": test_space["id"],
            "status": "current",
            "title": f"Sibling Parent {uuid.uuid4().hex[:8]}",
            "body": {"representation": "storage", "value": "<p>Parent.</p>"},
        },
    )
    pages.append(parent)

    siblings = []
    for i in range(3):
        child = confluence_client.post(
            "/api/v2/pages",
            json_data={
                "spaceId": test_space["id"],
                "status": "current",
                "title": f"Sibling {i} {uuid.uuid4().hex[:8]}",
                "parentId": parent["id"],
                "body": {"representation": "storage", "value": f"<p>Sibling {i}.</p>"},
            },
        )
        pages.append(child)
        siblings.append(child)

    yield {"parent": parent, "siblings": siblings}

    for page in reversed(pages):
        with contextlib.suppress(Exception):
            confluence_client.delete(f"/api/v2/pages/{page['id']}")


@pytest.mark.integration
class TestSiblingLive:
    """Live tests for sibling page operations."""

    def test_get_siblings_via_parent(self, confluence_client, sibling_pages):
        """Test getting siblings by querying parent's children."""
        parent = sibling_pages["parent"]

        children = confluence_client.get(f"/api/v2/pages/{parent['id']}/children")

        assert "results" in children
        assert len(children["results"]) >= 3

    def test_siblings_have_same_parent(self, confluence_client, sibling_pages):
        """Test that siblings share the same parent."""
        parent = sibling_pages["parent"]

        for sibling in sibling_pages["siblings"]:
            page = confluence_client.get(f"/api/v2/pages/{sibling['id']}")
            assert page["parentId"] == parent["id"]

    def test_find_sibling_by_title(self, confluence_client, sibling_pages):
        """Test finding a sibling by searching."""
        sibling = sibling_pages["siblings"][0]
        parent = sibling_pages["parent"]

        # Get all children and find by title
        children = confluence_client.get(f"/api/v2/pages/{parent['id']}/children")

        titles = [c["title"] for c in children.get("results", [])]
        assert sibling["title"] in titles

    def test_siblings_are_at_same_level(self, confluence_client, sibling_pages):
        """Test that siblings are at the same hierarchy level."""
        parent = sibling_pages["parent"]

        for sibling in sibling_pages["siblings"]:
            page = confluence_client.get(
                f"/rest/api/content/{sibling['id']}", params={"expand": "ancestors"}
            )
            ancestors = page.get("ancestors", [])
            # All should have same number of ancestors
            if ancestors:
                assert ancestors[-1]["id"] == parent["id"]
