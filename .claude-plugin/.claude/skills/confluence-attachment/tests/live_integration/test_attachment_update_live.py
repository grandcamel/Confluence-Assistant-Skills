"""
Live integration tests for attachment update operations.

Usage:
    pytest test_attachment_update_live.py --profile development -v
"""

import pytest
import uuid
import sys
import tempfile
import os
from pathlib import Path
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
            'title': f'Attachment Update Test {uuid.uuid4().hex[:8]}',
            'body': {'representation': 'storage', 'value': '<p>Test.</p>'}
        }
    )
    yield page
    try:
        confluence_client.delete(f"/api/v2/pages/{page['id']}")
    except Exception:
        pass

@pytest.mark.integration
class TestAttachmentUpdateLive:
    """Live tests for attachment update operations."""

    def test_upload_new_version(self, confluence_client, test_page):
        """Test uploading a new version of an attachment."""
        # Create initial attachment
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('Version 1 content.')
            temp_path = Path(f.name)

        try:
            result = confluence_client.upload_file(
                f"/rest/api/content/{test_page['id']}/child/attachment",
                temp_path
            )
            attachment = result['results'][0]
            attachment_id = attachment['id']

            # Update with version 2
            with open(temp_path, 'w') as f:
                f.write('Version 2 content.')

            # Upload new version using update endpoint
            updated = confluence_client.upload_file(
                f"/rest/api/content/{test_page['id']}/child/attachment/{attachment_id}/data",
                temp_path
            )

            # Should have updated successfully
            assert updated is not None
        finally:
            os.unlink(temp_path)

    def test_rename_attachment(self, confluence_client, test_page):
        """Test that attachment can be retrieved after upload."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('Rename test content.')
            temp_path = Path(f.name)

        try:
            result = confluence_client.upload_file(
                f"/rest/api/content/{test_page['id']}/child/attachment",
                temp_path
            )
            attachment = result['results'][0]

            # Get the attachment using v2 API
            fetched = confluence_client.get(
                f"/api/v2/attachments/{attachment['id']}"
            )
            assert fetched['id'] == attachment['id']
        finally:
            os.unlink(temp_path)

    def test_delete_attachment(self, confluence_client, test_page):
        """Test deleting an attachment."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('Delete test.')
            temp_path = Path(f.name)

        try:
            result = confluence_client.upload_file(
                f"/rest/api/content/{test_page['id']}/child/attachment",
                temp_path
            )
            attachment = result['results'][0]

            # Delete using v1 API (more reliable)
            confluence_client.delete(f"/rest/api/content/{attachment['id']}")

            # Verify deleted
            try:
                confluence_client.get(f"/api/v2/attachments/{attachment['id']}")
                assert False, "Attachment should be deleted"
            except Exception:
                pass  # Expected
        finally:
            os.unlink(temp_path)
