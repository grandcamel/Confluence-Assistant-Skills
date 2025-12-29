"""
Live integration tests for page label operations.

Usage:
    pytest test_page_labels_live.py --profile development -v
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
def test_page(confluence_client, test_space):
    page = confluence_client.post(
        '/api/v2/pages',
        json_data={
            'spaceId': test_space['id'],
            'status': 'current',
            'title': f'Page Labels Test {uuid.uuid4().hex[:8]}',
            'body': {'representation': 'storage', 'value': '<p>Test.</p>'}
        }
    )
    yield page
    try:
        confluence_client.delete(f"/api/v2/pages/{page['id']}")
    except Exception:
        pass


@pytest.mark.integration
class TestPageLabelsLive:
    """Live tests for page label operations."""

    def test_add_label_to_page(self, confluence_client, test_page):
        """Test adding a label to a page."""
        label = f"test-{uuid.uuid4().hex[:8]}"

        confluence_client.post(
            f"/api/v2/pages/{test_page['id']}/labels",
            json_data={'name': label}
        )

        labels = confluence_client.get(f"/api/v2/pages/{test_page['id']}/labels")
        label_names = [l['name'] for l in labels.get('results', [])]
        assert label in label_names

    def test_remove_label_from_page(self, confluence_client, test_page):
        """Test removing a label from a page."""
        label = f"remove-{uuid.uuid4().hex[:8]}"

        # Add
        confluence_client.post(
            f"/api/v2/pages/{test_page['id']}/labels",
            json_data={'name': label}
        )

        # Get label ID
        labels = confluence_client.get(f"/api/v2/pages/{test_page['id']}/labels")
        label_id = None
        for l in labels.get('results', []):
            if l['name'] == label:
                label_id = l['id']
                break

        # Remove
        if label_id:
            confluence_client.delete(
                f"/api/v2/pages/{test_page['id']}/labels/{label_id}"
            )

        # Verify
        labels = confluence_client.get(f"/api/v2/pages/{test_page['id']}/labels")
        label_names = [l['name'] for l in labels.get('results', [])]
        assert label not in label_names

    def test_list_page_labels(self, confluence_client, test_page):
        """Test listing all labels on a page."""
        labels = ['label-a', 'label-b', 'label-c']

        for label in labels:
            confluence_client.post(
                f"/api/v2/pages/{test_page['id']}/labels",
                json_data={'name': f"{label}-{uuid.uuid4().hex[:4]}"}
            )

        page_labels = confluence_client.get(
            f"/api/v2/pages/{test_page['id']}/labels"
        )

        assert len(page_labels.get('results', [])) >= 3

    def test_page_with_no_labels(self, confluence_client, test_space):
        """Test that new page has no labels."""
        page = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'status': 'current',
                'title': f'No Labels Test {uuid.uuid4().hex[:8]}',
                'body': {'representation': 'storage', 'value': '<p>Test.</p>'}
            }
        )

        try:
            labels = confluence_client.get(f"/api/v2/pages/{page['id']}/labels")
            assert len(labels.get('results', [])) == 0
        finally:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")
