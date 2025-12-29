"""
Live integration tests for confluence-comment skill.

Tests comment operations against a real Confluence instance.

Usage:
    pytest test_comment_live.py --profile development -v
"""

import pytest
import uuid
import sys
from confluence_assistant_skills_lib import (
    get_confluence_client,
)

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
def test_page(confluence_client, test_space):
    page = confluence_client.post(
        '/api/v2/pages',
        json_data={
            'spaceId': test_space['id'],
            'status': 'current',
            'title': f'Comment Test Page {uuid.uuid4().hex[:8]}',
            'body': {'representation': 'storage', 'value': '<p>Test content.</p>'}
        }
    )
    yield page
    try:
        confluence_client.delete(f"/api/v2/pages/{page['id']}")
    except Exception:
        pass

@pytest.mark.integration
class TestAddCommentLive:
    """Live tests for adding comments."""

    def test_add_footer_comment(self, confluence_client, test_page):
        """Test adding a footer comment to a page."""
        comment = confluence_client.post(
            f"/api/v2/pages/{test_page['id']}/footer-comments",
            json_data={
                'body': {
                    'representation': 'storage',
                    'value': '<p>Test comment from live test.</p>'
                }
            }
        )

        assert comment['id'] is not None
        assert 'body' in comment

    def test_add_multiple_comments(self, confluence_client, test_page):
        """Test adding multiple comments."""
        comments = []
        for i in range(3):
            comment = confluence_client.post(
                f"/api/v2/pages/{test_page['id']}/footer-comments",
                json_data={
                    'body': {
                        'representation': 'storage',
                        'value': f'<p>Comment {i + 1}</p>'
                    }
                }
            )
            comments.append(comment)

        assert len(comments) == 3
        assert all(c['id'] for c in comments)

@pytest.mark.integration
class TestGetCommentsLive:
    """Live tests for retrieving comments."""

    def test_get_page_comments(self, confluence_client, test_page):
        """Test getting comments from a page."""
        # Add a comment first
        confluence_client.post(
            f"/api/v2/pages/{test_page['id']}/footer-comments",
            json_data={
                'body': {'representation': 'storage', 'value': '<p>Test</p>'}
            }
        )

        # Get comments
        comments = confluence_client.get(
            f"/api/v2/pages/{test_page['id']}/footer-comments"
        )

        assert 'results' in comments
        assert len(comments['results']) >= 1

    def test_get_comments_empty_page(self, confluence_client, test_space):
        """Test getting comments from a page with no comments."""
        # Create fresh page
        page = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'status': 'current',
                'title': f'Empty Comments {uuid.uuid4().hex[:8]}',
                'body': {'representation': 'storage', 'value': '<p>No comments.</p>'}
            }
        )

        try:
            comments = confluence_client.get(
                f"/api/v2/pages/{page['id']}/footer-comments"
            )
            assert 'results' in comments
            assert len(comments['results']) == 0
        finally:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")

@pytest.mark.integration
class TestUpdateCommentLive:
    """Live tests for updating comments."""

    def test_update_comment_body(self, confluence_client, test_page):
        """Test updating a comment's body."""
        # Create comment
        comment = confluence_client.post(
            f"/api/v2/pages/{test_page['id']}/footer-comments",
            json_data={
                'body': {'representation': 'storage', 'value': '<p>Original</p>'}
            }
        )

        # Update it
        updated = confluence_client.put(
            f"/api/v2/footer-comments/{comment['id']}",
            json_data={
                'version': {'number': comment['version']['number'] + 1},
                'body': {'representation': 'storage', 'value': '<p>Updated</p>'}
            }
        )

        assert updated['version']['number'] == comment['version']['number'] + 1

@pytest.mark.integration
class TestDeleteCommentLive:
    """Live tests for deleting comments."""

    def test_delete_comment(self, confluence_client, test_page):
        """Test deleting a comment."""
        # Create comment
        comment = confluence_client.post(
            f"/api/v2/pages/{test_page['id']}/footer-comments",
            json_data={
                'body': {'representation': 'storage', 'value': '<p>Delete me</p>'}
            }
        )

        comment_id = comment['id']

        # Delete it
        confluence_client.delete(f"/api/v2/footer-comments/{comment_id}")

        # Verify deleted
        comments = confluence_client.get(
            f"/api/v2/pages/{test_page['id']}/footer-comments"
        )
        comment_ids = [c['id'] for c in comments['results']]
        assert comment_id not in comment_ids
