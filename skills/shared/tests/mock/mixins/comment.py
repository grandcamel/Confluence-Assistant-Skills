"""
Comment Mixin for Mock Confluence Client

Provides mock behavior for comment operations.
"""

from __future__ import annotations

import re
from typing import Any, Optional


class CommentMixin:
    """
    Mock behavior for comment operations.

    Handles footer comments and inline comments.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._comments: dict[str, dict[str, Any]] = {}
        self._page_comments: dict[str, list[str]] = {}  # page_id -> comment_ids

    # =========================================================================
    # Comment Management
    # =========================================================================

    def add_comment(
        self,
        page_id: str,
        body: str,
        comment_id: Optional[str] = None,
        parent_comment_id: Optional[str] = None,
        inline: bool = False,
    ) -> dict[str, Any]:
        """Add a comment to a page."""
        if comment_id is None:
            comment_id = self.generate_id()

        comment = {
            "id": comment_id,
            "type": "comment",
            "status": "current",
            "pageId": page_id,
            "parentId": parent_comment_id,
            "authorId": "user123",
            "createdAt": self.generate_timestamp(),
            "version": {
                "number": 1,
                "createdAt": self.generate_timestamp(),
            },
            "body": {
                "storage": {"value": body, "representation": "storage"},
            },
            "inline": inline,
            "resolved": False,
        }

        self._comments[comment_id] = comment

        if page_id not in self._page_comments:
            self._page_comments[page_id] = []
        self._page_comments[page_id].append(comment_id)

        return comment

    def get_comment(self, comment_id: str) -> Optional[dict[str, Any]]:
        """Get a comment by ID."""
        return self._comments.get(comment_id)

    def get_page_comments(
        self,
        page_id: str,
        include_replies: bool = True,
    ) -> list[dict[str, Any]]:
        """Get all comments for a page."""
        comment_ids = self._page_comments.get(page_id, [])
        comments = [self._comments[cid] for cid in comment_ids if cid in self._comments]

        if not include_replies:
            comments = [c for c in comments if not c.get("parentId")]

        return comments

    def update_comment(
        self,
        comment_id: str,
        body: Optional[str] = None,
        resolved: Optional[bool] = None,
    ) -> Optional[dict[str, Any]]:
        """Update a comment."""
        comment = self._comments.get(comment_id)
        if not comment:
            return None

        if body is not None:
            comment["body"]["storage"]["value"] = body
            comment["version"]["number"] += 1

        if resolved is not None:
            comment["resolved"] = resolved

        return comment

    def delete_comment(self, comment_id: str) -> bool:
        """Delete a comment."""
        comment = self._comments.pop(comment_id, None)
        if comment:
            page_id = comment.get("pageId")
            if page_id and page_id in self._page_comments:
                self._page_comments[page_id] = [
                    cid for cid in self._page_comments[page_id] if cid != comment_id
                ]
            return True
        return False

    def resolve_comment(self, comment_id: str) -> Optional[dict[str, Any]]:
        """Resolve an inline comment."""
        return self.update_comment(comment_id, resolved=True)

    def unresolve_comment(self, comment_id: str) -> Optional[dict[str, Any]]:
        """Unresolve an inline comment."""
        return self.update_comment(comment_id, resolved=False)

    # =========================================================================
    # Request Handlers
    # =========================================================================

    def _handle_get(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]],
        data: Optional[dict[str, Any]],
    ) -> Optional[dict[str, Any]]:
        """Handle GET requests for comments."""
        # GET /api/v2/footer-comments/{id}
        match = re.match(r"/api/v2/footer-comments/(\d+)$", endpoint)
        if match:
            comment_id = match.group(1)
            comment = self.get_comment(comment_id)
            if comment:
                return comment
            raise self._not_found_error(f"Comment {comment_id} not found")

        # GET /api/v2/pages/{id}/footer-comments
        match = re.match(r"/api/v2/pages/(\d+)/footer-comments", endpoint)
        if match:
            page_id = match.group(1)
            comments = self.get_page_comments(page_id)
            return {"results": comments}

        # GET /api/v2/pages/{id}/inline-comments
        match = re.match(r"/api/v2/pages/(\d+)/inline-comments", endpoint)
        if match:
            page_id = match.group(1)
            comments = [c for c in self.get_page_comments(page_id) if c.get("inline")]
            return {"results": comments}

        return None

    def _handle_post(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]],
        data: Optional[dict[str, Any]],
    ) -> Optional[dict[str, Any]]:
        """Handle POST requests for comments."""
        # POST /api/v2/pages/{id}/footer-comments
        match = re.match(r"/api/v2/pages/(\d+)/footer-comments", endpoint)
        if match and data:
            page_id = match.group(1)
            body = data.get("body", {}).get("value", "<p>Comment</p>")
            return self.add_comment(page_id, body)

        # POST /api/v2/pages/{id}/inline-comments
        match = re.match(r"/api/v2/pages/(\d+)/inline-comments", endpoint)
        if match and data:
            page_id = match.group(1)
            body = data.get("body", {}).get("value", "<p>Inline comment</p>")
            return self.add_comment(page_id, body, inline=True)

        # POST /api/v2/footer-comments/{id}/children (reply)
        match = re.match(r"/api/v2/footer-comments/(\d+)/children", endpoint)
        if match and data:
            parent_id = match.group(1)
            parent = self.get_comment(parent_id)
            if parent:
                body = data.get("body", {}).get("value", "<p>Reply</p>")
                return self.add_comment(
                    parent["pageId"],
                    body,
                    parent_comment_id=parent_id,
                )

        return None

    def _handle_put(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]],
        data: Optional[dict[str, Any]],
    ) -> Optional[dict[str, Any]]:
        """Handle PUT requests for comments."""
        # PUT /api/v2/footer-comments/{id}
        match = re.match(r"/api/v2/footer-comments/(\d+)$", endpoint)
        if match and data:
            comment_id = match.group(1)
            body = data.get("body", {}).get("value")
            comment = self.update_comment(comment_id, body=body)
            if comment:
                return comment
            raise self._not_found_error(f"Comment {comment_id} not found")

        return None

    def _handle_delete(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]],
        data: Optional[dict[str, Any]],
    ) -> Optional[dict[str, Any]]:
        """Handle DELETE requests for comments."""
        # DELETE /api/v2/footer-comments/{id}
        match = re.match(r"/api/v2/footer-comments/(\d+)$", endpoint)
        if match:
            comment_id = match.group(1)
            if self.delete_comment(comment_id):
                return {}
            raise self._not_found_error(f"Comment {comment_id} not found")

        # DELETE /api/v2/inline-comments/{id}
        match = re.match(r"/api/v2/inline-comments/(\d+)$", endpoint)
        if match:
            comment_id = match.group(1)
            if self.delete_comment(comment_id):
                return {}
            raise self._not_found_error(f"Comment {comment_id} not found")

        return None

    def _not_found_error(self, message: str) -> Exception:
        """Create a not found error."""
        try:
            from confluence_assistant_skills_lib import NotFoundError
            return NotFoundError(message)
        except ImportError:
            return Exception(f"404: {message}")
