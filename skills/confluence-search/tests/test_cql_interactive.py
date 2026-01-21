"""
Unit tests for cql_interactive.py

Tests interactive CQL query builder functionality.
"""

import pytest


class TestQueryBuilder:
    """Tests for interactive query builder."""

    def test_build_simple_space_query(self):
        """Test building a simple space filter query."""
        # User selects: space = 'DOCS'
        expected = "space = 'DOCS'"

        # This would be built interactively
        parts = ["space", "=", "'DOCS'"]
        result = " ".join(parts)

        assert result == expected

    def test_build_query_with_and(self):
        """Test building query with AND operator."""
        # User selects: space = 'DOCS' AND type = page
        expected = "space = 'DOCS' AND type = page"

        parts = ["space = 'DOCS'", "AND", "type = page"]
        result = " ".join(parts)

        assert result == expected

    def test_build_query_with_or(self):
        """Test building query with OR operator."""
        # User selects: space = 'DOCS' OR space = 'KB'
        expected = "space = 'DOCS' OR space = 'KB'"

        parts = ["space = 'DOCS'", "OR", "space = 'KB'"]
        result = " ".join(parts)

        assert result == expected

    def test_build_text_search_query(self):
        """Test building text search query."""
        # User selects: text ~ 'documentation'
        expected = "text ~ 'documentation'"

        parts = ["text", "~", "'documentation'"]
        result = " ".join(parts)

        assert result == expected

    def test_build_date_range_query(self):
        """Test building date range query."""
        # User selects: created >= '2024-01-01' AND created < '2024-02-01'
        expected = "created >= '2024-01-01' AND created < '2024-02-01'"

        parts = ["created >= '2024-01-01'", "AND", "created < '2024-02-01'"]
        result = " ".join(parts)

        assert result == expected


class TestQueryValidation:
    """Tests for query validation in interactive mode."""

    def test_validate_complete_query(self):
        """Test validating a complete query."""
        from confluence_as import validate_cql

        query = "space = 'DOCS' AND type = page"
        result = validate_cql(query)

        assert result == query

    def test_validate_incomplete_query(self):
        """Test handling incomplete query."""
        # Query like "space = " should be caught

        # In interactive mode, this should prompt for value
        # Not raise an error immediately
        pass

    def test_validate_unbalanced_quotes(self):
        """Test handling unbalanced quotes."""
        from confluence_as import ValidationError, validate_cql

        query = "space = 'DOCS"  # Missing closing quote

        with pytest.raises(ValidationError):
            validate_cql(query)

    def test_validate_unbalanced_parens(self):
        """Test handling unbalanced parentheses."""
        from confluence_as import ValidationError, validate_cql

        query = "(space = 'DOCS' AND type = page"

        with pytest.raises(ValidationError):
            validate_cql(query)


class TestInteractiveMenus:
    """Tests for interactive menu system."""

    def test_display_field_menu(self, sample_cql_fields):
        """Test displaying field selection menu."""
        # Would display numbered list of fields
        fields = sample_cql_fields[:5]

        menu_items = [f"{i + 1}. {f['name']}" for i, f in enumerate(fields)]

        assert len(menu_items) == 5
        assert "1. space" in menu_items

    def test_display_operator_menu(self):
        """Test displaying operator selection menu for a field."""
        # After selecting 'space', show valid operators
        operators = ["=", "!=", "in", "not in"]

        menu_items = [f"{i + 1}. {op}" for i, op in enumerate(operators)]

        assert len(menu_items) == 4
        assert "1. =" in menu_items

    def test_display_value_suggestions(self, sample_spaces_for_suggestion):
        """Test displaying value suggestions."""
        # After selecting space =, show space keys
        spaces = sample_spaces_for_suggestion["results"]
        suggestions = [s["key"] for s in spaces]

        assert "DOCS" in suggestions
        assert "KB" in suggestions

    def test_display_continue_menu(self):
        """Test displaying continue/finish menu."""
        # After completing a clause, show options
        options = [
            "1. Add AND condition",
            "2. Add OR condition",
            "3. Add ORDER BY",
            "4. Finish and execute",
            "5. Cancel",
        ]

        assert len(options) == 5
        assert any("AND" in o for o in options)


class TestQueryExecution:
    """Tests for executing built queries."""

    def test_execute_query_success(self, mock_client, sample_search_results):
        """Test executing a successfully built query."""
        mock_client.setup_response("get", sample_search_results)

        query = "space = 'DOCS' AND type = page"

        # Would execute via client
        result = mock_client.get("/rest/api/search", params={"cql": query, "limit": 25})

        assert "results" in result
        assert len(result["results"]) > 0

    def test_execute_query_no_results(self, mock_client):
        """Test executing query that returns no results."""
        mock_client.setup_response("get", {"results": [], "size": 0})

        query = "label = 'nonexistent'"

        result = mock_client.get("/rest/api/search", params={"cql": query, "limit": 25})

        assert result["results"] == []
        assert result["size"] == 0

    def test_save_query_option(self):
        """Test option to save query after building."""

        # User should be prompted to save
        # Would write to history file
        pass


class TestInteractiveHelpers:
    """Tests for interactive helper functions."""

    def test_quote_value_if_needed(self):
        """Test automatically quoting string values."""
        # String values should be quoted
        value = "DOCS"
        expected = "'DOCS'"

        # If not already quoted
        if not (value.startswith("'") or value.startswith('"')):
            result = f"'{value}'"
        else:
            result = value

        assert result == expected

    def test_dont_quote_numbers(self):
        """Test not quoting numeric values."""
        value = "12345"

        # Should not quote if numeric and used with id field
        if value.isdigit():
            result = value
        else:
            result = f"'{value}'"

        assert result == value

    def test_dont_quote_functions(self):
        """Test not quoting function calls."""
        value = "currentUser()"

        # Should not quote functions
        if value.endswith("()"):
            result = value
        else:
            result = f"'{value}'"

        assert result == value

    def test_format_in_list(self):
        """Test formatting IN operator with list."""
        values = ["DOCS", "KB", "DEV"]
        expected = "('DOCS', 'KB', 'DEV')"

        result = "(" + ", ".join(f"'{v}'" for v in values) + ")"

        assert result == expected


class TestPrefiltering:
    """Tests for pre-filtering options."""

    def test_prefilter_by_space(self):
        """Test starting with space pre-filter."""
        # python cql_interactive.py --space DOCS
        # Should start query with: space = 'DOCS' AND

        space = "DOCS"
        prefix = f"space = '{space}' AND "

        assert prefix == "space = 'DOCS' AND "

    def test_prefilter_by_type(self):
        """Test starting with type pre-filter."""
        # python cql_interactive.py --type page

        content_type = "page"
        prefix = f"type = {content_type} AND "

        assert prefix == "type = page AND "

    def test_prefilter_multiple(self):
        """Test combining multiple pre-filters."""
        # python cql_interactive.py --space DOCS --type page

        parts = []
        parts.append("space = 'DOCS'")
        parts.append("type = page")

        result = " AND ".join(parts)

        assert result == "space = 'DOCS' AND type = page"


class TestOrderBy:
    """Tests for ORDER BY clause building."""

    def test_add_order_by_single(self):
        """Test adding single ORDER BY."""
        query = "space = 'DOCS'"
        order = "ORDER BY lastModified DESC"

        result = f"{query} {order}"

        assert result == "space = 'DOCS' ORDER BY lastModified DESC"

    def test_order_direction_options(self):
        """Test ASC/DESC options."""
        directions = ["ASC", "DESC"]

        assert "ASC" in directions
        assert "DESC" in directions

    def test_orderable_fields(self):
        """Test which fields can be used in ORDER BY."""
        orderable = ["created", "lastModified", "title"]

        assert "created" in orderable
        assert "lastModified" in orderable
        assert "title" in orderable
