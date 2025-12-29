"""
Live integration tests for comment thread operations.

Usage:
    pytest test_comment_threads_live.py --profile development -v
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
def test_page(confluence_client, test_space):
    page = confluence_client.post(
        '/api/v2/pages',
        json_data={
            'spaceId': test_space['id'],
            'status': 'current',
            'title': f'Comment Thread Test {uuid.uuid4().hex[:8]}',
            'body': {'representation': 'storage', 'value': '<p>Test.</p>'}
        }
    )
    yield page
    try:
        confluence_client.delete(f"/api/v2/pages/{page['id']}")
    except Exception:
        pass


@pytest.mark.integration
class TestCommentThreadsLive:
    """Live tests for comment thread operations."""

    def test_create_comment_with_reply(self, confluence_client, test_page):
        """Test creating a comment and adding a reply."""
        # Create parent comment
        parent = confluence_client.post(
            f"/api/v2/pages/{test_page['id']}/footer-comments",
            json_data={
                'body': {
                    'representation': 'storage',
                    'value': '<p>Parent comment.</p>'
                }
            }
        )

        try:
            # Create reply using v1 API
            reply = confluence_client.post(
                f"/rest/api/content/{test_page['id']}/child/comment",
                json_data={
                    'type': 'comment',
                    'container': {'id': test_page['id'], 'type': 'page'},
                    'ancestors': [{'id': parent['id']}],
                    'body': {
                        'storage': {
                            'value': '<p>Reply comment.</p>',
                            'representation': 'storage'
                        }
                    }
                }
            )

            assert reply['id'] is not None
        finally:
            # Cleanup
            try:
                confluence_client.delete(f"/api/v2/footer-comments/{parent['id']}")
            except Exception:
                pass

    def test_get_all_comments_in_thread(self, confluence_client, test_page):
        """Test getting all comments including replies."""
        # Create a comment
        comment = confluence_client.post(
            f"/api/v2/pages/{test_page['id']}/footer-comments",
            json_data={
                'body': {
                    'representation': 'storage',
                    'value': '<p>Thread test comment.</p>'
                }
            }
        )

        try:
            # Get all comments
            comments = confluence_client.get(
                f"/api/v2/pages/{test_page['id']}/footer-comments"
            )

            assert 'results' in comments
            comment_ids = [c['id'] for c in comments.get('results', [])]
            assert comment['id'] in comment_ids
        finally:
            try:
                confluence_client.delete(f"/api/v2/footer-comments/{comment['id']}")
            except Exception:
                pass

    def test_delete_comment_with_replies(self, confluence_client, test_page):
        """Test deleting a comment that may have replies."""
        # Create comment
        comment = confluence_client.post(
            f"/api/v2/pages/{test_page['id']}/footer-comments",
            json_data={
                'body': {
                    'representation': 'storage',
                    'value': '<p>Will be deleted.</p>'
                }
            }
        )

        # Delete it
        confluence_client.delete(f"/api/v2/footer-comments/{comment['id']}")

        # Verify deletion
        comments = confluence_client.get(
            f"/api/v2/pages/{test_page['id']}/footer-comments"
        )
        comment_ids = [c['id'] for c in comments.get('results', [])]
        assert comment['id'] not in comment_ids
