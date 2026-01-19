"""
Shared Pytest Fixtures for Confluence Live Integration Tests

This module provides reusable fixtures that can be imported by skill-specific
conftest.py files using pytest_plugins.

Usage in skill conftest.py:
    # Import all fixtures from this module
    pytest_plugins = ["fixtures"]

    # Or import specific fixtures
    from fixtures import confluence_client, test_space, test_page

Available Fixtures:
    Session-Scoped (shared across all tests):
        - confluence_connection: Docker container or external connection
        - confluence_client: Configured ConfluenceClient
        - test_space: Test space (auto-created/cleaned)
        - confluence_info: Server/Cloud info dict

    Function-Scoped (fresh per test):
        - test_page: Simple test page
        - test_page_with_content: Page with rich content
        - test_child_page: Child page under test_page
        - test_blogpost: Test blog post
        - test_label: Unique label string
        - fresh_test_data: Isolated test content (10 pages)

    Helpers:
        - page_factory: Factory for creating pages
        - search_helper: Simplified search interface
        - cleanup_tracker: Track resources for cleanup
"""

from __future__ import annotations

import contextlib
import uuid
from collections.abc import Generator
from typing import TYPE_CHECKING, Any, Callable, Optional

import pytest

if TYPE_CHECKING:
    from confluence_assistant_skills_lib import ConfluenceClient

from confluence_container import ConfluenceConnection, get_confluence_connection


# =============================================================================
# Session-Scoped Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def confluence_connection() -> Generator[ConfluenceConnection, None, None]:
    """
    Get or create Confluence connection for the test session.

    Automatically uses Docker container or external instance based on
    environment variables.

    Yields:
        ConfluenceConnection instance
    """
    connection = get_confluence_connection()
    connection.start()

    yield connection

    connection.stop()


@pytest.fixture(scope="session")
def confluence_client(confluence_connection: ConfluenceConnection) -> "ConfluenceClient":
    """
    Get configured ConfluenceClient for the test session.

    Yields:
        ConfluenceClient instance
    """
    return confluence_connection.get_client()


@pytest.fixture(scope="session")
def confluence_info(confluence_client: "ConfluenceClient") -> dict[str, Any]:
    """
    Get Confluence server information.

    Returns:
        Dict with version, deploymentType, etc.
    """
    try:
        return confluence_client.get("/rest/api/settings/systemInfo", operation="get info")
    except Exception:
        return {}


@pytest.fixture(scope="session")
def test_space(
    confluence_client: "ConfluenceClient",
    request,
) -> Generator[dict[str, Any], None, None]:
    """
    Create or use existing test space for the session.

    Uses --space-key option if provided, otherwise creates a temporary space.
    Automatically cleaned up after all tests (unless --keep-space).

    Yields:
        Dict with: id, key, name, homepageId, is_temporary
    """
    # Check for existing space option
    existing_key = request.config.getoption("--space-key", None)
    keep_space = request.config.getoption("--keep-space", False)

    if existing_key:
        # Use existing space
        spaces = list(confluence_client.paginate(
            "/api/v2/spaces",
            params={"keys": existing_key},
            operation="get existing space",
        ))

        if not spaces:
            pytest.fail(f"Existing space not found: {existing_key}")

        space = spaces[0]
        print(f"\n[fixture] Using existing space: {space['key']}")

        yield {
            "id": space["id"],
            "key": space["key"],
            "name": space["name"],
            "homepageId": space.get("homepageId"),
            "is_temporary": False,
        }
        return

    # Create temporary space
    space_key = f"CAS{uuid.uuid4().hex[:6].upper()}"
    space_name = f"CAS Test {space_key}"

    print(f"\n[fixture] Creating test space: {space_key}")

    space = confluence_client.post(
        "/api/v2/spaces",
        json_data={"key": space_key, "name": space_name},
        operation="create test space",
    )

    test_space_data = {
        "id": space["id"],
        "key": space["key"],
        "name": space["name"],
        "homepageId": space.get("homepageId"),
        "is_temporary": True,
    }

    yield test_space_data

    # Cleanup
    if not keep_space and test_space_data["is_temporary"]:
        print(f"\n[fixture] Cleaning up test space: {space_key}")
        try:
            _cleanup_space(confluence_client, space["id"], space_key)
        except Exception as e:
            print(f"[fixture] Warning: Failed to cleanup space: {e}")
    else:
        print(f"\n[fixture] Keeping test space: {space_key}")


# =============================================================================
# Function-Scoped Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def test_page(
    confluence_client: "ConfluenceClient",
    test_space: dict[str, Any],
) -> Generator[dict[str, Any], None, None]:
    """
    Create a simple test page for individual tests.

    Automatically cleaned up after test.

    Yields:
        Page data dict
    """
    page_title = f"Test Page {uuid.uuid4().hex[:8]}"

    page = confluence_client.post(
        "/api/v2/pages",
        json_data={
            "spaceId": test_space["id"],
            "status": "current",
            "title": page_title,
            "body": {
                "representation": "storage",
                "value": "<p>Test page content.</p>",
            },
        },
        operation="create test page",
    )

    yield page

    # Cleanup
    with contextlib.suppress(Exception):
        confluence_client.delete(f"/api/v2/pages/{page['id']}", operation="cleanup test page")


@pytest.fixture(scope="function")
def test_page_with_content(
    confluence_client: "ConfluenceClient",
    test_space: dict[str, Any],
) -> Generator[dict[str, Any], None, None]:
    """
    Create a test page with rich content.

    Includes headings, paragraphs, lists, and code blocks.

    Yields:
        Page data dict
    """
    page_title = f"Rich Content Page {uuid.uuid4().hex[:8]}"

    content = """
    <h1>Test Heading Level 1</h1>
    <p>This is an introductory paragraph with <strong>bold</strong> and <em>italic</em> text.</p>

    <h2>Subheading Level 2</h2>
    <ul>
        <li>List item one</li>
        <li>List item two with <a href="https://example.com">a link</a></li>
        <li>List item three</li>
    </ul>

    <h3>Code Example</h3>
    <ac:structured-macro ac:name="code">
        <ac:parameter ac:name="language">python</ac:parameter>
        <ac:plain-text-body><![CDATA[def hello():
    print("Hello, World!")
]]></ac:plain-text-body>
    </ac:structured-macro>

    <p>End of test content.</p>
    """

    page = confluence_client.post(
        "/api/v2/pages",
        json_data={
            "spaceId": test_space["id"],
            "status": "current",
            "title": page_title,
            "body": {"representation": "storage", "value": content.strip()},
        },
        operation="create rich test page",
    )

    yield page

    with contextlib.suppress(Exception):
        confluence_client.delete(f"/api/v2/pages/{page['id']}", operation="cleanup rich test page")


@pytest.fixture(scope="function")
def test_child_page(
    confluence_client: "ConfluenceClient",
    test_space: dict[str, Any],
    test_page: dict[str, Any],
) -> Generator[dict[str, Any], None, None]:
    """
    Create a child page under test_page.

    Yields:
        Child page data dict
    """
    child_title = f"Child Page {uuid.uuid4().hex[:8]}"

    child = confluence_client.post(
        "/api/v2/pages",
        json_data={
            "spaceId": test_space["id"],
            "parentId": test_page["id"],
            "status": "current",
            "title": child_title,
            "body": {
                "representation": "storage",
                "value": "<p>Child page content.</p>",
            },
        },
        operation="create child page",
    )

    yield child

    with contextlib.suppress(Exception):
        confluence_client.delete(f"/api/v2/pages/{child['id']}", operation="cleanup child page")


@pytest.fixture(scope="function")
def test_blogpost(
    confluence_client: "ConfluenceClient",
    test_space: dict[str, Any],
) -> Generator[dict[str, Any], None, None]:
    """
    Create a test blog post.

    Yields:
        Blog post data dict
    """
    post_title = f"Test Blog Post {uuid.uuid4().hex[:8]}"

    blogpost = confluence_client.post(
        "/api/v2/blogposts",
        json_data={
            "spaceId": test_space["id"],
            "status": "current",
            "title": post_title,
            "body": {
                "representation": "storage",
                "value": "<p>Test blog post content.</p>",
            },
        },
        operation="create test blogpost",
    )

    yield blogpost

    with contextlib.suppress(Exception):
        confluence_client.delete(f"/api/v2/blogposts/{blogpost['id']}", operation="cleanup blogpost")


@pytest.fixture(scope="function")
def test_label() -> str:
    """Generate a unique test label."""
    return f"test-label-{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="function")
def fresh_test_data(
    confluence_client: "ConfluenceClient",
    test_space: dict[str, Any],
) -> Generator[list[dict[str, Any]], None, None]:
    """
    Create fresh, isolated test data for a single test.

    Creates 10 pages with unique labels for isolation.

    Yields:
        List of created page dicts
    """
    from test_utils import PageBuilder

    unique_label = f"fresh-{uuid.uuid4().hex[:8]}"
    pages = []

    for i in range(10):
        page = (PageBuilder()
            .with_random_title(f"Fresh Data {i}")
            .with_space_id(test_space["id"])
            .with_labels([unique_label, f"page-{i}"])
            .build_and_create(confluence_client))
        pages.append(page)

    yield pages

    # Cleanup
    for page in pages:
        with contextlib.suppress(Exception):
            confluence_client.delete(f"/api/v2/pages/{page['id']}", operation="cleanup fresh data")


# =============================================================================
# Factory Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def page_factory(
    confluence_client: "ConfluenceClient",
    test_space: dict[str, Any],
) -> Generator[Callable[..., dict[str, Any]], None, None]:
    """
    Factory for creating test pages with automatic cleanup.

    Usage:
        def test_something(page_factory):
            page1 = page_factory(title="Page 1")
            page2 = page_factory(title="Page 2", parent_id=page1["id"])

    Yields:
        Function that creates pages
    """
    created_pages = []

    def create_page(
        title: Optional[str] = None,
        body: str = "<p>Test content</p>",
        parent_id: Optional[str] = None,
        labels: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        if title is None:
            title = f"Factory Page {uuid.uuid4().hex[:8]}"

        data = {
            "spaceId": test_space["id"],
            "status": "current",
            "title": title,
            "body": {"representation": "storage", "value": body},
        }

        if parent_id:
            data["parentId"] = parent_id

        page = confluence_client.post("/api/v2/pages", json_data=data, operation="create factory page")
        created_pages.append(page)

        # Add labels if specified
        if labels:
            for label in labels:
                confluence_client.post(
                    f"/api/v2/pages/{page['id']}/labels",
                    json_data={"name": label},
                    operation=f"add label '{label}'",
                )

        return page

    yield create_page

    # Cleanup all created pages
    for page in reversed(created_pages):
        with contextlib.suppress(Exception):
            confluence_client.delete(f"/api/v2/pages/{page['id']}", operation="cleanup factory page")


@pytest.fixture(scope="function")
def search_helper(confluence_client: "ConfluenceClient"):
    """
    Simplified search interface for tests.

    Usage:
        def test_search(search_helper):
            results = search_helper.search("space = TEST")
            assert len(results) > 0

    Yields:
        SearchHelper instance
    """
    class SearchHelper:
        def __init__(self, client: "ConfluenceClient"):
            self._client = client

        def search(
            self,
            cql: str,
            limit: int = 25,
            expand: Optional[str] = None,
        ) -> list[dict[str, Any]]:
            """Execute CQL search and return results."""
            params = {"cql": cql, "limit": limit}
            if expand:
                params["expand"] = expand

            response = self._client.get("/rest/api/search", params=params, operation="search")
            return response.get("results", [])

        def search_pages(self, space_key: str, label: Optional[str] = None) -> list[dict[str, Any]]:
            """Search for pages in a space."""
            cql = f'space = "{space_key}" AND type = page'
            if label:
                cql += f' AND label = "{label}"'
            return self.search(cql)

        def wait_for_results(
            self,
            cql: str,
            min_count: int = 1,
            timeout: int = 30,
        ) -> list[dict[str, Any]]:
            """Wait for search to return at least min_count results."""
            import time
            start_time = time.time()

            while time.time() - start_time < timeout:
                results = self.search(cql)
                if len(results) >= min_count:
                    return results
                time.sleep(2)

            raise TimeoutError(f"Search did not return {min_count} results within {timeout}s")

    return SearchHelper(confluence_client)


@pytest.fixture(scope="function")
def cleanup_tracker():
    """
    Track resources for manual cleanup.

    Usage:
        def test_with_cleanup(cleanup_tracker, confluence_client):
            page = create_page()
            cleanup_tracker.add("page", page["id"])

            # If test fails, cleanup still runs
    """
    class CleanupTracker:
        def __init__(self):
            self._items: list[tuple[str, str]] = []

        def add(self, resource_type: str, resource_id: str) -> None:
            """Track a resource for cleanup."""
            self._items.append((resource_type, resource_id))

        def cleanup(self, client: "ConfluenceClient") -> None:
            """Clean up all tracked resources."""
            for resource_type, resource_id in reversed(self._items):
                try:
                    if resource_type == "page":
                        client.delete(f"/api/v2/pages/{resource_id}", operation="cleanup")
                    elif resource_type == "blogpost":
                        client.delete(f"/api/v2/blogposts/{resource_id}", operation="cleanup")
                    elif resource_type == "space":
                        _cleanup_space(client, resource_id, None)
                except Exception:
                    pass

            self._items.clear()

    return CleanupTracker()


# =============================================================================
# Helper Functions
# =============================================================================

def _cleanup_space(
    client: "ConfluenceClient",
    space_id: str,
    space_key: Optional[str],
) -> None:
    """
    Clean up all resources in a space before deletion.

    Deletes pages (children first), blog posts, then the space itself.
    """
    import time

    # Delete all pages (children first)
    try:
        pages = list(client.paginate(
            "/api/v2/pages",
            params={"space-id": space_id, "limit": 100},
            operation="list pages for cleanup",
        ))

        # Sort by depth approximation (delete deeper pages first)
        for page in reversed(pages):
            with contextlib.suppress(Exception):
                client.delete(f"/api/v2/pages/{page['id']}", operation="cleanup page")
    except Exception:
        pass

    # Delete all blog posts
    try:
        blogposts = list(client.paginate(
            "/api/v2/blogposts",
            params={"space-id": space_id, "limit": 100},
            operation="list blogposts for cleanup",
        ))

        for post in blogposts:
            with contextlib.suppress(Exception):
                client.delete(f"/api/v2/blogposts/{post['id']}", operation="cleanup blogpost")
    except Exception:
        pass

    # Delete the space using v1 API (v2 doesn't support space deletion)
    if space_key:
        try:
            response = client.session.delete(
                f"{client.base_url}/wiki/rest/api/space/{space_key}"
            )
            if response.status_code == 202:
                # Async deletion - wait briefly
                time.sleep(2)
        except Exception:
            pass
