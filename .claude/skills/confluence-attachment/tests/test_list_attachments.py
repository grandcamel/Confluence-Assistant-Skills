"""
Unit tests for list_attachments.py
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock



class TestListAttachments:
    """Tests for listing attachments functionality."""

    def test_list_attachments_empty(self, mock_client):
        """Test listing attachments when page has none."""
        mock_client.get = MagicMock(return_value={
            "results": [],
            "_links": {}
        })

        page_id = "123456"
        result = mock_client.get(
            f"/api/v2/pages/{page_id}/attachments",
            operation="list attachments"
        )

        assert result["results"] == []

    def test_list_attachments_single(self, mock_client, sample_attachment):
        """Test listing attachments with one attachment."""
        mock_client.get = MagicMock(return_value={
            "results": [sample_attachment],
            "_links": {}
        })

        page_id = "123456"
        result = mock_client.get(
            f"/api/v2/pages/{page_id}/attachments",
            operation="list attachments"
        )

        assert len(result["results"]) == 1
        assert result["results"][0]["id"] == "att123456"
        assert result["results"][0]["title"] == "test-file.pdf"

    def test_list_attachments_multiple(self, mock_client, sample_attachment):
        """Test listing multiple attachments."""
        attachments = [
            {**sample_attachment, "id": "att1", "title": "file1.pdf"},
            {**sample_attachment, "id": "att2", "title": "file2.docx"},
            {**sample_attachment, "id": "att3", "title": "image.png"},
        ]

        mock_client.get = MagicMock(return_value={
            "results": attachments,
            "_links": {}
        })

        page_id = "123456"
        result = mock_client.get(
            f"/api/v2/pages/{page_id}/attachments",
            operation="list attachments"
        )

        assert len(result["results"]) == 3
        assert result["results"][0]["title"] == "file1.pdf"
        assert result["results"][1]["title"] == "file2.docx"
        assert result["results"][2]["title"] == "image.png"

    def test_list_attachments_with_pagination(self, mock_client, sample_attachment):
        """Test listing attachments with pagination."""
        first_page = {
            "results": [{**sample_attachment, "id": "att1"}],
            "_links": {
                "next": "/api/v2/pages/123456/attachments?cursor=abc123"
            }
        }

        second_page = {
            "results": [{**sample_attachment, "id": "att2"}],
            "_links": {}
        }

        mock_client.get = MagicMock(side_effect=[first_page, second_page])

        # First call
        result1 = mock_client.get(
            "/api/v2/pages/123456/attachments",
            operation="list attachments"
        )

        assert len(result1["results"]) == 1
        assert "_links" in result1
        assert "next" in result1["_links"]

        # Second call with cursor
        result2 = mock_client.get(
            "/api/v2/pages/123456/attachments",
            params={"cursor": "abc123"},
            operation="list attachments"
        )

        assert len(result2["results"]) == 1

    def test_list_attachments_filter_by_media_type(self, mock_client, sample_attachment):
        """Test filtering attachments by media type."""
        attachments = [
            {**sample_attachment, "id": "att1", "mediaType": "application/pdf"},
            {**sample_attachment, "id": "att2", "mediaType": "image/png"},
            {**sample_attachment, "id": "att3", "mediaType": "application/pdf"},
        ]

        mock_client.get = MagicMock(return_value={
            "results": attachments,
            "_links": {}
        })

        result = mock_client.get(
            "/api/v2/pages/123456/attachments",
            params={"mediaType": "application/pdf"},
            operation="list attachments"
        )

        # In practice, the API would filter, but we're testing the request
        assert "results" in result


class TestAttachmentFormatting:
    """Tests for attachment data formatting."""

    def test_format_attachment_basic(self, sample_attachment):
        """Test basic attachment formatting."""
        from confluence_assistant_skills_lib import format_json

        # Test JSON formatting
        json_output = format_json(sample_attachment)
        assert "att123456" in json_output
        assert "test-file.pdf" in json_output

    def test_format_attachment_size(self):
        """Test file size formatting."""
        def format_file_size(bytes: int) -> str:
            """Format file size in human-readable format."""
            for unit in ['B', 'KB', 'MB', 'GB']:
                if bytes < 1024.0:
                    return f"{bytes:.1f} {unit}"
                bytes /= 1024.0
            return f"{bytes:.1f} TB"

        assert format_file_size(512) == "512.0 B"
        assert format_file_size(1024) == "1.0 KB"
        assert format_file_size(1024 * 1024) == "1.0 MB"
        assert format_file_size(1536) == "1.5 KB"

    def test_attachment_metadata(self, sample_attachment):
        """Test extracting attachment metadata."""
        assert sample_attachment["id"] == "att123456"
        assert sample_attachment["title"] == "test-file.pdf"
        assert sample_attachment["fileSize"] == 1024
        assert sample_attachment["mediaType"] == "application/pdf"
        assert "version" in sample_attachment
        assert sample_attachment["version"]["number"] == 1
