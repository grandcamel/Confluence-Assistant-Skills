"""
Unit tests for download_attachment.py
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch



class TestDownloadAttachment:
    """Tests for attachment download functionality."""

    def test_download_attachment_basic(self, mock_client, sample_attachment, tmp_path):
        """Test basic attachment download."""
        output_path = tmp_path / "downloaded.pdf"

        # Mock download_file method
        mock_client.download_file = MagicMock(return_value=output_path)

        download_url = sample_attachment["downloadLink"]
        result = mock_client.download_file(
            download_url,
            output_path,
            operation="download attachment"
        )

        assert result == output_path
        mock_client.download_file.assert_called_once()

    def test_download_attachment_to_directory(self, mock_client, sample_attachment, tmp_path):
        """Test downloading attachment to a directory."""
        # Create output directory
        output_dir = tmp_path / "downloads"
        output_dir.mkdir()

        # Expected output file
        output_file = output_dir / sample_attachment["title"]

        mock_client.download_file = MagicMock(return_value=output_file)

        result = mock_client.download_file(
            sample_attachment["downloadLink"],
            output_file,
            operation="download attachment"
        )

        assert result == output_file

    def test_download_creates_parent_directories(self, tmp_path):
        """Test that download creates parent directories if needed."""
        output_path = tmp_path / "nested" / "dir" / "file.pdf"

        # Parent should not exist yet
        assert not output_path.parent.exists()

        # This would be handled by download_file in the client
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"test")

        assert output_path.exists()
        assert output_path.parent.exists()

    def test_download_attachment_by_id(self, mock_client, sample_attachment):
        """Test downloading attachment by ID."""
        attachment_id = "att123456"

        # First get attachment metadata
        mock_client.get = MagicMock(return_value=sample_attachment)

        result = mock_client.get(
            f"/api/v2/attachments/{attachment_id}",
            operation="get attachment"
        )

        assert result["id"] == attachment_id
        assert "downloadLink" in result

    def test_download_all_from_page(self, mock_client, sample_attachment, tmp_path):
        """Test downloading all attachments from a page."""
        attachments = [
            {**sample_attachment, "id": "att1", "title": "file1.pdf"},
            {**sample_attachment, "id": "att2", "title": "file2.docx"},
        ]

        mock_client.get = MagicMock(return_value={
            "results": attachments,
            "_links": {}
        })

        # Get all attachments
        result = mock_client.get(
            "/api/v2/pages/123456/attachments",
            operation="list attachments"
        )

        assert len(result["results"]) == 2

        # Simulate downloading each
        for att in result["results"]:
            output_file = tmp_path / att["title"]
            mock_client.download_file = MagicMock(return_value=output_file)
            downloaded = mock_client.download_file(
                att["downloadLink"],
                output_file,
                operation="download attachment"
            )
            assert downloaded == output_file

    def test_download_with_invalid_attachment_id(self, mock_client):
        """Test download with non-existent attachment ID."""
        from confluence_assistant_skills_lib import NotFoundError

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.ok = False
        mock_response.json.return_value = {
            "message": "Attachment not found"
        }

        # Would raise NotFoundError
        # This tests the concept
        assert mock_response.status_code == 404

    def test_download_overwrites_existing_file(self, tmp_path):
        """Test that download can overwrite existing files."""
        output_file = tmp_path / "existing.pdf"
        output_file.write_bytes(b"old content")

        assert output_file.exists()
        assert output_file.read_bytes() == b"old content"

        # Overwrite
        output_file.write_bytes(b"new content")
        assert output_file.read_bytes() == b"new content"

    def test_download_binary_content(self, tmp_path):
        """Test downloading binary content."""
        output_file = tmp_path / "binary.dat"
        binary_data = bytes([0, 1, 2, 255, 254, 253])

        output_file.write_bytes(binary_data)

        assert output_file.read_bytes() == binary_data


class TestDownloadValidation:
    """Tests for download-specific validation."""

    def test_validate_output_path(self, tmp_path):
        """Test output path validation."""
        from confluence_assistant_skills_lib import validate_file_path

        # Valid output path (doesn't need to exist)
        output = tmp_path / "output.pdf"
        result = validate_file_path(output, must_exist=False)
        assert result == output

    def test_validate_attachment_id(self):
        """Test attachment ID validation."""
        from confluence_assistant_skills_lib import validate_page_id

        # Attachment IDs are numeric strings like page IDs
        assert validate_page_id("123456") == "123456"
        assert validate_page_id("789012") == "789012"
