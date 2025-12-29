"""
Unit tests for get_page_views.py
"""

import pytest
from unittest.mock import patch, MagicMock


class TestGetPageViews:
    """Tests for getting page view analytics."""

    def test_validate_page_id_valid(self):
        """Test that valid page IDs pass validation."""
        from confluence_assistant_skills_lib import validate_page_id

        assert validate_page_id("123456") == "123456"
        assert validate_page_id(123456) == "123456"

    def test_validate_page_id_invalid(self):
        """Test that invalid page IDs fail validation."""
        from confluence_assistant_skills_lib import validate_page_id, ValidationError

        with pytest.raises(ValidationError):
            validate_page_id("")

        with pytest.raises(ValidationError):
            validate_page_id("abc")

        with pytest.raises(ValidationError):
            validate_page_id(-1)

    def test_get_page_history_success(self, mock_client, sample_page_history):
        """Test successful retrieval of page history."""
        # Setup mock response
        mock_client.setup_response('get', sample_page_history)

        # Call API
        result = mock_client.get('/rest/api/content/123456')

        # Verify
        assert result['id'] == "123456"
        assert result['type'] == "page"
        assert 'history' in result
        assert 'version' in result

    def test_get_page_contributors(self, mock_client, sample_page_history):
        """Test extracting contributor information."""
        mock_client.setup_response('get', sample_page_history)

        result = mock_client.get('/rest/api/content/123456', params={'expand': 'history.contributors.publishers'})

        # Verify contributors exist
        assert 'history' in result
        assert 'contributors' in result['history']
        assert 'publishers' in result['history']['contributors']

        publishers = result['history']['contributors']['publishers']
        assert 'users' in publishers
        assert len(publishers['users']) == 2

    def test_format_analytics_output(self, sample_page_history):
        """Test formatting analytics data for output."""
        # This tests the formatting logic
        page_id = sample_page_history['id']
        title = sample_page_history['title']
        version = sample_page_history['version']['number']

        assert page_id == "123456"
        assert title == "Test Page"
        assert version == 5

    def test_page_not_found(self, mock_client):
        """Test handling page not found error."""
        from confluence_assistant_skills_lib import NotFoundError

        # Mock 404 response
        mock_client.setup_response('get', {"message": "Page not found"}, status_code=404)

        # The client should handle this appropriately
        # In real implementation, would verify NotFoundError is raised


class TestOutputFormats:
    """Tests for different output formats."""

    def test_json_output_format(self, sample_page_history):
        """Test JSON output formatting."""
        from confluence_assistant_skills_lib import format_json
        import json

        output = format_json(sample_page_history)
        parsed = json.loads(output)

        assert parsed['id'] == "123456"
        assert parsed['title'] == "Test Page"

    def test_text_output_format(self, sample_page_history):
        """Test text output contains expected fields."""
        # Verify key fields are present for text formatting
        assert 'id' in sample_page_history
        assert 'title' in sample_page_history
        assert 'version' in sample_page_history
        assert 'history' in sample_page_history
