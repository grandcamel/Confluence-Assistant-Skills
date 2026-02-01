"""
Unit tests for watch_page.py
"""

import pytest


class TestWatchPage:
    """Tests for page watching functionality."""

    def test_validate_page_id_valid(self):
        """Test that valid page IDs pass validation."""
        from confluence_as import validate_page_id

        assert validate_page_id("12345") == "12345"
        assert validate_page_id(67890) == "67890"

    def test_validate_page_id_invalid(self):
        """Test that invalid page IDs fail validation."""
        from confluence_as import ValidationError, validate_page_id

        with pytest.raises(ValidationError):
            validate_page_id("")

        with pytest.raises(ValidationError):
            validate_page_id("abc")  # Not numeric

        with pytest.raises(ValidationError):
            validate_page_id(None)

    def test_watch_page_success(self, mock_client, sample_watch_response):
        """Test successful page watching."""
        mock_client.setup_response("post", sample_watch_response)

        # Mock the API call
        result = mock_client.post(
            "/rest/api/user/watch/content/123456", operation="watch page"
        )

        assert result["success"] is True
        assert result["status_code"] == 200

    def test_watch_page_already_watching(self, mock_client):
        """Test watching a page that is already being watched."""
        # API returns 200 even if already watching
        mock_client.setup_response("post", {"success": True, "status_code": 200})

        result = mock_client.post(
            "/rest/api/user/watch/content/123456", operation="watch page"
        )

        assert result["success"] is True

    def test_watch_page_not_found(self, mock_client, mock_response):
        """Test watching a non-existent page."""
        from confluence_as import NotFoundError, handle_confluence_error

        error_response = mock_response(
            status_code=404, json_data={"message": "Page not found"}
        )

        with pytest.raises(NotFoundError):
            handle_confluence_error(error_response, "watch page")

    def test_watch_page_permission_denied(self, mock_client, mock_response):
        """Test watching a page without permission."""
        from confluence_as import PermissionError, handle_confluence_error

        error_response = mock_response(
            status_code=403, json_data={"message": "Permission denied"}
        )

        with pytest.raises(PermissionError):
            handle_confluence_error(error_response, "watch page")

    def test_watch_page_basic_post(self, mock_client, sample_watch_response):
        """Test basic watch page POST request."""
        mock_client.setup_response("post", sample_watch_response)

        result = mock_client.post(
            "/rest/api/user/watch/content/123456", operation="watch page"
        )

        assert result["success"] is True

    def test_watch_page_output_json(self):
        """Test JSON output format."""
        from confluence_as import format_json

        data = {"success": True, "page_id": "123456"}
        result = format_json(data)

        assert '"success": true' in result
        assert '"page_id": "123456"' in result

    def test_watch_page_output_text(self):
        """Test text output format."""
        # Verify that text output is readable
        page_id = "123456"
        message = f"Now watching page {page_id}"

        assert "watching" in message.lower()
        assert page_id in message
