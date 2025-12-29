"""
Live integration tests for attachment version operations.

Usage:
    pytest test_attachment_versions_live.py --profile development -v
"""

import pytest
import uuid
import tempfile
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
            'title': f'Attachment Version Test {uuid.uuid4().hex[:8]}',
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
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write('Version 1 content.')
        temp_path = Path(f.name)
    yield temp_path
    try:
        temp_path.unlink()
    except Exception:
        pass


@pytest.mark.integration
class TestAttachmentVersionsLive:
    """Live tests for attachment version operations."""

    def test_upload_new_version(self, confluence_client, test_page, test_file):
        """Test uploading a new version of an attachment."""
        filename = f"versioned-{uuid.uuid4().hex[:8]}.txt"

        # Upload v1
        with open(test_file, 'rb') as f:
            response = confluence_client.session.post(
                f"{confluence_client.base_url}/wiki/rest/api/content/{test_page['id']}/child/attachment",
                headers={'X-Atlassian-Token': 'nocheck'},
                files={'file': (filename, f, 'text/plain')},
                data={'comment': 'Version 1'}
            )

        result = response.json()
        attachment_id = result['results'][0]['id']

        # Upload v2 - same filename
        with open(test_file, 'w') as f:
            f.write('Version 2 content - updated.')

        with open(test_file, 'rb') as f:
            response = confluence_client.session.post(
                f"{confluence_client.base_url}/wiki/rest/api/content/{test_page['id']}/child/attachment",
                headers={'X-Atlassian-Token': 'nocheck'},
                files={'file': (filename, f, 'text/plain')},
                data={'comment': 'Version 2'}
            )

        # Should update existing attachment
        assert response.status_code in [200, 201]

        # Clean up
        confluence_client.delete(f"/api/v2/attachments/{attachment_id}")

    def test_get_attachment_metadata(self, confluence_client, test_page, test_file):
        """Test getting attachment metadata."""
        filename = f"meta-{uuid.uuid4().hex[:8]}.txt"

        with open(test_file, 'rb') as f:
            response = confluence_client.session.post(
                f"{confluence_client.base_url}/wiki/rest/api/content/{test_page['id']}/child/attachment",
                headers={'X-Atlassian-Token': 'nocheck'},
                files={'file': (filename, f, 'text/plain')}
            )

        result = response.json()
        attachment_id = result['results'][0]['id']

        # Get metadata using v2 API
        attachment = confluence_client.get(f"/api/v2/attachments/{attachment_id}")

        assert 'title' in attachment
        assert 'mediaType' in attachment

        # Clean up
        confluence_client.delete(f"/api/v2/attachments/{attachment_id}")
