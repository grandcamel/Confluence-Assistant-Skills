"""
Live integration tests for hierarchy depth operations.

Usage:
    pytest test_depth_live.py --live -v
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


@pytest.mark.integration
class TestDepthLive:
    """Live tests for hierarchy depth operations."""

    def test_get_root_pages(self, confluence_client, test_space):
        """Test getting root level pages."""
        pages = confluence_client.get(
            "/api/v2/pages",
            params={"space-id": test_space["id"], "depth": "root", "limit": 20},
        )

        assert "results" in pages

    def test_calculate_page_depth(self, confluence_client, test_space):
        """Test calculating a page's depth by counting ancestors."""
        # Get any page
        pages = confluence_client.get(
            "/api/v2/pages", params={"space-id": test_space["id"], "limit": 1}
        )

        if pages.get("results"):
            page = pages["results"][0]
            detailed = confluence_client.get(
                f"/rest/api/content/{page['id']}", params={"expand": "ancestors"}
            )

            depth = len(detailed.get("ancestors", []))
            assert depth >= 0

    def test_create_nested_pages(self, confluence_client, test_space):
        """Test creating pages at different depths."""
        pages = []

        # Level 0 (root)
        level0 = confluence_client.post(
            "/api/v2/pages",
            json_data={
                "spaceId": test_space["id"],
                "status": "current",
                "title": f"Depth L0 {uuid.uuid4().hex[:8]}",
                "body": {"representation": "storage", "value": "<p>L0.</p>"},
            },
        )
        pages.append(level0)

        # Level 1
        level1 = confluence_client.post(
            "/api/v2/pages",
            json_data={
                "spaceId": test_space["id"],
                "status": "current",
                "title": f"Depth L1 {uuid.uuid4().hex[:8]}",
                "parentId": level0["id"],
                "body": {"representation": "storage", "value": "<p>L1.</p>"},
            },
        )
        pages.append(level1)

        try:
            # Verify depths
            l0_detail = confluence_client.get(
                f"/rest/api/content/{level0['id']}", params={"expand": "ancestors"}
            )
            l1_detail = confluence_client.get(
                f"/rest/api/content/{level1['id']}", params={"expand": "ancestors"}
            )

            assert len(l1_detail.get("ancestors", [])) > len(
                l0_detail.get("ancestors", [])
            )
        finally:
            for page in reversed(pages):
                with contextlib.suppress(Exception):
                    confluence_client.delete(f"/api/v2/pages/{page['id']}")
