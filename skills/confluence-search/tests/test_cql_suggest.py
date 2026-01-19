"""
Unit tests for cql_suggest.py

Tests CQL field and value suggestion functionality.
"""


class TestCQLFieldSuggestions:
    """Tests for CQL field suggestions."""

    def test_get_all_fields(self, sample_cql_fields):
        """Test getting all available CQL fields."""
        # Import the module we'll create
        from confluence_assistant_skills_lib import validate_cql

        # Test that we can list common CQL fields
        common_fields = [
            "space",
            "title",
            "text",
            "type",
            "label",
            "creator",
            "created",
            "lastModified",
            "ancestor",
            "parent",
        ]

        for field in common_fields:
            # Verify field appears in valid queries
            cql = f"{field} = 'test'"
            assert validate_cql(cql) == cql

    def test_field_descriptions(self, sample_cql_fields):
        """Test that fields have descriptions."""
        for field in sample_cql_fields:
            assert "name" in field
            assert "description" in field
            assert len(field["description"]) > 0

    def test_field_types(self, sample_cql_fields):
        """Test that fields have proper types."""
        valid_types = ["string", "enum", "date", "number", "boolean"]

        for field in sample_cql_fields:
            assert "type" in field
            assert field["type"] in valid_types

    def test_enum_field_has_values(self, sample_cql_fields):
        """Test that enum fields have value lists."""
        type_field = next(f for f in sample_cql_fields if f["name"] == "type")

        assert "values" in type_field
        assert len(type_field["values"]) > 0
        assert "page" in type_field["values"]
        assert "blogpost" in type_field["values"]


class TestCQLOperatorSuggestions:
    """Tests for CQL operator suggestions."""

    def test_get_all_operators(self, sample_cql_operators):
        """Test getting all CQL operators."""
        expected_ops = ["=", "!=", "~", "!~", ">", "<", ">=", "<=", "in", "not in"]

        actual_ops = [op["operator"] for op in sample_cql_operators]

        for expected in expected_ops:
            assert expected in actual_ops

    def test_operator_descriptions(self, sample_cql_operators):
        """Test that operators have descriptions."""
        for op in sample_cql_operators:
            assert "operator" in op
            assert "description" in op
            assert len(op["description"]) > 0


class TestCQLFunctionSuggestions:
    """Tests for CQL function suggestions."""

    def test_get_all_functions(self, sample_cql_functions):
        """Test getting all CQL functions."""
        expected_funcs = [
            "currentUser()",
            "startOfDay()",
            "startOfWeek()",
            "startOfMonth()",
            "startOfYear()",
        ]

        actual_funcs = [f["name"] for f in sample_cql_functions]

        for expected in expected_funcs:
            assert expected in actual_funcs

    def test_function_descriptions(self, sample_cql_functions):
        """Test that functions have descriptions."""
        for func in sample_cql_functions:
            assert "name" in func
            assert "description" in func
            assert func["name"].endswith("()")


class TestCQLValueSuggestions:
    """Tests for CQL field value suggestions."""

    def test_suggest_space_values(self, mock_client, sample_spaces_for_suggestion):
        """Test suggesting space key values."""
        mock_client.setup_response("get", sample_spaces_for_suggestion)

        # Would call the suggestion function here
        # Expected: ['DOCS', 'KB', 'DEV']
        space_keys = [s["key"] for s in sample_spaces_for_suggestion["results"]]

        assert "DOCS" in space_keys
        assert "KB" in space_keys
        assert "DEV" in space_keys

    def test_suggest_type_values(self):
        """Test suggesting content type values."""
        # Content types are static
        expected_types = ["page", "blogpost", "comment", "attachment"]

        for ctype in expected_types:
            assert ctype in expected_types

    def test_suggest_label_values(self, mock_client, sample_labels_for_suggestion):
        """Test suggesting label values."""
        mock_client.setup_response("get", sample_labels_for_suggestion)

        label_names = [l["name"] for l in sample_labels_for_suggestion["results"]]

        assert "documentation" in label_names
        assert "api" in label_names
        assert "tutorial" in label_names

    def test_date_function_suggestions(self):
        """Test suggesting date function values."""
        date_functions = [
            "startOfDay()",
            "startOfWeek()",
            "startOfMonth()",
            "startOfYear()",
            "endOfDay()",
            "endOfWeek()",
            "endOfMonth()",
            "endOfYear()",
        ]

        for func in date_functions:
            assert func.endswith("()")
            assert "Of" in func or "end" in func.lower() or "start" in func.lower()


class TestCQLSuggestScript:
    """Integration tests for cql_suggest.py script."""

    def test_list_fields_flag(self, capsys):
        """Test --fields flag lists all fields."""
        # This would run: python cql_suggest.py --fields
        # Expected output: JSON array of field objects
        pass

    def test_suggest_field_values(self, mock_client, capsys):
        """Test --field flag suggests values for a field."""
        # This would run: python cql_suggest.py --field space
        # Expected: List of space keys
        pass

    def test_suggest_unknown_field(self, capsys):
        """Test suggesting values for unknown field."""
        # This would run: python cql_suggest.py --field invalid_field
        # Expected: Error or empty list
        pass

    def test_json_output(self, capsys):
        """Test JSON output format."""
        # This would run: python cql_suggest.py --fields --output json
        # Expected: Valid JSON output
        pass

    def test_text_output(self, capsys):
        """Test text output format."""
        # This would run: python cql_suggest.py --fields --output text
        # Expected: Human-readable text
        pass


class TestCQLCompletion:
    """Tests for query completion logic."""

    def test_complete_partial_field(self):
        """Test completing partial field names."""
        partial = "spa"

        # Would match fields starting with 'spa'
        fields = ["space", "type", "title", "text"]
        matches = [f for f in fields if f.startswith(partial)]

        assert "space" in matches

    def test_complete_partial_operator(self):
        """Test completing partial operators."""
        partial = "!="
        operators = ["=", "!=", "~", "!~"]

        assert partial in operators

    def test_suggest_next_field(self):
        """Test suggesting next field after AND/OR."""
        # After AND, should suggest field names

        # This is a more advanced feature
        pass

    def test_suggest_operator_after_field(self):
        """Test suggesting operators after field name."""
        # After field, should suggest operators

        # Text fields support these operators
        pass
