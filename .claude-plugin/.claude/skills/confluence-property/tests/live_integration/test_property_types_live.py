"""
Live integration tests for property type operations.

Usage:
    pytest test_property_types_live.py --profile development -v
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
            "title": f"Property Types Test {uuid.uuid4().hex[:8]}",
            "body": {"representation": "storage", "value": "<p>Test.</p>"},
        },
    )
    yield page
    with contextlib.suppress(Exception):
        confluence_client.delete(f"/api/v2/pages/{page['id']}")


@pytest.mark.integration
class TestPropertyTypesLive:
    """Live tests for different property value types."""

    def test_string_property(self, confluence_client, test_page):
        """Test setting a string property."""
        key = f"string-{uuid.uuid4().hex[:8]}"

        confluence_client.post(
            f"/rest/api/content/{test_page['id']}/property",
            json_data={"key": key, "value": "simple string value"},
        )

        prop = confluence_client.get(
            f"/rest/api/content/{test_page['id']}/property/{key}"
        )
        assert prop["value"] == "simple string value"

    def test_numeric_property(self, confluence_client, test_page):
        """Test setting a numeric property."""
        key = f"number-{uuid.uuid4().hex[:8]}"

        confluence_client.post(
            f"/rest/api/content/{test_page['id']}/property",
            json_data={"key": key, "value": 42},
        )

        prop = confluence_client.get(
            f"/rest/api/content/{test_page['id']}/property/{key}"
        )
        assert prop["value"] == 42

    def test_boolean_property(self, confluence_client, test_page):
        """Test setting a boolean property."""
        key = f"bool-{uuid.uuid4().hex[:8]}"

        confluence_client.post(
            f"/rest/api/content/{test_page['id']}/property",
            json_data={"key": key, "value": True},
        )

        prop = confluence_client.get(
            f"/rest/api/content/{test_page['id']}/property/{key}"
        )
        assert prop["value"]

    def test_object_property(self, confluence_client, test_page):
        """Test setting an object property."""
        key = f"object-{uuid.uuid4().hex[:8]}"
        value = {"name": "test", "count": 5, "active": True}

        confluence_client.post(
            f"/rest/api/content/{test_page['id']}/property",
            json_data={"key": key, "value": value},
        )

        prop = confluence_client.get(
            f"/rest/api/content/{test_page['id']}/property/{key}"
        )
        assert prop["value"] == value

    def test_array_property(self, confluence_client, test_page):
        """Test setting an array property."""
        key = f"array-{uuid.uuid4().hex[:8]}"
        value = ["item1", "item2", "item3"]

        confluence_client.post(
            f"/rest/api/content/{test_page['id']}/property",
            json_data={"key": key, "value": value},
        )

        prop = confluence_client.get(
            f"/rest/api/content/{test_page['id']}/property/{key}"
        )
        assert prop["value"] == value
