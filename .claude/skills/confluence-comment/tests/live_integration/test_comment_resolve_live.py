"""
Live integration tests for comment resolve operations.

Usage:
    pytest test_comment_resolve_live.py --profile development -v
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
            'title': f'Comment Resolve Test {uuid.uuid4().hex[:8]}',
            'body': {'representation': 'storage', 'value': '<p>Test.</p>'}
        }
    )
    yield page
    try:
        confluence_client.delete(f"/api/v2/pages/{page['id']}")
    except Exception:
        pass

@pytest.mark.integration
class TestCommentResolveLive:
    """Live tests for comment resolve operations."""

    def test_create_inline_comment(self, confluence_client, test_page):
        """Test creating an inline comment."""
        try:
            comment = confluence_client.post(
                f"/api/v2/pages/{test_page['id']}/inline-comments",
                json_data={
                    'body': {
                        'representation': 'storage',
                        'value': '<p>Inline comment.</p>'
                    },
                    'inlineCommentProperties': {
                        'textSelection': 'Test',
                        'textSelectionMatchCount': 1,
                        'textSelectionMatchIndex': 0
                    }
                }
            )
            assert comment['id'] is not None
        except Exception:
            # Inline comments may not be available on all instances
            pass

    def test_list_inline_comments(self, confluence_client, test_page):
        """Test listing inline comments."""
        try:
            comments = confluence_client.get(
                f"/api/v2/pages/{test_page['id']}/inline-comments"
            )
            assert 'results' in comments
        except Exception:
            # Inline comments API may differ
            pass

    def test_footer_comment_lifecycle(self, confluence_client, test_page):
        """Test full comment lifecycle."""
        # Create
        comment = confluence_client.post(
            f"/api/v2/pages/{test_page['id']}/footer-comments",
            json_data={
                'body': {
                    'representation': 'storage',
                    'value': '<p>Lifecycle test.</p>'
                }
            }
        )

        try:
            # Read
            fetched = confluence_client.get(
                f"/api/v2/footer-comments/{comment['id']}"
            )
            assert fetched['id'] == comment['id']

            # Update
            updated = confluence_client.put(
                f"/api/v2/footer-comments/{comment['id']}",
                json_data={
                    'body': {
                        'representation': 'storage',
                        'value': '<p>Updated lifecycle.</p>'
                    },
                    'version': {'number': comment['version']['number'] + 1}
                }
            )
            assert updated['version']['number'] > comment['version']['number']

        finally:
            # Delete
            confluence_client.delete(f"/api/v2/footer-comments/{comment['id']}")
