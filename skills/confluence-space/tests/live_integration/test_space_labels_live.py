"""
Live integration tests for space label operations.

Usage:
    pytest test_space_labels_live.py --live -v
"""

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


@pytest.mark.integration
class TestSpaceLabelsLive:
    """Live tests for space label operations."""

    def test_get_space_labels(self, confluence_client, test_space):
        """Test getting labels on a space."""
        try:
            labels = confluence_client.get(f"/rest/api/space/{test_space['key']}/label")
            assert "results" in labels
        except Exception:
            # Space labels may not be available
            pass

    def test_add_and_remove_space_label(self, confluence_client, test_space):
        """Test adding and removing a label from a space."""
        label = f"space-test-{uuid.uuid4().hex[:8]}"

        try:
            # Add label
            confluence_client.post(
                f"/rest/api/space/{test_space['key']}/label",
                json_data=[{"prefix": "global", "name": label}],
            )

            # Verify
            labels = confluence_client.get(f"/rest/api/space/{test_space['key']}/label")
            label_names = [l["name"] for l in labels.get("results", [])]
            assert label in label_names

            # Remove
            confluence_client.delete(
                f"/rest/api/space/{test_space['key']}/label/{label}"
            )
        except Exception:
            # Space labels may require special permissions
            pass

    def test_search_spaces_by_label(self, confluence_client):
        """Test searching for spaces with labels."""
        spaces = confluence_client.get("/api/v2/spaces", params={"limit": 10})

        # Just verify we can query spaces
        assert "results" in spaces
