"""
Live integration tests for space homepage operations.

Usage:
    pytest test_space_homepage_live.py --profile development -v
"""

import pytest
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
class TestSpaceHomepageLive:
    """Live tests for space homepage operations."""

    def test_get_space_homepage_id(self, confluence_client, test_space):
        """Test getting space homepage ID."""
        space = confluence_client.get(f"/api/v2/spaces/{test_space['id']}")

        # Space should have homepageId
        assert 'homepageId' in space or 'homepage' in space

    def test_get_homepage_content(self, confluence_client, test_space):
        """Test getting homepage content."""
        space = confluence_client.get(f"/api/v2/spaces/{test_space['id']}")

        if space.get('homepageId'):
            homepage = confluence_client.get(
                f"/api/v2/pages/{space['homepageId']}"
            )
            assert homepage['id'] == space['homepageId']

    def test_homepage_is_page(self, confluence_client, test_space):
        """Test that homepage is a page type."""
        space = confluence_client.get(f"/api/v2/spaces/{test_space['id']}")

        if space.get('homepageId'):
            homepage = confluence_client.get(
                f"/api/v2/pages/{space['homepageId']}"
            )
            # Should be accessible as a page
            assert homepage['id'] is not None

    def test_homepage_has_title(self, confluence_client, test_space):
        """Test that homepage has a title."""
        space = confluence_client.get(f"/api/v2/spaces/{test_space['id']}")

        if space.get('homepageId'):
            homepage = confluence_client.get(
                f"/api/v2/pages/{space['homepageId']}"
            )
            assert 'title' in homepage
            assert len(homepage['title']) > 0

    def test_space_has_key(self, confluence_client, test_space):
        """Test that space has a key."""
        space = confluence_client.get(f"/api/v2/spaces/{test_space['id']}")
        assert 'key' in space
        assert len(space['key']) > 0
