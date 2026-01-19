"""
Mock Client Architecture for Confluence Assistant Skills

This module provides a composable mock client system using mixins.
Each mixin provides mock behavior for a specific API domain.

Usage:
    from mock import MockConfluenceClient

    # Full mock client with all capabilities
    client = MockConfluenceClient()
    client.add_page(page_id="123", title="Test Page")
    page = client.get("/api/v2/pages/123")

    # Custom mock with only specific mixins
    from mock.base import MockConfluenceClientBase
    from mock.mixins import PageMixin, SearchMixin

    class CustomMockClient(PageMixin, SearchMixin, MockConfluenceClientBase):
        pass

    client = CustomMockClient()

Available Mixins:
    - PageMixin: Page CRUD operations
    - SpaceMixin: Space management
    - SearchMixin: CQL search
    - ContentMixin: Generic content operations
    - LabelMixin: Label operations
    - CommentMixin: Comment operations
    - AttachmentMixin: Attachment operations
"""

from .base import MockConfluenceClientBase
from .mixins import (
    AttachmentMixin,
    CommentMixin,
    ContentMixin,
    LabelMixin,
    PageMixin,
    SearchMixin,
    SpaceMixin,
)


class MockConfluenceClient(
    PageMixin,
    SpaceMixin,
    SearchMixin,
    ContentMixin,
    LabelMixin,
    CommentMixin,
    AttachmentMixin,
    MockConfluenceClientBase,
):
    """
    Full-featured mock Confluence client.

    Combines all available mixins into a single mock client.
    Use this for tests that need comprehensive mocking.
    """
    pass


__all__ = [
    "MockConfluenceClient",
    "MockConfluenceClientBase",
    "PageMixin",
    "SpaceMixin",
    "SearchMixin",
    "ContentMixin",
    "LabelMixin",
    "CommentMixin",
    "AttachmentMixin",
]
