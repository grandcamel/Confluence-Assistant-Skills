"""
Live integration tests for JSON property operations.

Usage:
    pytest test_property_json_live.py --profile development -v
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

@pytest.fixture
def test_page(confluence_client, test_space):
    page = confluence_client.post(
        '/api/v2/pages',
        json_data={
            'spaceId': test_space['id'],
            'status': 'current',
            'title': f'Property JSON Test {uuid.uuid4().hex[:8]}',
            'body': {'representation': 'storage', 'value': '<p>Test.</p>'}
        }
    )
    yield page
    try:
        confluence_client.delete(f"/api/v2/pages/{page['id']}")
    except Exception:
        pass

@pytest.mark.integration
class TestPropertyJsonLive:
    """Live tests for complex JSON property operations."""

    def test_nested_json_property(self, confluence_client, test_page):
        """Test storing nested JSON structure."""
        key = f'nested-{uuid.uuid4().hex[:8]}'
        value = {
            'level1': {
                'level2': {
                    'level3': 'deep value'
                }
            }
        }

        confluence_client.post(
            f"/rest/api/content/{test_page['id']}/property",
            json_data={'key': key, 'value': value}
        )

        prop = confluence_client.get(
            f"/rest/api/content/{test_page['id']}/property/{key}"
        )

        assert prop['value']['level1']['level2']['level3'] == 'deep value'

    def test_array_of_objects_property(self, confluence_client, test_page):
        """Test storing array of objects."""
        key = f'array-obj-{uuid.uuid4().hex[:8]}'
        value = [
            {'name': 'item1', 'count': 1},
            {'name': 'item2', 'count': 2},
            {'name': 'item3', 'count': 3}
        ]

        confluence_client.post(
            f"/rest/api/content/{test_page['id']}/property",
            json_data={'key': key, 'value': value}
        )

        prop = confluence_client.get(
            f"/rest/api/content/{test_page['id']}/property/{key}"
        )

        assert len(prop['value']) == 3
        assert prop['value'][0]['name'] == 'item1'

    def test_mixed_types_property(self, confluence_client, test_page):
        """Test storing mixed types in property."""
        key = f'mixed-{uuid.uuid4().hex[:8]}'
        value = {
            'string': 'text',
            'number': 42,
            'float': 3.14,
            'boolean': True,
            'null': None,
            'array': [1, 2, 3],
            'object': {'nested': 'value'}
        }

        confluence_client.post(
            f"/rest/api/content/{test_page['id']}/property",
            json_data={'key': key, 'value': value}
        )

        prop = confluence_client.get(
            f"/rest/api/content/{test_page['id']}/property/{key}"
        )

        assert prop['value']['string'] == 'text'
        assert prop['value']['number'] == 42
        assert prop['value']['boolean'] == True
