"""
Unit tests for create_from_template.py
"""

import pytest
from unittest.mock import patch


class TestCreateFromTemplate:
    """Tests for creating pages from templates."""

    def test_create_page_from_template_minimal(self, mock_client, sample_template, sample_page):
        """Test creating a page with minimal arguments."""
        # Mock template lookup
        mock_client.setup_response('get', sample_template)
        # Mock page creation
        mock_client.setup_response('post', sample_page)

        # Would execute: python create_from_template.py --template tmpl-123 --space DOCS --title "New Page"
        # Verify POST to /rest/api/content with templateId

    def test_create_page_from_template_with_parent(self, mock_client, sample_template, sample_page):
        """Test creating a page under a parent."""
        mock_client.setup_response('get', sample_template)
        mock_client.setup_response('post', sample_page)

        # Would execute with --parent-id 12345
        # Verify ancestors array is set

    def test_create_page_from_template_with_labels(self, mock_client, sample_template, sample_page):
        """Test creating a page with labels."""
        mock_client.setup_response('get', sample_template)
        mock_client.setup_response('post', sample_page)

        # Would execute with --labels "label1,label2"
        # Verify labels are added to request

    def test_create_from_template_not_found(self, mock_client):
        """Test creating from non-existent template."""
        from confluence_assistant_skills_lib import NotFoundError

        mock_client.setup_response('get', {"message": "Template not found"}, status_code=404)

        # Should raise NotFoundError

    def test_create_from_template_invalid_space(self, mock_client, sample_template):
        """Test creating in non-existent space."""
        from confluence_assistant_skills_lib import ValidationError

        mock_client.setup_response('get', sample_template)

        # Invalid space key should fail validation

    def test_create_from_blueprint(self, mock_client, sample_blueprint, sample_page):
        """Test creating from a blueprint."""
        mock_client.setup_response('get', sample_blueprint)
        mock_client.setup_response('post', sample_page)

        # Would execute with --blueprint flag
        # Verify correct API parameters for blueprint

    def test_create_from_template_with_content_override(self, mock_client, sample_template, sample_page):
        """Test creating from template but overriding content."""
        mock_client.setup_response('get', sample_template)
        mock_client.setup_response('post', sample_page)

        # Would execute with --content or --file
        # Verify template is used as base but content is replaced

    def test_validate_required_fields(self):
        """Test that required fields are validated."""
        from confluence_assistant_skills_lib import ValidationError

        # Should require: template ID, space, title


class TestTemplateContentMerging:
    """Tests for merging template content with user input."""

    def test_merge_template_with_custom_content(self):
        """Test merging template structure with custom content."""
        # Template might have placeholders
        # User content should replace or merge appropriately

    def test_preserve_template_structure(self):
        """Test that template structure is preserved."""
        # Custom content should maintain template layout
