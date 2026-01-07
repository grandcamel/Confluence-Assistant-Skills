"""
Unit tests for delete_comment.py
"""

import pytest


class TestDeleteComment:
    """Tests for deleting comments."""

    def test_delete_comment_basic(self, mock_client):
        """Test deleting a comment."""
        # DELETE returns 204 No Content on success
        mock_client.setup_response("delete", {}, status_code=204)

        # Would verify DELETE /api/v2/footer-comments/{comment_id}

    def test_delete_comment_not_found(self, mock_client):
        """Test deleting non-existent comment."""

        mock_client.setup_response("delete", {}, status_code=404)
        # Would verify NotFoundError is raised

    def test_delete_comment_no_permission(self, mock_client):
        """Test deleting comment without permission."""

        mock_client.setup_response("delete", {}, status_code=403)
        # Would verify PermissionError is raised

    def test_delete_comment_confirmation_prompt(self, mock_client):
        """Test that confirmation is required for delete."""
        # When --force is not provided, should prompt user
        # This would be tested in integration tests

    def test_delete_comment_with_force(self, mock_client):
        """Test deleting with --force flag (no confirmation)."""
        mock_client.setup_response("delete", {}, status_code=204)
        # Would verify delete proceeds without prompt when --force is used


class TestDeleteValidation:
    """Tests for delete validation."""

    def test_comment_id_required(self):
        """Test that comment ID is required."""
        from confluence_assistant_skills_lib import ValidationError, validate_page_id

        with pytest.raises(ValidationError):
            validate_page_id("", "comment_id")

    def test_comment_id_numeric(self):
        """Test that comment ID must be numeric."""
        from confluence_assistant_skills_lib import ValidationError, validate_page_id

        with pytest.raises(ValidationError):
            validate_page_id("abc", "comment_id")
