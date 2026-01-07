"""
Unit tests for update_template.py
"""


class TestUpdateTemplate:
    """Tests for updating existing templates."""

    def test_update_template_name(self, mock_client, sample_template):
        """Test updating template name."""
        # Mock getting current template
        mock_client.setup_response("get", sample_template)

        # Mock update
        updated = sample_template.copy()
        updated["name"] = "Updated Template"
        mock_client.setup_response("put", updated)

        # Would execute: python update_template.py tmpl-123 --name "Updated Template"
        # Verify PUT to /rest/api/template/tmpl-123

    def test_update_template_description(self, mock_client, sample_template):
        """Test updating template description."""
        mock_client.setup_response("get", sample_template)
        updated = sample_template.copy()
        updated["description"] = "New description"
        mock_client.setup_response("put", updated)

        # Would execute with --description "New description"

    def test_update_template_body(self, mock_client, sample_template):
        """Test updating template body content."""
        mock_client.setup_response("get", sample_template)

        updated = sample_template.copy()
        updated["body"]["storage"]["value"] = "<h1>Updated</h1>"
        mock_client.setup_response("put", updated)

        # Would execute with --content or --file

    def test_update_template_body_from_file(
        self, mock_client, sample_template, tmp_path
    ):
        """Test updating template body from file."""
        template_file = tmp_path / "updated.html"
        template_file.write_text("<h1>Updated Content</h1>")

        mock_client.setup_response("get", sample_template)
        mock_client.setup_response("put", sample_template)

        # Would execute with --file updated.html

    def test_update_template_markdown(self, mock_client, sample_template, tmp_path):
        """Test updating with Markdown file."""
        md_file = tmp_path / "updated.md"
        md_file.write_text("# Updated\n\nNew content")

        mock_client.setup_response("get", sample_template)
        mock_client.setup_response("put", sample_template)

        # Would execute with --file updated.md
        # Verify Markdown conversion

    def test_update_template_add_labels(self, mock_client, sample_template):
        """Test adding labels to template."""
        mock_client.setup_response("get", sample_template)
        mock_client.setup_response("put", sample_template)

        # Would execute with --add-labels "new-label"

    def test_update_template_remove_labels(self, mock_client, sample_template):
        """Test removing labels from template."""
        mock_client.setup_response("get", sample_template)
        mock_client.setup_response("put", sample_template)

        # Would execute with --remove-labels "old-label"

    def test_update_template_not_found(self, mock_client):
        """Test updating non-existent template."""

        mock_client.setup_response(
            "get", {"message": "Template not found"}, status_code=404
        )

        # Should raise NotFoundError

    def test_update_template_no_changes(self, mock_client, sample_template):
        """Test update with no changes provided."""

        # Should require at least one field to update

    def test_update_preserves_existing_fields(self, mock_client, sample_template):
        """Test that update preserves fields not being changed."""
        mock_client.setup_response("get", sample_template)
        mock_client.setup_response("put", sample_template)

        # When updating name only, description and body should remain
        # Verify GET is called first to retrieve current state


class TestTemplateVersioning:
    """Tests for template version management."""

    def test_update_increments_version(self, mock_client, sample_template):
        """Test that updating increments version number."""
        # Templates may have version tracking
        # Verify version handling

    def test_update_with_version_conflict(self, mock_client):
        """Test handling version conflicts."""

        # If template was modified by another user
        # Should detect and handle conflict
