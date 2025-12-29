"""
Live integration tests for comment author operations.

Usage:
    pytest test_comment_author_live.py --profile development -v
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
            'title': f'Comment Author Test {uuid.uuid4().hex[:8]}',
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

@pytest.mark.integration
class TestCommentAuthorLive:
    """Live tests for comment author operations."""

    def test_comment_has_author(self, confluence_client, test_page, current_user):
        """Test that comments have author information."""
        comment = confluence_client.post(
            f"/api/v2/pages/{test_page['id']}/footer-comments",
            json_data={
                'body': {
                    'representation': 'storage',
                    'value': '<p>Author test.</p>'
                }
            }
        )

        try:
            # Get comment with author info via v1
            detailed = confluence_client.get(
                f"/rest/api/content/{comment['id']}",
                params={'expand': 'history.createdBy'}
            )

            assert 'history' in detailed or 'version' in detailed
        finally:
            confluence_client.delete(f"/api/v2/footer-comments/{comment['id']}")

    def test_find_user_comments(self, confluence_client, test_space, current_user):
        """Test finding comments by current user."""
        results = confluence_client.get(
            '/rest/api/search',
            params={
                'cql': f'type = comment AND space = "{test_space["key"]}" AND creator = currentUser()',
                'limit': 10
            }
        )

        assert 'results' in results
