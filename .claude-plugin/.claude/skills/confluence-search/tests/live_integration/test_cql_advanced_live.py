"""
Live integration tests for advanced CQL queries.

Usage:
    pytest test_cql_advanced_live.py --profile development -v
"""

import pytest
import sys
from datetime import datetime, timedelta
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
class TestCQLAdvancedLive:
    """Live tests for advanced CQL queries."""

    def test_cql_with_ordering(self, confluence_client, test_space):
        """Test CQL query with ORDER BY clause."""
        results = confluence_client.get(
            '/rest/api/search',
            params={
                'cql': f'space = "{test_space["key"]}" ORDER BY lastModified DESC',
                'limit': 10
            }
        )

        assert 'results' in results

    def test_cql_type_filter(self, confluence_client, test_space):
        """Test CQL query with type filter."""
        results = confluence_client.get(
            '/rest/api/search',
            params={
                'cql': f'space = "{test_space["key"]}" AND type = page',
                'limit': 10
            }
        )

        assert 'results' in results
        for result in results.get('results', []):
            assert result.get('content', {}).get('type') == 'page'

    def test_cql_date_range(self, confluence_client, test_space):
        """Test CQL query with date range."""
        # Last 30 days
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

        results = confluence_client.get(
            '/rest/api/search',
            params={
                'cql': f'space = "{test_space["key"]}" AND lastModified >= "{start_date}"',
                'limit': 25
            }
        )

        assert 'results' in results

    def test_cql_text_search(self, confluence_client, test_space):
        """Test CQL full-text search."""
        results = confluence_client.get(
            '/rest/api/search',
            params={
                'cql': f'space = "{test_space["key"]}" AND text ~ "test"',
                'limit': 10
            }
        )

        assert 'results' in results

    def test_cql_creator_filter(self, confluence_client):
        """Test CQL query filtering by creator."""
        results = confluence_client.get(
            '/rest/api/search',
            params={
                'cql': 'creator = currentUser() AND type = page',
                'limit': 10
            }
        )

        assert 'results' in results

    def test_cql_combined_filters(self, confluence_client, test_space):
        """Test CQL query with multiple combined filters."""
        start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')

        results = confluence_client.get(
            '/rest/api/search',
            params={
                'cql': f'space = "{test_space["key"]}" AND type = page AND lastModified >= "{start_date}" ORDER BY created DESC',
                'limit': 10
            }
        )

        assert 'results' in results

    def test_cql_exclude_pattern(self, confluence_client, test_space):
        """Test CQL query with exclusion."""
        results = confluence_client.get(
            '/rest/api/search',
            params={
                'cql': f'space = "{test_space["key"]}" AND type = page AND title !~ "Test"',
                'limit': 10
            }
        )

        assert 'results' in results
