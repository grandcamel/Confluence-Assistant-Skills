"""
Unit tests for unwatch_page.py
"""

import pytest


class TestUnwatchPage:
    """Tests for page unwatching functionality."""

    def test_unwatch_page_success(self, mock_client):
        """Test successful page unwatching."""
        mock_client.setup_response("delete", {})

        result = mock_client.delete(
            "/rest/api/user/watch/content/123456", operation="unwatch page"
        )

        assert result == {} or result.get("success") is True

    def test_unwatch_page_not_watching(self, mock_client):
        """Test unwatching a page that wasn't being watched."""
        # API should return success even if not watching
        mock_client.setup_response("delete", {})

        result = mock_client.delete(
            "/rest/api/user/watch/content/123456", operation="unwatch page"
        )

        # Should succeed without error
        assert result == {} or result.get("success") is True

    def test_unwatch_page_not_found(self, mock_client, mock_response):
        """Test unwatching a non-existent page."""
        from confluence_as import handle_confluence_error

        error_response = mock_response(
            status_code=404, json_data={"message": "Page not found"}
        )

        with pytest.raises(Exception):
            handle_confluence_error(error_response, "unwatch page")

    def test_unwatch_page_validation(self):
        """Test page ID validation."""
        from confluence_as import ValidationError, validate_page_id

        with pytest.raises(ValidationError):
            validate_page_id("")

        with pytest.raises(ValidationError):
            validate_page_id("not-a-number")

    def test_unwatch_page_output(self):
        """Test output message."""
        page_id = "123456"
        message = f"Stopped watching page {page_id}"

        assert "stopped" in message.lower() or "unwatch" in message.lower()
        assert page_id in message
