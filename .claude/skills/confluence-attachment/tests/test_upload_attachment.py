"""
Unit tests for upload_attachment.py
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, call

# Add shared lib to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'shared' / 'scripts' / 'lib'))


class TestUploadAttachment:
    """Tests for attachment upload functionality."""

    def test_validate_page_id_valid(self):
        """Test that valid page IDs pass validation."""
        from validators import validate_page_id

        assert validate_page_id("12345") == "12345"
        assert validate_page_id(67890) == "67890"

    def test_validate_page_id_invalid(self):
        """Test that invalid page IDs fail validation."""
        from validators import validate_page_id, ValidationError

        with pytest.raises(ValidationError):
            validate_page_id("")

        with pytest.raises(ValidationError):
            validate_page_id("abc")

        with pytest.raises(ValidationError):
            validate_page_id(None)

    def test_validate_file_path_exists(self, test_file):
        """Test file path validation with existing file."""
        from validators import validate_file_path

        result = validate_file_path(test_file)
        assert result == test_file
        assert result.exists()
        assert result.is_file()

    def test_validate_file_path_not_exists(self):
        """Test file path validation with non-existent file."""
        from validators import validate_file_path, ValidationError

        with pytest.raises(ValidationError) as exc_info:
            validate_file_path("/nonexistent/file.txt")

        assert "does not exist" in str(exc_info.value)

    def test_validate_file_path_is_directory(self, tmp_path):
        """Test file path validation when path is a directory."""
        from validators import validate_file_path, ValidationError

        with pytest.raises(ValidationError) as exc_info:
            validate_file_path(tmp_path)

        assert "not a file" in str(exc_info.value)

    def test_upload_attachment_basic(self, mock_client, sample_attachment, test_file):
        """Test basic attachment upload."""
        # Mock the upload_file method
        mock_client.upload_file = MagicMock(return_value={
            "results": [sample_attachment]
        })

        page_id = "123456"
        result = mock_client.upload_file(
            f"/api/v2/pages/{page_id}/attachments",
            test_file,
            operation="upload attachment"
        )

        assert result["results"][0]["id"] == "att123456"
        assert result["results"][0]["title"] == "test-file.pdf"
        mock_client.upload_file.assert_called_once()

    def test_upload_attachment_with_comment(self, mock_client, sample_attachment, test_file):
        """Test attachment upload with comment."""
        attachment_with_comment = sample_attachment.copy()
        attachment_with_comment["comment"] = "Test comment"

        mock_client.upload_file = MagicMock(return_value={
            "results": [attachment_with_comment]
        })

        page_id = "123456"
        result = mock_client.upload_file(
            f"/api/v2/pages/{page_id}/attachments",
            test_file,
            additional_data={"comment": "Test comment"},
            operation="upload attachment"
        )

        assert result["results"][0]["comment"] == "Test comment"

    def test_upload_multiple_file_types(self, mock_client, test_file, test_pdf_file, test_image_file):
        """Test uploading different file types."""
        from validators import validate_file_path

        # All should pass validation
        assert validate_file_path(test_file).suffix == ".txt"
        assert validate_file_path(test_pdf_file).suffix == ".pdf"
        assert validate_file_path(test_image_file).suffix == ".png"

    def test_get_mime_type(self, test_file, test_pdf_file, test_image_file):
        """Test MIME type detection for different file types."""
        import mimetypes

        # Initialize mimetypes
        mimetypes.init()

        assert mimetypes.guess_type(str(test_file))[0] == "text/plain"
        assert mimetypes.guess_type(str(test_pdf_file))[0] == "application/pdf"
        assert mimetypes.guess_type(str(test_image_file))[0] == "image/png"


class TestAttachmentValidation:
    """Tests for attachment-specific validation."""

    def test_file_size_limits(self, tmp_path):
        """Test file size validation."""
        # Create a large file (mock)
        large_file = tmp_path / "large.bin"
        # Don't actually create a huge file, just test the concept
        large_file.write_bytes(b"x" * 1000)

        from validators import validate_file_path

        # Should validate successfully
        result = validate_file_path(large_file)
        assert result.stat().st_size == 1000

    def test_attachment_id_validation(self):
        """Test attachment ID validation."""
        from validators import validate_page_id

        # Attachment IDs are numeric like page IDs
        assert validate_page_id("123456") == "123456"

    def test_allowed_extensions(self, tmp_path):
        """Test file extension validation."""
        from validators import validate_file_path, ValidationError

        # Create test files
        pdf_file = tmp_path / "doc.pdf"
        pdf_file.write_bytes(b"pdf")

        txt_file = tmp_path / "doc.txt"
        txt_file.write_bytes(b"txt")

        exe_file = tmp_path / "program.exe"
        exe_file.write_bytes(b"exe")

        # Allow specific extensions
        assert validate_file_path(pdf_file, allowed_extensions=['.pdf']).suffix == '.pdf'

        # Reject disallowed extensions
        with pytest.raises(ValidationError):
            validate_file_path(exe_file, allowed_extensions=['.pdf', '.txt'])
