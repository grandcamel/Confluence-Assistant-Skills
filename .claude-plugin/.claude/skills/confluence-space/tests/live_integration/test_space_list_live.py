"""
Live integration tests for space listing operations.

Usage:
    pytest test_space_list_live.py --live -v
"""

import pytest

from confluence_assistant_skills_lib import (
    get_confluence_client,
)


@pytest.fixture(scope="session")
def confluence_client():
    return get_confluence_client()


@pytest.mark.integration
class TestSpaceListLive:
    """Live tests for space listing operations."""

    def test_list_all_spaces(self, confluence_client):
        """Test listing all spaces."""
        spaces = confluence_client.get("/api/v2/spaces", params={"limit": 25})

        assert "results" in spaces
        assert len(spaces["results"]) > 0

    def test_list_spaces_with_pagination(self, confluence_client):
        """Test paginated space listing."""
        page1 = confluence_client.get("/api/v2/spaces", params={"limit": 5})

        assert "results" in page1

        if len(page1.get("results", [])) == 5 and page1.get("_links", {}).get("next"):
            # There's more data
            assert "_links" in page1

    def test_filter_spaces_by_type(self, confluence_client):
        """Test filtering spaces by type."""
        spaces = confluence_client.get(
            "/api/v2/spaces", params={"type": "global", "limit": 10}
        )

        assert "results" in spaces

    def test_space_has_required_fields(self, confluence_client):
        """Test that spaces have required fields."""
        spaces = confluence_client.get("/api/v2/spaces", params={"limit": 5})

        for space in spaces.get("results", []):
            assert "id" in space
            assert "key" in space
            assert "name" in space

    def test_get_space_count(self, confluence_client):
        """Test getting approximate space count."""
        spaces = confluence_client.get("/api/v2/spaces", params={"limit": 250})

        count = len(spaces.get("results", []))
        assert count > 0
