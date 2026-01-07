"""
Live integration tests for blog post operations.

Usage:
    pytest test_blogpost_live.py --live -v
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


@pytest.mark.integration
class TestBlogpostLive:
    """Live tests for blog post operations."""

    def test_create_blogpost(self, confluence_client, test_space):
        """Test creating a blog post."""
        title = f"Blog Post Test {uuid.uuid4().hex[:8]}"

        post = confluence_client.post(
            "/api/v2/blogposts",
            json_data={
                "spaceId": test_space["id"],
                "status": "current",
                "title": title,
                "body": {"representation": "storage", "value": "<p>Blog content.</p>"},
            },
        )

        try:
            assert post["id"] is not None
            assert post["title"] == title
        finally:
            confluence_client.delete(f"/api/v2/blogposts/{post['id']}")

    def test_update_blogpost(self, confluence_client, test_space):
        """Test updating a blog post."""
        post = confluence_client.post(
            "/api/v2/blogposts",
            json_data={
                "spaceId": test_space["id"],
                "status": "current",
                "title": f"Blog Update Test {uuid.uuid4().hex[:8]}",
                "body": {"representation": "storage", "value": "<p>Original.</p>"},
            },
        )

        try:
            updated = confluence_client.put(
                f"/api/v2/blogposts/{post['id']}",
                json_data={
                    "id": post["id"],
                    "status": "current",
                    "title": post["title"],
                    "spaceId": test_space["id"],
                    "body": {"representation": "storage", "value": "<p>Updated.</p>"},
                    "version": {"number": post["version"]["number"] + 1},
                },
            )
            assert updated["version"]["number"] == post["version"]["number"] + 1
        finally:
            confluence_client.delete(f"/api/v2/blogposts/{post['id']}")

    def test_list_blogposts(self, confluence_client, test_space):
        """Test listing blog posts in a space."""
        posts = confluence_client.get(
            "/api/v2/blogposts", params={"space-id": test_space["id"], "limit": 10}
        )

        assert "results" in posts

    def test_get_blogpost_by_id(self, confluence_client, test_space):
        """Test getting a blog post by ID."""
        post = confluence_client.post(
            "/api/v2/blogposts",
            json_data={
                "spaceId": test_space["id"],
                "status": "current",
                "title": f"Blog Get Test {uuid.uuid4().hex[:8]}",
                "body": {"representation": "storage", "value": "<p>Content.</p>"},
            },
        )

        try:
            fetched = confluence_client.get(f"/api/v2/blogposts/{post['id']}")
            assert fetched["id"] == post["id"]
        finally:
            confluence_client.delete(f"/api/v2/blogposts/{post['id']}")
