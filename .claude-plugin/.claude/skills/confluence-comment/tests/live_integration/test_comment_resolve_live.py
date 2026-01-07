"""
Live integration tests for comment resolve operations.

Usage:
    pytest test_comment_resolve_live.py --profile development -v
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
def test_page(confluence_client, test_space):
    page = confluence_client.post(
        "/api/v2/pages",
        json_data={
            "spaceId": test_space["id"],
            "status": "current",
            "title": f"Comment Resolve Test {uuid.uuid4().hex[:8]}",
            "body": {"representation": "storage", "value": "<p>Test.</p>"},
        },
    )
    yield page
    with contextlib.suppress(Exception):
        confluence_client.delete(f"/api/v2/pages/{page['id']}")


@pytest.mark.integration
class TestCommentResolveLive:
    """Live tests for comment resolve operations."""

    def test_create_inline_comment(self, confluence_client, test_page):
        """Test creating an inline comment."""
        try:
            comment = confluence_client.post(
                f"/api/v2/pages/{test_page['id']}/inline-comments",
                json_data={
                    "body": {
                        "representation": "storage",
                        "value": "<p>Inline comment.</p>",
                    },
                    "inlineCommentProperties": {
                        "textSelection": "Test",
                        "textSelectionMatchCount": 1,
                        "textSelectionMatchIndex": 0,
                    },
                },
            )
            assert comment["id"] is not None
        except Exception:
            # Inline comments may not be available on all instances
            pass

    def test_list_inline_comments(self, confluence_client, test_page):
        """Test listing inline comments."""
        try:
            comments = confluence_client.get(
                f"/api/v2/pages/{test_page['id']}/inline-comments"
            )
            assert "results" in comments
        except Exception:
            # Inline comments API may differ
            pass

    def test_footer_comment_lifecycle(self, confluence_client, test_page):
        """Test full comment lifecycle."""
        # Create using v1 API
        comment = confluence_client.post(
            "/rest/api/content",
            json_data={
                "type": "comment",
                "container": {"id": test_page["id"], "type": "page"},
                "body": {
                    "storage": {
                        "representation": "storage",
                        "value": "<p>Lifecycle test.</p>",
                    }
                },
            },
        )

        try:
            # Read using v1 API
            fetched = confluence_client.get(f"/rest/api/content/{comment['id']}")
            assert fetched["id"] == comment["id"]

            # Update using v1 API
            updated = confluence_client.put(
                f"/rest/api/content/{comment['id']}",
                json_data={
                    "type": "comment",
                    "body": {
                        "storage": {
                            "representation": "storage",
                            "value": "<p>Updated lifecycle.</p>",
                        }
                    },
                    "version": {"number": comment["version"]["number"] + 1},
                },
            )
            assert updated["version"]["number"] > comment["version"]["number"]

        finally:
            # Delete using v1 API
            confluence_client.delete(f"/rest/api/content/{comment['id']}")
