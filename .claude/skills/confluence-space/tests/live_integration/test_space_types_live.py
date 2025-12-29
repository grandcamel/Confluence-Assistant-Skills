"""
Live integration tests for space type operations.

Usage:
    pytest test_space_types_live.py --profile development -v
"""

import pytest
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


@pytest.mark.integration
class TestSpaceTypesLive:
    """Live tests for different space types."""

    def test_list_global_spaces(self, confluence_client):
        """Test listing global spaces."""
        spaces = confluence_client.get(
            '/api/v2/spaces',
            params={'type': 'global', 'limit': 10}
        )

        assert 'results' in spaces

    def test_list_personal_spaces(self, confluence_client):
        """Test listing personal spaces."""
        spaces = confluence_client.get(
            '/api/v2/spaces',
            params={'type': 'personal', 'limit': 10}
        )

        assert 'results' in spaces

    def test_space_has_type_field(self, confluence_client):
        """Test that spaces have type field."""
        spaces = confluence_client.get('/api/v2/spaces', params={'limit': 5})

        for space in spaces.get('results', []):
            assert 'type' in space

    def test_filter_spaces_by_status(self, confluence_client):
        """Test filtering spaces by status."""
        spaces = confluence_client.get(
            '/api/v2/spaces',
            params={'status': 'current', 'limit': 10}
        )

        assert 'results' in spaces
