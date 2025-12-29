"""
Live integration tests for breadcrumb navigation.

Usage:
    pytest test_breadcrumb_live.py --profile development -v
"""

import pytest
import uuid
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'shared' / 'scripts' / 'lib'))

from config_manager import get_confluence_client


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
def deep_hierarchy(confluence_client, test_space):
    """Create a 3-level hierarchy."""
    pages = []

    level1 = confluence_client.post(
        '/api/v2/pages',
        json_data={
            'spaceId': test_space['id'],
            'status': 'current',
            'title': f'Level 1 {uuid.uuid4().hex[:8]}',
            'body': {'representation': 'storage', 'value': '<p>Level 1.</p>'}
        }
    )
    pages.append(level1)

    level2 = confluence_client.post(
        '/api/v2/pages',
        json_data={
            'spaceId': test_space['id'],
            'status': 'current',
            'title': f'Level 2 {uuid.uuid4().hex[:8]}',
            'parentId': level1['id'],
            'body': {'representation': 'storage', 'value': '<p>Level 2.</p>'}
        }
    )
    pages.append(level2)

    level3 = confluence_client.post(
        '/api/v2/pages',
        json_data={
            'spaceId': test_space['id'],
            'status': 'current',
            'title': f'Level 3 {uuid.uuid4().hex[:8]}',
            'parentId': level2['id'],
            'body': {'representation': 'storage', 'value': '<p>Level 3.</p>'}
        }
    )
    pages.append(level3)

    yield {'level1': level1, 'level2': level2, 'level3': level3}

    for page in reversed(pages):
        try:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")
        except Exception:
            pass


@pytest.mark.integration
class TestBreadcrumbLive:
    """Live tests for breadcrumb navigation."""

    def test_build_breadcrumb_path(self, confluence_client, deep_hierarchy):
        """Test building breadcrumb path from ancestors."""
        level3 = deep_hierarchy['level3']

        page = confluence_client.get(
            f"/rest/api/content/{level3['id']}",
            params={'expand': 'ancestors'}
        )

        ancestors = page.get('ancestors', [])
        assert len(ancestors) >= 2

        # Build breadcrumb
        breadcrumb = [a['title'] for a in ancestors]
        breadcrumb.append(page['title'])

        assert len(breadcrumb) >= 3

    def test_root_page_breadcrumb(self, confluence_client, deep_hierarchy):
        """Test breadcrumb for root page."""
        level1 = deep_hierarchy['level1']

        page = confluence_client.get(
            f"/rest/api/content/{level1['id']}",
            params={'expand': 'ancestors'}
        )

        ancestors = page.get('ancestors', [])
        # Root page should have minimal ancestors
        assert len(ancestors) == 0 or ancestors == []

    def test_ancestor_order(self, confluence_client, deep_hierarchy):
        """Test that ancestors are in correct order."""
        level3 = deep_hierarchy['level3']

        page = confluence_client.get(
            f"/rest/api/content/{level3['id']}",
            params={'expand': 'ancestors'}
        )

        ancestors = page.get('ancestors', [])
        if len(ancestors) >= 2:
            # Last ancestor should be immediate parent (level2)
            assert ancestors[-1]['id'] == deep_hierarchy['level2']['id']
