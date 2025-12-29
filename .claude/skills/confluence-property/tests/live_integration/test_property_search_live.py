"""
Live integration tests for property search operations.

Usage:
    pytest test_property_search_live.py --profile development -v
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


@pytest.fixture
def page_with_property(confluence_client, test_space):
    """Create a page with a content property."""
    page = confluence_client.post(
        '/api/v2/pages',
        json_data={
            'spaceId': test_space['id'],
            'status': 'current',
            'title': f'Property Search Test {uuid.uuid4().hex[:8]}',
            'body': {'representation': 'storage', 'value': '<p>Test.</p>'}
        }
    )

    prop_key = f'search-prop-{uuid.uuid4().hex[:8]}'
    prop_value = {'searchable': True, 'category': 'test'}

    confluence_client.post(
        f"/rest/api/content/{page['id']}/property",
        json_data={'key': prop_key, 'value': prop_value}
    )

    yield {'page': page, 'prop_key': prop_key, 'prop_value': prop_value}

    try:
        confluence_client.delete(f"/api/v2/pages/{page['id']}")
    except Exception:
        pass


@pytest.mark.integration
class TestPropertySearchLive:
    """Live tests for property search operations."""

    def test_find_pages_with_property(self, confluence_client, page_with_property):
        """Test finding pages that have a specific property key."""
        page = page_with_property['page']
        prop_key = page_with_property['prop_key']

        # Get the property to verify it exists
        prop = confluence_client.get(
            f"/rest/api/content/{page['id']}/property/{prop_key}"
        )

        assert prop['key'] == prop_key

    def test_list_all_properties_on_page(self, confluence_client, page_with_property):
        """Test listing all properties on a page."""
        page = page_with_property['page']

        props = confluence_client.get(
            f"/rest/api/content/{page['id']}/property"
        )

        assert 'results' in props
        prop_keys = [p['key'] for p in props.get('results', [])]
        assert page_with_property['prop_key'] in prop_keys

    def test_property_value_retrieval(self, confluence_client, page_with_property):
        """Test that property value is correctly retrieved."""
        page = page_with_property['page']
        prop_key = page_with_property['prop_key']
        expected_value = page_with_property['prop_value']

        prop = confluence_client.get(
            f"/rest/api/content/{page['id']}/property/{prop_key}"
        )

        assert prop['value'] == expected_value

    def test_search_content_with_properties(self, confluence_client, test_space):
        """Test searching for content in space (properties are metadata)."""
        # CQL search for pages - properties themselves aren't directly CQL searchable
        # but we can find pages and then check their properties
        results = confluence_client.get(
            '/rest/api/search',
            params={
                'cql': f'space = "{test_space["key"]}" AND type = page',
                'limit': 10
            }
        )

        assert 'results' in results
