"""
Live integration tests for bulk permission operations.

Usage:
    pytest test_bulk_permission_live.py --live -v
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
def test_pages(confluence_client, test_space):
    """Create multiple test pages."""
    pages = []
    for i in range(3):
        page = confluence_client.post(
            "/api/v2/pages",
            json_data={
                "spaceId": test_space["id"],
                "status": "current",
                "title": f"Bulk Perm Test {i} {uuid.uuid4().hex[:8]}",
                "body": {"representation": "storage", "value": f"<p>Page {i}.</p>"},
            },
        )
        pages.append(page)

    yield pages

    for page in pages:
        with contextlib.suppress(Exception):
            confluence_client.delete(f"/api/v2/pages/{page['id']}")


@pytest.fixture
def current_user(confluence_client):
    return confluence_client.get("/rest/api/user/current")


@pytest.mark.integration
class TestBulkPermissionLive:
    """Live tests for bulk permission operations."""

    def test_check_permissions_on_multiple_pages(self, confluence_client, test_pages):
        """Test checking permissions on multiple pages."""
        for page in test_pages:
            # If we can read it, we have permission
            result = confluence_client.get(f"/api/v2/pages/{page['id']}")
            assert result["id"] == page["id"]

    def test_add_restriction_to_multiple_pages(
        self, confluence_client, test_pages, current_user
    ):
        """Test adding restrictions to multiple pages."""
        for page in test_pages:
            confluence_client.put(
                f"/rest/api/content/{page['id']}/restriction",
                json_data={
                    "results": [
                        {
                            "operation": "update",
                            "restrictions": {
                                "user": {
                                    "results": [
                                        {"accountId": current_user["accountId"]}
                                    ]
                                }
                            },
                        }
                    ]
                },
            )

        # Clean up restrictions
        for page in test_pages:
            with contextlib.suppress(Exception):
                confluence_client.delete(f"/rest/api/content/{page['id']}/restriction")

    def test_remove_all_restrictions(self, confluence_client, test_pages, current_user):
        """Test removing restrictions from multiple pages."""
        # Add restrictions first
        for page in test_pages:
            confluence_client.put(
                f"/rest/api/content/{page['id']}/restriction",
                json_data={
                    "results": [
                        {
                            "operation": "read",
                            "restrictions": {
                                "user": {
                                    "results": [
                                        {"accountId": current_user["accountId"]}
                                    ]
                                }
                            },
                        }
                    ]
                },
            )

        # Remove all
        for page in test_pages:
            confluence_client.delete(f"/rest/api/content/{page['id']}/restriction")

        # Verify removal - page should still be accessible
        for page in test_pages:
            result = confluence_client.get(f"/api/v2/pages/{page['id']}")
            assert result["id"] == page["id"]
