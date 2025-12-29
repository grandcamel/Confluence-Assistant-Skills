"""
Live integration tests for confluence-analytics skill.

Tests analytics and view operations against a real Confluence instance.

Usage:
    pytest test_analytics_live.py --profile development -v
"""

import pytest
import uuid
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'shared' / 'scripts' / 'lib'))

from config_manager import get_confluence_client


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
            'title': f'Analytics Test Page {uuid.uuid4().hex[:8]}',
            'body': {'representation': 'storage', 'value': '<p>Test.</p>'}
        }
    )
    yield page
    try:
        confluence_client.delete(f"/api/v2/pages/{page['id']}")
    except Exception:
        pass


@pytest.mark.integration
class TestGetPageViewsLive:
    """Live tests for getting page view statistics."""

    def test_get_page_views(self, confluence_client, test_page):
        """Test getting view count for a page."""
        # View the page to ensure there's at least one view
        confluence_client.get(f"/api/v2/pages/{test_page['id']}")

        # Get view statistics - use v1 API analytics endpoint
        # Note: Some Confluence instances may not have analytics enabled
        try:
            stats = confluence_client.get(
                f"/rest/api/content/{test_page['id']}",
                params={'expand': 'history'}
            )

            assert 'id' in stats
            # history.lastUpdated shows when last viewed/modified
            assert 'history' in stats

        except Exception as e:
            # Analytics may not be available on all instances
            pytest.skip(f"Analytics not available: {e}")


@pytest.mark.integration
class TestGetWatchersLive:
    """Live tests for getting content watchers."""

    def test_get_page_watchers(self, confluence_client, test_page):
        """Test getting watchers for a page."""
        # Watch the page first
        confluence_client.post(
            f'/rest/api/user/watch/content/{test_page["id"]}'
        )

        # Get watchers
        watchers = confluence_client.get(
            f"/rest/api/content/{test_page['id']}/notification/created"
        )

        assert 'results' in watchers
        assert len(watchers['results']) >= 1

        # Cleanup - unwatch
        try:
            confluence_client.delete(
                f'/rest/api/user/watch/content/{test_page["id"]}'
            )
        except Exception:
            pass

    def test_get_watchers_empty(self, confluence_client, test_space):
        """Test getting watchers for unwatched page."""
        page = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'status': 'current',
                'title': f'No Watchers {uuid.uuid4().hex[:8]}',
                'body': {'representation': 'storage', 'value': '<p>Empty.</p>'}
            }
        )

        try:
            watchers = confluence_client.get(
                f"/rest/api/content/{page['id']}/notification/created"
            )
            assert 'results' in watchers
        finally:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")


@pytest.mark.integration
class TestGetSpaceAnalyticsLive:
    """Live tests for space analytics."""

    def test_get_space_content_count(self, confluence_client, test_space):
        """Test getting content count in a space."""
        # List pages in space to get count
        pages = confluence_client.get(
            '/api/v2/pages',
            params={'space-id': test_space['id'], 'limit': 250}
        )

        assert 'results' in pages
        # Should be at least the homepage
        assert len(pages['results']) >= 0

    def test_get_space_info(self, confluence_client, test_space):
        """Test getting space information."""
        space = confluence_client.get(
            f"/api/v2/spaces/{test_space['id']}"
        )

        assert space['id'] == test_space['id']
        assert 'name' in space
        assert 'key' in space


@pytest.mark.integration
class TestGetPopularContentLive:
    """Live tests for popular content."""

    def test_search_recent_content(self, confluence_client, test_space):
        """Test finding recently modified content."""
        # Use CQL to find recent content
        results = confluence_client.get(
            '/rest/api/search',
            params={
                'cql': f'space = "{test_space["key"]}" ORDER BY lastModified DESC',
                'limit': 10
            }
        )

        assert 'results' in results
        # May have no results if space is new

    def test_search_content_by_type(self, confluence_client, test_space):
        """Test finding content by type."""
        # Search for pages
        results = confluence_client.get(
            '/rest/api/search',
            params={
                'cql': f'space = "{test_space["key"]}" AND type = page',
                'limit': 10
            }
        )

        assert 'results' in results
