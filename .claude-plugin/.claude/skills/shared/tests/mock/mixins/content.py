"""
Content Mixin for Mock Confluence Client

Provides mock behavior for generic content operations (blog posts, etc.).
"""

from __future__ import annotations

import re
from typing import Any, Optional


class ContentMixin:
    """
    Mock behavior for generic content operations.

    Handles blog posts and content properties.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._blogposts: dict[str, dict[str, Any]] = {}
        self._properties: dict[str, dict[str, dict[str, Any]]] = {}  # content_id -> key -> property

    # =========================================================================
    # Blog Post Management
    # =========================================================================

    def add_blogpost(
        self,
        blogpost_id: Optional[str] = None,
        title: str = "Test Blog Post",
        space_id: str = "123456",
        body: str = "<p>Test blog content</p>",
        status: str = "current",
    ) -> dict[str, Any]:
        """Add a blog post to the mock store."""
        if blogpost_id is None:
            blogpost_id = self.generate_id()

        blogpost = {
            "id": blogpost_id,
            "type": "blogpost",
            "status": status,
            "title": title,
            "spaceId": space_id,
            "authorId": "user123",
            "createdAt": self.generate_timestamp(),
            "version": {
                "number": 1,
                "createdAt": self.generate_timestamp(),
            },
            "body": {
                "storage": {"value": body, "representation": "storage"},
            },
            "_links": {
                "webui": f"/wiki/spaces/TEST/blog/{blogpost_id}",
            },
        }

        self._blogposts[blogpost_id] = blogpost
        return blogpost

    def get_blogpost(self, blogpost_id: str) -> Optional[dict[str, Any]]:
        """Get a blog post from the mock store."""
        return self._blogposts.get(blogpost_id)

    def delete_blogpost(self, blogpost_id: str) -> bool:
        """Delete a blog post from the mock store."""
        if blogpost_id in self._blogposts:
            del self._blogposts[blogpost_id]
            return True
        return False

    # =========================================================================
    # Content Properties
    # =========================================================================

    def set_property(
        self,
        content_id: str,
        key: str,
        value: Any,
        version: int = 1,
    ) -> dict[str, Any]:
        """Set a content property."""
        if content_id not in self._properties:
            self._properties[content_id] = {}

        prop = {
            "id": f"{content_id}-{key}",
            "key": key,
            "value": value,
            "version": {"number": version},
        }

        self._properties[content_id][key] = prop
        return prop

    def get_property(self, content_id: str, key: str) -> Optional[dict[str, Any]]:
        """Get a content property."""
        return self._properties.get(content_id, {}).get(key)

    def list_properties(self, content_id: str) -> list[dict[str, Any]]:
        """List all properties for a content item."""
        return list(self._properties.get(content_id, {}).values())

    def delete_property(self, content_id: str, key: str) -> bool:
        """Delete a content property."""
        if content_id in self._properties and key in self._properties[content_id]:
            del self._properties[content_id][key]
            return True
        return False

    # =========================================================================
    # Request Handlers
    # =========================================================================

    def _handle_get(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]],
        data: Optional[dict[str, Any]],
    ) -> Optional[dict[str, Any]]:
        """Handle GET requests for content."""
        # GET /api/v2/blogposts/{id}
        match = re.match(r"/api/v2/blogposts/(\d+)$", endpoint)
        if match:
            blogpost_id = match.group(1)
            blogpost = self.get_blogpost(blogpost_id)
            if blogpost:
                return blogpost
            raise self._not_found_error(f"Blog post {blogpost_id} not found")

        # GET /api/v2/blogposts (list)
        if endpoint == "/api/v2/blogposts":
            space_id = params.get("space-id") if params else None
            blogposts = list(self._blogposts.values())
            if space_id:
                blogposts = [b for b in blogposts if b["spaceId"] == space_id]
            return {"results": blogposts}

        # GET /rest/api/content/{id}/property
        match = re.match(r"/rest/api/content/(\d+)/property$", endpoint)
        if match:
            content_id = match.group(1)
            properties = self.list_properties(content_id)
            return {"results": properties}

        # GET /rest/api/content/{id}/property/{key}
        match = re.match(r"/rest/api/content/(\d+)/property/([^/]+)$", endpoint)
        if match:
            content_id, key = match.groups()
            prop = self.get_property(content_id, key)
            if prop:
                return prop
            raise self._not_found_error(f"Property {key} not found")

        return None

    def _handle_post(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]],
        data: Optional[dict[str, Any]],
    ) -> Optional[dict[str, Any]]:
        """Handle POST requests for content."""
        # POST /api/v2/blogposts
        if endpoint == "/api/v2/blogposts" and data:
            return self.add_blogpost(
                title=data.get("title", "New Blog Post"),
                space_id=data.get("spaceId", "123"),
                body=data.get("body", {}).get("value", "<p>Content</p>"),
                status=data.get("status", "current"),
            )

        # POST /rest/api/content/{id}/property
        match = re.match(r"/rest/api/content/(\d+)/property$", endpoint)
        if match and data:
            content_id = match.group(1)
            return self.set_property(
                content_id=content_id,
                key=data.get("key", "unknown"),
                value=data.get("value"),
            )

        return None

    def _handle_delete(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]],
        data: Optional[dict[str, Any]],
    ) -> Optional[dict[str, Any]]:
        """Handle DELETE requests for content."""
        # DELETE /api/v2/blogposts/{id}
        match = re.match(r"/api/v2/blogposts/(\d+)$", endpoint)
        if match:
            blogpost_id = match.group(1)
            if self.delete_blogpost(blogpost_id):
                return {}
            raise self._not_found_error(f"Blog post {blogpost_id} not found")

        # DELETE /rest/api/content/{id}/property/{key}
        match = re.match(r"/rest/api/content/(\d+)/property/([^/]+)$", endpoint)
        if match:
            content_id, key = match.groups()
            if self.delete_property(content_id, key):
                return {}
            raise self._not_found_error(f"Property {key} not found")

        return None

    def _not_found_error(self, message: str) -> Exception:
        """Create a not found error."""
        try:
            from confluence_assistant_skills_lib import NotFoundError
            return NotFoundError(message)
        except ImportError:
            return Exception(f"404: {message}")
