"""
Search Mixin for Mock Confluence Client

Provides mock behavior for CQL search operations.
"""

from __future__ import annotations

import re
from typing import Any


class SearchMixin:
    """
    Mock behavior for search operations.

    Provides basic CQL parsing and filtering against stored content.
    """

    # =========================================================================
    # Search Implementation
    # =========================================================================

    def search(
        self,
        cql: str,
        limit: int = 25,
        start: int = 0,
    ) -> dict[str, Any]:
        """
        Execute a mock CQL search.

        Supports basic CQL syntax:
        - space = "KEY"
        - type = page|blogpost|comment|attachment
        - label = "name"
        - title ~ "text"
        - text ~ "text"
        - ancestor = 12345
        """
        results = []

        # Get all searchable content
        all_content = self._get_all_searchable_content()

        # Parse and filter by CQL
        filters = self._parse_cql(cql)

        for item in all_content:
            if self._matches_filters(item, filters):
                results.append(
                    {
                        "content": item,
                        "excerpt": self._generate_excerpt(item),
                        "lastModified": item.get("createdAt", ""),
                    }
                )

        # Apply pagination
        total = len(results)
        results = results[start : start + limit]

        return {
            "results": results,
            "start": start,
            "limit": limit,
            "size": len(results),
            "totalSize": total,
            "_links": {},
        }

    def _get_all_searchable_content(self) -> list[dict[str, Any]]:
        """Get all content that can be searched."""
        content = []

        # Pages (from PageMixin)
        if hasattr(self, "_pages"):
            content.extend(self._pages.values())

        # Blog posts (from ContentMixin)
        if hasattr(self, "_blogposts"):
            for post in self._blogposts.values():
                post["type"] = "blogpost"
                content.append(post)

        # Comments (from CommentMixin)
        if hasattr(self, "_comments"):
            for comment in self._comments.values():
                comment["type"] = "comment"
                content.append(comment)

        # Default type for pages
        for item in content:
            if "type" not in item:
                item["type"] = "page"

        return content

    def _parse_cql(self, cql: str) -> dict[str, Any]:
        """
        Parse CQL query into filter dict.

        Returns dict with filter conditions.
        """
        filters = {}

        # space = "KEY" or space = KEY
        match = re.search(r'space\s*=\s*["\']?([A-Za-z0-9_]+)["\']?', cql)
        if match:
            filters["space_key"] = match.group(1)

        # space.id = 123
        match = re.search(r"space\.id\s*=\s*(\d+)", cql)
        if match:
            filters["space_id"] = match.group(1)

        # type = page|blogpost|comment|attachment
        match = re.search(r"type\s*=\s*(\w+)", cql)
        if match:
            filters["type"] = match.group(1)

        # label = "name"
        match = re.search(r'label\s*=\s*["\']([^"\']+)["\']', cql)
        if match:
            filters["label"] = match.group(1)

        # title ~ "text"
        match = re.search(r'title\s*~\s*["\']([^"\']+)["\']', cql)
        if match:
            filters["title_contains"] = match.group(1).lower()

        # text ~ "text"
        match = re.search(r'text\s*~\s*["\']([^"\']+)["\']', cql)
        if match:
            filters["text_contains"] = match.group(1).lower()

        # ancestor = 12345
        match = re.search(r"ancestor\s*=\s*(\d+)", cql)
        if match:
            filters["ancestor"] = match.group(1)

        # creator = currentUser() or creator = "email"
        match = re.search(r"creator\s*=\s*currentUser\(\)", cql)
        if match:
            filters["creator"] = "user123"  # Mock current user
        else:
            match = re.search(r'creator\s*=\s*["\']([^"\']+)["\']', cql)
            if match:
                filters["creator"] = match.group(1)

        return filters

    def _matches_filters(
        self,
        item: dict[str, Any],
        filters: dict[str, Any],
    ) -> bool:
        """Check if an item matches all filters."""
        # Space key filter
        if "space_key" in filters:
            # Need to look up space by ID to check key
            space_id = item.get("spaceId")
            if hasattr(self, "_spaces"):
                space = self._spaces.get(space_id)
                if not space or space.get("key") != filters["space_key"]:
                    return False
            else:
                return False

        # Space ID filter
        if "space_id" in filters and item.get("spaceId") != filters["space_id"]:
            return False

        # Type filter
        if "type" in filters and item.get("type", "page") != filters["type"]:
            return False

        # Label filter
        if "label" in filters:
            labels = item.get("_labels", [])
            if filters["label"] not in labels:
                return False

        # Title contains filter
        if "title_contains" in filters:
            title = item.get("title", "").lower()
            if filters["title_contains"] not in title:
                return False

        # Text contains filter
        if "text_contains" in filters:
            body = item.get("body", {}).get("storage", {}).get("value", "").lower()
            title = item.get("title", "").lower()
            if (
                filters["text_contains"] not in body
                and filters["text_contains"] not in title
            ):
                return False

        # Ancestor filter
        if "ancestor" in filters:
            parent_id = item.get("parentId")
            if parent_id != filters["ancestor"]:
                # TODO: Check full ancestor chain
                return False

        # Creator filter
        return not ("creator" in filters and item.get("authorId") != filters["creator"])

    def _generate_excerpt(self, item: dict[str, Any]) -> str:
        """Generate a search excerpt from content."""
        body = item.get("body", {}).get("storage", {}).get("value", "")
        # Strip HTML tags for excerpt
        text = re.sub(r"<[^>]+>", "", body)
        # Truncate
        if len(text) > 150:
            text = text[:150] + "..."
        return text

    # =========================================================================
    # Request Handlers
    # =========================================================================

    def _handle_get(
        self,
        endpoint: str,
        params: dict[str, Any] | None,
        data: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Handle GET requests for search."""
        # GET /rest/api/search
        if endpoint == "/rest/api/search":
            cql = params.get("cql", "") if params else ""
            limit = int(params.get("limit", 25)) if params else 25
            start = int(params.get("start", 0)) if params else 0
            return self.search(cql, limit=limit, start=start)

        return None
