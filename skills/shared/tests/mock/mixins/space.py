"""
Space Mixin for Mock Confluence Client

Provides mock behavior for space management operations.
"""

from __future__ import annotations

import re
from typing import Any, Optional


class SpaceMixin:
    """
    Mock behavior for space operations.

    Maintains an in-memory space store for realistic CRUD behavior.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._spaces: dict[str, dict[str, Any]] = {}

    # =========================================================================
    # Space Store Management
    # =========================================================================

    def add_space(
        self,
        space_id: Optional[str] = None,
        key: str = "TEST",
        name: str = "Test Space",
        space_type: str = "global",
        status: str = "current",
        description: str = "",
        homepage_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Add a space to the mock store.

        Returns the space data dict.
        """
        if space_id is None:
            space_id = self.generate_id()

        space = {
            "id": space_id,
            "key": key,
            "name": name,
            "type": space_type,
            "status": status,
            "homepageId": homepage_id,
            "description": {
                "plain": {"value": description, "representation": "plain"}
            } if description else None,
            "_links": {"webui": f"/wiki/spaces/{key}"},
        }

        self._spaces[space_id] = space
        # Also index by key for lookup
        self._spaces[key] = space

        return space

    def get_space(self, space_id_or_key: str) -> Optional[dict[str, Any]]:
        """Get a space from the mock store by ID or key."""
        return self._spaces.get(space_id_or_key)

    def update_space(
        self,
        space_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        homepage_id: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """Update a space in the mock store."""
        space = self._spaces.get(space_id)
        if not space:
            return None

        if name:
            space["name"] = name
        if description is not None:
            space["description"] = {
                "plain": {"value": description, "representation": "plain"}
            }
        if homepage_id:
            space["homepageId"] = homepage_id

        return space

    def delete_space(self, space_id_or_key: str) -> bool:
        """Delete a space from the mock store."""
        space = self._spaces.get(space_id_or_key)
        if space:
            # Remove by both ID and key
            self._spaces.pop(space["id"], None)
            self._spaces.pop(space["key"], None)
            return True
        return False

    def list_spaces(
        self,
        space_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """List spaces matching filters."""
        # Get unique spaces (avoid duplicates from ID/key indexing)
        seen_ids = set()
        results = []
        for space in self._spaces.values():
            if space["id"] not in seen_ids:
                seen_ids.add(space["id"])
                results.append(space)

        if space_type:
            results = [s for s in results if s["type"] == space_type]
        if status:
            results = [s for s in results if s["status"] == status]

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
        """Handle GET requests for spaces."""
        # GET /api/v2/spaces/{id}
        match = re.match(r"/api/v2/spaces/(\d+)$", endpoint)
        if match:
            space_id = match.group(1)
            space = self.get_space(space_id)
            if space:
                return space
            raise self._not_found_error(f"Space {space_id} not found")

        # GET /api/v2/spaces (list)
        if endpoint == "/api/v2/spaces":
            keys = params.get("keys") if params else None
            if keys:
                # Filter by specific keys
                spaces = [self.get_space(k) for k in keys.split(",") if self.get_space(k)]
                return {"results": spaces}

            space_type = params.get("type") if params else None
            spaces = self.list_spaces(space_type=space_type)
            return {"results": spaces}

        return None

    def _handle_post(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]],
        data: Optional[dict[str, Any]],
    ) -> Optional[dict[str, Any]]:
        """Handle POST requests for spaces."""
        # POST /api/v2/spaces
        if endpoint == "/api/v2/spaces" and data:
            desc = ""
            if data.get("description"):
                desc = data["description"].get("plain", {}).get("value", "")

            return self.add_space(
                key=data.get("key", "NEW"),
                name=data.get("name", "New Space"),
                description=desc,
            )

        return None

    def _handle_put(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]],
        data: Optional[dict[str, Any]],
    ) -> Optional[dict[str, Any]]:
        """Handle PUT requests for spaces."""
        # PUT /api/v2/spaces/{id}
        match = re.match(r"/api/v2/spaces/(\d+)$", endpoint)
        if match and data:
            space_id = match.group(1)
            desc = None
            if data.get("description"):
                desc = data["description"].get("plain", {}).get("value")

            space = self.update_space(
                space_id=space_id,
                name=data.get("name"),
                description=desc,
                homepage_id=data.get("homepageId"),
            )
            if space:
                return space
            raise self._not_found_error(f"Space {space_id} not found")

        return None

    def _handle_delete(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]],
        data: Optional[dict[str, Any]],
    ) -> Optional[dict[str, Any]]:
        """Handle DELETE requests for spaces."""
        # Note: v2 API doesn't support space deletion, but we mock it anyway
        match = re.match(r"/api/v2/spaces/(\d+)$", endpoint)
        if match:
            space_id = match.group(1)
            if self.delete_space(space_id):
                return {}
            raise self._not_found_error(f"Space {space_id} not found")

        # v1 API space deletion
        match = re.match(r"/rest/api/space/([A-Z0-9]+)$", endpoint)
        if match:
            space_key = match.group(1)
            if self.delete_space(space_key):
                return {}
            raise self._not_found_error(f"Space {space_key} not found")

        return None

    def _not_found_error(self, message: str) -> Exception:
        """Create a not found error."""
        try:
            from confluence_as import NotFoundError
            return NotFoundError(message)
        except ImportError:
            return Exception(f"404: {message}")
