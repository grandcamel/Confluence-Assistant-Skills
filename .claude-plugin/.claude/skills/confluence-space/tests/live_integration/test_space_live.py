"""
Live integration tests for confluence-space skill.

Tests space operations against a real Confluence instance.

Usage:
    pytest test_space_live.py --profile development -v
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

@pytest.mark.integration
class TestListSpacesLive:
    """Live tests for listing spaces."""

    def test_list_all_spaces(self, confluence_client):
        """Test listing all accessible spaces."""
        spaces = confluence_client.get(
            '/api/v2/spaces',
            params={'limit': 25}
        )

        assert 'results' in spaces
        assert isinstance(spaces['results'], list)
        assert len(spaces['results']) > 0

    def test_list_spaces_with_pagination(self, confluence_client):
        """Test listing spaces with pagination."""
        # First page
        page1 = confluence_client.get(
            '/api/v2/spaces',
            params={'limit': 5}
        )

        assert 'results' in page1
        assert '_links' in page1

    def test_list_global_spaces(self, confluence_client):
        """Test listing global spaces only."""
        spaces = confluence_client.get(
            '/api/v2/spaces',
            params={'type': 'global', 'limit': 10}
        )

        assert 'results' in spaces
        for space in spaces['results']:
            assert space.get('type') == 'global'

@pytest.mark.integration
class TestGetSpaceLive:
    """Live tests for getting space details."""

    def test_get_space_by_id(self, confluence_client):
        """Test getting a space by ID."""
        # First get a space ID
        spaces = confluence_client.get('/api/v2/spaces', params={'limit': 1})
        if not spaces.get('results'):
            pytest.skip("No spaces available")

        space_id = spaces['results'][0]['id']

        # Get by ID
        space = confluence_client.get(f'/api/v2/spaces/{space_id}')

        assert space['id'] == space_id
        assert 'key' in space
        assert 'name' in space

    def test_get_space_by_key(self, confluence_client):
        """Test getting a space by key."""
        spaces = confluence_client.get('/api/v2/spaces', params={'limit': 1})
        if not spaces.get('results'):
            pytest.skip("No spaces available")

        space_key = spaces['results'][0]['key']

        # Get by key using filter
        result = confluence_client.get(
            '/api/v2/spaces',
            params={'keys': space_key}
        )

        assert 'results' in result
        assert len(result['results']) >= 1
        assert result['results'][0]['key'] == space_key

    def test_get_space_homepage(self, confluence_client):
        """Test getting a space's homepage."""
        spaces = confluence_client.get('/api/v2/spaces', params={'limit': 1})
        if not spaces.get('results'):
            pytest.skip("No spaces available")

        space = spaces['results'][0]
        homepage_id = space.get('homepageId')

        if homepage_id:
            homepage = confluence_client.get(f'/api/v2/pages/{homepage_id}')
            assert homepage['id'] == homepage_id

@pytest.mark.integration
class TestCreateSpaceLive:
    """Live tests for creating spaces."""

    def test_create_and_delete_space(self, confluence_client):
        """Test creating and deleting a space."""
        space_key = f"TST{uuid.uuid4().hex[:5].upper()}"
        space_name = f"Test Space {space_key}"

        # Create
        space = confluence_client.post(
            '/api/v2/spaces',
            json_data={
                'key': space_key,
                'name': space_name
            }
        )

        try:
            assert space['key'] == space_key
            assert space['name'] == space_name
            assert 'id' in space
        finally:
            # Delete using v1 API (v2 doesn't support delete)
            import time
            time.sleep(1)  # Allow space to initialize

            response = confluence_client.session.delete(
                f"{confluence_client.base_url}/wiki/rest/api/space/{space_key}"
            )
            # 202 = async delete started, 204 = deleted, 404 = already gone
            assert response.status_code in [200, 202, 204, 404]

@pytest.mark.integration
class TestUpdateSpaceLive:
    """Live tests for updating spaces."""

    def test_update_space_name(self, confluence_client):
        """Test updating a space's name."""
        # Create a test space
        space_key = f"UPD{uuid.uuid4().hex[:5].upper()}"

        space = confluence_client.post(
            '/api/v2/spaces',
            json_data={
                'key': space_key,
                'name': f"Original Name {space_key}"
            }
        )

        try:
            new_name = f"Updated Name {space_key}"

            # Update using v1 API (v2 API doesn't support PUT for spaces)
            updated = confluence_client.put(
                f"/rest/api/space/{space_key}",
                json_data={
                    'key': space_key,
                    'name': new_name
                }
            )

            assert updated['name'] == new_name
        finally:
            # Cleanup
            import time
            time.sleep(1)
            confluence_client.session.delete(
                f"{confluence_client.base_url}/wiki/rest/api/space/{space_key}"
            )

@pytest.mark.integration
class TestSpaceContentLive:
    """Live tests for space content operations."""

    def test_list_pages_in_space(self, confluence_client):
        """Test listing pages in a space."""
        spaces = confluence_client.get('/api/v2/spaces', params={'limit': 1})
        if not spaces.get('results'):
            pytest.skip("No spaces available")

        space_id = spaces['results'][0]['id']

        pages = confluence_client.get(
            '/api/v2/pages',
            params={'space-id': space_id, 'limit': 10}
        )

        assert 'results' in pages

    def test_list_blogposts_in_space(self, confluence_client):
        """Test listing blog posts in a space."""
        spaces = confluence_client.get('/api/v2/spaces', params={'limit': 1})
        if not spaces.get('results'):
            pytest.skip("No spaces available")

        space_id = spaces['results'][0]['id']

        posts = confluence_client.get(
            '/api/v2/blogposts',
            params={'space-id': space_id, 'limit': 10}
        )

        assert 'results' in posts

    def test_get_space_content_count(self, confluence_client):
        """Test getting content count in a space."""
        spaces = confluence_client.get('/api/v2/spaces', params={'limit': 1})
        if not spaces.get('results'):
            pytest.skip("No spaces available")

        space = spaces['results'][0]

        # Get all pages (up to limit)
        pages = confluence_client.get(
            '/api/v2/pages',
            params={'space-id': space['id'], 'limit': 250}
        )

        # Count is the number of results
        count = len(pages.get('results', []))
        assert count >= 0  # May be 0 for empty spaces
