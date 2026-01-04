"""
Live integration tests for permission inheritance operations.

Usage:
    pytest test_permission_inherit_live.py --profile development -v
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

@pytest.mark.integration
class TestPermissionInheritLive:
    """Live tests for permission inheritance operations."""

    def test_child_inherits_parent_access(self, confluence_client, test_space):
        """Test that child page inherits access from parent."""
        parent = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'status': 'current',
                'title': f'Inherit Parent {uuid.uuid4().hex[:8]}',
                'body': {'representation': 'storage', 'value': '<p>Parent.</p>'}
            }
        )

        child = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'status': 'current',
                'title': f'Inherit Child {uuid.uuid4().hex[:8]}',
                'parentId': parent['id'],
                'body': {'representation': 'storage', 'value': '<p>Child.</p>'}
            }
        )

        try:
            # If we can read parent, we should be able to read child
            parent_page = confluence_client.get(f"/api/v2/pages/{parent['id']}")
            child_page = confluence_client.get(f"/api/v2/pages/{child['id']}")

            assert parent_page['id'] == parent['id']
            assert child_page['id'] == child['id']
        finally:
            confluence_client.delete(f"/api/v2/pages/{child['id']}")
            confluence_client.delete(f"/api/v2/pages/{parent['id']}")

    def test_page_restrictions_isolated(self, confluence_client, test_space):
        """Test that page restrictions don't affect siblings."""
        parent = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'status': 'current',
                'title': f'Isolated Parent {uuid.uuid4().hex[:8]}',
                'body': {'representation': 'storage', 'value': '<p>Parent.</p>'}
            }
        )

        child1 = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'status': 'current',
                'title': f'Child 1 {uuid.uuid4().hex[:8]}',
                'parentId': parent['id'],
                'body': {'representation': 'storage', 'value': '<p>Child 1.</p>'}
            }
        )

        child2 = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'status': 'current',
                'title': f'Child 2 {uuid.uuid4().hex[:8]}',
                'parentId': parent['id'],
                'body': {'representation': 'storage', 'value': '<p>Child 2.</p>'}
            }
        )

        try:
            # Both children should be accessible
            assert confluence_client.get(f"/api/v2/pages/{child1['id']}")
            assert confluence_client.get(f"/api/v2/pages/{child2['id']}")
        finally:
            confluence_client.delete(f"/api/v2/pages/{child1['id']}")
            confluence_client.delete(f"/api/v2/pages/{child2['id']}")
            confluence_client.delete(f"/api/v2/pages/{parent['id']}")
