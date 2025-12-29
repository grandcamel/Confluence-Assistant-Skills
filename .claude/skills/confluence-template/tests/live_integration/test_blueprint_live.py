"""
Live integration tests for blueprint template operations.

Usage:
    pytest test_blueprint_live.py --profile development -v
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
class TestBlueprintLive:
    """Live tests for blueprint templates."""

    def test_list_blueprints(self, confluence_client):
        """Test listing available blueprints."""
        blueprints = confluence_client.get(
            '/rest/api/template/blueprint',
            params={'limit': 25}
        )

        assert 'results' in blueprints
        # Should have built-in blueprints

    def test_list_space_blueprints(self, confluence_client, test_space):
        """Test listing blueprints available in a space."""
        blueprints = confluence_client.get(
            '/rest/api/template/blueprint',
            params={'spaceKey': test_space['key'], 'limit': 25}
        )

        assert 'results' in blueprints

    def test_blueprint_structure(self, confluence_client):
        """Test that blueprints have expected structure."""
        blueprints = confluence_client.get(
            '/rest/api/template/blueprint',
            params={'limit': 5}
        )

        for bp in blueprints.get('results', []):
            assert 'templateId' in bp or 'contentBlueprintId' in bp
            assert 'name' in bp

    def test_create_page_from_blank_blueprint(self, confluence_client, test_space):
        """Test creating a page (equivalent to blank blueprint)."""
        title = f"Blueprint Test {uuid.uuid4().hex[:8]}"

        page = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'status': 'current',
                'title': title,
                'body': {
                    'representation': 'storage',
                    'value': '<p>Created from blank.</p>'
                }
            }
        )

        try:
            assert page['id'] is not None
            assert page['title'] == title
        finally:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")
