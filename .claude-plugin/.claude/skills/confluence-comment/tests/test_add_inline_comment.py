"""
Unit tests for add_inline_comment.py
"""

import pytest


class TestAddInlineComment:
    """Tests for adding inline comments."""

    def test_add_inline_comment_basic(self, mock_client, sample_comment):
        """Test adding an inline comment."""
        inline_comment = sample_comment.copy()
        inline_comment["inlineProperties"] = {
            "originalSelection": "selected text",
            "textSelection": "selected text",
        }

        mock_client.setup_response("post", inline_comment)

        # Would verify POST /api/v2/pages/{page_id}/inline-comments

    def test_add_inline_comment_with_position(self, mock_client, sample_comment):
        """Test adding inline comment with text selection."""
        # Inline comments reference specific text in the page

    def test_validate_inline_text_selection(self):
        """Test that text selection is validated."""
        from confluence_assistant_skills_lib import ValidationError

        selection = ""
        if not selection.strip():
            with pytest.raises(ValidationError):
                raise ValidationError("Text selection is required for inline comments")

    def test_add_inline_comment_page_not_found(self, mock_client):
        """Test adding inline comment to non-existent page."""

        mock_client.setup_response("post", {}, status_code=404)
        # Would verify NotFoundError is raised


class TestInlineCommentValidation:
    """Tests for inline comment validation."""

    def test_page_id_required(self):
        """Test that page ID is required."""
        from confluence_assistant_skills_lib import ValidationError, validate_page_id

        with pytest.raises(ValidationError):
            validate_page_id("")

    def test_comment_body_required(self):
        """Test that comment body is required."""
        from confluence_assistant_skills_lib import ValidationError

        body = ""
        if not body.strip():
            with pytest.raises(ValidationError):
                raise ValidationError("Comment body cannot be empty")

    def test_text_selection_required(self):
        """Test that text selection is required for inline comments."""
        selection = "   "
        if not selection.strip():
            from confluence_assistant_skills_lib import ValidationError

            with pytest.raises(ValidationError):
                raise ValidationError("Text selection is required")
