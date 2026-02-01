"""
Label Mixin for Mock Confluence Client

Provides mock behavior for label operations.
"""

from __future__ import annotations

import re
from typing import Any


class LabelMixin:
    """
    Mock behavior for label operations.

    Maintains label associations with content.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._labels: dict[str, list[dict[str, Any]]] = {}  # content_id -> labels

    # =========================================================================
    # Label Management
    # =========================================================================

    def add_label(
        self,
        content_id: str,
        label_name: str,
        prefix: str = "global",
    ) -> dict[str, Any]:
        """Add a label to content."""
        if content_id not in self._labels:
            self._labels[content_id] = []

        # Check if label already exists
        for label in self._labels[content_id]:
            if label["name"] == label_name:
                return label

        label = {
            "id": f"label-{self.generate_id()[:8]}",
            "name": label_name,
            "prefix": prefix,
        }

        self._labels[content_id].append(label)

        # Also update the content's _labels list if it exists
        if hasattr(self, "_pages") and content_id in self._pages:
            page = self._pages[content_id]
            if "_labels" not in page:
                page["_labels"] = []
            if label_name not in page["_labels"]:
                page["_labels"].append(label_name)

        return label

    def get_labels(self, content_id: str) -> list[dict[str, Any]]:
        """Get all labels for content."""
        return self._labels.get(content_id, [])

    def remove_label(self, content_id: str, label_id_or_name: str) -> bool:
        """Remove a label from content."""
        if content_id not in self._labels:
            return False

        original_count = len(self._labels[content_id])
        self._labels[content_id] = [
            label
            for label in self._labels[content_id]
            if label["id"] != label_id_or_name and label["name"] != label_id_or_name
        ]

        removed = len(self._labels[content_id]) < original_count

        # Also update the content's _labels list if it exists
        if removed and hasattr(self, "_pages") and content_id in self._pages:
            page = self._pages[content_id]
            if "_labels" in page:
                page["_labels"] = [
                    label for label in page["_labels"] if label != label_id_or_name
                ]

        return removed

    def find_content_by_label(self, label_name: str) -> list[str]:
        """Find all content IDs with a specific label."""
        content_ids = []
        for content_id, labels in self._labels.items():
            for label in labels:
                if label["name"] == label_name:
                    content_ids.append(content_id)
                    break
        return content_ids

    # =========================================================================
    # Request Handlers
    # =========================================================================

    def _handle_get(
        self,
        endpoint: str,
        params: dict[str, Any] | None,
        data: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Handle GET requests for labels."""
        # GET /api/v2/pages/{id}/labels
        match = re.match(r"/api/v2/pages/(\d+)/labels", endpoint)
        if match:
            content_id = match.group(1)
            labels = self.get_labels(content_id)
            return {"results": labels}

        # GET /api/v2/blogposts/{id}/labels
        match = re.match(r"/api/v2/blogposts/(\d+)/labels", endpoint)
        if match:
            content_id = match.group(1)
            labels = self.get_labels(content_id)
            return {"results": labels}

        return None

    def _handle_post(
        self,
        endpoint: str,
        params: dict[str, Any] | None,
        data: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Handle POST requests for labels."""
        # POST /api/v2/pages/{id}/labels
        match = re.match(r"/api/v2/pages/(\d+)/labels", endpoint)
        if match and data:
            content_id = match.group(1)
            label_name = data.get("name", "unknown")
            return self.add_label(content_id, label_name)

        # POST /api/v2/blogposts/{id}/labels
        match = re.match(r"/api/v2/blogposts/(\d+)/labels", endpoint)
        if match and data:
            content_id = match.group(1)
            label_name = data.get("name", "unknown")
            return self.add_label(content_id, label_name)

        return None

    def _handle_delete(
        self,
        endpoint: str,
        params: dict[str, Any] | None,
        data: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Handle DELETE requests for labels."""
        # DELETE /api/v2/pages/{id}/labels/{label_id}
        match = re.match(r"/api/v2/pages/(\d+)/labels/([^/]+)", endpoint)
        if match:
            content_id, label_id = match.groups()
            if self.remove_label(content_id, label_id):
                return {}
            raise self._not_found_error(f"Label {label_id} not found")

        # DELETE /api/v2/blogposts/{id}/labels/{label_id}
        match = re.match(r"/api/v2/blogposts/(\d+)/labels/([^/]+)", endpoint)
        if match:
            content_id, label_id = match.groups()
            if self.remove_label(content_id, label_id):
                return {}
            raise self._not_found_error(f"Label {label_id} not found")

        return None

    def _not_found_error(self, message: str) -> Exception:
        """Create a not found error."""
        try:
            from confluence_as import NotFoundError

            return NotFoundError(message)
        except ImportError:
            return Exception(f"404: {message}")
