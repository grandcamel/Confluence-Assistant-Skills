"""
Unit tests for add_label.py
"""

import pytest
from unittest.mock import patch, MagicMock


class TestAddLabel:
    """Tests for add label functionality."""

    def test_validate_label_valid(self):
        """Test that valid labels pass validation."""
        from validators import validate_label

        assert validate_label("documentation") == "documentation"
        assert validate_label("APPROVED") == "approved"
        assert validate_label("my-label") == "my-label"
        assert validate_label("test_label") == "test_label"

    def test_validate_label_invalid(self):
        """Test that invalid labels fail validation."""
        from validators import validate_label, ValidationError

        # Empty label
        with pytest.raises(ValidationError):
            validate_label("")

        # Contains spaces
        with pytest.raises(ValidationError):
            validate_label("my label")

        # Too long
        with pytest.raises(ValidationError):
            validate_label("a" * 256)

        # Invalid characters
        with pytest.raises(ValidationError):
            validate_label("label@special")

    def test_add_single_label_success(self, mock_client, sample_page, sample_label):
        """Test successful single label addition."""
        page_id = "123456"
        label_name = "documentation"

        # Setup mock response for adding label
        mock_client.setup_response('post', sample_label)

        # Would verify API call was made correctly
        # result = client.post(f'/api/v2/pages/{page_id}/labels', json_data={'name': label_name})
        # assert result['name'] == label_name

    def test_add_multiple_labels_success(self, mock_client, sample_labels):
        """Test successful multiple label addition."""
        page_id = "123456"
        labels = ["doc", "approved", "v2"]

        # Would verify each label is added
        # For each label in labels, API should be called

    def test_add_label_page_not_found(self, mock_client, mock_response):
        """Test label addition with non-existent page."""
        page_id = "999999"
        label_name = "test"

        # Setup 404 response
        error_response = mock_response(
            status_code=404,
            json_data={"errors": [{"title": "Page not found"}]}
        )
        mock_client.session.post.return_value = error_response

        # Would verify NotFoundError is raised

    def test_add_duplicate_label(self, mock_client, mock_response):
        """Test adding a label that already exists."""
        page_id = "123456"
        label_name = "existing"

        # Confluence typically returns success even if label exists
        # Test should verify idempotent behavior


class TestLabelParsing:
    """Tests for parsing label input."""

    def test_parse_comma_separated_labels(self):
        """Test parsing comma-separated label string."""
        labels_str = "doc,approved,v2"
        labels = [l.strip() for l in labels_str.split(',')]
        assert labels == ["doc", "approved", "v2"]

    def test_parse_single_label(self):
        """Test parsing single label."""
        labels_str = "documentation"
        labels = [l.strip() for l in labels_str.split(',')]
        assert labels == ["documentation"]

    def test_parse_labels_with_spaces(self):
        """Test parsing labels with extra spaces."""
        labels_str = " doc , approved , v2 "
        labels = [l.strip() for l in labels_str.split(',') if l.strip()]
        assert labels == ["doc", "approved", "v2"]
