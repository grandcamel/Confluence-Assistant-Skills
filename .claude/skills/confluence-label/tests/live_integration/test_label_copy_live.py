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
        # Use v1 API - add all labels in one request
        label_data = [{'prefix': 'global', 'name': label} for label in labels]
        confluence_client.post(
            f"/rest/api/content/{source['id']}/label",
            json_data=label_data
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

            # Copy to target using v1 API
            label_data = [{'prefix': 'global', 'name': l['name']} for l in source_labels.get('results', [])]
            if label_data:
                confluence_client.post(
                    f"/rest/api/content/{target['id']}/label",
                    json_data=label_data
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
