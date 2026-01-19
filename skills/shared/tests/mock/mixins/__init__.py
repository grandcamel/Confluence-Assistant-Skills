"""
Mock Client Mixins

Each mixin provides mock behavior for a specific Confluence API domain.
Combine mixins to create custom mock clients with specific capabilities.
"""

from .page import PageMixin
from .space import SpaceMixin
from .search import SearchMixin
from .content import ContentMixin
from .label import LabelMixin
from .comment import CommentMixin
from .attachment import AttachmentMixin

__all__ = [
    "PageMixin",
    "SpaceMixin",
    "SearchMixin",
    "ContentMixin",
    "LabelMixin",
    "CommentMixin",
    "AttachmentMixin",
]
