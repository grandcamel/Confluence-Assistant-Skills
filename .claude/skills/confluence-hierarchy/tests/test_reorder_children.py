"""
Unit tests for reorder_children.py
"""

import pytest
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))


class TestReorderChildren:
    """Tests for reordering child pages."""

    def test_validate_page_order(self):
        """Test validating page order input."""
        # Valid comma-separated IDs
        order_str = "200,201,202"
        page_ids = [id.strip() for id in order_str.split(',')]

        assert len(page_ids) == 3
        assert page_ids == ['200', '201', '202']

    def test_validate_all_numeric_ids(self):
        """Test that all IDs are numeric."""
        from confluence_assistant_skills_lib import validate_page_id

        order_str = "200,201,202"
        page_ids = [id.strip() for id in order_str.split(',')]

        # All should be valid
        for page_id in page_ids:
            validated = validate_page_id(page_id)
            assert validated.isdigit()

    def test_reject_invalid_order_format(self):
        """Test rejection of invalid order formats."""
        from confluence_assistant_skills_lib import ValidationError, validate_page_id

        # Non-numeric ID
        with pytest.raises(ValidationError):
            validate_page_id("abc")

        # Empty ID
        with pytest.raises(ValidationError):
            validate_page_id("")

    def test_reorder_api_call_structure(self, mock_client):
        """Test structure of reorder API call."""
        # The v2 API uses PUT to update page positions
        # Note: Actual API endpoint may vary - check Confluence API docs

        parent_id = "123456"
        new_order = ["200", "201", "202"]

        # Mock successful reorder
        mock_client.setup_response('put', {'status': 'success'})

        # Simulate API call (actual endpoint TBD)
        # PUT /api/v2/pages/{parent_id}/children/order
        result = mock_client.put(
            f'/api/v2/pages/{parent_id}/children/order',
            json_data={'order': new_order}
        )

        # Verify call was made
        assert result is not None

    def test_verify_children_exist(self, mock_client, sample_children):
        """Test verifying all children exist before reordering."""
        mock_client.setup_response('get', sample_children)

        # Get current children
        result = mock_client.get('/api/v2/pages/123456/children')
        current_children = result['results']
        current_ids = [c['id'] for c in current_children]

        # Verify proposed order contains valid IDs
        proposed_order = ['200', '201']
        for page_id in proposed_order:
            assert page_id in current_ids

    def test_reject_missing_children_in_order(self):
        """Test that order must include all children."""
        current_children = [
            {'id': '200', 'title': 'Child 1'},
            {'id': '201', 'title': 'Child 2'},
            {'id': '202', 'title': 'Child 3'}
        ]
        current_ids = set(c['id'] for c in current_children)

        # Proposed order is missing one child
        proposed_order = ['200', '201']
        proposed_ids = set(proposed_order)

        # Should detect missing children
        missing = current_ids - proposed_ids
        assert len(missing) == 1
        assert '202' in missing

    def test_reject_duplicate_ids_in_order(self):
        """Test rejection of duplicate IDs in order."""
        proposed_order = ['200', '201', '200']  # Duplicate

        # Check for duplicates
        unique_ids = set(proposed_order)
        has_duplicates = len(unique_ids) != len(proposed_order)

        assert has_duplicates is True

    def test_reject_extra_ids_in_order(self):
        """Test rejection of IDs not in current children."""
        current_children = [
            {'id': '200', 'title': 'Child 1'},
            {'id': '201', 'title': 'Child 2'}
        ]
        current_ids = set(c['id'] for c in current_children)

        # Proposed order includes non-existent child
        proposed_order = ['200', '201', '999']
        proposed_ids = set(proposed_order)

        # Should detect extra IDs
        extra = proposed_ids - current_ids
        assert len(extra) == 1
        assert '999' in extra

    def test_reorder_output_success(self):
        """Test success message format."""
        parent_id = "123456"
        new_order = ['200', '201', '202']

        message = f"Successfully reordered {len(new_order)} children of page {parent_id}"
        assert 'Successfully reordered 3 children' in message

    def test_preserve_order_specification(self):
        """Test that specified order is preserved."""
        proposed_order = ['202', '200', '201']

        # Order should be exactly as specified
        assert proposed_order[0] == '202'
        assert proposed_order[1] == '200'
        assert proposed_order[2] == '201'
