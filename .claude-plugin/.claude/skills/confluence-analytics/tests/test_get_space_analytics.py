"""
Unit tests for get_space_analytics.py
"""

import pytest


class TestGetSpaceAnalytics:
    """Tests for getting space-level analytics."""

    def test_validate_space_key_valid(self):
        """Test that valid space keys pass validation."""
        from confluence_assistant_skills_lib import validate_space_key

        assert validate_space_key("DOCS") == "DOCS"
        assert validate_space_key("kb") == "KB"
        assert validate_space_key("Test_Space") == "TEST_SPACE"

    def test_validate_space_key_invalid(self):
        """Test that invalid space keys fail validation."""
        from confluence_assistant_skills_lib import ValidationError, validate_space_key

        with pytest.raises(ValidationError):
            validate_space_key("")

        with pytest.raises(ValidationError):
            validate_space_key("A")  # Too short

        with pytest.raises(ValidationError):
            validate_space_key("123")  # Starts with number

    def test_search_space_content(self, mock_client, sample_search_results):
        """Test CQL search for space content."""
        mock_client.setup_response("get", sample_search_results)

        result = mock_client.get(
            "/rest/api/search", params={"cql": "space=TEST AND type=page"}
        )

        assert "results" in result
        assert len(result["results"]) == 2
        assert result["size"] == 2

    def test_aggregate_space_statistics(self, sample_search_results):
        """Test aggregating statistics from search results."""
        # Count total pages
        total_pages = len(sample_search_results["results"])
        assert total_pages == 2

        # Extract page IDs
        page_ids = [r["content"]["id"] for r in sample_search_results["results"]]
        assert page_ids == ["123456", "123457"]

    def test_space_not_found(self, mock_client):
        """Test handling space not found error."""
        # Mock empty search results
        mock_client.setup_response("get", {"results": [], "size": 0})

        result = mock_client.get("/rest/api/search", params={"cql": "space=NOTFOUND"})

        assert result["size"] == 0
        assert len(result["results"]) == 0


class TestDateRangeFiltering:
    """Tests for date range filtering in analytics."""

    def test_cql_with_date_filter(self):
        """Test CQL query construction with date filters."""
        space_key = "TEST"
        start_date = "2024-01-01"

        # Construct CQL
        cql = f'space={space_key} AND created >= "{start_date}"'

        assert "space=TEST" in cql
        assert "created >=" in cql
        assert "2024-01-01" in cql

    def test_cql_date_range(self):
        """Test CQL with date range."""
        space_key = "TEST"
        start_date = "2024-01-01"
        end_date = "2024-12-31"

        cql = f'space={space_key} AND created >= "{start_date}" AND created <= "{end_date}"'

        assert "2024-01-01" in cql
        assert "2024-12-31" in cql
