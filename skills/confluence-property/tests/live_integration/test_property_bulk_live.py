"""
Live integration tests for bulk property operations.

Usage:
    pytest test_property_bulk_live.py --live -v
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
            "title": f"Bulk Property Test {uuid.uuid4().hex[:8]}",
            "body": {"representation": "storage", "value": "<p>Test.</p>"},
        },
    )
    yield page
    with contextlib.suppress(Exception):
        confluence_client.delete(f"/api/v2/pages/{page['id']}")


@pytest.mark.integration
class TestBulkPropertyLive:
    """Live tests for bulk property operations."""

    def test_set_multiple_properties(self, confluence_client, test_page):
        """Test setting multiple properties on a page."""
        properties = [
            {"key": f"prop-{i}-{uuid.uuid4().hex[:4]}", "value": {"index": i}}
            for i in range(5)
        ]

        for prop in properties:
            confluence_client.post(
                f"/rest/api/content/{test_page['id']}/property",
                json_data={"key": prop["key"], "value": prop["value"]},
            )

        # Verify all properties exist
        all_props = confluence_client.get(
            f"/rest/api/content/{test_page['id']}/property"
        )

        prop_keys = [p["key"] for p in all_props.get("results", [])]
        for prop in properties:
            assert prop["key"] in prop_keys

    def test_update_multiple_properties(self, confluence_client, test_page):
        """Test updating multiple properties."""
        key1 = f"update-1-{uuid.uuid4().hex[:4]}"
        key2 = f"update-2-{uuid.uuid4().hex[:4]}"

        # Create properties
        for key in [key1, key2]:
            confluence_client.post(
                f"/rest/api/content/{test_page['id']}/property",
                json_data={"key": key, "value": {"version": 1}},
            )

        # Update each
        for key in [key1, key2]:
            prop = confluence_client.get(
                f"/rest/api/content/{test_page['id']}/property/{key}"
            )
            confluence_client.put(
                f"/rest/api/content/{test_page['id']}/property/{key}",
                json_data={
                    "key": key,
                    "value": {"version": 2},
                    "version": {"number": prop["version"]["number"] + 1},
                },
            )

        # Verify updates
        for key in [key1, key2]:
            prop = confluence_client.get(
                f"/rest/api/content/{test_page['id']}/property/{key}"
            )
            assert prop["value"]["version"] == 2

    def test_delete_all_properties(self, confluence_client, test_page):
        """Test deleting all properties from a page."""
        # Create some properties
        for i in range(3):
            confluence_client.post(
                f"/rest/api/content/{test_page['id']}/property",
                json_data={
                    "key": f"delete-{i}-{uuid.uuid4().hex[:4]}",
                    "value": {"temp": True},
                },
            )

        # Get all and delete
        props = confluence_client.get(f"/rest/api/content/{test_page['id']}/property")

        for prop in props.get("results", []):
            if prop["key"].startswith("delete-"):
                confluence_client.delete(
                    f"/rest/api/content/{test_page['id']}/property/{prop['key']}"
                )

        # Verify deletion
        remaining = confluence_client.get(
            f"/rest/api/content/{test_page['id']}/property"
        )
        remaining_keys = [p["key"] for p in remaining.get("results", [])]

        for prop in props.get("results", []):
            if prop["key"].startswith("delete-"):
                assert prop["key"] not in remaining_keys
