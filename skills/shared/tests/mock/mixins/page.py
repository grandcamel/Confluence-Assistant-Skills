"""
Page Mixin for Mock Confluence Client

Provides mock behavior for page CRUD operations.
"""

from __future__ import annotations

import re
from typing import Any, Optional


class PageMixin:
    """
    Mock behavior for page operations.

    Maintains an in-memory page store for realistic CRUD behavior.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pages: dict[str, dict[str, Any]] = {}
        self._page_versions: dict[str, list[dict[str, Any]]] = {}

    # =========================================================================
    # Page Store Management
    # =========================================================================

    def add_page(
        self,
        page_id: Optional[str] = None,
        title: str = "Test Page",
        space_id: str = "123456",
        parent_id: Optional[str] = None,
        body: str = "<p>Test content</p>",
        status: str = "current",
        labels: Optional[list[str]] = None,
        version: int = 1,
    ) -> dict[str, Any]:
        """
        Add a page to the mock store.

        Returns the page data dict.
        """
        if page_id is None:
            page_id = self.generate_id()

        page = {
            "id": page_id,
            "status": status,
            "title": title,
            "spaceId": space_id,
            "parentId": parent_id,
            "parentType": "page" if parent_id else None,
            "position": 0,
            "authorId": "user123",
            "ownerId": "user123",
            "lastOwnerId": "user123",
            "createdAt": self.generate_timestamp(),
            "version": {
                "number": version,
                "message": "",
                "minorEdit": False,
                "authorId": "user123",
                "createdAt": self.generate_timestamp(),
            },
            "body": {
                "storage": {"value": body, "representation": "storage"},
            },
            "_links": {
                "webui": f"/wiki/spaces/TEST/pages/{page_id}/{title.replace(' ', '+')}",
                "editui": f"/wiki/pages/resumedraft.action?draftId={page_id}",
                "tinyui": f"/wiki/x/{page_id[:6]}",
            },
            "_labels": labels or [],
        }

        self._pages[page_id] = page
        self._page_versions[page_id] = [page.copy()]

        return page

    def get_page(self, page_id: str) -> Optional[dict[str, Any]]:
        """Get a page from the mock store."""
        return self._pages.get(page_id)

    def update_page(
        self,
        page_id: str,
        title: Optional[str] = None,
        body: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """Update a page in the mock store."""
        page = self._pages.get(page_id)
        if not page:
            return None

        # Store current version
        self._page_versions[page_id].append(page.copy())

        # Update fields
        if title:
            page["title"] = title
        if body:
            page["body"]["storage"]["value"] = body
        if status:
            page["status"] = status

        # Increment version
        page["version"]["number"] += 1
        page["version"]["createdAt"] = self.generate_timestamp()

        return page

    def delete_page(self, page_id: str) -> bool:
        """Delete a page from the mock store."""
        if page_id in self._pages:
            del self._pages[page_id]
            return True
        return False

    def list_pages(
        self,
        space_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """List pages matching filters."""
        results = list(self._pages.values())

        if space_id:
            results = [p for p in results if p["spaceId"] == space_id]
        if parent_id:
            results = [p for p in results if p["parentId"] == parent_id]
        if status:
            results = [p for p in results if p["status"] == status]

        return results

    # =========================================================================
    # Request Handlers
    # =========================================================================

    def _handle_get(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]],
        data: Optional[dict[str, Any]],
    ) -> Optional[dict[str, Any]]:
        """Handle GET requests for pages."""
        # GET /api/v2/pages/{id}
        match = re.match(r"/api/v2/pages/(\d+)$", endpoint)
        if match:
            page_id = match.group(1)
            page = self.get_page(page_id)
            if page:
                return page
            raise self._not_found_error(f"Page {page_id} not found")

        # GET /api/v2/pages/{id}/versions
        match = re.match(r"/api/v2/pages/(\d+)/versions", endpoint)
        if match:
            page_id = match.group(1)
            versions = self._page_versions.get(page_id, [])
            return {"results": versions}

        # GET /api/v2/pages (list)
        if endpoint == "/api/v2/pages":
            space_id = params.get("space-id") if params else None
            parent_id = params.get("parent-id") if params else None
            pages = self.list_pages(space_id=space_id, parent_id=parent_id)
            return {"results": pages}

        return None

    def _handle_post(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]],
        data: Optional[dict[str, Any]],
    ) -> Optional[dict[str, Any]]:
        """Handle POST requests for pages."""
        # POST /api/v2/pages
        if endpoint == "/api/v2/pages" and data:
            return self.add_page(
                title=data.get("title", "New Page"),
                space_id=data.get("spaceId", "123"),
                parent_id=data.get("parentId"),
                body=data.get("body", {}).get("value", "<p>Content</p>"),
                status=data.get("status", "current"),
            )

        return None

    def _handle_put(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]],
        data: Optional[dict[str, Any]],
    ) -> Optional[dict[str, Any]]:
        """Handle PUT requests for pages."""
        # PUT /api/v2/pages/{id}
        match = re.match(r"/api/v2/pages/(\d+)$", endpoint)
        if match and data:
            page_id = match.group(1)
            page = self.update_page(
                page_id=page_id,
                title=data.get("title"),
                body=data.get("body", {}).get("value"),
                status=data.get("status"),
            )
            if page:
                return page
            raise self._not_found_error(f"Page {page_id} not found")

        return None

    def _handle_delete(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]],
        data: Optional[dict[str, Any]],
    ) -> Optional[dict[str, Any]]:
        """Handle DELETE requests for pages."""
        # DELETE /api/v2/pages/{id}
        match = re.match(r"/api/v2/pages/(\d+)$", endpoint)
        if match:
            page_id = match.group(1)
            if self.delete_page(page_id):
                return {}
            raise self._not_found_error(f"Page {page_id} not found")

        return None

    def _not_found_error(self, message: str) -> Exception:
        """Create a not found error."""
        # Import here to avoid circular dependency
        try:
            from confluence_as import NotFoundError
            return NotFoundError(message)
        except ImportError:
            return Exception(f"404: {message}")
