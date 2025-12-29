"""
Live integration tests for template content operations.

Usage:
    pytest test_template_content_live.py --profile development -v
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


@pytest.mark.integration
class TestTemplateContentLive:
    """Live tests for template content operations."""

    def test_create_decision_template(self, confluence_client, test_space):
        """Test creating a decision document template."""
        title = f"Decision {uuid.uuid4().hex[:8]}"

        content = '''<h2>Decision</h2>
        <p><ac:placeholder>Describe the decision</ac:placeholder></p>
        <h2>Context</h2>
        <p><ac:placeholder>Background information</ac:placeholder></p>
        <h2>Options Considered</h2>
        <ol>
            <li>Option A</li>
            <li>Option B</li>
        </ol>
        <h2>Outcome</h2>
        <p><ac:placeholder>Final decision and rationale</ac:placeholder></p>'''

        page = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'status': 'current',
                'title': title,
                'body': {'representation': 'storage', 'value': content}
            }
        )

        try:
            assert page['id'] is not None
        finally:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")

    def test_create_meeting_notes_template(self, confluence_client, test_space):
        """Test creating a meeting notes template."""
        title = f"Meeting Notes {uuid.uuid4().hex[:8]}"

        content = '''<h2>Meeting Information</h2>
        <p><strong>Date:</strong> <ac:placeholder>Date</ac:placeholder></p>
        <p><strong>Attendees:</strong> <ac:placeholder>List attendees</ac:placeholder></p>
        <h2>Agenda</h2>
        <ol>
            <li>Topic 1</li>
            <li>Topic 2</li>
        </ol>
        <h2>Discussion</h2>
        <p><ac:placeholder>Notes</ac:placeholder></p>
        <h2>Action Items</h2>
        <ac:task-list>
            <ac:task>
                <ac:task-status>incomplete</ac:task-status>
                <ac:task-body><ac:placeholder>Action item</ac:placeholder></ac:task-body>
            </ac:task>
        </ac:task-list>'''

        page = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'status': 'current',
                'title': title,
                'body': {'representation': 'storage', 'value': content}
            }
        )

        try:
            assert page['id'] is not None
        finally:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")
