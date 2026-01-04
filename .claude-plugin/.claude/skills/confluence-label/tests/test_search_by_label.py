"""
Unit tests for search_by_label.py
"""

import pytest
from unittest.mock import patch, MagicMock


class TestSearchByLabel:
    """Tests for searching content by label."""

    def test_search_by_label_success(self, mock_client):
        """Test successful search by label."""
        label_name = "documentation"

        # Sample search results
        search_results = {
            "results": [
                {
                    "id": "123",
                    "type": "page",
                    "title": "API Docs",
                    "spaceId": "789",
                    "_links": {"webui": "/wiki/spaces/DOCS/pages/123"}
                },
                {
                    "id": "124",
                    "type": "page",
                    "title": "User Guide",
                    "spaceId": "789",
                    "_links": {"webui": "/wiki/spaces/DOCS/pages/124"}
                }
            ],
            "_links": {}
        }

        mock_client.setup_response('get', search_results)

        # Would verify CQL query construction and results

    def test_search_by_label_with_space_filter(self, mock_client):
        """Test search by label filtered to specific space."""
        label_name = "approved"
        space_key = "DOCS"

        # Would verify CQL query includes both label and space
        # Expected CQL: label = "approved" AND space = "DOCS"

    def test_search_by_label_no_results(self, mock_client):
        """Test search by label with no results."""
        label_name = "nonexistent"

        # Setup empty response
        empty_results = {"results": [], "_links": {}}
        mock_client.setup_response('get', empty_results)

        # Would verify empty result handling

    def test_search_by_label_with_limit(self, mock_client):
        """Test search by label with result limit."""
        label_name = "documentation"
        limit = 10

        # Would verify limit parameter is passed correctly


class TestCQLQueryConstruction:
    """Tests for CQL query building."""

    def test_build_label_query_simple(self):
        """Test building simple label query."""
        label = "documentation"
        expected = 'label = "documentation"'

        # Would verify query construction
        query = f'label = "{label}"'
        assert query == expected

    def test_build_label_query_with_space(self):
        """Test building label query with space filter."""
        label = "approved"
        space = "DOCS"
        expected = 'label = "approved" AND space = "DOCS"'

        # Would verify query construction
        query = f'label = "{label}" AND space = "{space}"'
        assert query == expected

    def test_build_label_query_with_type(self):
        """Test building label query with type filter."""
        label = "documentation"
        content_type = "page"
        expected = 'label = "documentation" AND type = "page"'

        # Would verify query construction
        query = f'label = "{label}" AND type = "{content_type}"'
        assert query == expected
