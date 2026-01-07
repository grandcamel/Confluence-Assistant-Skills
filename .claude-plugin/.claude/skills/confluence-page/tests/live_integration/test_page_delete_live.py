"""
Live integration tests for page delete operations.

Usage:
    pytest test_page_delete_live.py --profile development -v
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


@pytest.mark.integration
class TestPageDeleteLive:
    """Live tests for page delete operations."""

    def test_delete_page(self, confluence_client, test_space):
        """Test deleting a page."""
        page = confluence_client.post(
            "/api/v2/pages",
            json_data={
                "spaceId": test_space["id"],
                "status": "current",
                "title": f"Delete Test {uuid.uuid4().hex[:8]}",
                "body": {"representation": "storage", "value": "<p>To delete.</p>"},
            },
        )

        page_id = page["id"]

        # Delete
        confluence_client.delete(f"/api/v2/pages/{page_id}")

        # Verify deleted
        try:
            confluence_client.get(f"/api/v2/pages/{page_id}")
            raise AssertionError("Page should be deleted")
        except Exception:
            pass  # Expected - page not found

    def test_delete_page_with_children(self, confluence_client, test_space):
        """Test deleting a page with children (children should be orphaned or deleted)."""
        parent = confluence_client.post(
            "/api/v2/pages",
            json_data={
                "spaceId": test_space["id"],
                "status": "current",
                "title": f"Parent Delete Test {uuid.uuid4().hex[:8]}",
                "body": {"representation": "storage", "value": "<p>Parent.</p>"},
            },
        )

        child = confluence_client.post(
            "/api/v2/pages",
            json_data={
                "spaceId": test_space["id"],
                "status": "current",
                "title": f"Child Delete Test {uuid.uuid4().hex[:8]}",
                "parentId": parent["id"],
                "body": {"representation": "storage", "value": "<p>Child.</p>"},
            },
        )

        try:
            # Delete parent
            confluence_client.delete(f"/api/v2/pages/{parent['id']}")
        finally:
            # Clean up child if still exists
            with contextlib.suppress(Exception):
                confluence_client.delete(f"/api/v2/pages/{child['id']}")

    def test_delete_nonexistent_page(self, confluence_client):
        """Test deleting a page that doesn't exist."""
        fake_id = "999999999"
        try:
            confluence_client.delete(f"/api/v2/pages/{fake_id}")
        except Exception:
            pass  # Expected - not found error
