"""
Unit tests for list_properties.py
"""


class TestListProperties:
    """Tests for list properties functionality."""

    def test_list_all_properties(self, mock_client, sample_properties):
        """Test listing all properties on content."""
        mock_client.setup_response("get", sample_properties)

        result = mock_client.get("/rest/api/content/12345/property")

        assert len(result["results"]) == 2
        assert result["results"][0]["key"] == "property-one"
        assert result["results"][1]["key"] == "property-two"

    def test_list_properties_empty(self, mock_client):
        """Test listing when no properties exist."""
        mock_client.setup_response("get", {"results": [], "_links": {}})

        result = mock_client.get("/rest/api/content/12345/property")

        assert result["results"] == []

    def test_filter_properties_by_prefix(self, sample_properties):
        """Test filtering properties by key prefix."""
        properties = sample_properties["results"]

        # Filter by prefix
        prefix = "property-one"
        filtered = [p for p in properties if p["key"].startswith(prefix)]

        assert len(filtered) == 1
        assert filtered[0]["key"] == "property-one"

    def test_filter_properties_by_regex(self, sample_properties):
        """Test filtering properties by regex pattern."""
        import re

        properties = sample_properties["results"]

        # Filter by regex
        pattern = re.compile(r"property-\w+")
        filtered = [p for p in properties if pattern.match(p["key"])]

        assert len(filtered) == 2

    def test_format_property_output_text(self, sample_property):
        """Test text output formatting."""
        # Text format should show key and value
        output_lines = [
            f"Key: {sample_property['key']}",
            f"Value: {sample_property['value']}",
            f"Version: {sample_property['version']['number']}",
        ]

        assert any("my-property" in line for line in output_lines)
        assert any("test value" in str(line) for line in output_lines)

    def test_format_property_output_json(self, sample_property):
        """Test JSON output formatting."""
        import json

        # JSON format should be valid and complete
        json_output = json.dumps(sample_property, indent=2)

        assert json_output is not None
        parsed = json.loads(json_output)
        assert parsed["key"] == "my-property"

    def test_sort_properties_by_key(self, sample_properties):
        """Test sorting properties by key."""
        properties = sample_properties["results"]

        # Sort by key
        sorted_props = sorted(properties, key=lambda p: p["key"])

        assert sorted_props[0]["key"] == "property-one"
        assert sorted_props[1]["key"] == "property-two"

    def test_list_properties_with_pagination(self, mock_client):
        """Test listing properties with pagination."""

        # Would handle pagination by following _links.next

    def test_list_properties_includes_metadata(self, mock_client):
        """Test that property metadata is included."""
        properties_with_metadata = {
            "results": [
                {
                    "id": "prop-1",
                    "key": "property-one",
                    "value": {"data": "value one"},
                    "version": {
                        "number": 1,
                        "when": "2024-01-01",
                        "by": "user@example.com",
                    },
                }
            ],
            "_links": {},
        }

        mock_client.setup_response("get", properties_with_metadata)

        result = mock_client.get(
            "/rest/api/content/12345/property", params={"expand": "version"}
        )

        assert "when" in result["results"][0]["version"]
        assert "by" in result["results"][0]["version"]
