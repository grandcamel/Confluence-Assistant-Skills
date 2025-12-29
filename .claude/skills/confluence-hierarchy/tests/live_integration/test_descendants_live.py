"""
Live integration tests for descendant operations.

Usage:
    pytest test_descendants_live.py --profile development -v
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
def page_hierarchy(confluence_client, test_space):
    """Create a page hierarchy: parent -> child1, child2."""
    pages = []

    parent = confluence_client.post(
        '/api/v2/pages',
        json_data={
            'spaceId': test_space['id'],
            'status': 'current',
            'title': f'Desc Parent {uuid.uuid4().hex[:8]}',
            'body': {'representation': 'storage', 'value': '<p>Parent.</p>'}
        }
    )
    pages.append(parent)

    for i in range(2):
        child = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'status': 'current',
                'title': f'Desc Child {i} {uuid.uuid4().hex[:8]}',
                'parentId': parent['id'],
                'body': {'representation': 'storage', 'value': f'<p>Child {i}.</p>'}
            }
        )
        pages.append(child)

    yield {'parent': parent, 'children': pages[1:]}

    for page in reversed(pages):
        try:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")
        except Exception:
            pass


@pytest.mark.integration
class TestDescendantsLive:
    """Live tests for descendant operations."""

    def test_get_page_children(self, confluence_client, page_hierarchy):
        """Test getting direct children of a page."""
        parent = page_hierarchy['parent']

        children = confluence_client.get(
            f"/api/v2/pages/{parent['id']}/children"
        )

        assert 'results' in children
        child_ids = [c['id'] for c in children.get('results', [])]
        for child in page_hierarchy['children']:
            assert child['id'] in child_ids

    def test_get_descendants_v1(self, confluence_client, page_hierarchy):
        """Test getting descendants using v1 API."""
        parent = page_hierarchy['parent']

        descendants = confluence_client.get(
            f"/rest/api/content/{parent['id']}/descendant/page"
        )

        assert 'results' in descendants

    def test_count_children(self, confluence_client, page_hierarchy):
        """Test counting page children."""
        parent = page_hierarchy['parent']

        children = confluence_client.get(
            f"/api/v2/pages/{parent['id']}/children"
        )

        assert len(children.get('results', [])) >= 2

    def test_leaf_page_has_no_children(self, confluence_client, page_hierarchy):
        """Test that leaf page has no children."""
        child = page_hierarchy['children'][0]

        children = confluence_client.get(
            f"/api/v2/pages/{child['id']}/children"
        )

        assert len(children.get('results', [])) == 0
