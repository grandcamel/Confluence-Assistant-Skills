"""
Live integration tests for template variable operations.

Usage:
    pytest test_template_variables_live.py --profile development -v
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
class TestTemplateVariablesLive:
    """Live tests for template variable operations."""

    def test_create_page_with_placeholder(self, confluence_client, test_space):
        """Test creating a page with placeholder text."""
        title = f"Placeholder Test {uuid.uuid4().hex[:8]}"

        content = '''<p>Name: <ac:placeholder>Enter name here</ac:placeholder></p>
        <p>Date: <ac:placeholder>Enter date</ac:placeholder></p>'''

        page = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'status': 'current',
                'title': title,
                'body': {
                    'representation': 'storage',
                    'value': content
                }
            }
        )

        try:
            assert page['id'] is not None
        finally:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")

    def test_page_with_date_macro(self, confluence_client, test_space):
        """Test creating a page with date macro."""
        title = f"Date Macro Test {uuid.uuid4().hex[:8]}"

        from datetime import datetime
        today = datetime.now().strftime('%Y-%m-%d')

        content = f'''<p>Created on: <time datetime="{today}" /></p>'''

        page = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'status': 'current',
                'title': title,
                'body': {
                    'representation': 'storage',
                    'value': content
                }
            }
        )

        try:
            assert page['id'] is not None
        finally:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")

    def test_page_with_user_mention(self, confluence_client, test_space):
        """Test creating a page with user mention placeholder."""
        title = f"User Mention Test {uuid.uuid4().hex[:8]}"

        # Get current user for mention
        user = confluence_client.get('/rest/api/user/current')

        content = f'''<p>Author: <ac:link>
            <ri:user ri:account-id="{user['accountId']}" />
        </ac:link></p>'''

        page = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'status': 'current',
                'title': title,
                'body': {
                    'representation': 'storage',
                    'value': content
                }
            }
        )

        try:
            assert page['id'] is not None
        finally:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")

    def test_page_with_toc_macro(self, confluence_client, test_space):
        """Test creating a page with table of contents macro."""
        title = f"TOC Test {uuid.uuid4().hex[:8]}"

        content = '''<ac:structured-macro ac:name="toc" />
        <h1>Section 1</h1>
        <p>Content 1</p>
        <h1>Section 2</h1>
        <p>Content 2</p>'''

        page = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'status': 'current',
                'title': title,
                'body': {
                    'representation': 'storage',
                    'value': content
                }
            }
        )

        try:
            assert page['id'] is not None
        finally:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")
