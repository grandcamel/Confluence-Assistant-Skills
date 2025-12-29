"""
Live integration tests for page reorder operations.

Usage:
    pytest test_reorder_live.py --profile development -v
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
def ordered_pages(confluence_client, test_space):
    """Create a parent with ordered child pages."""
    pages = []

    parent = confluence_client.post(
        '/api/v2/pages',
        json_data={
            'spaceId': test_space['id'],
            'status': 'current',
            'title': f'Reorder Parent {uuid.uuid4().hex[:8]}',
            'body': {'representation': 'storage', 'value': '<p>Parent.</p>'}
        }
    )
    pages.append(parent)

    children = []
    for i in range(3):
        child = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'status': 'current',
                'title': f'Child {i} {uuid.uuid4().hex[:8]}',
                'parentId': parent['id'],
                'body': {'representation': 'storage', 'value': f'<p>Child {i}.</p>'}
            }
        )
        pages.append(child)
        children.append(child)

    yield {'parent': parent, 'children': children}

    for page in reversed(pages):
        try:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")
        except Exception:
            pass


@pytest.mark.integration
class TestReorderLive:
    """Live tests for page reorder operations."""

    def test_get_children_order(self, confluence_client, ordered_pages):
        """Test getting children in their current order."""
        parent = ordered_pages['parent']

        children = confluence_client.get(
            f"/api/v2/pages/{parent['id']}/children"
        )

        assert 'results' in children
        assert len(children['results']) >= 3

    def test_children_maintain_parent(self, confluence_client, ordered_pages):
        """Test that children maintain parent relationship."""
        parent = ordered_pages['parent']

        for child in ordered_pages['children']:
            page = confluence_client.get(f"/api/v2/pages/{child['id']}")
            assert page['parentId'] == parent['id']

    def test_move_child_between_parents(self, confluence_client, test_space, ordered_pages):
        """Test moving a child to a new parent."""
        child = ordered_pages['children'][0]

        # Create new parent
        new_parent = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'status': 'current',
                'title': f'New Parent {uuid.uuid4().hex[:8]}',
                'body': {'representation': 'storage', 'value': '<p>New parent.</p>'}
            }
        )

        try:
            # Move child
            confluence_client.put(
                f'/api/v2/pages/{child["id"]}',
                json_data={
                    'id': child['id'],
                    'status': 'current',
                    'title': child['title'],
                    'spaceId': test_space['id'],
                    'parentId': new_parent['id'],
                    'body': {'representation': 'storage', 'value': '<p>Moved.</p>'},
                    'version': {'number': child['version']['number'] + 1}
                }
            )

            # Verify new parent
            moved = confluence_client.get(f"/api/v2/pages/{child['id']}")
            assert moved['parentId'] == new_parent['id']
        finally:
            confluence_client.delete(f"/api/v2/pages/{new_parent['id']}")
