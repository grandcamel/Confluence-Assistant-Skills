"""
Live integration tests for label search operations.

Usage:
    pytest test_label_search_live.py --profile development -v
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
def labeled_page(confluence_client, test_space):
    """Create a page with a unique label."""
    label = f"search-test-{uuid.uuid4().hex[:8]}"

    page = confluence_client.post(
        '/api/v2/pages',
        json_data={
            'spaceId': test_space['id'],
            'status': 'current',
            'title': f'Label Search Test {uuid.uuid4().hex[:8]}',
            'body': {'representation': 'storage', 'value': '<p>Test.</p>'}
        }
    )

    # Add the label using v1 API
    confluence_client.post(
        f"/rest/api/content/{page['id']}/label",
        json_data=[{'prefix': 'global', 'name': label}]
    )

    yield {'page': page, 'label': label}

    try:
        confluence_client.delete(f"/api/v2/pages/{page['id']}")
    except Exception:
        pass

@pytest.mark.integration
class TestLabelSearchLive:
    """Live tests for label search operations."""

    def test_search_by_label_cql(self, confluence_client, labeled_page):
        """Test searching for content by label using CQL."""
        label = labeled_page['label']

        results = confluence_client.get(
            '/rest/api/search',
            params={
                'cql': f'label = "{label}"',
                'limit': 10
            }
        )

        assert 'results' in results
        # Should find our page
        page_ids = [
            r.get('content', {}).get('id')
            for r in results.get('results', [])
        ]
        assert labeled_page['page']['id'] in page_ids

    def test_search_multiple_labels(self, confluence_client, test_space, labeled_page):
        """Test searching with multiple label conditions."""
        label = labeled_page['label']

        # Add another label using v1 API
        second_label = f"second-{uuid.uuid4().hex[:8]}"
        confluence_client.post(
            f"/rest/api/content/{labeled_page['page']['id']}/label",
            json_data=[{'prefix': 'global', 'name': second_label}]
        )

        # Search for pages with both labels
        results = confluence_client.get(
            '/rest/api/search',
            params={
                'cql': f'label = "{label}" AND label = "{second_label}"',
                'limit': 10
            }
        )

        assert 'results' in results

    def test_search_label_in_space(self, confluence_client, test_space, labeled_page):
        """Test searching for labeled content within a space."""
        label = labeled_page['label']

        results = confluence_client.get(
            '/rest/api/search',
            params={
                'cql': f'space = "{test_space["key"]}" AND label = "{label}"',
                'limit': 10
            }
        )

        assert 'results' in results

    def test_get_all_labels_in_space(self, confluence_client, test_space):
        """Test getting all unique labels used in a space."""
        # Search for any labeled content in the space
        results = confluence_client.get(
            '/rest/api/search',
            params={
                'cql': f'space = "{test_space["key"]}" AND label IS NOT NULL',
                'limit': 25
            }
        )

        assert 'results' in results
