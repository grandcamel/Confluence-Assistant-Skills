"""
Live integration tests for page label operations.

Usage:
    pytest test_page_labels_live.py --live -v
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
            "title": f"Page Labels Test {uuid.uuid4().hex[:8]}",
            "body": {"representation": "storage", "value": "<p>Test.</p>"},
        },
    )
    yield page
    with contextlib.suppress(Exception):
        confluence_client.delete(f"/api/v2/pages/{page['id']}")


@pytest.mark.integration
class TestPageLabelsLive:
    """Live tests for page label operations."""

    def test_add_label_to_page(self, confluence_client, test_page):
        """Test adding a label to a page."""
        label = f"test-{uuid.uuid4().hex[:8]}"

        # Use v1 API for adding labels
        confluence_client.post(
            f"/rest/api/content/{test_page['id']}/label",
            json_data=[{"prefix": "global", "name": label}],
        )

        labels = confluence_client.get(f"/api/v2/pages/{test_page['id']}/labels")
        label_names = [l["name"] for l in labels.get("results", [])]
        assert label in label_names

    def test_remove_label_from_page(self, confluence_client, test_page):
        """Test removing a label from a page."""
        label = f"remove-{uuid.uuid4().hex[:8]}"

        # Add using v1 API
        confluence_client.post(
            f"/rest/api/content/{test_page['id']}/label",
            json_data=[{"prefix": "global", "name": label}],
        )

        # Verify label was added
        labels = confluence_client.get(f"/api/v2/pages/{test_page['id']}/labels")
        label_names = [l["name"] for l in labels.get("results", [])]
        assert label in label_names

        # Remove using v1 API
        confluence_client.delete(f"/rest/api/content/{test_page['id']}/label/{label}")

        # Verify
        labels = confluence_client.get(f"/api/v2/pages/{test_page['id']}/labels")
        label_names = [l["name"] for l in labels.get("results", [])]
        assert label not in label_names

    def test_list_page_labels(self, confluence_client, test_page):
        """Test listing all labels on a page."""
        labels = [f"label-{c}-{uuid.uuid4().hex[:4]}" for c in ["a", "b", "c"]]

        # Add all labels at once using v1 API
        label_data = [{"prefix": "global", "name": label} for label in labels]
        confluence_client.post(
            f"/rest/api/content/{test_page['id']}/label", json_data=label_data
        )

        page_labels = confluence_client.get(f"/api/v2/pages/{test_page['id']}/labels")

        assert len(page_labels.get("results", [])) >= 3

    def test_page_with_no_labels(self, confluence_client, test_space):
        """Test that new page has no labels."""
        page = confluence_client.post(
            "/api/v2/pages",
            json_data={
                "spaceId": test_space["id"],
                "status": "current",
                "title": f"No Labels Test {uuid.uuid4().hex[:8]}",
                "body": {"representation": "storage", "value": "<p>Test.</p>"},
            },
        )

        try:
            labels = confluence_client.get(f"/api/v2/pages/{page['id']}/labels")
            assert len(labels.get("results", [])) == 0
        finally:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")
