"""
Live integration tests for page copy operations.

Usage:
    pytest test_page_copy_live.py --live -v
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
def source_page(confluence_client, test_space):
    """Create a source page with content."""
    page = confluence_client.post(
        "/api/v2/pages",
        json_data={
            "spaceId": test_space["id"],
            "status": "current",
            "title": f"Copy Source {uuid.uuid4().hex[:8]}",
            "body": {
                "representation": "storage",
                "value": "<p>Original content to copy.</p><ul><li>Item 1</li><li>Item 2</li></ul>",
            },
        },
    )
    yield page
    with contextlib.suppress(Exception):
        confluence_client.delete(f"/api/v2/pages/{page['id']}")


@pytest.mark.integration
class TestPageCopyLive:
    """Live tests for page copy operations."""

    def test_copy_page_same_space(self, confluence_client, test_space, source_page):
        """Test copying a page within the same space."""
        new_title = f"Copy of {source_page['title']}"

        # Get source content
        source = confluence_client.get(
            f"/api/v2/pages/{source_page['id']}", params={"body-format": "storage"}
        )

        # Create copy
        copy = confluence_client.post(
            "/api/v2/pages",
            json_data={
                "spaceId": test_space["id"],
                "status": "current",
                "title": new_title,
                "body": source["body"],
            },
        )

        try:
            assert copy["title"] == new_title
            assert copy["id"] != source_page["id"]

            # Verify content matches
            copy_content = confluence_client.get(
                f"/api/v2/pages/{copy['id']}", params={"body-format": "storage"}
            )
            assert "Original content" in copy_content["body"]["storage"]["value"]

        finally:
            confluence_client.delete(f"/api/v2/pages/{copy['id']}")

    def test_copy_page_with_new_parent(
        self, confluence_client, test_space, source_page
    ):
        """Test copying a page under a new parent."""
        # Create a parent page
        parent = confluence_client.post(
            "/api/v2/pages",
            json_data={
                "spaceId": test_space["id"],
                "status": "current",
                "title": f"Parent for Copy {uuid.uuid4().hex[:8]}",
                "body": {"representation": "storage", "value": "<p>Parent.</p>"},
            },
        )

        try:
            # Get source content
            source = confluence_client.get(
                f"/api/v2/pages/{source_page['id']}", params={"body-format": "storage"}
            )

            # Create copy under parent
            copy = confluence_client.post(
                "/api/v2/pages",
                json_data={
                    "spaceId": test_space["id"],
                    "parentId": parent["id"],
                    "status": "current",
                    "title": f"Child Copy {uuid.uuid4().hex[:8]}",
                    "body": source["body"],
                },
            )

            try:
                assert copy["parentId"] == parent["id"]
            finally:
                confluence_client.delete(f"/api/v2/pages/{copy['id']}")

        finally:
            confluence_client.delete(f"/api/v2/pages/{parent['id']}")
