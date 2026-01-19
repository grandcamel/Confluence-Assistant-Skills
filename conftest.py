"""
Shared pytest fixtures for all Confluence Assistant Skills tests.

Provides common fixtures used across multiple skill tests.
Skill-specific fixtures remain in their respective conftest.py files.

This root conftest.py centralizes:
- pytest hooks (addoption, configure, collection_modifyitems)
- Temporary directory fixtures
- Project structure fixtures
- Mock client fixtures
"""

import os
import tempfile
from pathlib import Path
from typing import Any, Optional

import pytest

# =============================================================================
# PYTEST HOOKS
# =============================================================================

def pytest_addoption(parser):
    """Add custom command-line options."""
    try:
        parser.addoption(
            "--live",
            action="store_true",
            default=False,
            help="Run live integration tests"
        )
    except ValueError:
        pass  # Option already added

    try:
        parser.addoption(
            "--keep-space",
            action="store_true",
            default=False,
            help="Keep the test space after tests complete (for debugging)"
        )
    except ValueError:
        pass

    try:
        parser.addoption(
            "--space-key",
            action="store",
            default=None,
            help="Use an existing space instead of creating a new one"
        )
    except ValueError:
        pass

    try:
        parser.addoption(
            "--run-slow",
            action="store_true",
            default=False,
            help="Run slow tests"
        )
    except ValueError:
        pass

    try:
        parser.addoption(
            "--run-destructive",
            action="store_true",
            default=False,
            help="Run destructive tests"
        )
    except ValueError:
        pass


def pytest_configure(config):
    """Configure pytest with custom markers."""
    # Note: Most markers are now defined in pytest.ini
    # This function adds any dynamic markers needed
    pass


def pytest_collection_modifyitems(config, items):
    """
    Modify test collection based on command-line options.

    - Skip live tests unless --live is provided
    - Skip slow tests unless --run-slow is provided
    - Skip destructive tests unless --run-destructive is provided
    """
    skip_live = pytest.mark.skip(reason="Need --live to run")
    skip_slow = pytest.mark.skip(reason="Need --run-slow to run slow tests")
    skip_destructive = pytest.mark.skip(reason="Need --run-destructive to run destructive tests")

    run_live = config.getoption("--live", False)
    run_slow = config.getoption("--run-slow", False)
    run_destructive = config.getoption("--run-destructive", False)

    for item in items:
        # Skip live tests
        if "live" in item.keywords and not run_live:
            item.add_marker(skip_live)

        # Skip slow tests (only if not explicitly running slow tests)
        if "slow" in item.keywords and not run_slow:
            item.add_marker(skip_slow)

        # Skip destructive tests (only if not explicitly running destructive tests)
        # Note: In live mode, we default to running destructive tests unless skipped
        if "destructive" in item.keywords and not run_destructive and not run_live:
            item.add_marker(skip_destructive)


# =============================================================================
# TEMPORARY DIRECTORY FIXTURES
# =============================================================================

@pytest.fixture
def temp_path():
    """Create a temporary directory as Path object.

    Preferred fixture for new tests. Automatically cleaned up.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_dir(temp_path):
    """Create a temporary directory as string.

    Legacy compatibility. Prefer temp_path for new tests.
    """
    return str(temp_path)


# =============================================================================
# PROJECT STRUCTURE FIXTURES
# =============================================================================

@pytest.fixture
def claude_project_structure(temp_path):
    """Create a standard .claude project structure."""
    project = temp_path / "Test-Project"
    project.mkdir()

    claude_dir = project / ".claude"
    skills_dir = claude_dir / "skills"
    shared_lib = skills_dir / "shared" / "scripts" / "lib"
    shared_lib.mkdir(parents=True)

    settings = claude_dir / "settings.json"
    settings.write_text('{}')

    return {
        "root": project,
        "claude_dir": claude_dir,
        "skills_dir": skills_dir,
        "shared_lib": shared_lib,
        "settings": settings,
    }


@pytest.fixture
def sample_skill_md():
    """Return sample SKILL.md content."""
    return '''---
name: sample-skill
description: A sample skill for testing.
---

# Sample Skill

## Quick Start

```bash
echo "Hello"
```
'''


# =============================================================================
# MOCK CLIENT FIXTURES
# =============================================================================

@pytest.fixture
def mock_confluence_client():
    """
    Create a full-featured mock Confluence client.

    Usage:
        def test_something(mock_confluence_client):
            mock_confluence_client.add_page(page_id="123", title="Test")
            page = mock_confluence_client.get("/api/v2/pages/123")
            assert page["title"] == "Test"
    """
    try:
        from mock import MockConfluenceClient
        return MockConfluenceClient()
    except ImportError:
        # Fall back to basic mock if mock module not available
        from unittest.mock import MagicMock
        return MagicMock()


@pytest.fixture
def mock_config():
    """Create a mock configuration dictionary."""
    return {
        "api": {
            "timeout": 30,
            "max_retries": 3,
            "retry_backoff": 2.0,
        },
        "confluence": {
            "site_url": "https://test.atlassian.net",
            "email": "test@example.com",
        },
    }


# =============================================================================
# SESSION CLEANUP FIXTURES
# =============================================================================

@pytest.fixture(scope="session", autouse=True)
def session_cleanup(request):
    """
    Session-level cleanup hook.

    Ensures all resources are cleaned up at the end of the test session.
    """
    yield

    # Clean up any session-level resources
    # This runs after all tests complete
    try:
        # Reset singleton connections
        from confluence_container import reset_confluence_connection
        reset_confluence_connection()
    except ImportError:
        pass


# =============================================================================
# ENVIRONMENT FIXTURES
# =============================================================================

@pytest.fixture
def confluence_env_vars():
    """
    Fixture to temporarily set Confluence environment variables.

    Usage:
        def test_with_env(confluence_env_vars):
            with confluence_env_vars(CONFLUENCE_SITE_URL="https://test.atlassian.net"):
                # Test code here
                pass
    """
    import contextlib

    @contextlib.contextmanager
    def _set_env(**env_vars):
        old_values = {}
        for key, value in env_vars.items():
            old_values[key] = os.environ.get(key)
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        try:
            yield
        finally:
            for key, old_value in old_values.items():
                if old_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = old_value

    return _set_env


# =============================================================================
# SAMPLE DATA FIXTURES
# =============================================================================

@pytest.fixture
def sample_page_data():
    """Return sample page data matching Confluence API response format."""
    return {
        "id": "123456",
        "status": "current",
        "title": "Test Page",
        "spaceId": "789",
        "parentId": "111",
        "parentType": "page",
        "position": 0,
        "authorId": "user123",
        "ownerId": "user123",
        "createdAt": "2024-01-15T10:30:00.000Z",
        "version": {
            "number": 1,
            "message": "Initial version",
            "minorEdit": False,
            "authorId": "user123",
            "createdAt": "2024-01-15T10:30:00.000Z",
        },
        "body": {
            "storage": {"value": "<p>Test content</p>", "representation": "storage"},
        },
        "_links": {
            "webui": "/wiki/spaces/TEST/pages/123456/Test+Page",
        },
    }


@pytest.fixture
def sample_space_data():
    """Return sample space data matching Confluence API response format."""
    return {
        "id": "789",
        "key": "TEST",
        "name": "Test Space",
        "type": "global",
        "status": "current",
        "homepageId": "123456",
        "_links": {"webui": "/wiki/spaces/TEST"},
    }


@pytest.fixture
def sample_search_results(sample_page_data):
    """Return sample search results matching Confluence API response format."""
    return {
        "results": [
            {
                "content": sample_page_data,
                "excerpt": "This is a <em>test</em> page...",
                "lastModified": "2024-01-15T10:30:00.000Z",
            }
        ],
        "start": 0,
        "limit": 25,
        "size": 1,
        "totalSize": 1,
        "_links": {},
    }
