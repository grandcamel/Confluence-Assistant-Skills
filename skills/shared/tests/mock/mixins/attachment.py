"""
Attachment Mixin for Mock Confluence Client

Provides mock behavior for attachment operations.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


class AttachmentMixin:
    """
    Mock behavior for attachment operations.

    Handles file upload, download, and metadata.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._attachments: dict[str, dict[str, Any]] = {}
        self._page_attachments: dict[str, list[str]] = {}  # page_id -> attachment_ids
        self._attachment_data: dict[str, bytes] = {}  # attachment_id -> file content

    # =========================================================================
    # Attachment Management
    # =========================================================================

    def add_attachment(
        self,
        page_id: str,
        filename: str,
        content: bytes = b"Mock file content",
        attachment_id: str | None = None,
        media_type: str = "application/octet-stream",
    ) -> dict[str, Any]:
        """Add an attachment to a page."""
        if attachment_id is None:
            attachment_id = self.generate_id()

        attachment = {
            "id": attachment_id,
            "status": "current",
            "title": filename,
            "mediaType": media_type,
            "mediaTypeDescription": self._get_media_description(media_type),
            "fileSize": len(content),
            "webuiLink": f"/wiki/download/attachments/{page_id}/{filename}",
            "downloadLink": f"/wiki/download/attachments/{page_id}/{filename}",
            "pageId": page_id,
            "version": {
                "number": 1,
                "createdAt": self.generate_timestamp(),
            },
            "_links": {
                "download": f"/wiki/download/attachments/{page_id}/{filename}",
            },
        }

        self._attachments[attachment_id] = attachment
        self._attachment_data[attachment_id] = content

        if page_id not in self._page_attachments:
            self._page_attachments[page_id] = []
        self._page_attachments[page_id].append(attachment_id)

        return attachment

    def get_attachment(self, attachment_id: str) -> dict[str, Any] | None:
        """Get attachment metadata."""
        return self._attachments.get(attachment_id)

    def get_attachment_content(self, attachment_id: str) -> bytes | None:
        """Get attachment file content."""
        return self._attachment_data.get(attachment_id)

    def get_page_attachments(self, page_id: str) -> list[dict[str, Any]]:
        """Get all attachments for a page."""
        attachment_ids = self._page_attachments.get(page_id, [])
        return [
            self._attachments[aid] for aid in attachment_ids if aid in self._attachments
        ]

    def update_attachment(
        self,
        attachment_id: str,
        content: bytes | None = None,
        filename: str | None = None,
    ) -> dict[str, Any] | None:
        """Update an attachment."""
        attachment = self._attachments.get(attachment_id)
        if not attachment:
            return None

        if content is not None:
            self._attachment_data[attachment_id] = content
            attachment["fileSize"] = len(content)

        if filename is not None:
            attachment["title"] = filename
            page_id = attachment["pageId"]
            attachment["downloadLink"] = (
                f"/wiki/download/attachments/{page_id}/{filename}"
            )

        attachment["version"]["number"] += 1
        attachment["version"]["createdAt"] = self.generate_timestamp()

        return attachment

    def delete_attachment(self, attachment_id: str) -> bool:
        """Delete an attachment."""
        attachment = self._attachments.pop(attachment_id, None)
        self._attachment_data.pop(attachment_id, None)

        if attachment:
            page_id = attachment.get("pageId")
            if page_id and page_id in self._page_attachments:
                self._page_attachments[page_id] = [
                    aid
                    for aid in self._page_attachments[page_id]
                    if aid != attachment_id
                ]
            return True
        return False

    def _get_media_description(self, media_type: str) -> str:
        """Get human-readable description for media type."""
        descriptions = {
            "application/pdf": "PDF Document",
            "image/png": "PNG Image",
            "image/jpeg": "JPEG Image",
            "image/gif": "GIF Image",
            "text/plain": "Plain Text",
            "application/json": "JSON File",
            "application/xml": "XML File",
            "application/zip": "ZIP Archive",
        }
        return descriptions.get(media_type, "Binary File")

    # =========================================================================
    # File Operations
    # =========================================================================

    def upload_file(
        self,
        endpoint: str,
        file_path: str | Path,
        params: dict[str, Any] | None = None,
        additional_data: dict[str, str] | None = None,
        operation: str = "upload file",
    ) -> dict[str, Any]:
        """Mock file upload."""
        file_path = Path(file_path)

        # Extract page ID from endpoint
        match = re.match(r".*/content/(\d+)/child/attachment", endpoint)
        if not match:
            raise ValueError(f"Invalid upload endpoint: {endpoint}")

        page_id = match.group(1)

        # Mock reading file content
        if file_path.exists():
            content = file_path.read_bytes()
        else:
            content = b"Mock file content"

        # Determine media type from extension
        media_types = {
            ".pdf": "application/pdf",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".txt": "text/plain",
            ".json": "application/json",
            ".xml": "application/xml",
            ".zip": "application/zip",
        }
        media_type = media_types.get(
            file_path.suffix.lower(), "application/octet-stream"
        )

        attachment = self.add_attachment(
            page_id=page_id,
            filename=file_path.name,
            content=content,
            media_type=media_type,
        )

        return {"results": [attachment]}

    def download_file(
        self,
        download_url: str,
        output_path: str | Path,
        operation: str = "download file",
    ) -> Path:
        """Mock file download."""
        output_path = Path(output_path)

        # Find attachment by URL
        for att_id, attachment in self._attachments.items():
            if download_url.endswith(attachment["title"]) or att_id in download_url:
                content = self._attachment_data.get(att_id, b"Mock content")
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(content)
                return output_path

        # Default mock content
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"Mock downloaded content")
        return output_path

    # =========================================================================
    # Request Handlers
    # =========================================================================

    def _handle_get(
        self,
        endpoint: str,
        params: dict[str, Any] | None,
        data: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Handle GET requests for attachments."""
        # GET /api/v2/attachments/{id}
        match = re.match(r"/api/v2/attachments/(\d+)$", endpoint)
        if match:
            attachment_id = match.group(1)
            attachment = self.get_attachment(attachment_id)
            if attachment:
                return attachment
            raise self._not_found_error(f"Attachment {attachment_id} not found")

        # GET /api/v2/pages/{id}/attachments
        match = re.match(r"/api/v2/pages/(\d+)/attachments", endpoint)
        if match:
            page_id = match.group(1)
            attachments = self.get_page_attachments(page_id)
            return {"results": attachments}

        return None

    def _handle_delete(
        self,
        endpoint: str,
        params: dict[str, Any] | None,
        data: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Handle DELETE requests for attachments."""
        # DELETE /api/v2/attachments/{id}
        match = re.match(r"/api/v2/attachments/(\d+)$", endpoint)
        if match:
            attachment_id = match.group(1)
            if self.delete_attachment(attachment_id):
                return {}
            raise self._not_found_error(f"Attachment {attachment_id} not found")

        return None

    def _not_found_error(self, message: str) -> Exception:
        """Create a not found error."""
        try:
            from confluence_as import NotFoundError

            return NotFoundError(message)
        except ImportError:
            return Exception(f"404: {message}")
