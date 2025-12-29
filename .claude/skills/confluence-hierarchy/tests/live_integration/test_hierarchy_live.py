"""
Live integration tests for confluence-hierarchy skill.

Tests page hierarchy operations against a real Confluence instance.

Usage:
    pytest test_hierarchy_live.py --profile development -v
"""

import pytest
import uuid
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'shared' / 'scripts' / 'lib'))

from config_manager import get_confluence_client


def pytest_addoption(parser):
    try:
        parser.addoption("--profile", action="store", default=None, help="Confluence profile")
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
def parent_page(confluence_client, test_space):
    """Create a parent page."""
    page = confluence_client.post(
        '/api/v2/pages',
        json_data={
            'spaceId': test_space['id'],
            'status': 'current',
            'title': f'Parent Page {uuid.uuid4().hex[:8]}',
            'body': {'representation': 'storage', 'value': '<p>Parent.</p>'}
        }
    )
    yield page
    try:
        confluence_client.delete(f"/api/v2/pages/{page['id']}")
    except Exception:
        pass


@pytest.fixture
def child_page(confluence_client, test_space, parent_page):
    """Create a child page under parent."""
    page = confluence_client.post(
        '/api/v2/pages',
        json_data={
            'spaceId': test_space['id'],
            'parentId': parent_page['id'],
            'status': 'current',
            'title': f'Child Page {uuid.uuid4().hex[:8]}',
            'body': {'representation': 'storage', 'value': '<p>Child.</p>'}
        }
    )
    yield page
    try:
        confluence_client.delete(f"/api/v2/pages/{page['id']}")
    except Exception:
        pass


@pytest.fixture
def grandchild_page(confluence_client, test_space, child_page):
    """Create a grandchild page."""
    page = confluence_client.post(
        '/api/v2/pages',
        json_data={
            'spaceId': test_space['id'],
            'parentId': child_page['id'],
            'status': 'current',
            'title': f'Grandchild Page {uuid.uuid4().hex[:8]}',
            'body': {'representation': 'storage', 'value': '<p>Grandchild.</p>'}
        }
    )
    yield page
    try:
        confluence_client.delete(f"/api/v2/pages/{page['id']}")
    except Exception:
        pass


@pytest.mark.integration
class TestGetChildrenLive:
    """Live tests for getting child pages."""

    def test_get_children(self, confluence_client, parent_page, child_page):
        """Test getting children of a page."""
        children = confluence_client.get(
            f"/api/v2/pages/{parent_page['id']}/children"
        )

        assert 'results' in children
        child_ids = [c['id'] for c in children['results']]
        assert child_page['id'] in child_ids

    def test_get_children_empty(self, confluence_client, test_space):
        """Test getting children of a page with none."""
        page = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'status': 'current',
                'title': f'No Children {uuid.uuid4().hex[:8]}',
                'body': {'representation': 'storage', 'value': '<p>Leaf.</p>'}
            }
        )

        try:
            children = confluence_client.get(
                f"/api/v2/pages/{page['id']}/children"
            )
            assert 'results' in children
            assert len(children['results']) == 0
        finally:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")

    def test_get_multiple_children(self, confluence_client, test_space, parent_page):
        """Test getting multiple children."""
        child_ids = []
        for i in range(3):
            child = confluence_client.post(
                '/api/v2/pages',
                json_data={
                    'spaceId': test_space['id'],
                    'parentId': parent_page['id'],
                    'status': 'current',
                    'title': f'Multi Child {i} {uuid.uuid4().hex[:8]}',
                    'body': {'representation': 'storage', 'value': f'<p>Child {i}.</p>'}
                }
            )
            child_ids.append(child['id'])

        try:
            children = confluence_client.get(
                f"/api/v2/pages/{parent_page['id']}/children"
            )
            result_ids = [c['id'] for c in children['results']]
            for child_id in child_ids:
                assert child_id in result_ids
        finally:
            for child_id in child_ids:
                try:
                    confluence_client.delete(f"/api/v2/pages/{child_id}")
                except Exception:
                    pass


@pytest.mark.integration
class TestGetAncestorsLive:
    """Live tests for getting ancestors."""

    def test_get_ancestors(self, confluence_client, parent_page, child_page, grandchild_page):
        """Test getting ancestors of a page."""
        ancestors = confluence_client.get(
            f"/api/v2/pages/{grandchild_page['id']}/ancestors"
        )

        assert 'results' in ancestors
        ancestor_ids = [a['id'] for a in ancestors['results']]
        assert child_page['id'] in ancestor_ids
        assert parent_page['id'] in ancestor_ids

    def test_get_ancestors_root(self, confluence_client, parent_page):
        """Test getting ancestors of a root-level page."""
        ancestors = confluence_client.get(
            f"/api/v2/pages/{parent_page['id']}/ancestors"
        )

        assert 'results' in ancestors
        # May have space homepage as ancestor, but parent is not its own ancestor
        ancestor_ids = [a['id'] for a in ancestors['results']]
        assert parent_page['id'] not in ancestor_ids


@pytest.mark.integration
class TestGetDescendantsLive:
    """Live tests for getting descendants."""

    def test_get_descendants(self, confluence_client, parent_page, child_page, grandchild_page):
        """Test getting all descendants of a page."""
        # Use v1 API for descendants
        descendants = confluence_client.get(
            f"/rest/api/content/{parent_page['id']}/descendant/page"
        )

        assert 'results' in descendants
        descendant_ids = [d['id'] for d in descendants['results']]
        assert child_page['id'] in descendant_ids
        assert grandchild_page['id'] in descendant_ids


@pytest.mark.integration
class TestMovePageLive:
    """Live tests for moving pages in hierarchy."""

    def test_move_page_to_new_parent(self, confluence_client, test_space):
        """Test moving a page to a different parent."""
        # Create structure
        parent1 = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'status': 'current',
                'title': f'Parent 1 {uuid.uuid4().hex[:8]}',
                'body': {'representation': 'storage', 'value': '<p>P1.</p>'}
            }
        )
        parent2 = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'status': 'current',
                'title': f'Parent 2 {uuid.uuid4().hex[:8]}',
                'body': {'representation': 'storage', 'value': '<p>P2.</p>'}
            }
        )
        child = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'parentId': parent1['id'],
                'status': 'current',
                'title': f'Moving Child {uuid.uuid4().hex[:8]}',
                'body': {'representation': 'storage', 'value': '<p>Moving.</p>'}
            }
        )

        try:
            # Move to parent2 using v1 API
            confluence_client.session.put(
                f"{confluence_client.base_url}/wiki/rest/api/content/{child['id']}/move/position/append/targetId/{parent2['id']}",
                headers={'Content-Type': 'application/json'}
            )

            # Verify new parent
            moved = confluence_client.get(f"/api/v2/pages/{child['id']}")
            assert moved['parentId'] == parent2['id']

        finally:
            for page in [child, parent2, parent1]:
                try:
                    confluence_client.delete(f"/api/v2/pages/{page['id']}")
                except Exception:
                    pass
