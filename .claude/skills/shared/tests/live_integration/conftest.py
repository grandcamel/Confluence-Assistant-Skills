"""
Confluence Assistant Skills - Live Integration Test Configuration

Session-scoped fixtures for test space and cleanup.
Function-scoped fixtures for individual test resources.

Usage:
    pytest .claude/skills/shared/tests/live_integration/ --profile development -v
    pytest --keep-space -v  # Don't delete test space after tests
    pytest --space-key EXISTING -v  # Use existing space
"""

import os
import sys
import uuid
import pytest
from pathlib import Path
from typing import Any, Dict, Generator, Optional

# Add shared lib to path
lib_path = Path(__file__).parent.parent.parent / 'scripts' / 'lib'
sys.path.insert(0, str(lib_path))

from confluence_client import ConfluenceClient
from config_manager import get_confluence_client


# =============================================================================
# Pytest Configuration (extends parent conftest.py)
# Note: --profile is already defined in parent conftest.py
# =============================================================================

def pytest_addoption(parser):
    """Add custom command-line options for live integration tests."""
    # Only add options not already defined in parent
    parser.addoption(
        "--keep-space",
        action="store_true",
        default=False,
        help="Keep the test space after tests complete (for debugging)"
    )
    parser.addoption(
        "--space-key",
        action="store",
        default=None,
        help="Use an existing space instead of creating a new one"
    )


def pytest_configure(config):
    """Register custom markers for live integration tests."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "confluence: mark test as Confluence test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "pages: mark test as page-related")
    config.addinivalue_line("markers", "spaces: mark test as space-related")
    config.addinivalue_line("markers", "search: mark test as search-related")
    config.addinivalue_line("markers", "comments: mark test as comment-related")
    config.addinivalue_line("markers", "attachments: mark test as attachment-related")
    config.addinivalue_line("markers", "labels: mark test as label-related")


# =============================================================================
# Session-Scoped Fixtures (created once per test session)
# =============================================================================

@pytest.fixture(scope="session")
def confluence_profile(request) -> str:
    """Get the Confluence profile from command line or environment."""
    profile = request.config.getoption("--profile")
    # Default to development if not specified
    return profile or os.environ.get("CONFLUENCE_PROFILE", "development")


@pytest.fixture(scope="session")
def keep_space(request) -> bool:
    """Check if we should keep the test space after tests."""
    return request.config.getoption("--keep-space")


@pytest.fixture(scope="session")
def existing_space_key(request) -> Optional[str]:
    """Get existing space key if provided."""
    return request.config.getoption("--space-key")


@pytest.fixture(scope="session")
def confluence_client(confluence_profile) -> Generator[ConfluenceClient, None, None]:
    """
    Create a Confluence client for the test session.

    Yields:
        Configured ConfluenceClient instance
    """
    client = get_confluence_client(profile=confluence_profile)

    # Verify connection
    test_result = client.test_connection()
    if not test_result.get('success'):
        pytest.fail(f"Failed to connect to Confluence: {test_result.get('error')}")

    print(f"\nConnected to Confluence as: {test_result.get('user')}")

    yield client


@pytest.fixture(scope="session")
def test_space(
    confluence_client: ConfluenceClient,
    keep_space: bool,
    existing_space_key: Optional[str]
) -> Generator[Dict[str, Any], None, None]:
    """
    Create a unique test space for the session.

    - Generated key: CAS + 6 random hex chars (e.g., CASA1B2C3)
    - Auto-deletes after tests (unless --keep-space flag)

    Yields:
        Dict with keys: id, key, name, homepageId, is_temporary
    """
    # Use existing space if provided
    if existing_space_key:
        spaces = list(confluence_client.paginate(
            '/api/v2/spaces',
            params={'keys': existing_space_key},
            operation='get existing space'
        ))
        if not spaces:
            pytest.fail(f"Existing space not found: {existing_space_key}")

        space = spaces[0]
        print(f"\nUsing existing space: {space['key']} ({space['name']})")
        yield {
            'id': space['id'],
            'key': space['key'],
            'name': space['name'],
            'homepageId': space.get('homepageId'),
            'is_temporary': False
        }
        return

    # Generate unique space key
    space_key = f"CAS{uuid.uuid4().hex[:6].upper()}"
    space_name = f"CAS Integration Test {space_key}"

    print(f"\nCreating test space: {space_key}")

    # Create the space (omit description as it can cause 500 errors in some configurations)
    space = confluence_client.post(
        '/api/v2/spaces',
        json_data={
            'key': space_key,
            'name': space_name
        },
        operation='create test space'
    )

    test_space_data = {
        'id': space['id'],
        'key': space['key'],
        'name': space['name'],
        'homepageId': space.get('homepageId'),
        'is_temporary': True
    }

    print(f"Created test space: {space_key} (ID: {space['id']})")

    yield test_space_data

    # Cleanup
    if not keep_space and test_space_data['is_temporary']:
        print(f"\nCleaning up test space: {space_key}")
        try:
            cleanup_space(confluence_client, space['id'], space_key)
            print(f"Deleted test space: {space_key}")
        except Exception as e:
            print(f"Warning: Failed to delete test space {space_key}: {e}")
    else:
        print(f"\nKeeping test space: {space_key}")


# =============================================================================
# Function-Scoped Fixtures (created fresh for each test)
# =============================================================================

@pytest.fixture(scope="function")
def test_page(
    confluence_client: ConfluenceClient,
    test_space: Dict[str, Any]
) -> Generator[Dict[str, Any], None, None]:
    """
    Create a test page for individual tests.

    Yields:
        Dict with page data including: id, title, spaceId, version
    """
    page_title = f"Test Page {uuid.uuid4().hex[:8]}"

    page = confluence_client.post(
        '/api/v2/pages',
        json_data={
            'spaceId': test_space['id'],
            'status': 'current',
            'title': page_title,
            'body': {
                'representation': 'storage',
                'value': '<p>Test page content for integration tests.</p>'
            }
        },
        operation='create test page'
    )

    yield page

    # Cleanup
    try:
        confluence_client.delete(
            f"/api/v2/pages/{page['id']}",
            operation='delete test page'
        )
    except Exception:
        pass  # Ignore cleanup errors


@pytest.fixture(scope="function")
def test_page_with_content(
    confluence_client: ConfluenceClient,
    test_space: Dict[str, Any]
) -> Generator[Dict[str, Any], None, None]:
    """
    Create a test page with rich content.

    Yields:
        Dict with page data
    """
    page_title = f"Rich Content Page {uuid.uuid4().hex[:8]}"

    content = """
    <h1>Test Heading</h1>
    <p>This is a paragraph with <strong>bold</strong> and <em>italic</em> text.</p>
    <ul>
        <li>List item 1</li>
        <li>List item 2</li>
        <li>List item 3</li>
    </ul>
    <ac:structured-macro ac:name="code">
        <ac:parameter ac:name="language">python</ac:parameter>
        <ac:plain-text-body><![CDATA[print("Hello, World!")]]></ac:plain-text-body>
    </ac:structured-macro>
    <p>End of test content.</p>
    """

    page = confluence_client.post(
        '/api/v2/pages',
        json_data={
            'spaceId': test_space['id'],
            'status': 'current',
            'title': page_title,
            'body': {
                'representation': 'storage',
                'value': content
            }
        },
        operation='create test page with content'
    )

    yield page

    # Cleanup
    try:
        confluence_client.delete(
            f"/api/v2/pages/{page['id']}",
            operation='delete test page'
        )
    except Exception:
        pass


@pytest.fixture(scope="function")
def test_child_page(
    confluence_client: ConfluenceClient,
    test_space: Dict[str, Any],
    test_page: Dict[str, Any]
) -> Generator[Dict[str, Any], None, None]:
    """
    Create a child page under test_page.

    Yields:
        Dict with child page data
    """
    child_title = f"Child Page {uuid.uuid4().hex[:8]}"

    child = confluence_client.post(
        '/api/v2/pages',
        json_data={
            'spaceId': test_space['id'],
            'parentId': test_page['id'],
            'status': 'current',
            'title': child_title,
            'body': {
                'representation': 'storage',
                'value': '<p>Child page content.</p>'
            }
        },
        operation='create child page'
    )

    yield child

    # Cleanup
    try:
        confluence_client.delete(
            f"/api/v2/pages/{child['id']}",
            operation='delete child page'
        )
    except Exception:
        pass


@pytest.fixture(scope="function")
def test_blogpost(
    confluence_client: ConfluenceClient,
    test_space: Dict[str, Any]
) -> Generator[Dict[str, Any], None, None]:
    """
    Create a test blog post.

    Yields:
        Dict with blog post data
    """
    post_title = f"Test Blog Post {uuid.uuid4().hex[:8]}"

    blogpost = confluence_client.post(
        '/api/v2/blogposts',
        json_data={
            'spaceId': test_space['id'],
            'status': 'current',
            'title': post_title,
            'body': {
                'representation': 'storage',
                'value': '<p>Test blog post content.</p>'
            }
        },
        operation='create test blogpost'
    )

    yield blogpost

    # Cleanup
    try:
        confluence_client.delete(
            f"/api/v2/blogposts/{blogpost['id']}",
            operation='delete test blogpost'
        )
    except Exception:
        pass


@pytest.fixture(scope="function")
def test_label() -> str:
    """Generate a unique test label."""
    return f"test-label-{uuid.uuid4().hex[:8]}"


# =============================================================================
# Cleanup Utilities
# =============================================================================

def delete_space_by_key(client: ConfluenceClient, space_key: str) -> None:
    """
    Delete a space using the v1 API (async operation).

    The v2 API doesn't support space deletion. The v1 API returns a long-running
    task ID for space deletion.

    Args:
        client: Confluence client
        space_key: Space key to delete
    """
    import time

    # Use v1 API for space deletion - returns async task
    response = client.session.delete(
        f"{client.base_url}/wiki/rest/api/space/{space_key}"
    )

    if response.status_code == 202:
        # Async deletion started - wait briefly for it to complete
        time.sleep(1)
    elif response.status_code == 204:
        # Immediate success
        pass
    elif response.status_code == 404:
        # Already deleted
        pass
    else:
        raise Exception(f"Failed to delete space: {response.status_code} - {response.text}")


def cleanup_space(client: ConfluenceClient, space_id: str, space_key: str = None) -> None:
    """
    Clean up all resources in a space before deletion.

    Args:
        client: Confluence client
        space_id: Space ID to clean up
        space_key: Space key (needed for v1 API deletion)
    """
    # Step 1: Delete all pages (children first, then parents)
    try:
        pages = list(client.paginate(
            '/api/v2/pages',
            params={'space-id': space_id, 'limit': 50},
            operation='list pages for cleanup'
        ))

        # Sort by depth (delete deepest first)
        # Simple approach: delete in reverse creation order
        for page in reversed(pages):
            try:
                client.delete(
                    f"/api/v2/pages/{page['id']}",
                    operation='cleanup page'
                )
            except Exception as e:
                print(f"  Warning: Could not delete page {page.get('title', page['id'])}: {e}")
    except Exception as e:
        print(f"  Warning: Could not list pages for cleanup: {e}")

    # Step 2: Delete all blog posts
    try:
        blogposts = list(client.paginate(
            '/api/v2/blogposts',
            params={'space-id': space_id, 'limit': 50},
            operation='list blogposts for cleanup'
        ))

        for post in blogposts:
            try:
                client.delete(
                    f"/api/v2/blogposts/{post['id']}",
                    operation='cleanup blogpost'
                )
            except Exception:
                pass
    except Exception:
        pass

    # Step 3: Delete the space using v1 API (v2 doesn't support space deletion)
    if space_key:
        delete_space_by_key(client, space_key)
    else:
        raise Exception("Space key required for deletion")


# =============================================================================
# Helper Fixtures
# =============================================================================

@pytest.fixture
def unique_title() -> str:
    """Generate a unique page title."""
    return f"Test Page {uuid.uuid4().hex[:8]}"


@pytest.fixture
def unique_space_key() -> str:
    """Generate a unique space key."""
    return f"CAS{uuid.uuid4().hex[:6].upper()}"
