"""
Live integration tests for bulk label operations.

Usage:
    pytest test_bulk_label_live.py --profile development -v
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
def test_pages(confluence_client, test_space):
    """Create multiple test pages."""
    pages = []
    for i in range(3):
        page = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'status': 'current',
                'title': f'Bulk Label Test {i} {uuid.uuid4().hex[:8]}',
                'body': {'representation': 'storage', 'value': f'<p>Page {i}.</p>'}
            }
        )
        pages.append(page)

    yield pages

    for page in pages:
        try:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")
        except Exception:
            pass


@pytest.mark.integration
class TestBulkLabelLive:
    """Live tests for bulk label operations."""

    def test_add_same_label_to_multiple_pages(self, confluence_client, test_pages):
        """Test adding the same label to multiple pages."""
        label = f"bulk-test-{uuid.uuid4().hex[:8]}"

        for page in test_pages:
            confluence_client.post(
                f"/api/v2/pages/{page['id']}/labels",
                json_data={'name': label}
            )

        # Verify all pages have the label
        for page in test_pages:
            labels = confluence_client.get(f"/api/v2/pages/{page['id']}/labels")
            label_names = [l['name'] for l in labels.get('results', [])]
            assert label in label_names

    def test_add_multiple_labels_to_page(self, confluence_client, test_pages):
        """Test adding multiple labels to a single page."""
        page = test_pages[0]
        labels = [f"multi-{i}-{uuid.uuid4().hex[:4]}" for i in range(5)]

        for label in labels:
            confluence_client.post(
                f"/api/v2/pages/{page['id']}/labels",
                json_data={'name': label}
            )

        # Verify all labels exist
        page_labels = confluence_client.get(f"/api/v2/pages/{page['id']}/labels")
        label_names = [l['name'] for l in page_labels.get('results', [])]

        for label in labels:
            assert label in label_names

    def test_remove_labels_from_multiple_pages(self, confluence_client, test_pages):
        """Test removing labels from multiple pages."""
        label = f"remove-test-{uuid.uuid4().hex[:8]}"

        # Add to all pages
        for page in test_pages:
            confluence_client.post(
                f"/api/v2/pages/{page['id']}/labels",
                json_data={'name': label}
            )

        # Remove from all pages
        for page in test_pages:
            labels = confluence_client.get(f"/api/v2/pages/{page['id']}/labels")
            for l in labels.get('results', []):
                if l['name'] == label:
                    confluence_client.delete(
                        f"/api/v2/pages/{page['id']}/labels/{l['id']}"
                    )
                    break

        # Verify removal
        for page in test_pages:
            labels = confluence_client.get(f"/api/v2/pages/{page['id']}/labels")
            label_names = [l['name'] for l in labels.get('results', [])]
            assert label not in label_names
