"""
Live integration tests for comment count operations.

Usage:
    pytest test_comment_count_live.py --profile development -v
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
            'title': f'Comment Count Test {uuid.uuid4().hex[:8]}',
            'body': {'representation': 'storage', 'value': '<p>Test.</p>'}
        }
    )
    yield page
    try:
        confluence_client.delete(f"/api/v2/pages/{page['id']}")
    except Exception:
        pass


@pytest.mark.integration
class TestCommentCountLive:
    """Live tests for comment count operations."""

    def test_count_zero_comments(self, confluence_client, test_page):
        """Test counting comments on page with no comments."""
        comments = confluence_client.get(
            f"/api/v2/pages/{test_page['id']}/footer-comments"
        )

        count = len(comments.get('results', []))
        assert count == 0

    def test_count_after_adding_comments(self, confluence_client, test_page):
        """Test counting after adding comments."""
        comment_ids = []

        # Add 3 comments
        for i in range(3):
            comment = confluence_client.post(
                f"/api/v2/pages/{test_page['id']}/footer-comments",
                json_data={
                    'body': {
                        'representation': 'storage',
                        'value': f'<p>Comment {i}.</p>'
                    }
                }
            )
            comment_ids.append(comment['id'])

        try:
            comments = confluence_client.get(
                f"/api/v2/pages/{test_page['id']}/footer-comments"
            )
            count = len(comments.get('results', []))
            assert count >= 3
        finally:
            for cid in comment_ids:
                try:
                    confluence_client.delete(f"/api/v2/footer-comments/{cid}")
                except Exception:
                    pass

    def test_count_after_deleting_comment(self, confluence_client, test_page):
        """Test count updates after deleting a comment."""
        # Add a comment
        comment = confluence_client.post(
            f"/api/v2/pages/{test_page['id']}/footer-comments",
            json_data={
                'body': {
                    'representation': 'storage',
                    'value': '<p>To delete.</p>'
                }
            }
        )

        # Verify added
        comments = confluence_client.get(
            f"/api/v2/pages/{test_page['id']}/footer-comments"
        )
        initial_count = len(comments.get('results', []))

        # Delete
        confluence_client.delete(f"/api/v2/footer-comments/{comment['id']}")

        # Verify count decreased
        comments = confluence_client.get(
            f"/api/v2/pages/{test_page['id']}/footer-comments"
        )
        final_count = len(comments.get('results', []))

        assert final_count == initial_count - 1
