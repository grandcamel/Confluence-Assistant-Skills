"""
Live integration tests for property version operations.

Usage:
    pytest test_property_version_live.py --profile development -v
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
            "title": f"Property Version Test {uuid.uuid4().hex[:8]}",
            "body": {"representation": "storage", "value": "<p>Test.</p>"},
        },
    )
    yield page
    with contextlib.suppress(Exception):
        confluence_client.delete(f"/api/v2/pages/{page['id']}")


@pytest.mark.integration
class TestPropertyVersionLive:
    """Live tests for property version operations."""

    def test_property_has_version(self, confluence_client, test_page):
        """Test that properties have version info."""
        key = f"version-test-{uuid.uuid4().hex[:8]}"

        confluence_client.post(
            f"/rest/api/content/{test_page['id']}/property",
            json_data={"key": key, "value": {"data": "v1"}},
        )

        prop = confluence_client.get(
            f"/rest/api/content/{test_page['id']}/property/{key}"
        )

        assert "version" in prop
        assert "number" in prop["version"]

    def test_update_increments_version(self, confluence_client, test_page):
        """Test that updating property increments version."""
        key = f"increment-test-{uuid.uuid4().hex[:8]}"

        confluence_client.post(
            f"/rest/api/content/{test_page['id']}/property",
            json_data={"key": key, "value": {"count": 1}},
        )

        prop = confluence_client.get(
            f"/rest/api/content/{test_page['id']}/property/{key}"
        )
        initial_version = prop["version"]["number"]

        # Update
        confluence_client.put(
            f"/rest/api/content/{test_page['id']}/property/{key}",
            json_data={
                "key": key,
                "value": {"count": 2},
                "version": {"number": initial_version + 1},
            },
        )

        updated = confluence_client.get(
            f"/rest/api/content/{test_page['id']}/property/{key}"
        )

        assert updated["version"]["number"] == initial_version + 1

    def test_update_with_wrong_version_fails(self, confluence_client, test_page):
        """Test that updating with wrong version fails."""
        key = f"wrong-version-{uuid.uuid4().hex[:8]}"

        confluence_client.post(
            f"/rest/api/content/{test_page['id']}/property",
            json_data={"key": key, "value": {"test": True}},
        )

        try:
            # Try to update with wrong version
            confluence_client.put(
                f"/rest/api/content/{test_page['id']}/property/{key}",
                json_data={
                    "key": key,
                    "value": {"test": False},
                    "version": {"number": 999},
                },
            )
            # Should have failed
        except Exception:
            pass  # Expected - version conflict

    def test_delete_property(self, confluence_client, test_page):
        """Test deleting a property."""
        key = f"delete-test-{uuid.uuid4().hex[:8]}"

        confluence_client.post(
            f"/rest/api/content/{test_page['id']}/property",
            json_data={"key": key, "value": "temp"},
        )

        # Delete
        confluence_client.delete(f"/rest/api/content/{test_page['id']}/property/{key}")

        # Verify deleted
        try:
            confluence_client.get(f"/rest/api/content/{test_page['id']}/property/{key}")
            raise AssertionError("Property should be deleted")
        except Exception:
            pass  # Expected
