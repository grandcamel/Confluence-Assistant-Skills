"""
Live integration tests for attachment metadata operations.

Usage:
    pytest test_attachment_metadata_live.py --profile development -v
"""

import pytest
import uuid
import sys
import tempfile
import os
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
            'title': f'Attachment Metadata Test {uuid.uuid4().hex[:8]}',
            'body': {'representation': 'storage', 'value': '<p>Test.</p>'}
        }
    )
    yield page
    try:
        confluence_client.delete(f"/api/v2/pages/{page['id']}")
    except Exception:
        pass

@pytest.fixture
def test_attachment(confluence_client, test_page):
    """Create a test attachment."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write('Test attachment content for metadata tests.')
        temp_path = f.name

    try:
        with open(temp_path, 'rb') as f:
            attachment = confluence_client.upload_attachment(
                page_id=test_page['id'],
                file_path=temp_path,
                file_name=f'metadata-test-{uuid.uuid4().hex[:8]}.txt'
            )
        yield attachment
    finally:
        os.unlink(temp_path)

@pytest.mark.integration
class TestAttachmentMetadataLive:
    """Live tests for attachment metadata operations."""

    def test_get_attachment_details(self, confluence_client, test_page, test_attachment):
        """Test getting attachment details."""
        attachment = confluence_client.get(
            f"/api/v2/attachments/{test_attachment['id']}"
        )

        assert attachment['id'] == test_attachment['id']
        assert 'title' in attachment
        assert 'mediaType' in attachment

    def test_list_page_attachments(self, confluence_client, test_page, test_attachment):
        """Test listing all attachments on a page."""
        attachments = confluence_client.get(
            f"/api/v2/pages/{test_page['id']}/attachments"
        )

        assert 'results' in attachments
        attachment_ids = [a['id'] for a in attachments.get('results', [])]
        assert test_attachment['id'] in attachment_ids

    def test_attachment_media_type(self, confluence_client, test_attachment):
        """Test that attachment has correct media type."""
        attachment = confluence_client.get(
            f"/api/v2/attachments/{test_attachment['id']}"
        )

        # Text file should have text media type
        assert 'text' in attachment.get('mediaType', '').lower() or 'plain' in attachment.get('mediaType', '').lower()

    def test_attachment_has_file_size(self, confluence_client, test_attachment):
        """Test that attachment reports file size."""
        attachment = confluence_client.get(
            f"/api/v2/attachments/{test_attachment['id']}"
        )

        # Should have fileSize or webuiLink
        assert 'fileSize' in attachment or 'webuiLink' in attachment
