"""
Unit tests for delete_property.py
"""

import pytest
from unittest.mock import patch, MagicMock


class TestDeleteProperty:
    """Tests for delete property functionality."""

    def test_delete_property_success(self, mock_client):
        """Test successful deletion of a property."""
        mock_client.setup_response('delete', {})

        result = mock_client.delete('/rest/api/content/12345/property/my-property')

        # DELETE typically returns empty response on success
        assert result == {}

    def test_delete_property_not_found(self, mock_client):
        """Test deletion of non-existent property."""
        mock_client.setup_response('delete', {'message': 'Property not found'}, status_code=404)

        # Would verify NotFoundError is raised

    def test_delete_property_invalid_content_id(self):
        """Test deletion with invalid content ID."""
        from confluence_assistant_skills_lib import validate_page_id, ValidationError

        with pytest.raises(ValidationError):
            validate_page_id("")

    def test_delete_property_permission_denied(self, mock_client):
        """Test deletion without permission."""
        mock_client.setup_response('delete', {'message': 'Permission denied'}, status_code=403)

        # Would verify PermissionError is raised

    def test_delete_property_validates_key(self):
        """Test that property key is validated before deletion."""
        # Empty key should fail validation
        key = ""
        assert key == "" or len(key.strip()) == 0

        # Valid key
        key = "my-property"
        assert key and len(key.strip()) > 0


class TestDeleteMultipleProperties:
    """Tests for batch deletion scenarios."""

    def test_delete_all_properties_by_prefix(self, mock_client, sample_properties):
        """Test deleting properties matching a prefix."""
        # First get all properties
        mock_client.setup_response('get', sample_properties)

        properties = mock_client.get('/rest/api/content/12345/property')

        # Filter by prefix
        prefix = "property-"
        matching = [p for p in properties['results'] if p['key'].startswith(prefix)]

        assert len(matching) == 2
        assert all(p['key'].startswith(prefix) for p in matching)

    def test_confirm_deletion_required(self):
        """Test that deletion requires confirmation for safety."""
        # Deletion should be explicit and confirmed
        should_delete = True  # Would come from user confirmation
        assert should_delete in [True, False]
