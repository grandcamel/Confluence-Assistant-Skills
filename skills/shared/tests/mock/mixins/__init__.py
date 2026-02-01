"""
Mock Client Mixins

Each mixin provides mock behavior for a specific Confluence API domain.
Combine mixins to create custom mock clients with specific capabilities.
"""

from .attachment import AttachmentMixin
from .comment import CommentMixin
from .content import ContentMixin
from .label import LabelMixin
from .page import PageMixin
from .search import SearchMixin
from .space import SpaceMixin

__all__ = [
    "AttachmentMixin",
    "CommentMixin",
    "ContentMixin",
    "LabelMixin",
    "PageMixin",
    "SearchMixin",
    "SpaceMixin",
]
