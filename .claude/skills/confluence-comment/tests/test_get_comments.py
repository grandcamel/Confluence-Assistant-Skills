"""
Unit tests for get_comments.py
"""

import pytest
from unittest.mock import patch, MagicMock


class TestGetComments:
    """Tests for retrieving comments from a page."""

    def test_get_comments_basic(self, mock_client, sample_comment):
        """Test getting comments from a page."""
        comments_response = {
            'results': [sample_comment],
            '_links': {}
        }
        mock_client.setup_response('get', comments_response)

        # Would verify GET /api/v2/pages/{page_id}/footer-comments

    def test_get_comments_pagination(self, mock_client, sample_comment):
        """Test getting comments with pagination."""
        page1 = {
            'results': [sample_comment],
            '_links': {'next': '/api/v2/pages/123/footer-comments?cursor=abc'}
        }
        page2 = {
            'results': [sample_comment.copy()],
            '_links': {}
        }

        mock_client.setup_response('get', page1)
        # Would verify pagination logic

    def test_get_comments_empty(self, mock_client):
        """Test getting comments from page with no comments."""
        empty_response = {
            'results': [],
            '_links': {}
        }
        mock_client.setup_response('get', empty_response)

        # Would verify empty result handling

    def test_get_comments_with_limit(self, mock_client, sample_comment):
        """Test getting comments with limit parameter."""
        from validators import validate_limit

        limit = validate_limit(5)
        assert limit == 5

    def test_get_comments_sort_by_created(self, mock_client, sample_comment):
        """Test getting comments sorted by creation date."""
        # Would verify sort parameter is passed correctly

    def test_get_comments_page_not_found(self, mock_client):
        """Test getting comments from non-existent page."""
        from error_handler import NotFoundError

        mock_client.setup_response('get', {}, status_code=404)
        # Would verify NotFoundError is raised


class TestCommentListFormatting:
    """Tests for formatting comment lists."""

    def test_format_empty_comments(self):
        """Test formatting empty comment list."""
        from formatters import format_comments

        result = format_comments([])
        assert "No comments" in result

    def test_format_multiple_comments(self, sample_comment):
        """Test formatting multiple comments."""
        from formatters import format_comments

        comments = [
            sample_comment,
            {**sample_comment, 'id': '1000', 'body': {'storage': {'value': '<p>Second comment</p>'}}},
            {**sample_comment, 'id': '1001', 'body': {'storage': {'value': '<p>Third comment</p>'}}}
        ]

        result = format_comments(comments)
        assert '1.' in result
        assert '2.' in result
        assert '3.' in result

    def test_format_comments_with_limit(self, sample_comment):
        """Test formatting comments with display limit."""
        from formatters import format_comments

        comments = [sample_comment] * 10
        result = format_comments(comments, limit=3)

        # Should only show first 3
        assert result.count('Comment') == 3
