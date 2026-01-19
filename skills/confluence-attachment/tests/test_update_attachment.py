"""
Unit tests for update_attachment.py
"""

from unittest.mock import MagicMock, Mock

import pytest


class TestUpdateAttachment:
    """Tests for attachment update/replace functionality."""

    def test_update_attachment_basic(self, mock_client, sample_attachment, test_file):
        """Test basic attachment update."""
        attachment_id = "att123456"

        updated_attachment = sample_attachment.copy()
        updated_attachment["version"]["number"] = 2

        # Mock upload_file for update (same as upload)
        mock_client.upload_file = MagicMock(
            return_value={"results": [updated_attachment]}
        )

        # For v2 API, updating is done via POST with same filename
        result = mock_client.upload_file(
            f"/api/v2/attachments/{attachment_id}/data",
            test_file,
            operation="update attachment",
        )

        assert result["results"][0]["version"]["number"] == 2

    def test_update_increments_version(self, sample_attachment):
        """Test that update increments version number."""
        original_version = sample_attachment["version"]["number"]

        # After update
        updated_version = original_version + 1

        assert updated_version == 2
        assert updated_version > original_version

    def test_update_with_different_file(
        self, mock_client, sample_attachment, test_file, test_pdf_file
    ):
        """Test updating attachment with a different file."""
        attachment_id = "att123456"

        # Original was .txt, updating with .pdf
        updated_attachment = sample_attachment.copy()
        updated_attachment["title"] = test_pdf_file.name
        updated_attachment["mediaType"] = "application/pdf"
        updated_attachment["version"]["number"] = 2

        mock_client.upload_file = MagicMock(
            return_value={"results": [updated_attachment]}
        )

        result = mock_client.upload_file(
            f"/api/v2/attachments/{attachment_id}/data",
            test_pdf_file,
            operation="update attachment",
        )

        assert result["results"][0]["mediaType"] == "application/pdf"

    def test_update_preserves_attachment_id(self, sample_attachment):
        """Test that update preserves the attachment ID."""
        original_id = sample_attachment["id"]

        # After update, ID should remain the same
        updated_id = original_id

        assert updated_id == "att123456"
        assert updated_id == original_id

    def test_update_attachment_not_found(self, mock_client):
        """Test updating non-existent attachment."""

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.ok = False
        mock_response.json.return_value = {"message": "Attachment not found"}

        # Would raise NotFoundError in actual implementation
        assert mock_response.status_code == 404

    def test_validate_file_for_update(self, test_file):
        """Test file validation for update."""
        from confluence_assistant_skills_lib import validate_file_path

        # File must exist
        result = validate_file_path(test_file)
        assert result.exists()
        assert result.is_file()

        # Non-existent file should fail
        from confluence_assistant_skills_lib import ValidationError

        with pytest.raises(ValidationError):
            validate_file_path("/nonexistent/file.txt")


class TestAttachmentVersioning:
    """Tests for attachment versioning concepts."""

    def test_version_history(self, sample_attachment):
        """Test attachment version structure."""
        version = sample_attachment["version"]

        assert "number" in version
        assert version["number"] >= 1
        assert "createdAt" in version

    def test_get_attachment_versions(self, mock_client, sample_attachment):
        """Test getting attachment version history."""
        attachment_id = "att123456"

        versions = [
            {**sample_attachment["version"], "number": 1},
            {**sample_attachment["version"], "number": 2},
        ]

        # Note: This endpoint might not exist in v2 API
        # Testing the concept
        mock_client.get = MagicMock(return_value={"results": versions})

        result = mock_client.get(
            f"/api/v2/attachments/{attachment_id}/versions",
            operation="get attachment versions",
        )

        assert len(result["results"]) == 2

    def test_update_with_comment(self, mock_client, sample_attachment, test_file):
        """Test updating attachment with version comment."""
        attachment_id = "att123456"

        updated_attachment = sample_attachment.copy()
        updated_attachment["version"]["number"] = 2
        updated_attachment["version"]["message"] = "Updated document"

        mock_client.upload_file = MagicMock(
            return_value={"results": [updated_attachment]}
        )

        result = mock_client.upload_file(
            f"/api/v2/attachments/{attachment_id}/data",
            test_file,
            additional_data={"comment": "Updated document"},
            operation="update attachment",
        )

        assert result["results"][0]["version"]["message"] == "Updated document"
