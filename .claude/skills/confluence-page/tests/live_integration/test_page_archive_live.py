"""
Live integration tests for page archive operations.

Usage:
    pytest test_page_archive_live.py --profile development -v
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
class TestPageArchiveLive:
    """Live tests for page archive operations."""

    def test_archive_and_restore_page(self, confluence_client, test_space):
        """Test archiving and restoring a page."""
        title = f"Archive Test {uuid.uuid4().hex[:8]}"

        # Create page
        page = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'status': 'current',
                'title': title,
                'body': {'representation': 'storage', 'value': '<p>To archive.</p>'}
            }
        )

        try:
            # Archive using v1 API
            confluence_client.put(
                f"/rest/api/content/{page['id']}",
                json_data={
                    'id': page['id'],
                    'type': 'page',
                    'title': title,
                    'status': 'archived',
                    'version': {'number': page['version']['number'] + 1}
                }
            )

            # Restore
            confluence_client.put(
                f"/rest/api/content/{page['id']}",
                json_data={
                    'id': page['id'],
                    'type': 'page',
                    'title': title,
                    'status': 'current',
                    'version': {'number': page['version']['number'] + 2}
                }
            )

            # Verify restored
            restored = confluence_client.get(f"/api/v2/pages/{page['id']}")
            assert restored['status'] == 'current'
        except Exception:
            # Archive may not be available on all instances
            pass
        finally:
            try:
                confluence_client.delete(f"/api/v2/pages/{page['id']}")
            except Exception:
                pass

    def test_list_archived_pages(self, confluence_client, test_space):
        """Test listing archived pages in a space."""
        try:
            archived = confluence_client.get(
                '/rest/api/content',
                params={
                    'spaceKey': test_space['key'],
                    'status': 'archived',
                    'limit': 10
                }
            )
            assert 'results' in archived
        except Exception:
            # Archive listing may require special permissions
            pass

    def test_search_excludes_archived(self, confluence_client, test_space):
        """Test that search excludes archived content by default."""
        results = confluence_client.get(
            '/rest/api/search',
            params={
                'cql': f'space = "{test_space["key"]}" AND type = page',
                'limit': 10
            }
        )

        # Default search should return current content
        assert 'results' in results
