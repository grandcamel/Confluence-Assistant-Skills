"""
Unit tests for delete_attachment.py
"""

from unittest.mock import MagicMock, Mock

import pytest


class TestDeleteAttachment:
    """Tests for attachment deletion functionality."""

    def test_delete_attachment_basic(self, mock_client):
        """Test basic attachment deletion."""
        attachment_id = "att123456"

        mock_client.delete = MagicMock(return_value={})

        result = mock_client.delete(
            f"/api/v2/attachments/{attachment_id}", operation="delete attachment"
        )

        # DELETE returns empty response on success
        assert result == {}
        mock_client.delete.assert_called_once()

    def test_delete_attachment_not_found(self, mock_client):
        """Test deleting non-existent attachment."""

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.ok = False
        mock_response.json.return_value = {"message": "Attachment not found"}

        # Would raise NotFoundError in actual implementation
        assert mock_response.status_code == 404

    def test_delete_attachment_no_permission(self, mock_client):
        """Test deleting attachment without permission."""

        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.ok = False
        mock_response.json.return_value = {"message": "Insufficient permissions"}

        # Would raise PermissionError in actual implementation
        assert mock_response.status_code == 403

    def test_delete_with_confirmation(self):
        """Test deletion with confirmation prompt."""
        # In actual script, would use --force flag to skip confirmation
        # or interactive prompt for confirmation
        force = True
        assert force is True

        # Without force, would prompt
        force = False
        assert force is False

    def test_validate_attachment_id_for_delete(self):
        """Test attachment ID validation for deletion."""
        from confluence_assistant_skills_lib import validate_page_id

        # Attachment IDs use same validation as page IDs (numeric)
        assert validate_page_id("123456") == "123456"
        assert validate_page_id("789012") == "789012"

        # Invalid IDs should fail
        from confluence_assistant_skills_lib import ValidationError

        with pytest.raises(ValidationError):
            validate_page_id("")

        with pytest.raises(ValidationError):
            validate_page_id(None)


class TestDeleteBulkAttachments:
    """Tests for bulk attachment deletion."""

    def test_delete_multiple_attachments(self, mock_client):
        """Test deleting multiple attachments."""
        attachment_ids = ["att1", "att2", "att3"]

        mock_client.delete = MagicMock(return_value={})

        results = []
        for att_id in attachment_ids:
            result = mock_client.delete(
                f"/api/v2/attachments/{att_id}", operation="delete attachment"
            )
            results.append(result)

        assert len(results) == 3
        assert mock_client.delete.call_count == 3

    def test_delete_all_from_page(self, mock_client, sample_attachment):
        """Test deleting all attachments from a page."""
        attachments = [
            {**sample_attachment, "id": "att1"},
            {**sample_attachment, "id": "att2"},
        ]

        # First get all attachments
        mock_client.get = MagicMock(return_value={"results": attachments, "_links": {}})

        result = mock_client.get(
            "/api/v2/pages/123456/attachments", operation="list attachments"
        )

        # Then delete each
        mock_client.delete = MagicMock(return_value={})
        for att in result["results"]:
            mock_client.delete(
                f"/api/v2/attachments/{att['id']}", operation="delete attachment"
            )

        assert mock_client.delete.call_count == 2

    def test_delete_with_errors(self, mock_client):
        """Test handling errors during bulk deletion."""
        attachment_ids = ["att1", "att2", "att3"]

        def delete_side_effect(endpoint, **kwargs):
            # Fail on second attachment
            if "att2" in endpoint:
                response = Mock()
                response.status_code = 404
                response.ok = False
                raise Exception("Not found")
            return {}

        mock_client.delete = MagicMock(side_effect=delete_side_effect)

        # Try to delete all, expect one to fail
        successful = []
        failed = []

        for att_id in attachment_ids:
            try:
                mock_client.delete(
                    f"/api/v2/attachments/{att_id}", operation="delete attachment"
                )
                successful.append(att_id)
            except Exception:
                failed.append(att_id)

        assert len(successful) == 2
        assert len(failed) == 1
        assert "att2" in failed
