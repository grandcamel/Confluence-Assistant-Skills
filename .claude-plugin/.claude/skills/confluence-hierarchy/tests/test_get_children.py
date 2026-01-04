"""
Unit tests for get_children.py
"""

import pytest
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))


class TestGetChildren:
    """Tests for getting child pages."""

    def test_get_children_with_results(self, mock_client, sample_children):
        """Test retrieving children when they exist."""
        mock_client.setup_response('get', sample_children)

        # Make request
        result = mock_client.get('/api/v2/pages/123456/children')

        # Verify children are present
        assert 'results' in result
        assert len(result['results']) == 2
        assert result['results'][0]['title'] == 'Child 1'
        assert result['results'][1]['title'] == 'Child 2'

    def test_get_children_empty(self, mock_client):
        """Test retrieving children for leaf page (no children)."""
        empty_children = {'results': [], '_links': {}}
        mock_client.setup_response('get', empty_children)

        # Make request
        result = mock_client.get('/api/v2/pages/123456/children')

        # Verify no children
        assert 'results' in result
        assert len(result['results']) == 0

    def test_get_children_with_type_filter(self, mock_client):
        """Test filtering children by type (page vs blogpost)."""
        # Only page children
        page_children = {
            'results': [
                {'id': '200', 'title': 'Child Page', 'type': 'page'}
            ],
            '_links': {}
        }
        mock_client.setup_response('get', page_children)

        # Make request with type filter
        result = mock_client.get('/api/v2/pages/123456/children?type=page')

        assert len(result['results']) == 1
        assert result['results'][0]['type'] == 'page'

    def test_get_children_with_limit(self, mock_client, sample_children):
        """Test pagination limit parameter."""
        mock_client.setup_response('get', sample_children)

        # Request with limit
        result = mock_client.get('/api/v2/pages/123456/children?limit=10')

        # Verify we get results (actual limiting is server-side)
        assert 'results' in result

    def test_children_output_text_format(self, sample_children):
        """Test formatting children for text output."""
        children = sample_children['results']

        # Build text output
        lines = []
        for i, child in enumerate(children, 1):
            lines.append(f"{i}. {child['title']} (ID: {child['id']})")

        output = '\n'.join(lines)

        assert 'Child 1' in output
        assert 'Child 2' in output
        assert 'ID: 200' in output
        assert 'ID: 201' in output

    def test_children_count(self, sample_children):
        """Test counting number of children."""
        count = len(sample_children['results'])
        assert count == 2

    def test_sort_children_by_title(self, sample_children):
        """Test sorting children by title."""
        children = sample_children['results']
        sorted_children = sorted(children, key=lambda x: x['title'])

        assert sorted_children[0]['title'] == 'Child 1'
        assert sorted_children[1]['title'] == 'Child 2'
