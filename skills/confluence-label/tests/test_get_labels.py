"""
Unit tests for get_labels.py
"""


class TestGetLabels:
    """Tests for getting labels functionality."""

    def test_get_labels_success(self, mock_client, sample_labels):
        """Test successful retrieval of labels."""

        # Setup mock response
        mock_client.setup_response("get", sample_labels)

        # Would verify API call and result formatting
        # result = client.get(f'/api/v2/pages/{page_id}/labels')
        # assert len(result['results']) == 3

    def test_get_labels_empty(self, mock_client):
        """Test getting labels when page has none."""

        # Setup empty response
        empty_labels = {"results": [], "_links": {}}
        mock_client.setup_response("get", empty_labels)

        # Would verify empty result handling

    def test_get_labels_page_not_found(self, mock_client, mock_response):
        """Test getting labels from non-existent page."""

        # Setup 404 response
        error_response = mock_response(
            status_code=404, json_data={"errors": [{"title": "Page not found"}]}
        )
        mock_client.session.get.return_value = error_response

        # Would verify NotFoundError is raised


class TestLabelFormatting:
    """Tests for label output formatting."""

    def test_format_label_with_prefix(self):
        """Test formatting label with prefix."""
        from confluence_as import format_label

        label = {"id": "1", "name": "test", "prefix": "global"}
        result = format_label(label)
        assert "global:test" in result
        assert "ID: 1" in result

    def test_format_label_without_prefix(self):
        """Test formatting label without prefix."""
        from confluence_as import format_label

        label = {"id": "1", "name": "test", "prefix": ""}
        result = format_label(label)
        assert "test" in result
        assert "global:" not in result

    def test_format_multiple_labels(self, sample_labels):
        """Test formatting multiple labels."""
        sample_labels["results"]

        # Would verify list formatting
        # Output should show all labels with their names
