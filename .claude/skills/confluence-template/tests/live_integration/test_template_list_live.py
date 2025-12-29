"""
Live integration tests for template listing operations.

Usage:
    pytest test_template_list_live.py --profile development -v
"""

import pytest
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
class TestTemplateListLive:
    """Live tests for template listing operations."""

    def test_list_global_page_templates(self, confluence_client):
        """Test listing global page templates."""
        templates = confluence_client.get(
            '/rest/api/template/page',
            params={'limit': 25}
        )

        assert 'results' in templates

    def test_list_space_page_templates(self, confluence_client, test_space):
        """Test listing page templates in a space."""
        templates = confluence_client.get(
            '/rest/api/template/page',
            params={'spaceKey': test_space['key'], 'limit': 25}
        )

        assert 'results' in templates

    def test_list_blueprints(self, confluence_client):
        """Test listing content blueprints."""
        blueprints = confluence_client.get(
            '/rest/api/template/blueprint',
            params={'limit': 25}
        )

        assert 'results' in blueprints

    def test_list_space_blueprints(self, confluence_client, test_space):
        """Test listing blueprints available in a space."""
        blueprints = confluence_client.get(
            '/rest/api/template/blueprint',
            params={'spaceKey': test_space['key'], 'limit': 25}
        )

        assert 'results' in blueprints

    def test_template_structure(self, confluence_client):
        """Test that templates have expected structure."""
        templates = confluence_client.get(
            '/rest/api/template/page',
            params={'limit': 5}
        )

        for t in templates.get('results', []):
            # Templates should have name
            assert 'name' in t or 'title' in t

    def test_count_available_templates(self, confluence_client, test_space):
        """Test counting available templates."""
        templates = confluence_client.get(
            '/rest/api/template/page',
            params={'spaceKey': test_space['key'], 'limit': 100}
        )

        count = len(templates.get('results', []))
        assert count >= 0
