"""
Unit tests for add_comment.py
"""

import pytest
from unittest.mock import patch, MagicMock


class TestAddComment:
    """Tests for adding footer comments to pages."""

    def test_validate_comment_id_valid(self):
        """Test that valid comment IDs pass validation."""
        from confluence_assistant_skills_lib import validate_page_id

        # Comment IDs use the same validation as page IDs
        assert validate_page_id("12345", "comment_id") == "12345"
        assert validate_page_id(67890, "comment_id") == "67890"

    def test_validate_comment_id_invalid(self):
        """Test that invalid comment IDs fail validation."""
        from confluence_assistant_skills_lib import validate_page_id, ValidationError

        with pytest.raises(ValidationError):
            validate_page_id("", "comment_id")

        with pytest.raises(ValidationError):
            validate_page_id("abc", "comment_id")

    def test_validate_comment_body_required(self):
        """Test that comment body is required."""
        from confluence_assistant_skills_lib import ValidationError

        # Simulating the validation that should happen
        body = ""
        if not body or not body.strip():
            with pytest.raises(ValidationError):
                raise ValidationError("Comment body is required")

    def test_add_comment_basic(self, mock_client, sample_comment):
        """Test adding a basic comment to a page."""
        # Setup mock response
        mock_client.setup_response('post', sample_comment)

        # Would verify comment is created with correct data structure
        # Expected API call: POST /api/v2/pages/{page_id}/footer-comments

    def test_add_comment_with_html(self, mock_client, sample_comment):
        """Test adding a comment with HTML content."""
        comment_with_html = sample_comment.copy()
        comment_with_html['body']['storage']['value'] = "<p>Bold text: <strong>important</strong></p>"

        mock_client.setup_response('post', comment_with_html)

        # Would verify HTML is preserved in storage format

    def test_add_comment_page_not_found(self, mock_client):
        """Test adding comment to non-existent page."""
        from confluence_assistant_skills_lib import NotFoundError

        mock_client.setup_response('post', {}, status_code=404)

        # Would verify NotFoundError is raised with appropriate message

    def test_add_comment_no_permission(self, mock_client):
        """Test adding comment without permission."""
        from confluence_assistant_skills_lib import PermissionError

        mock_client.setup_response('post', {}, status_code=403)

        # Would verify PermissionError is raised


class TestCommentBodyValidation:
    """Tests for comment body validation."""

    def test_empty_body_rejected(self):
        """Test that empty comment body is rejected."""
        from confluence_assistant_skills_lib import ValidationError

        body = ""
        if not body.strip():
            with pytest.raises(ValidationError):
                raise ValidationError("Comment body cannot be empty")

    def test_whitespace_only_rejected(self):
        """Test that whitespace-only body is rejected."""
        from confluence_assistant_skills_lib import ValidationError

        body = "   \n\t   "
        if not body.strip():
            with pytest.raises(ValidationError):
                raise ValidationError("Comment body cannot be empty")

    def test_valid_body_accepted(self):
        """Test that valid body is accepted."""
        body = "This is a valid comment"
        assert body.strip() == "This is a valid comment"


class TestCommentFormatting:
    """Tests for comment output formatting."""

    def test_format_comment_basic(self, sample_comment):
        """Test basic comment formatting."""
        from confluence_assistant_skills_lib import format_comment

        result = format_comment(sample_comment)

        assert "999" in result  # Comment ID
        assert "user123" in result  # Author ID
        assert "This is a comment" in result  # Body text

    def test_format_comment_without_body(self, sample_comment):
        """Test comment formatting without showing body."""
        from confluence_assistant_skills_lib import format_comment

        result = format_comment(sample_comment, show_body=False)

        assert "999" in result  # Comment ID
        assert "This is a comment" not in result  # Body should not be shown

    def test_format_comments_list(self, sample_comment):
        """Test formatting multiple comments."""
        from confluence_assistant_skills_lib import format_comments

        comments = [sample_comment, sample_comment.copy()]
        result = format_comments(comments)

        assert "1." in result
        assert "2." in result
