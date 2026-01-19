"""
Live integration test infrastructure for Confluence Assistant Skills.

This package provides fixtures and utilities for testing against a real
Confluence instance (Cloud or Data Center).

Usage in skill tests:
    # In your skill's tests/live_integration/conftest.py
    pytest_plugins = ["fixtures"]

Environment Variables:
    CONFLUENCE_TEST_URL: Confluence instance URL
    CONFLUENCE_TEST_EMAIL: User email for authentication
    CONFLUENCE_TEST_TOKEN: API token for authentication
    CONFLUENCE_TEST_SPACE: Test space key (default: SKILLSTEST)

Builders:
    PageBuilder: Fluent API for creating test pages

        page_data = (PageBuilder()
            .with_title("Test Page")
            .with_space_id("123")
            .with_body("Content here")
            .build())

    BlogPostBuilder: Fluent API for creating test blog posts
    SpaceBuilder: Fluent API for creating test spaces
"""

from .confluence_container import (
    ConfluenceConnection,
    ConfluenceContainer,
    get_confluence_connection,
)
from .test_utils import (
    BlogPostBuilder,
    PageBuilder,
    SpaceBuilder,
    assert_label_exists,
    assert_label_not_exists,
    assert_page_exists,
    assert_page_not_exists,
    assert_search_returns_empty,
    assert_search_returns_results,
    cleanup_test_labels,
    cleanup_test_pages,
    generate_random_text,
    generate_test_content,
    generate_xhtml_content,
    get_confluence_version,
    is_confluence_cloud,
    skip_if_version_below,
    wait_for_condition,
    wait_for_indexing,
)

__all__ = [
    # Connection
    "ConfluenceConnection",
    "ConfluenceContainer",
    "get_confluence_connection",
    # Builders
    "PageBuilder",
    "BlogPostBuilder",
    "SpaceBuilder",
    # Content generation
    "generate_random_text",
    "generate_xhtml_content",
    "generate_test_content",
    # Wait utilities
    "wait_for_indexing",
    "wait_for_condition",
    # Assertions
    "assert_page_exists",
    "assert_page_not_exists",
    "assert_search_returns_results",
    "assert_search_returns_empty",
    "assert_label_exists",
    "assert_label_not_exists",
    # Cleanup
    "cleanup_test_pages",
    "cleanup_test_labels",
    # Version detection
    "get_confluence_version",
    "skip_if_version_below",
    "is_confluence_cloud",
]
