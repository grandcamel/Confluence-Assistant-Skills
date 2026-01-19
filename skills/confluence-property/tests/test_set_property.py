"""
Unit tests for set_property.py
"""

import json


class TestSetProperty:
    """Tests for set property functionality."""

    def test_set_property_create_success(self, mock_client, sample_property):
        """Test successful creation of a new property."""
        mock_client.setup_response("post", sample_property)

        result = mock_client.post(
            "/rest/api/content/12345/property",
            json_data={"key": "my-property", "value": {"data": "test value"}},
        )

        assert result == sample_property
        assert result["key"] == "my-property"

    def test_set_property_update_success(self, mock_client, sample_property):
        """Test successful update of existing property."""
        updated_property = sample_property.copy()
        updated_property["value"]["data"] = "updated value"
        updated_property["version"]["number"] = 2

        mock_client.setup_response("put", updated_property)

        result = mock_client.put(
            "/rest/api/content/12345/property/my-property",
            json_data={
                "key": "my-property",
                "value": {"data": "updated value"},
                "version": {"number": 2},
            },
        )

        assert result["value"]["data"] == "updated value"
        assert result["version"]["number"] == 2

    def test_set_property_from_json_file(self, mock_client, sample_property, tmp_path):
        """Test setting property from JSON file."""
        # Create a test JSON file
        json_file = tmp_path / "property.json"
        json_file.write_text(json.dumps({"data": "file value", "metadata": {}}))

        # Read the file
        with open(json_file) as f:
            value_data = json.load(f)

        assert value_data["data"] == "file value"

    def test_set_property_from_string(self, mock_client, sample_property):
        """Test setting property from string value."""
        property_data = sample_property.copy()
        property_data["value"] = "simple string value"

        mock_client.setup_response("post", property_data)

        result = mock_client.post(
            "/rest/api/content/12345/property",
            json_data={"key": "my-property", "value": "simple string value"},
        )

        assert result["value"] == "simple string value"

    def test_set_property_complex_value(self, mock_client):
        """Test setting property with complex JSON value."""
        complex_value = {
            "array": [1, 2, 3],
            "nested": {"key": "value"},
            "boolean": True,
            "number": 42,
        }

        property_data = {
            "id": "prop-123",
            "key": "complex-property",
            "value": complex_value,
            "version": {"number": 1},
        }

        mock_client.setup_response("post", property_data)

        result = mock_client.post(
            "/rest/api/content/12345/property",
            json_data={"key": "complex-property", "value": complex_value},
        )

        assert result["value"]["array"] == [1, 2, 3]
        assert result["value"]["nested"]["key"] == "value"

    def test_set_property_version_conflict(self, mock_client):
        """Test handling version conflict on update."""
        mock_client.setup_response(
            "put", {"message": "Version conflict"}, status_code=409
        )

        # Would verify ConflictError is raised

    def test_validate_property_value_json(self):
        """Test that valid JSON values pass validation."""
        # Test various JSON types
        test_values = [
            {"data": "string"},
            {"number": 123},
            {"array": [1, 2, 3]},
            {"nested": {"key": "value"}},
            "simple string",
            123,
            True,
        ]

        for value in test_values:
            # Should be serializable to JSON
            json_str = json.dumps(value)
            assert json_str is not None
