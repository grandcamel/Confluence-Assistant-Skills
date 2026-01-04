"""
Live integration tests for page draft operations.

Usage:
    pytest test_page_drafts_live.py --profile development -v
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
class TestPageDraftsLive:
    """Live tests for page draft operations."""

    def test_create_draft_page(self, confluence_client, test_space):
        """Test creating a draft page."""
        title = f"Draft Test {uuid.uuid4().hex[:8]}"

        page = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'status': 'draft',
                'title': title,
                'body': {
                    'representation': 'storage',
                    'value': '<p>Draft content.</p>'
                }
            }
        )

        try:
            assert page['id'] is not None
            assert page['status'] == 'draft'
        finally:
            try:
                confluence_client.delete(f"/api/v2/pages/{page['id']}")
            except Exception:
                pass

    def test_publish_draft_page(self, confluence_client, test_space):
        """Test publishing a draft page."""
        title = f"Publish Draft Test {uuid.uuid4().hex[:8]}"

        # Create draft
        page = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'status': 'draft',
                'title': title,
                'body': {
                    'representation': 'storage',
                    'value': '<p>Will be published.</p>'
                }
            }
        )

        page_id = page['id']

        try:
            # Publish the draft - version must be 1 for first publish
            published = confluence_client.put(
                f'/api/v2/pages/{page_id}',
                json_data={
                    'id': page_id,
                    'status': 'current',
                    'title': title,
                    'spaceId': test_space['id'],
                    'body': {
                        'representation': 'storage',
                        'value': '<p>Now published.</p>'
                    },
                    'version': {'number': 1}
                }
            )

            assert published['status'] == 'current'
        finally:
            try:
                confluence_client.delete(f"/api/v2/pages/{page_id}")
            except Exception:
                pass  # Page may have been auto-deleted or not found

    def test_update_draft_content(self, confluence_client, test_space):
        """Test updating draft content before publishing."""
        title = f"Update Draft Test {uuid.uuid4().hex[:8]}"

        # Create draft
        page = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'status': 'draft',
                'title': title,
                'body': {
                    'representation': 'storage',
                    'value': '<p>Original draft.</p>'
                }
            }
        )

        page_id = page['id']

        try:
            # Update the draft - drafts don't support multiple versions, must use version 1
            updated = confluence_client.put(
                f'/api/v2/pages/{page_id}',
                json_data={
                    'id': page_id,
                    'status': 'draft',
                    'title': title,
                    'spaceId': test_space['id'],
                    'body': {
                        'representation': 'storage',
                        'value': '<p>Updated draft content.</p>'
                    },
                    'version': {'number': 1}
                }
            )

            assert updated['status'] == 'draft'
        finally:
            try:
                confluence_client.delete(f"/api/v2/pages/{page_id}")
            except Exception:
                pass
