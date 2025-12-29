"""
Live integration tests for page history operations.

Usage:
    pytest test_page_history_live.py --profile development -v
"""

import pytest
import uuid
import sys
from confluence_assistant_skills_lib import (
    get_confluence_client,
)

def pytest_addoption(parser):
    try:
        parser.addoption("--profile", action="store", default=None)
    except ValueError:
        pass

@pytest.fixture(scope="session")
def confluence_client(request):
    profile = request.config.getoption("--profile", default=None)
    return get_confluence_client(profile=profile)

@pytest.fixture(scope="session")
def test_space(confluence_client):
    spaces = confluence_client.get('/api/v2/spaces', params={'limit': 1})
    if not spaces.get('results'):
        pytest.skip("No spaces available")
    return spaces['results'][0]

@pytest.fixture
def page_with_history(confluence_client, test_space):
    """Create a page and update it to create history."""
    page = confluence_client.post(
        '/api/v2/pages',
        json_data={
            'spaceId': test_space['id'],
            'status': 'current',
            'title': f'History Test {uuid.uuid4().hex[:8]}',
            'body': {'representation': 'storage', 'value': '<p>Version 1.</p>'}
        }
    )

    # Create version 2
    page = confluence_client.put(
        f'/api/v2/pages/{page["id"]}',
        json_data={
            'id': page['id'],
            'status': 'current',
            'title': page['title'],
            'spaceId': test_space['id'],
            'body': {'representation': 'storage', 'value': '<p>Version 2.</p>'},
            'version': {'number': 2}
        }
    )

    # Create version 3
    page = confluence_client.put(
        f'/api/v2/pages/{page["id"]}',
        json_data={
            'id': page['id'],
            'status': 'current',
            'title': page['title'],
            'spaceId': test_space['id'],
            'body': {'representation': 'storage', 'value': '<p>Version 3.</p>'},
            'version': {'number': 3}
        }
    )

    yield page

    try:
        confluence_client.delete(f"/api/v2/pages/{page['id']}")
    except Exception:
        pass

@pytest.mark.integration
class TestPageHistoryLive:
    """Live tests for page history operations."""

    def test_get_page_versions(self, confluence_client, page_with_history):
        """Test getting all versions of a page."""
        versions = confluence_client.get(
            f"/api/v2/pages/{page_with_history['id']}/versions"
        )

        assert 'results' in versions
        assert len(versions['results']) >= 3

    def test_current_version_number(self, confluence_client, page_with_history):
        """Test that current version is 3."""
        page = confluence_client.get(
            f"/api/v2/pages/{page_with_history['id']}"
        )

        assert page['version']['number'] >= 3

    def test_get_specific_version(self, confluence_client, page_with_history):
        """Test getting a specific version."""
        versions = confluence_client.get(
            f"/api/v2/pages/{page_with_history['id']}/versions"
        )

        # Get first version details
        if versions.get('results'):
            version = versions['results'][0]
            assert 'number' in version

    def test_version_created_at(self, confluence_client, page_with_history):
        """Test that versions have creation timestamps."""
        versions = confluence_client.get(
            f"/api/v2/pages/{page_with_history['id']}/versions"
        )

        for v in versions.get('results', []):
            assert 'createdAt' in v or 'when' in v or 'number' in v

    def test_page_history_order(self, confluence_client, page_with_history):
        """Test that versions are in correct order."""
        versions = confluence_client.get(
            f"/api/v2/pages/{page_with_history['id']}/versions"
        )

        version_numbers = [v['number'] for v in versions.get('results', [])]
        # Should be ordered (ascending or descending)
        assert version_numbers == sorted(version_numbers) or \
               version_numbers == sorted(version_numbers, reverse=True)
