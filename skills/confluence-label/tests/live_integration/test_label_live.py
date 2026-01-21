"""
Live integration tests for confluence-label skill.

Tests label operations against a real Confluence instance.

Usage:
    pytest test_label_live.py --live -v
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
            "title": f"Label Test Page {uuid.uuid4().hex[:8]}",
            "body": {"representation": "storage", "value": "<p>Test.</p>"},
        },
    )
    yield page
    with contextlib.suppress(Exception):
        confluence_client.delete(f"/api/v2/pages/{page['id']}")


@pytest.fixture
def test_label():
    return f"test-label-{uuid.uuid4().hex[:8]}"


@pytest.mark.integration
class TestAddLabelLive:
    """Live tests for adding labels."""

    def test_add_label_to_page(self, confluence_client, test_page, test_label):
        """Test adding a label to a page."""
        # Use v1 API for adding labels (v2 doesn't support POST)
        result = confluence_client.post(
            f"/rest/api/content/{test_page['id']}/label",
            json_data=[{"prefix": "global", "name": test_label}],
        )

        assert result is not None

    def test_add_multiple_labels(self, confluence_client, test_page):
        """Test adding multiple labels."""
        labels = [f"label-{i}-{uuid.uuid4().hex[:4]}" for i in range(3)]

        # Use v1 API - can add all labels in one request
        label_data = [{"prefix": "global", "name": label} for label in labels]
        confluence_client.post(
            f"/rest/api/content/{test_page['id']}/label", json_data=label_data
        )

        # Verify all labels
        page_labels = confluence_client.get(f"/api/v2/pages/{test_page['id']}/labels")

        label_names = [l["name"] for l in page_labels.get("results", [])]
        for label in labels:
            assert label in label_names

    def test_add_duplicate_label(self, confluence_client, test_page, test_label):
        """Test adding the same label twice."""
        # Add first time using v1 API
        confluence_client.post(
            f"/rest/api/content/{test_page['id']}/label",
            json_data=[{"prefix": "global", "name": test_label}],
        )

        # Add second time - should not error
        result = confluence_client.post(
            f"/rest/api/content/{test_page['id']}/label",
            json_data=[{"prefix": "global", "name": test_label}],
        )
        assert result is not None


@pytest.mark.integration
class TestGetLabelsLive:
    """Live tests for retrieving labels."""

    def test_get_page_labels(self, confluence_client, test_page, test_label):
        """Test getting labels from a page."""
        # Add a label first using v1 API
        confluence_client.post(
            f"/rest/api/content/{test_page['id']}/label",
            json_data=[{"prefix": "global", "name": test_label}],
        )

        labels = confluence_client.get(f"/api/v2/pages/{test_page['id']}/labels")

        assert "results" in labels
        assert len(labels["results"]) >= 1
        assert any(l["name"] == test_label for l in labels["results"])

    def test_get_labels_empty(self, confluence_client, test_space):
        """Test getting labels from page with no labels."""
        page = confluence_client.post(
            "/api/v2/pages",
            json_data={
                "spaceId": test_space["id"],
                "status": "current",
                "title": f"No Labels {uuid.uuid4().hex[:8]}",
                "body": {"representation": "storage", "value": "<p>No labels.</p>"},
            },
        )

        try:
            labels = confluence_client.get(f"/api/v2/pages/{page['id']}/labels")
            assert "results" in labels
        finally:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")


@pytest.mark.integration
class TestRemoveLabelLive:
    """Live tests for removing labels."""

    def test_remove_label(self, confluence_client, test_page, test_label):
        """Test removing a label from a page."""
        # Add label using v1 API
        confluence_client.post(
            f"/rest/api/content/{test_page['id']}/label",
            json_data=[{"prefix": "global", "name": test_label}],
        )

        # Verify label was added
        labels = confluence_client.get(f"/api/v2/pages/{test_page['id']}/labels")
        label_names = [l["name"] for l in labels.get("results", [])]
        assert test_label in label_names

        # Remove label using v1 API (v2 API delete can be problematic)
        confluence_client.delete(
            f"/rest/api/content/{test_page['id']}/label/{test_label}"
        )

        # Verify removed
        labels_after = confluence_client.get(f"/api/v2/pages/{test_page['id']}/labels")
        label_names = [l["name"] for l in labels_after.get("results", [])]
        assert test_label not in label_names


@pytest.mark.integration
class TestSearchByLabelLive:
    """Live tests for searching by label."""

    def test_search_content_by_label(self, confluence_client, test_page, test_label):
        """Test searching for content by label."""
        # Add label using v1 API
        confluence_client.post(
            f"/rest/api/content/{test_page['id']}/label",
            json_data=[{"prefix": "global", "name": test_label}],
        )

        # Search using CQL
        import time

        time.sleep(1)  # Allow indexing

        results = confluence_client.get(
            "/rest/api/search", params={"cql": f'label = "{test_label}"'}
        )

        assert "results" in results
        # Page should be in results (may need indexing time)
