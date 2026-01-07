"""
Live integration tests for space content operations.

Usage:
    pytest test_space_content_live.py --profile development -v
"""

import contextlib

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


@pytest.mark.integration
class TestSpaceContentLive:
    """Live tests for space content queries."""

    def test_get_space_pages(self, confluence_client, test_space):
        """Test getting all pages in a space."""
        pages = confluence_client.get(
            "/api/v2/pages", params={"space-id": test_space["id"], "limit": 25}
        )

        assert "results" in pages

    def test_get_space_blogposts(self, confluence_client, test_space):
        """Test getting all blog posts in a space."""
        posts = confluence_client.get(
            "/api/v2/blogposts", params={"space-id": test_space["id"], "limit": 25}
        )

        assert "results" in posts

    def test_get_space_homepage(self, confluence_client, test_space):
        """Test getting the space homepage."""
        if test_space.get("homepageId"):
            homepage = confluence_client.get(
                f"/api/v2/pages/{test_space['homepageId']}"
            )
            assert homepage["id"] == test_space["homepageId"]

    def test_count_space_content(self, confluence_client, test_space):
        """Test counting content in a space."""
        # Get pages
        pages = confluence_client.get(
            "/api/v2/pages", params={"space-id": test_space["id"], "limit": 250}
        )
        page_count = len(pages.get("results", []))

        # Get blog posts
        posts = confluence_client.get(
            "/api/v2/blogposts", params={"space-id": test_space["id"], "limit": 250}
        )
        post_count = len(posts.get("results", []))

        total = page_count + post_count
        assert total >= 0

    def test_get_space_root_pages(self, confluence_client, test_space):
        """Test getting root-level pages in a space."""
        # Root pages have no parent
        pages = confluence_client.get(
            "/api/v2/pages",
            params={"space-id": test_space["id"], "depth": "root", "limit": 25},
        )

        assert "results" in pages
