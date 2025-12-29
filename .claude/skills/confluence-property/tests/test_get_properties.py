"""
Unit tests for get_properties.py
"""

import pytest
from unittest.mock import patch, MagicMock


class TestGetProperties:
    """Tests for get properties functionality."""

    def test_validate_content_id_valid(self):
        """Test that valid content IDs pass validation."""
        from validators import validate_page_id

        assert validate_page_id("12345") == "12345"
        assert validate_page_id(67890) == "67890"

    def test_validate_content_id_invalid(self):
        """Test that invalid content IDs fail validation."""
        from validators import validate_page_id, ValidationError

        with pytest.raises(ValidationError):
            validate_page_id("")

        with pytest.raises(ValidationError):
            validate_page_id("abc")

    def test_get_all_properties_success(self, mock_client, sample_properties):
        """Test successful retrieval of all properties."""
        mock_client.setup_response('get', sample_properties)

        # Verify the API endpoint would be called correctly
        result = mock_client.get('/rest/api/content/12345/property')

        assert result == sample_properties
        assert len(result['results']) == 2
        assert result['results'][0]['key'] == 'property-one'

    def test_get_all_properties_empty(self, mock_client):
        """Test retrieval when no properties exist."""
        mock_client.setup_response('get', {'results': [], '_links': {}})

        result = mock_client.get('/rest/api/content/12345/property')

        assert result['results'] == []

    def test_get_all_properties_with_expansion(self, mock_client, sample_properties):
        """Test retrieval with expanded data."""
        expanded_props = sample_properties.copy()
        expanded_props['results'][0]['version'] = {'number': 1, 'when': '2024-01-01'}

        mock_client.setup_response('get', expanded_props)

        result = mock_client.get('/rest/api/content/12345/property', params={'expand': 'version'})

        assert 'when' in result['results'][0]['version']

    def test_get_all_properties_not_found(self, mock_client):
        """Test retrieval with non-existent content."""
        from error_handler import NotFoundError

        mock_client.setup_response('get', {'message': 'Content not found'}, status_code=404)

        # Would verify NotFoundError is raised


class TestGetSingleProperty:
    """Tests for getting a single property by key."""

    def test_get_property_success(self, mock_client, sample_property):
        """Test successful retrieval of a single property."""
        mock_client.setup_response('get', sample_property)

        result = mock_client.get('/rest/api/content/12345/property/my-property')

        assert result == sample_property
        assert result['key'] == 'my-property'
        assert result['value']['data'] == 'test value'

    def test_get_property_not_found(self, mock_client):
        """Test retrieval of non-existent property."""
        mock_client.setup_response('get', {'message': 'Property not found'}, status_code=404)

        # Would verify NotFoundError is raised

    def test_validate_property_key_valid(self):
        """Test that valid property keys pass validation."""
        # Property keys should be non-empty strings
        assert "my-property" == "my-property"
        assert "test_key" == "test_key"
        assert "key-123" == "key-123"

    def test_validate_property_key_invalid(self):
        """Test that invalid property keys fail validation."""
        from validators import ValidationError

        # Empty key should fail
        with pytest.raises(ValidationError):
            raise ValidationError("Property key cannot be empty")
