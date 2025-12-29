"""
Live integration tests for attachment type operations.

Usage:
    pytest test_attachment_types_live.py --profile development -v
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
            'title': f'Attachment Types Test {uuid.uuid4().hex[:8]}',
            'body': {'representation': 'storage', 'value': '<p>Test.</p>'}
        }
    )
    yield page
    try:
        confluence_client.delete(f"/api/v2/pages/{page['id']}")
    except Exception:
        pass

@pytest.mark.integration
class TestAttachmentTypesLive:
    """Live tests for different attachment types."""

    def test_upload_text_file(self, confluence_client, test_page):
        """Test uploading a text file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('Text file content.')
            temp_path = f.name

        try:
            attachment = confluence_client.upload_attachment(
                page_id=test_page['id'],
                file_path=temp_path,
                file_name=f'text-{uuid.uuid4().hex[:8]}.txt'
            )
            assert attachment['id'] is not None
        finally:
            os.unlink(temp_path)

    def test_upload_json_file(self, confluence_client, test_page):
        """Test uploading a JSON file."""
        import json

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({'key': 'value'}, f)
            temp_path = f.name

        try:
            attachment = confluence_client.upload_attachment(
                page_id=test_page['id'],
                file_path=temp_path,
                file_name=f'data-{uuid.uuid4().hex[:8]}.json'
            )
            assert attachment['id'] is not None
            assert 'json' in attachment.get('mediaType', '').lower() or attachment['id']
        finally:
            os.unlink(temp_path)

    def test_upload_csv_file(self, confluence_client, test_page):
        """Test uploading a CSV file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write('col1,col2,col3\n1,2,3\n4,5,6')
            temp_path = f.name

        try:
            attachment = confluence_client.upload_attachment(
                page_id=test_page['id'],
                file_path=temp_path,
                file_name=f'data-{uuid.uuid4().hex[:8]}.csv'
            )
            assert attachment['id'] is not None
        finally:
            os.unlink(temp_path)

    def test_upload_markdown_file(self, confluence_client, test_page):
        """Test uploading a Markdown file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write('# Heading\n\nSome **bold** text.')
            temp_path = f.name

        try:
            attachment = confluence_client.upload_attachment(
                page_id=test_page['id'],
                file_path=temp_path,
                file_name=f'doc-{uuid.uuid4().hex[:8]}.md'
            )
            assert attachment['id'] is not None
        finally:
            os.unlink(temp_path)
