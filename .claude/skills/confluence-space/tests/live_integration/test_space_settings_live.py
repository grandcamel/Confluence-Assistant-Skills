"""
Live integration tests for space settings operations.

Usage:
    pytest test_space_settings_live.py --profile development -v
"""

import pytest
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

@pytest.mark.integration
class TestSpaceSettingsLive:
    """Live tests for space settings operations."""

    def test_get_space_details(self, confluence_client, test_space):
        """Test getting space details."""
        space = confluence_client.get(f"/api/v2/spaces/{test_space['id']}")

        assert space['id'] == test_space['id']
        assert 'name' in space
        assert 'key' in space

    def test_get_space_description(self, confluence_client, test_space):
        """Test getting space description."""
        space = confluence_client.get(
            f"/api/v2/spaces/{test_space['id']}",
            params={'description-format': 'plain'}
        )

        assert space['id'] == test_space['id']

    def test_list_all_spaces(self, confluence_client):
        """Test listing all accessible spaces."""
        spaces = confluence_client.get('/api/v2/spaces', params={'limit': 25})

        assert 'results' in spaces
        assert len(spaces['results']) > 0

    def test_get_space_by_key(self, confluence_client, test_space):
        """Test getting space by key."""
        spaces = confluence_client.get(
            '/api/v2/spaces',
            params={'keys': test_space['key']}
        )

        assert 'results' in spaces
        space_keys = [s['key'] for s in spaces['results']]
        assert test_space['key'] in space_keys

    def test_space_type(self, confluence_client, test_space):
        """Test getting space type information."""
        space = confluence_client.get(f"/api/v2/spaces/{test_space['id']}")

        # Should have type field
        assert 'type' in space or 'status' in space
