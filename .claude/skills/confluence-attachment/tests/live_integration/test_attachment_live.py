"""
Live integration tests for confluence-attachment skill.

Tests attachment operations against a real Confluence instance.

Usage:
    pytest test_attachment_live.py --profile development -v
"""

import pytest
import uuid
import sys
import tempfile
from pathlib import Path
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
            'title': f'Attachment Test Page {uuid.uuid4().hex[:8]}',
            'body': {'representation': 'storage', 'value': '<p>Test.</p>'}
        }
    )
    yield page
    try:
        confluence_client.delete(f"/api/v2/pages/{page['id']}")
    except Exception:
        pass

@pytest.fixture
def test_file():
    """Create a temporary test file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write('Test file content for attachment tests.')
        temp_path = Path(f.name)
    yield temp_path
    try:
        temp_path.unlink()
    except Exception:
        pass

@pytest.mark.integration
class TestUploadAttachmentLive:
    """Live tests for uploading attachments."""

    def test_upload_text_file(self, confluence_client, test_page, test_file):
        """Test uploading a text file attachment."""
        # Use v1 API for attachment upload
        with open(test_file, 'rb') as f:
            response = confluence_client.session.post(
                f"{confluence_client.base_url}/wiki/rest/api/content/{test_page['id']}/child/attachment",
                headers={'X-Atlassian-Token': 'nocheck'},
                files={'file': (test_file.name, f, 'text/plain')}
            )

        assert response.status_code in [200, 201]
        result = response.json()
        assert 'results' in result
        assert len(result['results']) >= 1

    def test_upload_with_comment(self, confluence_client, test_page, test_file):
        """Test uploading with a version comment."""
        with open(test_file, 'rb') as f:
            response = confluence_client.session.post(
                f"{confluence_client.base_url}/wiki/rest/api/content/{test_page['id']}/child/attachment",
                headers={'X-Atlassian-Token': 'nocheck'},
                files={'file': (test_file.name, f, 'text/plain')},
                data={'comment': 'Test upload comment'}
            )

        assert response.status_code in [200, 201]

@pytest.mark.integration
class TestListAttachmentsLive:
    """Live tests for listing attachments."""

    def test_list_page_attachments(self, confluence_client, test_page, test_file):
        """Test listing attachments on a page."""
        # Upload first
        with open(test_file, 'rb') as f:
            confluence_client.session.post(
                f"{confluence_client.base_url}/wiki/rest/api/content/{test_page['id']}/child/attachment",
                headers={'X-Atlassian-Token': 'nocheck'},
                files={'file': (test_file.name, f, 'text/plain')}
            )

        # List attachments
        attachments = confluence_client.get(
            f"/api/v2/pages/{test_page['id']}/attachments"
        )

        assert 'results' in attachments
        assert len(attachments['results']) >= 1

    def test_list_attachments_empty(self, confluence_client, test_space):
        """Test listing attachments on page with none."""
        page = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'status': 'current',
                'title': f'No Attachments {uuid.uuid4().hex[:8]}',
                'body': {'representation': 'storage', 'value': '<p>No attachments.</p>'}
            }
        )

        try:
            attachments = confluence_client.get(
                f"/api/v2/pages/{page['id']}/attachments"
            )
            assert 'results' in attachments
            assert len(attachments['results']) == 0
        finally:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")

@pytest.mark.integration
class TestDeleteAttachmentLive:
    """Live tests for deleting attachments."""

    def test_delete_attachment(self, confluence_client, test_page, test_file):
        """Test deleting an attachment."""
        # Upload
        with open(test_file, 'rb') as f:
            response = confluence_client.session.post(
                f"{confluence_client.base_url}/wiki/rest/api/content/{test_page['id']}/child/attachment",
                headers={'X-Atlassian-Token': 'nocheck'},
                files={'file': (f'delete-me-{uuid.uuid4().hex[:8]}.txt', f, 'text/plain')}
            )

        result = response.json()
        attachment_id = result['results'][0]['id']

        # Delete using v2 API
        confluence_client.delete(f"/api/v2/attachments/{attachment_id}")

        # Verify deleted
        attachments = confluence_client.get(
            f"/api/v2/pages/{test_page['id']}/attachments"
        )
        attachment_ids = [a['id'] for a in attachments.get('results', [])]
        assert attachment_id not in attachment_ids
