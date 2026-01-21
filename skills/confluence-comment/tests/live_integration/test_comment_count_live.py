"""
Live integration tests for comment count operations.

Usage:
    pytest test_comment_count_live.py --live -v
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


@pytest.fixture
def test_page(confluence_client, test_space):
    page = confluence_client.post(
        "/api/v2/pages",
        json_data={
            "spaceId": test_space["id"],
            "status": "current",
            "title": f"Comment Count Test {uuid.uuid4().hex[:8]}",
            "body": {"representation": "storage", "value": "<p>Test.</p>"},
        },
    )
    yield page
    with contextlib.suppress(Exception):
        confluence_client.delete(f"/api/v2/pages/{page['id']}")


@pytest.mark.integration
class TestCommentCountLive:
    """Live tests for comment count operations."""

    def test_count_zero_comments(self, confluence_client, test_page):
        """Test counting comments on page with no comments."""
        comments = confluence_client.get(
            f"/api/v2/pages/{test_page['id']}/footer-comments"
        )

        count = len(comments.get("results", []))
        assert count == 0

    def test_count_after_adding_comments(self, confluence_client, test_page):
        """Test counting after adding comments."""
        comment_ids = []

        # Add 3 comments using v1 API
        for i in range(3):
            comment = confluence_client.post(
                "/rest/api/content",
                json_data={
                    "type": "comment",
                    "container": {"id": test_page["id"], "type": "page"},
                    "body": {
                        "storage": {
                            "representation": "storage",
                            "value": f"<p>Comment {i}.</p>",
                        }
                    },
                },
            )
            comment_ids.append(comment["id"])

        try:
            comments = confluence_client.get(
                f"/api/v2/pages/{test_page['id']}/footer-comments"
            )
            count = len(comments.get("results", []))
            assert count >= 3
        finally:
            for cid in comment_ids:
                with contextlib.suppress(Exception):
                    confluence_client.delete(f"/rest/api/content/{cid}")

    def test_count_after_deleting_comment(self, confluence_client, test_page):
        """Test count updates after deleting a comment."""
        # Add a comment using v1 API
        comment = confluence_client.post(
            "/rest/api/content",
            json_data={
                "type": "comment",
                "container": {"id": test_page["id"], "type": "page"},
                "body": {
                    "storage": {
                        "representation": "storage",
                        "value": "<p>To delete.</p>",
                    }
                },
            },
        )

        # Verify added
        comments = confluence_client.get(
            f"/api/v2/pages/{test_page['id']}/footer-comments"
        )
        initial_count = len(comments.get("results", []))

        # Delete using v1 API
        confluence_client.delete(f"/rest/api/content/{comment['id']}")

        # Verify count decreased
        comments = confluence_client.get(
            f"/api/v2/pages/{test_page['id']}/footer-comments"
        )
        final_count = len(comments.get("results", []))

        assert final_count == initial_count - 1
