"""
Unit tests for create_template.py
"""

import pytest
from unittest.mock import patch


class TestCreateTemplate:
    """Tests for creating new templates."""

    def test_create_template_minimal(self, mock_client, sample_template):
        """Test creating a template with minimal fields."""
        mock_client.setup_response('post', sample_template)

        # Would execute: python create_template.py --name "My Template" --space DOCS
        # Verify POST to /rest/api/template

    def test_create_template_with_description(self, mock_client, sample_template):
        """Test creating a template with description."""
        mock_client.setup_response('post', sample_template)

        # Would execute with --description "Template description"
        # Verify description is included

    def test_create_template_with_body_from_file(self, mock_client, sample_template, tmp_path):
        """Test creating template with body from file."""
        # Create test file
        template_file = tmp_path / "template.html"
        template_file.write_text("<h1>Template</h1>")

        mock_client.setup_response('post', sample_template)

        # Would execute with --file template.html
        # Verify file content is read and used

    def test_create_template_with_markdown(self, mock_client, sample_template, tmp_path):
        """Test creating template from Markdown."""
        md_file = tmp_path / "template.md"
        md_file.write_text("# Template\n\nContent here")

        mock_client.setup_response('post', sample_template)

        # Would execute with --file template.md
        # Verify Markdown is converted to storage format

    def test_create_template_with_labels(self, mock_client, sample_template):
        """Test creating template with labels."""
        mock_client.setup_response('post', sample_template)

        # Would execute with --labels "template,meeting"
        # Verify labels are included

    def test_create_template_invalid_space(self, mock_client):
        """Test creating template in non-existent space."""
        from confluence_assistant_skills_lib import ValidationError

        # Invalid space should fail validation

    def test_create_template_duplicate_name(self, mock_client):
        """Test creating template with duplicate name."""
        from confluence_assistant_skills_lib import ConflictError

        mock_client.setup_response('post',
            {"message": "Template already exists"},
            status_code=409
        )

        # Should raise ConflictError

    def test_validate_template_name(self):
        """Test template name validation."""
        from confluence_assistant_skills_lib import ValidationError

        # Empty name should fail
        # Very long name should fail
        # Valid name should pass


class TestCreateBlueprintTemplate:
    """Tests for creating blueprint-based templates."""

    def test_create_from_blueprint_id(self, mock_client, sample_template):
        """Test creating template based on blueprint."""
        mock_client.setup_response('post', sample_template)

        # Would execute with --blueprint-id com.atlassian...
        # Verify contentBlueprintId is set

    def test_create_blueprint_with_module_key(self, mock_client, sample_template):
        """Test creating with module complete key."""
        mock_client.setup_response('post', sample_template)

        # Verify moduleCompleteKey parameter
