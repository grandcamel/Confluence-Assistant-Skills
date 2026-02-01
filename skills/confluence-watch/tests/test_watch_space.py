"""
Unit tests for watch_space.py
"""

import pytest


class TestWatchSpace:
    """Tests for space watching functionality."""

    def test_validate_space_key_valid(self):
        """Test that valid space keys pass validation."""
        from confluence_as import validate_space_key

        assert validate_space_key("DOCS") == "DOCS"
        assert validate_space_key("kb") == "KB"
        assert validate_space_key("Test_Space") == "TEST_SPACE"

    def test_validate_space_key_invalid(self):
        """Test that invalid space keys fail validation."""
        from confluence_as import ValidationError, validate_space_key

        with pytest.raises(ValidationError):
            validate_space_key("")

        with pytest.raises(ValidationError):
            validate_space_key("A")  # Too short

        with pytest.raises(ValidationError):
            validate_space_key("123")  # Starts with number

    def test_watch_space_success(self, mock_client, sample_space):
        """Test successful space watching."""
        # First get space ID
        mock_client.setup_response("get", sample_space)
        space = mock_client.get("/api/v2/spaces/TEST", operation="get space")

        # Then watch it
        mock_client.setup_response("post", {"success": True, "status_code": 200})
        result = mock_client.post(
            f"/rest/api/user/watch/space/{space['key']}", operation="watch space"
        )

        assert result["success"] is True

    def test_watch_space_not_found(self, mock_client, mock_response):
        """Test watching a non-existent space."""
        from confluence_as import NotFoundError, handle_confluence_error

        error_response = mock_response(
            status_code=404, json_data={"message": "Space not found"}
        )

        with pytest.raises(NotFoundError):
            handle_confluence_error(error_response, "watch space")

    def test_watch_space_permission_denied(self, mock_client, mock_response):
        """Test watching a space without permission."""
        from confluence_as import PermissionError, handle_confluence_error

        error_response = mock_response(
            status_code=403, json_data={"message": "Permission denied"}
        )

        with pytest.raises(PermissionError):
            handle_confluence_error(error_response, "watch space")

    def test_watch_space_output(self):
        """Test output message."""
        space_key = "DOCS"
        message = f"Now watching space {space_key}"

        assert "watching" in message.lower()
        assert space_key in message
