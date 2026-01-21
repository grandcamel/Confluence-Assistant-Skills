"""
Test Utilities for Confluence Live Integration Tests

Provides helper functions and fluent builders for creating test data,
generating content, and making test assertions.

Usage:
    from test_utils import PageBuilder, generate_test_content, assert_page_exists

    # Build page data
    page_data = PageBuilder().with_title("Test").with_space_id("123").build()

    # Generate test content
    pages = generate_test_content(client, space_id="123", count=10)

    # Assert page exists
    page = assert_page_exists(client, page_id="12345")
"""

from __future__ import annotations

import json
import random
import string
import time
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from confluence_as import ConfluenceClient


# =============================================================================
# PageBuilder Fluent API
# =============================================================================

class PageBuilder:
    """
    Fluent builder for creating page data structures.

    Usage:
        page_data = (PageBuilder()
            .with_title("My Page")
            .with_space_id("123")
            .with_body("Content here")
            .build())
    """

    def __init__(self):
        self._title: Optional[str] = None
        self._space_id: Optional[str] = None
        self._parent_id: Optional[str] = None
        self._body: Optional[str] = None
        self._body_format: str = "storage"
        self._status: str = "current"
        self._labels: list[str] = []

    def with_title(self, title: str) -> "PageBuilder":
        """Set page title."""
        self._title = title
        return self

    def with_random_title(self, prefix: str = "Test Page") -> "PageBuilder":
        """Set random unique title."""
        self._title = f"{prefix} {uuid.uuid4().hex[:8]}"
        return self

    def with_space_id(self, space_id: str) -> "PageBuilder":
        """Set space ID."""
        self._space_id = space_id
        return self

    def with_parent_id(self, parent_id: str) -> "PageBuilder":
        """Set parent page ID."""
        self._parent_id = parent_id
        return self

    def with_body(self, body: str) -> "PageBuilder":
        """Set body content (converts markdown to storage if needed)."""
        self._body = body
        return self

    def with_storage_body(self, storage: str) -> "PageBuilder":
        """Set body as XHTML storage format."""
        self._body = storage
        self._body_format = "storage"
        return self

    def with_adf_body(self, adf: dict[str, Any]) -> "PageBuilder":
        """Set body as Atlassian Document Format."""
        self._body = json.dumps(adf)
        self._body_format = "atlas_doc_format"
        return self

    def with_status(self, status: str) -> "PageBuilder":
        """Set page status (current or draft)."""
        self._status = status
        return self

    def with_labels(self, labels: list[str]) -> "PageBuilder":
        """Set labels to add after creation."""
        self._labels = labels
        return self

    def build(self) -> dict[str, Any]:
        """Build the page creation payload."""
        if not self._title:
            raise ValueError("Title is required")
        if not self._space_id:
            raise ValueError("Space ID is required")

        data: dict[str, Any] = {
            "spaceId": self._space_id,
            "status": self._status,
            "title": self._title,
        }

        if self._parent_id:
            data["parentId"] = self._parent_id

        if self._body:
            data["body"] = {
                "representation": self._body_format,
                "value": self._body,
            }
        else:
            # Default empty content
            data["body"] = {
                "representation": "storage",
                "value": "<p>Test page content.</p>",
            }

        return data

    def build_and_create(self, client: "ConfluenceClient") -> dict[str, Any]:
        """Build and create the page via API."""
        data = self.build()
        page = client.post("/api/v2/pages", json_data=data, operation="create test page")

        # Add labels if specified
        if self._labels:
            for label in self._labels:
                client.post(
                    f"/api/v2/pages/{page['id']}/labels",
                    json_data={"name": label},
                    operation=f"add label '{label}'",
                )

        return page


# =============================================================================
# BlogPostBuilder Fluent API
# =============================================================================

class BlogPostBuilder:
    """
    Fluent builder for creating blog post data structures.

    Usage:
        post_data = (BlogPostBuilder()
            .with_title("My Blog Post")
            .with_space_id("123")
            .with_body("Content here")
            .build())
    """

    def __init__(self):
        self._title: Optional[str] = None
        self._space_id: Optional[str] = None
        self._body: Optional[str] = None
        self._body_format: str = "storage"
        self._status: str = "current"

    def with_title(self, title: str) -> "BlogPostBuilder":
        """Set blog post title."""
        self._title = title
        return self

    def with_random_title(self, prefix: str = "Test Blog Post") -> "BlogPostBuilder":
        """Set random unique title."""
        self._title = f"{prefix} {uuid.uuid4().hex[:8]}"
        return self

    def with_space_id(self, space_id: str) -> "BlogPostBuilder":
        """Set space ID."""
        self._space_id = space_id
        return self

    def with_body(self, body: str) -> "BlogPostBuilder":
        """Set body content."""
        self._body = body
        return self

    def with_status(self, status: str) -> "BlogPostBuilder":
        """Set blog post status."""
        self._status = status
        return self

    def build(self) -> dict[str, Any]:
        """Build the blog post creation payload."""
        if not self._title:
            raise ValueError("Title is required")
        if not self._space_id:
            raise ValueError("Space ID is required")

        data: dict[str, Any] = {
            "spaceId": self._space_id,
            "status": self._status,
            "title": self._title,
        }

        if self._body:
            data["body"] = {
                "representation": self._body_format,
                "value": self._body,
            }
        else:
            data["body"] = {
                "representation": "storage",
                "value": "<p>Test blog post content.</p>",
            }

        return data

    def build_and_create(self, client: "ConfluenceClient") -> dict[str, Any]:
        """Build and create the blog post via API."""
        data = self.build()
        return client.post("/api/v2/blogposts", json_data=data, operation="create test blog post")


# =============================================================================
# SpaceBuilder Fluent API
# =============================================================================

class SpaceBuilder:
    """
    Fluent builder for creating space data structures.

    Usage:
        space_data = (SpaceBuilder()
            .with_key("TEST")
            .with_name("Test Space")
            .build())
    """

    def __init__(self):
        self._key: Optional[str] = None
        self._name: Optional[str] = None
        self._description: Optional[str] = None

    def with_key(self, key: str) -> "SpaceBuilder":
        """Set space key."""
        self._key = key
        return self

    def with_random_key(self, prefix: str = "CAS") -> "SpaceBuilder":
        """Set random unique key."""
        self._key = f"{prefix}{uuid.uuid4().hex[:6].upper()}"
        return self

    def with_name(self, name: str) -> "SpaceBuilder":
        """Set space name."""
        self._name = name
        return self

    def with_description(self, description: str) -> "SpaceBuilder":
        """Set space description."""
        self._description = description
        return self

    def build(self) -> dict[str, Any]:
        """Build the space creation payload."""
        if not self._key:
            raise ValueError("Key is required")
        if not self._name:
            self._name = f"Test Space {self._key}"

        data: dict[str, Any] = {
            "key": self._key,
            "name": self._name,
        }

        if self._description:
            data["description"] = {
                "plain": {
                    "value": self._description,
                    "representation": "plain",
                }
            }

        return data

    def build_and_create(self, client: "ConfluenceClient") -> dict[str, Any]:
        """Build and create the space via API."""
        data = self.build()
        return client.post("/api/v2/spaces", json_data=data, operation="create test space")


# =============================================================================
# Content Generation
# =============================================================================

def generate_random_text(length: int = 100) -> str:
    """Generate random text content."""
    words = [
        "confluence", "page", "content", "test", "documentation",
        "wiki", "knowledge", "base", "article", "information",
        "share", "collaborate", "team", "project", "data",
    ]
    result = []
    while len(" ".join(result)) < length:
        result.append(random.choice(words))
    return " ".join(result)[:length]


def generate_xhtml_content(paragraphs: int = 3, include_heading: bool = True) -> str:
    """Generate random XHTML storage format content."""
    parts = []

    if include_heading:
        parts.append(f"<h1>Test Page {uuid.uuid4().hex[:8]}</h1>")

    for i in range(paragraphs):
        text = generate_random_text(random.randint(50, 200))
        parts.append(f"<p>{text}</p>")

    return "\n".join(parts)


def generate_test_content(
    client: "ConfluenceClient",
    space_id: str,
    count: int = 10,
    content_type: str = "page",
    with_labels: Optional[list[str]] = None,
    title_prefix: str = "Generated Test",
) -> list[dict[str, Any]]:
    """
    Generate multiple test pages or blog posts.

    Args:
        client: Confluence client
        space_id: Space ID to create content in
        count: Number of items to create
        content_type: "page" or "blogpost"
        with_labels: Labels to add to each item
        title_prefix: Prefix for titles

    Returns:
        List of created content items
    """
    created = []

    for i in range(count):
        title = f"{title_prefix} {i+1} {uuid.uuid4().hex[:6]}"
        body = generate_xhtml_content(paragraphs=random.randint(1, 5))

        if content_type == "page":
            builder = (PageBuilder()
                .with_title(title)
                .with_space_id(space_id)
                .with_storage_body(body))
            if with_labels:
                builder.with_labels(with_labels)
            item = builder.build_and_create(client)
        else:
            builder = (BlogPostBuilder()
                .with_title(title)
                .with_space_id(space_id)
                .with_body(body))
            item = builder.build_and_create(client)
            # Add labels separately for blog posts
            if with_labels:
                for label in with_labels:
                    client.post(
                        f"/api/v2/blogposts/{item['id']}/labels",
                        json_data={"name": label},
                        operation=f"add label '{label}'",
                    )

        created.append(item)

    return created


# =============================================================================
# Wait Utilities
# =============================================================================

def wait_for_indexing(
    client: "ConfluenceClient",
    space_id: str,
    min_pages: int = 1,
    timeout: int = 60,
    poll_interval: float = 2.0,
) -> bool:
    """
    Wait for search indexing to complete.

    Args:
        client: Confluence client
        space_id: Space ID to check
        min_pages: Minimum number of pages expected
        timeout: Maximum wait time in seconds
        poll_interval: Time between checks

    Returns:
        True if indexing completed within timeout
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            # Search for pages in the space
            response = client.get(
                "/rest/api/search",
                params={
                    "cql": f"space.id = {space_id} AND type = page",
                    "limit": 1,
                },
                operation="check indexing",
            )

            total = response.get("totalSize", 0)
            if total >= min_pages:
                return True

        except Exception:
            pass

        time.sleep(poll_interval)

    return False


def wait_for_condition(
    condition_fn,
    timeout: int = 30,
    poll_interval: float = 1.0,
    message: str = "Condition not met",
) -> Any:
    """
    Wait for a condition to be true.

    Args:
        condition_fn: Function that returns truthy value when condition is met
        timeout: Maximum wait time in seconds
        poll_interval: Time between checks
        message: Error message if timeout

    Returns:
        The result of condition_fn when it returns truthy

    Raises:
        TimeoutError: If condition not met within timeout
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        result = condition_fn()
        if result:
            return result
        time.sleep(poll_interval)

    raise TimeoutError(f"{message} (timeout={timeout}s)")


# =============================================================================
# Assertion Helpers
# =============================================================================

def assert_page_exists(
    client: "ConfluenceClient",
    page_id: str,
    expected_title: Optional[str] = None,
) -> dict[str, Any]:
    """
    Assert that a page exists and optionally verify its title.

    Args:
        client: Confluence client
        page_id: Page ID to check
        expected_title: Expected page title (optional)

    Returns:
        Page data if it exists

    Raises:
        AssertionError: If page doesn't exist or title doesn't match
    """
    try:
        page = client.get(f"/api/v2/pages/{page_id}", operation="get page")
    except Exception as e:
        raise AssertionError(f"Page {page_id} does not exist: {e}") from e

    if expected_title and page.get("title") != expected_title:
        raise AssertionError(
            f"Page title mismatch: expected '{expected_title}', got '{page.get('title')}'"
        )

    return page


def assert_page_not_exists(client: "ConfluenceClient", page_id: str) -> None:
    """
    Assert that a page does not exist.

    Args:
        client: Confluence client
        page_id: Page ID to check

    Raises:
        AssertionError: If page exists
    """
    try:
        client.get(f"/api/v2/pages/{page_id}", operation="get page")
        raise AssertionError(f"Page {page_id} should not exist but does")
    except Exception as e:
        if "404" not in str(e):
            raise


def assert_search_returns_results(
    client: "ConfluenceClient",
    cql: str,
    min_count: int = 1,
    timeout: int = 30,
) -> list[dict[str, Any]]:
    """
    Assert that a CQL search returns at least min_count results.

    Waits for search indexing with retry.

    Args:
        client: Confluence client
        cql: CQL query string
        min_count: Minimum expected results
        timeout: Maximum wait time

    Returns:
        Search results

    Raises:
        AssertionError: If not enough results found
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            response = client.get(
                "/rest/api/search",
                params={"cql": cql, "limit": 100},
                operation="search",
            )

            results = response.get("results", [])
            if len(results) >= min_count:
                return results

        except Exception:
            pass

        time.sleep(2)

    raise AssertionError(
        f"Search '{cql}' returned fewer than {min_count} results (timeout={timeout}s)"
    )


def assert_search_returns_empty(
    client: "ConfluenceClient",
    cql: str,
) -> None:
    """
    Assert that a CQL search returns no results.

    Args:
        client: Confluence client
        cql: CQL query string

    Raises:
        AssertionError: If results found
    """
    response = client.get(
        "/rest/api/search",
        params={"cql": cql, "limit": 1},
        operation="search",
    )

    results = response.get("results", [])
    if results:
        raise AssertionError(f"Search '{cql}' should be empty but returned {len(results)} results")


def assert_label_exists(
    client: "ConfluenceClient",
    page_id: str,
    label_name: str,
) -> dict[str, Any]:
    """
    Assert that a label exists on a page.

    Args:
        client: Confluence client
        page_id: Page ID
        label_name: Label name to check

    Returns:
        Label data

    Raises:
        AssertionError: If label not found
    """
    labels = list(client.paginate(
        f"/api/v2/pages/{page_id}/labels",
        operation="get labels",
    ))

    for label in labels:
        if label.get("name") == label_name:
            return label

    raise AssertionError(f"Label '{label_name}' not found on page {page_id}")


def assert_label_not_exists(
    client: "ConfluenceClient",
    page_id: str,
    label_name: str,
) -> None:
    """
    Assert that a label does not exist on a page.

    Args:
        client: Confluence client
        page_id: Page ID
        label_name: Label name to check

    Raises:
        AssertionError: If label found
    """
    labels = list(client.paginate(
        f"/api/v2/pages/{page_id}/labels",
        operation="get labels",
    ))

    for label in labels:
        if label.get("name") == label_name:
            raise AssertionError(f"Label '{label_name}' should not exist on page {page_id}")


# =============================================================================
# Cleanup Utilities
# =============================================================================

def cleanup_test_pages(
    client: "ConfluenceClient",
    space_id: str,
    title_prefix: str = "Test",
) -> int:
    """
    Delete all pages with a specific title prefix in a space.

    Args:
        client: Confluence client
        space_id: Space ID
        title_prefix: Only delete pages with this title prefix

    Returns:
        Number of pages deleted
    """
    deleted = 0

    pages = list(client.paginate(
        "/api/v2/pages",
        params={"space-id": space_id, "limit": 100},
        operation="list pages for cleanup",
    ))

    for page in pages:
        if page.get("title", "").startswith(title_prefix):
            try:
                client.delete(f"/api/v2/pages/{page['id']}", operation="cleanup page")
                deleted += 1
            except Exception:
                pass

    return deleted


def cleanup_test_labels(
    client: "ConfluenceClient",
    page_id: str,
    label_prefix: str = "test-",
) -> int:
    """
    Remove all labels with a specific prefix from a page.

    Args:
        client: Confluence client
        page_id: Page ID
        label_prefix: Only remove labels with this prefix

    Returns:
        Number of labels removed
    """
    removed = 0

    labels = list(client.paginate(
        f"/api/v2/pages/{page_id}/labels",
        operation="get labels for cleanup",
    ))

    for label in labels:
        if label.get("name", "").startswith(label_prefix):
            try:
                client.delete(
                    f"/api/v2/pages/{page_id}/labels/{label['id']}",
                    operation="cleanup label",
                )
                removed += 1
            except Exception:
                pass

    return removed


# =============================================================================
# Version Detection
# =============================================================================

def get_confluence_version(client: "ConfluenceClient") -> tuple[int, int, int]:
    """
    Get Confluence version as tuple.

    Returns:
        Tuple of (major, minor, patch) version numbers
    """
    try:
        info = client.get("/rest/api/settings/systemInfo", operation="get version")
        version_str = info.get("version", "0.0.0")
        parts = version_str.split(".")[:3]
        return tuple(int(p) for p in parts)
    except Exception:
        return (0, 0, 0)


def skip_if_version_below(
    client: "ConfluenceClient",
    min_version: tuple[int, int, int],
    reason: str = "",
) -> None:
    """
    Skip test if Confluence version is below minimum.

    Args:
        client: Confluence client
        min_version: Minimum version tuple (major, minor, patch)
        reason: Skip reason message

    Raises:
        pytest.skip: If version is below minimum
    """
    import pytest

    current = get_confluence_version(client)

    if current < min_version:
        version_str = ".".join(str(v) for v in min_version)
        current_str = ".".join(str(v) for v in current)
        msg = reason or f"Requires Confluence {version_str}+ (current: {current_str})"
        pytest.skip(msg)


def is_confluence_cloud(client: "ConfluenceClient") -> bool:
    """
    Check if connected to Confluence Cloud (vs Server/Data Center).

    Returns:
        True if Confluence Cloud
    """
    try:
        info = client.get("/rest/api/settings/systemInfo", operation="check cloud")
        # Cloud typically has different deployment type or no on-prem indicators
        return "Cloud" in info.get("deploymentType", "") or not info.get("buildNumber")
    except Exception:
        return False
