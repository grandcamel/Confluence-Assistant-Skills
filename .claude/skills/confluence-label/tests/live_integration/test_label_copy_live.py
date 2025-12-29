"""
Live integration tests for label copy operations.

Usage:
    pytest test_label_copy_live.py --profile development -v
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
class TestLabelCopyLive:
    """Live tests for copying labels between pages."""

    def test_copy_labels_to_new_page(self, confluence_client, test_space):
        """Test copying labels from one page to another."""
        # Create source page with labels
        source = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'status': 'current',
                'title': f'Source Page {uuid.uuid4().hex[:8]}',
                'body': {'representation': 'storage', 'value': '<p>Source.</p>'}
            }
        )

        labels = [f'copy-{i}-{uuid.uuid4().hex[:4]}' for i in range(3)]
        for label in labels:
            confluence_client.post(
                f"/api/v2/pages/{source['id']}/labels",
                json_data={'name': label}
            )

        # Create target page
        target = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'status': 'current',
                'title': f'Target Page {uuid.uuid4().hex[:8]}',
                'body': {'representation': 'storage', 'value': '<p>Target.</p>'}
            }
        )

        try:
            # Get source labels
            source_labels = confluence_client.get(
                f"/api/v2/pages/{source['id']}/labels"
            )

            # Copy to target
            for l in source_labels.get('results', []):
                confluence_client.post(
                    f"/api/v2/pages/{target['id']}/labels",
                    json_data={'name': l['name']}
                )

            # Verify
            target_labels = confluence_client.get(
                f"/api/v2/pages/{target['id']}/labels"
            )
            target_names = [l['name'] for l in target_labels.get('results', [])]

            for label in labels:
                assert label in target_names
        finally:
            confluence_client.delete(f"/api/v2/pages/{source['id']}")
            confluence_client.delete(f"/api/v2/pages/{target['id']}")
