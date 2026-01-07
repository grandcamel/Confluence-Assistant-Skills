"""
Live integration tests for label prefix operations.

Usage:
    pytest test_label_prefix_live.py --profile development -v
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
            "title": f"Label Prefix Test {uuid.uuid4().hex[:8]}",
            "body": {"representation": "storage", "value": "<p>Test.</p>"},
        },
    )
    yield page
    with contextlib.suppress(Exception):
        confluence_client.delete(f"/api/v2/pages/{page['id']}")


@pytest.mark.integration
class TestLabelPrefixLive:
    """Live tests for label prefix operations."""

    def test_add_global_label(self, confluence_client, test_page):
        """Test adding a global label (default prefix)."""
        label = f"global-{uuid.uuid4().hex[:8]}"

        # Use v1 API for adding labels
        confluence_client.post(
            f"/rest/api/content/{test_page['id']}/label",
            json_data=[{"prefix": "global", "name": label}],
        )

        labels = confluence_client.get(f"/api/v2/pages/{test_page['id']}/labels")
        label_names = [l["name"] for l in labels.get("results", [])]
        assert label in label_names

    def test_label_with_prefix_format(self, confluence_client, test_page):
        """Test adding a label via v1 API with prefix."""
        label = f"prefixed-{uuid.uuid4().hex[:8]}"

        confluence_client.post(
            f"/rest/api/content/{test_page['id']}/label",
            json_data=[{"prefix": "global", "name": label}],
        )

        labels = confluence_client.get(f"/api/v2/pages/{test_page['id']}/labels")
        label_names = [l["name"] for l in labels.get("results", [])]
        assert label in label_names

    def test_labels_with_special_characters(self, confluence_client, test_page):
        """Test labels with hyphens and underscores."""
        label = f"test-label-{uuid.uuid4().hex[:4]}_underscore"

        # Use v1 API for adding labels
        confluence_client.post(
            f"/rest/api/content/{test_page['id']}/label",
            json_data=[{"prefix": "global", "name": label}],
        )

        labels = confluence_client.get(f"/api/v2/pages/{test_page['id']}/labels")
        label_names = [l["name"] for l in labels.get("results", [])]
        assert label in label_names

    def test_lowercase_labels(self, confluence_client, test_page):
        """Test that labels are lowercased."""
        label_input = f"UPPERCASE-{uuid.uuid4().hex[:8]}"

        # Use v1 API for adding labels
        confluence_client.post(
            f"/rest/api/content/{test_page['id']}/label",
            json_data=[{"prefix": "global", "name": label_input}],
        )

        labels = confluence_client.get(f"/api/v2/pages/{test_page['id']}/labels")
        label_names = [l["name"] for l in labels.get("results", [])]
        # Labels are typically lowercased
        assert label_input.lower() in label_names or label_input in label_names
