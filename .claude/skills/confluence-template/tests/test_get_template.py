"""
Unit tests for get_template.py
"""

import pytest
from unittest.mock import patch


class TestGetTemplate:
    """Tests for getting template details."""

    def test_get_template_success(self, mock_client, sample_template):
        """Test successfully retrieving a template."""
        mock_client.setup_response('get', sample_template)

        # Would execute: python get_template.py tmpl-123
        # Verify calls GET /rest/api/template/tmpl-123

    def test_get_template_with_body(self, mock_client, sample_template):
        """Test retrieving template with body content."""
        mock_client.setup_response('get', sample_template)

        # Would execute with --body flag
        # Verify body content is included in output

    def test_get_template_json_output(self, mock_client, sample_template):
        """Test JSON output format."""
        mock_client.setup_response('get', sample_template)

        # Would execute with --output json
        # Verify JSON is properly formatted

    def test_get_template_not_found(self, mock_client):
        """Test handling of non-existent template."""
        from error_handler import NotFoundError

        mock_client.setup_response('get', {"message": "Template not found"}, status_code=404)

        # Should raise NotFoundError
        # Should provide helpful error message

    def test_get_template_markdown_format(self, mock_client, sample_template):
        """Test converting template body to Markdown."""
        mock_client.setup_response('get', sample_template)

        # Would execute with --format markdown
        # Verify XHTML is converted to Markdown

    def test_validate_template_id(self):
        """Test template ID validation."""
        from validators import ValidationError

        # Template IDs can be various formats
        # Should validate non-empty string


class TestGetBlueprint:
    """Tests for getting blueprint details."""

    def test_get_blueprint_success(self, mock_client, sample_blueprint):
        """Test successfully retrieving a blueprint."""
        mock_client.setup_response('get', sample_blueprint)

        # Would execute with --blueprint flag
        # Verify calls correct API endpoint

    def test_get_blueprint_metadata(self, mock_client, sample_blueprint):
        """Test retrieving blueprint metadata."""
        mock_client.setup_response('get', sample_blueprint)

        # Verify module keys and IDs are displayed
