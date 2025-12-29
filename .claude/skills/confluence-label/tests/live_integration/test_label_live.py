"""
Live integration tests for confluence-label skill.

Tests label operations against a real Confluence instance.

Usage:
    pytest test_label_live.py --profile development -v
"""

import pytest
import uuid
import sys
from confluence_assistant_skills_lib import (
    get_confluence_client,
)

def pytest_addoption(parser):
    try:
        parser.addoption("--profile", action="store", default=None, help="Confluence profile")
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
            'title': f'Label Test Page {uuid.uuid4().hex[:8]}',
            'body': {'representation': 'storage', 'value': '<p>Test.</p>'}
        }
    )
    yield page
    try:
        confluence_client.delete(f"/api/v2/pages/{page['id']}")
    except Exception:
        pass

@pytest.fixture
def test_label():
    return f"test-label-{uuid.uuid4().hex[:8]}"

@pytest.mark.integration
class TestAddLabelLive:
    """Live tests for adding labels."""

    def test_add_label_to_page(self, confluence_client, test_page, test_label):
        """Test adding a label to a page."""
        result = confluence_client.post(
            f"/api/v2/pages/{test_page['id']}/labels",
            json_data={'name': test_label}
        )

        assert result is not None

    def test_add_multiple_labels(self, confluence_client, test_page):
        """Test adding multiple labels."""
        labels = [f"label-{i}-{uuid.uuid4().hex[:4]}" for i in range(3)]

        for label in labels:
            confluence_client.post(
                f"/api/v2/pages/{test_page['id']}/labels",
                json_data={'name': label}
            )

        # Verify all labels
        page_labels = confluence_client.get(
            f"/api/v2/pages/{test_page['id']}/labels"
        )

        label_names = [l['name'] for l in page_labels.get('results', [])]
        for label in labels:
            assert label in label_names

    def test_add_duplicate_label(self, confluence_client, test_page, test_label):
        """Test adding the same label twice."""
        # Add first time
        confluence_client.post(
            f"/api/v2/pages/{test_page['id']}/labels",
            json_data={'name': test_label}
        )

        # Add second time - should not error
        result = confluence_client.post(
            f"/api/v2/pages/{test_page['id']}/labels",
            json_data={'name': test_label}
        )
        assert result is not None

@pytest.mark.integration
class TestGetLabelsLive:
    """Live tests for retrieving labels."""

    def test_get_page_labels(self, confluence_client, test_page, test_label):
        """Test getting labels from a page."""
        # Add a label first
        confluence_client.post(
            f"/api/v2/pages/{test_page['id']}/labels",
            json_data={'name': test_label}
        )

        labels = confluence_client.get(
            f"/api/v2/pages/{test_page['id']}/labels"
        )

        assert 'results' in labels
        assert len(labels['results']) >= 1
        assert any(l['name'] == test_label for l in labels['results'])

    def test_get_labels_empty(self, confluence_client, test_space):
        """Test getting labels from page with no labels."""
        page = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'status': 'current',
                'title': f'No Labels {uuid.uuid4().hex[:8]}',
                'body': {'representation': 'storage', 'value': '<p>No labels.</p>'}
            }
        )

        try:
            labels = confluence_client.get(f"/api/v2/pages/{page['id']}/labels")
            assert 'results' in labels
        finally:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")

@pytest.mark.integration
class TestRemoveLabelLive:
    """Live tests for removing labels."""

    def test_remove_label(self, confluence_client, test_page, test_label):
        """Test removing a label from a page."""
        # Add label
        confluence_client.post(
            f"/api/v2/pages/{test_page['id']}/labels",
            json_data={'name': test_label}
        )

        # Get label ID
        labels = confluence_client.get(f"/api/v2/pages/{test_page['id']}/labels")
        label_id = None
        for l in labels['results']:
            if l['name'] == test_label:
                label_id = l['id']
                break

        assert label_id is not None

        # Remove label
        confluence_client.delete(
            f"/api/v2/pages/{test_page['id']}/labels/{label_id}"
        )

        # Verify removed
        labels_after = confluence_client.get(f"/api/v2/pages/{test_page['id']}/labels")
        label_names = [l['name'] for l in labels_after.get('results', [])]
        assert test_label not in label_names

@pytest.mark.integration
class TestSearchByLabelLive:
    """Live tests for searching by label."""

    def test_search_content_by_label(self, confluence_client, test_page, test_label):
        """Test searching for content by label."""
        # Add label
        confluence_client.post(
            f"/api/v2/pages/{test_page['id']}/labels",
            json_data={'name': test_label}
        )

        # Search using CQL
        import time
        time.sleep(1)  # Allow indexing

        results = confluence_client.get(
            '/rest/api/search',
            params={'cql': f'label = "{test_label}"'}
        )

        assert 'results' in results
        # Page should be in results (may need indexing time)
