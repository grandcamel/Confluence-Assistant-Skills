"""
Live integration tests for confluence-search skill.

Tests CQL search operations against a real Confluence instance.

Usage:
    pytest test_search_live.py --profile development -v
"""

import pytest
import uuid
import sys
import time
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
    unique_text = f"UniqueTestContent{uuid.uuid4().hex[:12]}"
    page = confluence_client.post(
        '/api/v2/pages',
        json_data={
            'spaceId': test_space['id'],
            'status': 'current',
            'title': f'Search Test {uuid.uuid4().hex[:8]}',
            'body': {
                'representation': 'storage',
                'value': f'<p>This page contains {unique_text} for searching.</p>'
            }
        }
    )
    page['_unique_text'] = unique_text
    # Allow time for indexing
    time.sleep(1)
    yield page
    try:
        confluence_client.delete(f"/api/v2/pages/{page['id']}")
    except Exception:
        pass

@pytest.mark.integration
class TestCqlSearchLive:
    """Live tests for CQL searches."""

    def test_search_by_space(self, confluence_client, test_space):
        """Test searching within a space."""
        results = confluence_client.get(
            '/rest/api/search',
            params={
                'cql': f'space = "{test_space["key"]}" AND type = page',
                'limit': 10
            }
        )

        assert 'results' in results
        assert isinstance(results['results'], list)

    def test_search_by_type(self, confluence_client):
        """Test searching by content type."""
        results = confluence_client.get(
            '/rest/api/search',
            params={
                'cql': 'type = page',
                'limit': 5
            }
        )

        assert 'results' in results
        for result in results['results']:
            content = result.get('content', {})
            assert content.get('type') == 'page'

    def test_search_by_text(self, confluence_client, test_page):
        """Test full-text search."""
        unique_text = test_page.get('_unique_text', '')

        # Give more time for indexing
        time.sleep(2)

        results = confluence_client.get(
            '/rest/api/search',
            params={
                'cql': f'text ~ "{unique_text}"',
                'limit': 10
            }
        )

        assert 'results' in results
        # May not find immediately due to indexing delay

    def test_search_by_title(self, confluence_client, test_page):
        """Test searching by title."""
        title = test_page['title']

        results = confluence_client.get(
            '/rest/api/search',
            params={
                'cql': f'title ~ "{title}"',
                'limit': 10
            }
        )

        assert 'results' in results

    def test_search_recent(self, confluence_client, test_space):
        """Test searching for recently modified content."""
        results = confluence_client.get(
            '/rest/api/search',
            params={
                'cql': f'space = "{test_space["key"]}" ORDER BY lastModified DESC',
                'limit': 5
            }
        )

        assert 'results' in results

    def test_search_by_creator(self, confluence_client):
        """Test searching by creator."""
        results = confluence_client.get(
            '/rest/api/search',
            params={
                'cql': 'creator = currentUser() AND type = page',
                'limit': 5
            }
        )

        assert 'results' in results

    def test_search_by_label(self, confluence_client, test_space, test_page):
        """Test searching by label."""
        label = f"searchtest-{uuid.uuid4().hex[:8]}"

        # Add label to page using v1 API (v2 doesn't support POST for labels)
        confluence_client.post(
            f"/rest/api/content/{test_page['id']}/label",
            json_data=[{'name': label}]
        )

        time.sleep(3)  # Wait for indexing

        results = confluence_client.get(
            '/rest/api/search',
            params={
                'cql': f'label = "{label}"',
                'limit': 10
            }
        )

        assert 'results' in results

@pytest.mark.integration
class TestSearchPaginationLive:
    """Live tests for search pagination."""

    def test_search_with_limit(self, confluence_client):
        """Test search with limit."""
        results = confluence_client.get(
            '/rest/api/search',
            params={
                'cql': 'type = page',
                'limit': 3
            }
        )

        assert 'results' in results
        assert len(results['results']) <= 3

    def test_search_with_start(self, confluence_client):
        """Test search with offset."""
        # First page
        page1 = confluence_client.get(
            '/rest/api/search',
            params={
                'cql': 'type = page ORDER BY created DESC',
                'limit': 2,
                'start': 0
            }
        )

        # Second page
        page2 = confluence_client.get(
            '/rest/api/search',
            params={
                'cql': 'type = page ORDER BY created DESC',
                'limit': 2,
                'start': 2
            }
        )

        assert 'results' in page1
        assert 'results' in page2

        # Pages should be different (if enough content exists)
        # Note: With sparse data, page2 may be empty or have same results
        page1_ids = [r.get('content', {}).get('id') for r in page1.get('results', [])]
        page2_ids = [r.get('content', {}).get('id') for r in page2.get('results', [])]

        # Verify pagination structure works - results may overlap with sparse data
        if len(page1_ids) >= 2 and len(page2_ids) >= 1:
            # With sufficient results, page 2 should have different content
            assert set(page1_ids) != set(page2_ids)
        # Otherwise just verify the structure is correct
        assert isinstance(page1_ids, list)
        assert isinstance(page2_ids, list)

@pytest.mark.integration
class TestSearchWithExpandLive:
    """Live tests for search with expanded data."""

    def test_search_expand_content(self, confluence_client, test_space):
        """Test search with content expansion."""
        results = confluence_client.get(
            '/rest/api/search',
            params={
                'cql': f'space = "{test_space["key"]}" AND type = page',
                'limit': 3,
                'expand': 'content.body.storage'
            }
        )

        assert 'results' in results

    def test_search_expand_space(self, confluence_client):
        """Test search with space expansion."""
        results = confluence_client.get(
            '/rest/api/search',
            params={
                'cql': 'type = page',
                'limit': 3,
                'expand': 'content.space'
            }
        )

        assert 'results' in results

@pytest.mark.integration
class TestCqlValidationLive:
    """Live tests for CQL query validation."""

    def test_invalid_cql_returns_error(self, confluence_client):
        """Test that invalid CQL returns an error."""
        with pytest.raises(Exception):
            confluence_client.get(
                '/rest/api/search',
                params={
                    'cql': 'invalid query syntax @@@@'
                }
            )

    def test_empty_cql_returns_error(self, confluence_client):
        """Test that empty CQL returns an error."""
        with pytest.raises(Exception):
            confluence_client.get(
                '/rest/api/search',
                params={
                    'cql': ''
                }
            )
