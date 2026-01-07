"""
Live integration tests for page tree operations.

Usage:
    pytest test_page_tree_live.py --profile development -v
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
def page_tree(confluence_client, test_space):
    """Create a tree of pages: root -> child1, child2 -> grandchild."""
    root = confluence_client.post(
        "/api/v2/pages",
        json_data={
            "spaceId": test_space["id"],
            "status": "current",
            "title": f"Tree Root {uuid.uuid4().hex[:8]}",
            "body": {"representation": "storage", "value": "<p>Root.</p>"},
        },
    )

    child1 = confluence_client.post(
        "/api/v2/pages",
        json_data={
            "spaceId": test_space["id"],
            "parentId": root["id"],
            "status": "current",
            "title": f"Tree Child 1 {uuid.uuid4().hex[:8]}",
            "body": {"representation": "storage", "value": "<p>Child 1.</p>"},
        },
    )

    child2 = confluence_client.post(
        "/api/v2/pages",
        json_data={
            "spaceId": test_space["id"],
            "parentId": root["id"],
            "status": "current",
            "title": f"Tree Child 2 {uuid.uuid4().hex[:8]}",
            "body": {"representation": "storage", "value": "<p>Child 2.</p>"},
        },
    )

    grandchild = confluence_client.post(
        "/api/v2/pages",
        json_data={
            "spaceId": test_space["id"],
            "parentId": child1["id"],
            "status": "current",
            "title": f"Tree Grandchild {uuid.uuid4().hex[:8]}",
            "body": {"representation": "storage", "value": "<p>Grandchild.</p>"},
        },
    )

    tree = {"root": root, "child1": child1, "child2": child2, "grandchild": grandchild}

    yield tree

    # Cleanup in reverse order
    for key in ["grandchild", "child2", "child1", "root"]:
        with contextlib.suppress(Exception):
            confluence_client.delete(f"/api/v2/pages/{tree[key]['id']}")


@pytest.mark.integration
class TestPageTreeLive:
    """Live tests for page tree operations."""

    def test_get_full_tree(self, confluence_client, page_tree):
        """Test getting full page tree from root."""
        root = page_tree["root"]

        # Get descendants using v1 API
        descendants = confluence_client.get(
            f"/rest/api/content/{root['id']}/descendant/page"
        )

        assert "results" in descendants
        desc_ids = [d["id"] for d in descendants["results"]]

        assert page_tree["child1"]["id"] in desc_ids
        assert page_tree["child2"]["id"] in desc_ids
        assert page_tree["grandchild"]["id"] in desc_ids

    def test_tree_depth(self, confluence_client, page_tree):
        """Test tree depth - grandchild has 2 ancestors."""
        grandchild = page_tree["grandchild"]

        ancestors = confluence_client.get(f"/api/v2/pages/{grandchild['id']}/ancestors")

        # Should have at least child1 and root as ancestors
        assert len(ancestors["results"]) >= 2

    def test_sibling_count(self, confluence_client, page_tree):
        """Test that root has 2 children."""
        root = page_tree["root"]

        children = confluence_client.get(f"/api/v2/pages/{root['id']}/children")

        assert len(children["results"]) == 2

    def test_leaf_page_no_children(self, confluence_client, page_tree):
        """Test that grandchild has no children."""
        grandchild = page_tree["grandchild"]

        children = confluence_client.get(f"/api/v2/pages/{grandchild['id']}/children")

        assert len(children["results"]) == 0

    def test_parent_child_relationship(self, confluence_client, page_tree):
        """Test parent-child relationships are correct."""
        child1 = confluence_client.get(f"/api/v2/pages/{page_tree['child1']['id']}")
        child2 = confluence_client.get(f"/api/v2/pages/{page_tree['child2']['id']}")
        grandchild = confluence_client.get(
            f"/api/v2/pages/{page_tree['grandchild']['id']}"
        )

        assert child1["parentId"] == page_tree["root"]["id"]
        assert child2["parentId"] == page_tree["root"]["id"]
        assert grandchild["parentId"] == page_tree["child1"]["id"]
