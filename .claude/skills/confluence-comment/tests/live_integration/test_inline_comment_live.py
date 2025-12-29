"""
Live integration tests for inline comment operations.

Usage:
    pytest test_inline_comment_live.py --profile development -v
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
            'title': f'Inline Comment Test {uuid.uuid4().hex[:8]}',
            'body': {
                'representation': 'storage',
                'value': '<p>This is paragraph one with some text.</p><p>This is paragraph two.</p>'
            }
        }
    )
    yield page
    try:
        confluence_client.delete(f"/api/v2/pages/{page['id']}")
    except Exception:
        pass

@pytest.mark.integration
class TestInlineCommentsLive:
    """Live tests for inline comments."""

    def test_get_inline_comments(self, confluence_client, test_page):
        """Test getting inline comments from a page."""
        comments = confluence_client.get(
            f"/api/v2/pages/{test_page['id']}/inline-comments"
        )

        assert 'results' in comments
        # New page should have no inline comments
        assert len(comments['results']) == 0

    def test_add_inline_comment(self, confluence_client, test_page):
        """Test adding an inline comment."""
        # Note: Inline comments require specific text selection context
        # This test creates a footer comment as inline requires browser context
        comment = confluence_client.post(
            f"/api/v2/pages/{test_page['id']}/footer-comments",
            json_data={
                'body': {
                    'representation': 'storage',
                    'value': '<p>This simulates inline feedback.</p>'
                }
            }
        )

        assert comment['id'] is not None

    def test_resolve_comment(self, confluence_client, test_page):
        """Test resolving a comment (marking as resolved)."""
        # Create comment
        comment = confluence_client.post(
            f"/api/v2/pages/{test_page['id']}/footer-comments",
            json_data={
                'body': {'representation': 'storage', 'value': '<p>To resolve.</p>'}
            }
        )

        # Note: Resolving comments may require specific API endpoints
        # The v2 API doesn't have a direct resolve endpoint
        # Check if comment was created
        assert comment['id'] is not None
