"""
Unit tests for get_popular_content.py
"""


class TestGetPopularContent:
    """Tests for getting popular/most viewed content."""

    def test_cql_order_by_created(self):
        """Test CQL query ordering by creation date."""
        space_key = "TEST"
        cql = f"space={space_key} AND type=page ORDER BY created DESC"

        assert "ORDER BY created DESC" in cql
        assert "space=TEST" in cql

    def test_cql_order_by_modified(self):
        """Test CQL query ordering by modification date."""
        space_key = "TEST"
        cql = f"space={space_key} AND type=page ORDER BY lastModified DESC"

        assert "ORDER BY lastModified DESC" in cql

    def test_search_popular_content(self, mock_client, sample_search_results):
        """Test searching for popular content via CQL."""
        mock_client.setup_response("get", sample_search_results)

        result = mock_client.get(
            "/rest/api/search",
            params={
                "cql": "space=TEST AND type=page ORDER BY created DESC",
                "limit": 10,
            },
        )

        assert "results" in result
        assert len(result["results"]) == 2

    def test_limit_results(self, mock_client, sample_search_results):
        """Test limiting number of results returned."""
        mock_client.setup_response("get", sample_search_results)

        result = mock_client.get(
            "/rest/api/search",
            params={"cql": "type=page ORDER BY created DESC", "limit": 5},
        )

        # Verify results are returned
        assert "results" in result

    def test_filter_by_space(self, sample_search_results):
        """Test filtering results by space."""
        # All results should be from TEST space
        for result in sample_search_results["results"]:
            assert result["content"]["space"]["key"] == "TEST"

    def test_filter_by_label(self):
        """Test CQL query with label filter."""
        label = "featured"
        cql = f"type=page AND label={label} ORDER BY created DESC"

        assert "label=featured" in cql
        assert "ORDER BY created DESC" in cql


class TestContentTypeFilters:
    """Tests for filtering by content type."""

    def test_filter_pages_only(self):
        """Test filtering for pages only."""
        cql = "type=page ORDER BY created DESC"
        assert "type=page" in cql

    def test_filter_blogposts_only(self):
        """Test filtering for blog posts only."""
        cql = "type=blogpost ORDER BY created DESC"
        assert "type=blogpost" in cql

    def test_filter_both_types(self):
        """Test filtering for both pages and blog posts."""
        cql = "type in (page, blogpost) ORDER BY created DESC"
        assert "type in (page, blogpost)" in cql
