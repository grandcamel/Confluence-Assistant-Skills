"""
Live integration tests for confluence-comment skill.

Tests comment operations against a real Confluence instance.

Usage:
    pytest test_comment_live.py --live -v
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
            "title": f"Comment Test Page {uuid.uuid4().hex[:8]}",
            "body": {"representation": "storage", "value": "<p>Test content.</p>"},
        },
    )
    yield page
    with contextlib.suppress(Exception):
        confluence_client.delete(f"/api/v2/pages/{page['id']}")


@pytest.mark.integration
class TestAddCommentLive:
    """Live tests for adding comments."""

    def test_add_footer_comment(self, confluence_client, test_page):
        """Test adding a footer comment to a page."""
        # Use v1 API (v2 doesn't support POST for comments)
        comment = confluence_client.post(
            "/rest/api/content",
            json_data={
                "type": "comment",
                "container": {"id": test_page["id"], "type": "page"},
                "body": {
                    "storage": {
                        "representation": "storage",
                        "value": "<p>Test comment from live test.</p>",
                    }
                },
            },
        )

        assert comment["id"] is not None
        assert "body" in comment

    def test_add_multiple_comments(self, confluence_client, test_page):
        """Test adding multiple comments."""
        # Use v1 API (v2 doesn't support POST for comments)
        comments = []
        for i in range(3):
            comment = confluence_client.post(
                "/rest/api/content",
                json_data={
                    "type": "comment",
                    "container": {"id": test_page["id"], "type": "page"},
                    "body": {
                        "storage": {
                            "representation": "storage",
                            "value": f"<p>Comment {i + 1}</p>",
                        }
                    },
                },
            )
            comments.append(comment)

        assert len(comments) == 3
        assert all(c["id"] for c in comments)


@pytest.mark.integration
class TestGetCommentsLive:
    """Live tests for retrieving comments."""

    def test_get_page_comments(self, confluence_client, test_page):
        """Test getting comments from a page."""
        # Add a comment first using v1 API
        confluence_client.post(
            "/rest/api/content",
            json_data={
                "type": "comment",
                "container": {"id": test_page["id"], "type": "page"},
                "body": {
                    "storage": {"representation": "storage", "value": "<p>Test</p>"}
                },
            },
        )

        # Get comments
        comments = confluence_client.get(
            f"/api/v2/pages/{test_page['id']}/footer-comments"
        )

        assert "results" in comments
        assert len(comments["results"]) >= 1

    def test_get_comments_empty_page(self, confluence_client, test_space):
        """Test getting comments from a page with no comments."""
        # Create fresh page
        page = confluence_client.post(
            "/api/v2/pages",
            json_data={
                "spaceId": test_space["id"],
                "status": "current",
                "title": f"Empty Comments {uuid.uuid4().hex[:8]}",
                "body": {"representation": "storage", "value": "<p>No comments.</p>"},
            },
        )

        try:
            comments = confluence_client.get(
                f"/api/v2/pages/{page['id']}/footer-comments"
            )
            assert "results" in comments
            assert len(comments["results"]) == 0
        finally:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")


@pytest.mark.integration
class TestUpdateCommentLive:
    """Live tests for updating comments."""

    def test_update_comment_body(self, confluence_client, test_page):
        """Test updating a comment's body."""
        # Create comment using v1 API
        comment = confluence_client.post(
            "/rest/api/content",
            json_data={
                "type": "comment",
                "container": {"id": test_page["id"], "type": "page"},
                "body": {
                    "storage": {"representation": "storage", "value": "<p>Original</p>"}
                },
            },
        )

        # Update it using v1 API
        updated = confluence_client.put(
            f"/rest/api/content/{comment['id']}",
            json_data={
                "type": "comment",
                "version": {"number": comment["version"]["number"] + 1},
                "body": {
                    "storage": {"representation": "storage", "value": "<p>Updated</p>"}
                },
            },
        )

        assert updated["version"]["number"] == comment["version"]["number"] + 1


@pytest.mark.integration
class TestDeleteCommentLive:
    """Live tests for deleting comments."""

    def test_delete_comment(self, confluence_client, test_page):
        """Test deleting a comment."""
        # Create comment using v1 API
        comment = confluence_client.post(
            "/rest/api/content",
            json_data={
                "type": "comment",
                "container": {"id": test_page["id"], "type": "page"},
                "body": {
                    "storage": {
                        "representation": "storage",
                        "value": "<p>Delete me</p>",
                    }
                },
            },
        )

        comment_id = comment["id"]

        # Delete it using v1 API
        confluence_client.delete(f"/rest/api/content/{comment_id}")

        # Verify deleted
        comments = confluence_client.get(
            f"/api/v2/pages/{test_page['id']}/footer-comments"
        )
        comment_ids = [c["id"] for c in comments["results"]]
        assert comment_id not in comment_ids
