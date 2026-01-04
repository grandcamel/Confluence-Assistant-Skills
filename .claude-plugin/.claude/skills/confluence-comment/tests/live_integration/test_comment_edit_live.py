"""
Live integration tests for comment edit operations.

Usage:
    pytest test_comment_edit_live.py --profile development -v
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
def test_page(confluence_client, test_space):
    page = confluence_client.post(
        '/api/v2/pages',
        json_data={
            'spaceId': test_space['id'],
            'status': 'current',
            'title': f'Comment Edit Test {uuid.uuid4().hex[:8]}',
            'body': {'representation': 'storage', 'value': '<p>Test.</p>'}
        }
    )
    yield page
    try:
        confluence_client.delete(f"/api/v2/pages/{page['id']}")
    except Exception:
        pass

@pytest.mark.integration
class TestCommentEditLive:
    """Live tests for comment edit operations."""

    def test_update_comment(self, confluence_client, test_page):
        """Test updating a comment."""
        # Create comment using v1 API
        comment = confluence_client.post(
            '/rest/api/content',
            json_data={
                'type': 'comment',
                'container': {'id': test_page['id'], 'type': 'page'},
                'body': {
                    'storage': {
                        'representation': 'storage',
                        'value': '<p>Original comment.</p>'
                    }
                }
            }
        )

        try:
            # Update comment using v1 API
            updated = confluence_client.put(
                f"/rest/api/content/{comment['id']}",
                json_data={
                    'type': 'comment',
                    'body': {
                        'storage': {
                            'representation': 'storage',
                            'value': '<p>Updated comment.</p>'
                        }
                    },
                    'version': {'number': comment['version']['number'] + 1}
                }
            )

            assert updated['id'] == comment['id']
        finally:
            try:
                confluence_client.delete(f"/rest/api/content/{comment['id']}")
            except Exception:
                pass

    def test_get_comment_by_id(self, confluence_client, test_page):
        """Test getting a specific comment by ID."""
        # Create comment using v1 API
        comment = confluence_client.post(
            '/rest/api/content',
            json_data={
                'type': 'comment',
                'container': {'id': test_page['id'], 'type': 'page'},
                'body': {
                    'storage': {
                        'representation': 'storage',
                        'value': '<p>Test comment.</p>'
                    }
                }
            }
        )

        try:
            # Get by ID using v1 API
            fetched = confluence_client.get(
                f"/rest/api/content/{comment['id']}"
            )

            assert fetched['id'] == comment['id']
        finally:
            try:
                confluence_client.delete(f"/rest/api/content/{comment['id']}")
            except Exception:
                pass

    def test_comment_version_increment(self, confluence_client, test_page):
        """Test that comment version increments on update."""
        # Create comment using v1 API
        comment = confluence_client.post(
            '/rest/api/content',
            json_data={
                'type': 'comment',
                'container': {'id': test_page['id'], 'type': 'page'},
                'body': {
                    'storage': {
                        'representation': 'storage',
                        'value': '<p>Version test.</p>'
                    }
                }
            }
        )

        initial_version = comment['version']['number']

        try:
            # Update using v1 API
            updated = confluence_client.put(
                f"/rest/api/content/{comment['id']}",
                json_data={
                    'type': 'comment',
                    'body': {
                        'storage': {
                            'representation': 'storage',
                            'value': '<p>Version 2.</p>'
                        }
                    },
                    'version': {'number': initial_version + 1}
                }
            )

            assert updated['version']['number'] == initial_version + 1
        finally:
            try:
                confluence_client.delete(f"/rest/api/content/{comment['id']}")
            except Exception:
                pass
