"""
Shared fixtures for confluence-page live integration tests.
Imports fixtures from shared conftest and adds skill-specific ones.
"""

import sys
from pathlib import Path

# Add shared lib to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'shared' / 'scripts' / 'lib'))

from config_manager import get_confluence_client
import pytest
import uuid


def pytest_addoption(parser):
    """Add --profile option if not already added."""
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
def test_page(confluence_client, test_space):
    page = confluence_client.post(
        '/api/v2/pages',
        json_data={
            'spaceId': test_space['id'],
            'status': 'current',
            'title': f'Test Page {uuid.uuid4().hex[:8]}',
            'body': {'representation': 'storage', 'value': '<p>Test.</p>'}
        }
    )
    yield page
    try:
        confluence_client.delete(f"/api/v2/pages/{page['id']}")
    except Exception:
        pass


@pytest.fixture
def current_user(confluence_client):
    return confluence_client.get('/rest/api/user/current')
