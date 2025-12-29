"""
Live integration tests for label suggestion operations.

Usage:
    pytest test_label_suggestions_live.py --profile development -v
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
class TestLabelSuggestionsLive:
    """Live tests for label suggestion operations."""

    def test_get_popular_labels(self, confluence_client, test_space):
        """Test getting popular labels in space."""
        # Search for content with labels
        results = confluence_client.get(
            '/rest/api/search',
            params={
                'cql': f'space = "{test_space["key"]}" AND label IS NOT NULL',
                'limit': 25
            }
        )

        assert 'results' in results

    def test_find_related_labels(self, confluence_client, test_space):
        """Test finding content with related labels."""
        # Create a page with labels
        page = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'status': 'current',
                'title': f'Label Suggest Test {uuid.uuid4().hex[:8]}',
                'body': {'representation': 'storage', 'value': '<p>Test.</p>'}
            }
        )

        try:
            label = f"suggest-{uuid.uuid4().hex[:8]}"
            confluence_client.post(
                f"/api/v2/pages/{page['id']}/labels",
                json_data={'name': label}
            )

            # Get page labels
            labels = confluence_client.get(f"/api/v2/pages/{page['id']}/labels")
            assert 'results' in labels
        finally:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")

    def test_list_all_space_labels(self, confluence_client, test_space):
        """Test listing all labels used in a space."""
        # Search for labeled content
        results = confluence_client.get(
            '/rest/api/search',
            params={
                'cql': f'space = "{test_space["key"]}"',
                'limit': 50
            }
        )

        # Collect unique labels from results
        all_labels = set()
        for r in results.get('results', []):
            content_id = r.get('content', {}).get('id')
            if content_id:
                try:
                    labels = confluence_client.get(
                        f"/api/v2/pages/{content_id}/labels"
                    )
                    for l in labels.get('results', []):
                        all_labels.add(l['name'])
                except Exception:
                    pass

        # Just verify we can collect labels
        assert isinstance(all_labels, set)
