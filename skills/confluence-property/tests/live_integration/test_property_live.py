"""
Live integration tests for confluence-property skill.

Tests content property operations against a real Confluence instance.

Usage:
    pytest test_property_live.py --live -v
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
def test_page(confluence_client, test_space):
    page = confluence_client.post(
        "/api/v2/pages",
        json_data={
            "spaceId": test_space["id"],
            "status": "current",
            "title": f"Property Test Page {uuid.uuid4().hex[:8]}",
            "body": {"representation": "storage", "value": "<p>Test.</p>"},
        },
    )
    yield page
    with contextlib.suppress(Exception):
        confluence_client.delete(f"/api/v2/pages/{page['id']}")


@pytest.fixture
def property_key():
    return f"test-prop-{uuid.uuid4().hex[:8]}"


@pytest.mark.integration
class TestSetPropertyLive:
    """Live tests for setting content properties."""

    def test_set_property_string(self, confluence_client, test_page, property_key):
        """Test setting a string property."""
        # Use v1 API for properties
        result = confluence_client.post(
            f"/rest/api/content/{test_page['id']}/property",
            json_data={"key": property_key, "value": {"stringValue": "test value"}},
        )

        assert result["key"] == property_key
        assert "value" in result

    def test_set_property_json(self, confluence_client, test_page, property_key):
        """Test setting a JSON property."""
        result = confluence_client.post(
            f"/rest/api/content/{test_page['id']}/property",
            json_data={
                "key": property_key,
                "value": {"name": "Test", "count": 42, "items": ["a", "b", "c"]},
            },
        )

        assert result["key"] == property_key
        assert result["value"]["count"] == 42

    def test_update_existing_property(self, confluence_client, test_page, property_key):
        """Test updating an existing property."""
        # Create property
        confluence_client.post(
            f"/rest/api/content/{test_page['id']}/property",
            json_data={"key": property_key, "value": {"version": 1}},
        )

        # Get current version
        prop = confluence_client.get(
            f"/rest/api/content/{test_page['id']}/property/{property_key}"
        )

        # Update
        updated = confluence_client.put(
            f"/rest/api/content/{test_page['id']}/property/{property_key}",
            json_data={
                "key": property_key,
                "value": {"version": 2},
                "version": {"number": prop["version"]["number"] + 1},
            },
        )

        assert updated["value"]["version"] == 2


@pytest.mark.integration
class TestGetPropertyLive:
    """Live tests for getting content properties."""

    def test_get_property(self, confluence_client, test_page, property_key):
        """Test getting a property by key."""
        # Set first
        confluence_client.post(
            f"/rest/api/content/{test_page['id']}/property",
            json_data={"key": property_key, "value": {"data": "test"}},
        )

        # Get
        prop = confluence_client.get(
            f"/rest/api/content/{test_page['id']}/property/{property_key}"
        )

        assert prop["key"] == property_key
        assert prop["value"]["data"] == "test"

    def test_get_nonexistent_property(self, confluence_client, test_page):
        """Test getting a property that doesn't exist."""
        from confluence_assistant_skills_lib import NotFoundError

        with pytest.raises(NotFoundError):
            confluence_client.get(
                f"/rest/api/content/{test_page['id']}/property/nonexistent-key-12345"
            )


@pytest.mark.integration
class TestListPropertiesLive:
    """Live tests for listing content properties."""

    def test_list_properties(self, confluence_client, test_page):
        """Test listing all properties on a page."""
        # Set some properties
        for i in range(3):
            confluence_client.post(
                f"/rest/api/content/{test_page['id']}/property",
                json_data={
                    "key": f"prop-{i}-{uuid.uuid4().hex[:8]}",
                    "value": {"index": i},
                },
            )

        # List
        props = confluence_client.get(f"/rest/api/content/{test_page['id']}/property")

        assert "results" in props
        assert len(props["results"]) >= 3

    def test_list_properties_empty(self, confluence_client, test_space):
        """Test listing properties on page with none."""
        page = confluence_client.post(
            "/api/v2/pages",
            json_data={
                "spaceId": test_space["id"],
                "status": "current",
                "title": f"No Props {uuid.uuid4().hex[:8]}",
                "body": {"representation": "storage", "value": "<p>Empty.</p>"},
            },
        )

        try:
            props = confluence_client.get(f"/rest/api/content/{page['id']}/property")
            assert "results" in props
        finally:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")


@pytest.mark.integration
class TestDeletePropertyLive:
    """Live tests for deleting content properties."""

    def test_delete_property(self, confluence_client, test_page, property_key):
        """Test deleting a property."""
        # Create
        confluence_client.post(
            f"/rest/api/content/{test_page['id']}/property",
            json_data={"key": property_key, "value": {"delete": True}},
        )

        # Delete
        confluence_client.delete(
            f"/rest/api/content/{test_page['id']}/property/{property_key}"
        )

        # Verify deleted
        from confluence_assistant_skills_lib import NotFoundError

        with pytest.raises(NotFoundError):
            confluence_client.get(
                f"/rest/api/content/{test_page['id']}/property/{property_key}"
            )
