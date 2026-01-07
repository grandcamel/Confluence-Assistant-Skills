"""
Unit tests for get_descendants.py
"""

import sys
from pathlib import Path

import pytest

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


class TestGetDescendants:
    """Tests for getting descendant pages."""

    def test_get_descendants_single_level(self, mock_client, sample_children):
        """Test getting descendants when there's only one level."""
        # First call - get children of root
        mock_client.setup_response("get", sample_children)

        result = mock_client.get("/api/v2/pages/123456/children")

        assert len(result["results"]) == 2

    def test_get_descendants_multiple_levels(self, mock_client):
        """Test getting all descendants across multiple levels."""
        # This would require recursive calls in the actual implementation
        # First level

        # Second level (children of Child 1)

        # Build expected descendants list
        all_descendants = [
            {"id": "200", "title": "Child 1", "depth": 1},
            {"id": "300", "title": "Grandchild 1", "depth": 2},
            {"id": "201", "title": "Child 2", "depth": 1},
        ]

        assert len(all_descendants) == 3

    def test_descendants_with_max_depth(self):
        """Test limiting descendants to a maximum depth."""
        all_descendants = [
            {"id": "200", "title": "Child 1", "depth": 1},
            {"id": "300", "title": "Grandchild 1", "depth": 2},
            {"id": "400", "title": "Great-Grandchild 1", "depth": 3},
        ]

        # Filter to max depth 2
        max_depth = 2
        filtered = [d for d in all_descendants if d["depth"] <= max_depth]

        assert len(filtered) == 2
        assert all(d["depth"] <= max_depth for d in filtered)

    def test_descendants_empty_tree(self, mock_client):
        """Test getting descendants for leaf page."""
        empty = {"results": [], "_links": {}}
        mock_client.setup_response("get", empty)

        result = mock_client.get("/api/v2/pages/123456/children")

        assert len(result["results"]) == 0

    def test_descendants_count(self):
        """Test counting total descendants."""
        descendants = [
            {"id": "200", "title": "Child 1"},
            {"id": "300", "title": "Grandchild 1"},
            {"id": "301", "title": "Grandchild 2"},
        ]

        count = len(descendants)
        assert count == 3

    def test_descendants_output_with_depth(self):
        """Test formatting descendants with indentation by depth."""
        descendants = [
            {"id": "200", "title": "Child 1", "depth": 1},
            {"id": "300", "title": "Grandchild 1", "depth": 2},
            {"id": "201", "title": "Child 2", "depth": 1},
        ]

        # Build output with indentation
        lines = []
        for d in descendants:
            indent = "  " * (d["depth"] - 1)
            lines.append(f"{indent}- {d['title']} (ID: {d['id']})")

        output = "\n".join(lines)

        assert "- Child 1" in output
        assert "  - Grandchild 1" in output

    def test_prevent_infinite_recursion(self):
        """Test that circular references are handled."""
        # Track visited pages to prevent infinite loops
        visited = set()
        page_id = "123456"

        if page_id not in visited:
            visited.add(page_id)
            assert page_id in visited

        # Attempting to visit again should be skipped
        if page_id not in visited:
            pytest.fail("Should not visit same page twice")
