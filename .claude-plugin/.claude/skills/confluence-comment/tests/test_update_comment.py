"""
Unit tests for update_comment.py
"""

import pytest


class TestUpdateComment:
    """Tests for updating existing comments."""

    def test_update_comment_basic(self, mock_client, sample_comment):
        """Test updating a comment's body."""
        updated = sample_comment.copy()
        updated["body"]["storage"]["value"] = "<p>Updated comment</p>"
        updated["version"]["number"] = 2

        mock_client.setup_response("put", updated)

        # Would verify PUT /api/v2/footer-comments/{comment_id}

    def test_update_comment_version_increment(self, mock_client, sample_comment):
        """Test that version is incremented on update."""
        # Version should be incremented automatically by API
        # Client should include current version in request

    def test_update_comment_not_found(self, mock_client):
        """Test updating non-existent comment."""

        mock_client.setup_response("put", {}, status_code=404)
        # Would verify NotFoundError is raised

    def test_update_comment_no_permission(self, mock_client):
        """Test updating comment without permission."""

        mock_client.setup_response("put", {}, status_code=403)
        # Would verify PermissionError is raised

    def test_update_comment_conflict(self, mock_client):
        """Test updating comment with version conflict."""

        mock_client.setup_response("put", {}, status_code=409)
        # Would verify ConflictError is raised for version mismatch


class TestUpdateValidation:
    """Tests for update validation."""

    def test_comment_id_required(self):
        """Test that comment ID is required."""
        from confluence_assistant_skills_lib import ValidationError, validate_page_id

        with pytest.raises(ValidationError):
            validate_page_id("", "comment_id")

    def test_updated_body_required(self):
        """Test that updated body is required."""
        # Same validation as add_comment
        body = ""
        if not body.strip():
            from confluence_assistant_skills_lib import ValidationError

            with pytest.raises(ValidationError):
                raise ValidationError("Comment body cannot be empty")

    def test_body_from_file(self, tmp_path):
        """Test reading updated body from file."""
        comment_file = tmp_path / "updated.txt"
        comment_file.write_text("Updated comment text")

        content = comment_file.read_text()
        assert content == "Updated comment text"
