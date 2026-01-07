"""
Unit tests for get_ancestors.py
"""

import sys
from pathlib import Path

import pytest

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


class TestGetAncestors:
    """Tests for getting ancestor pages."""

    def test_validate_page_id_valid(self):
        """Test that valid page IDs pass validation."""
        from confluence_assistant_skills_lib import validate_page_id

        assert validate_page_id("123456") == "123456"
        assert validate_page_id(123456) == "123456"
        assert validate_page_id("999") == "999"

    def test_validate_page_id_invalid(self):
        """Test that invalid page IDs fail validation."""
        from confluence_assistant_skills_lib import ValidationError, validate_page_id

        with pytest.raises(ValidationError):
            validate_page_id("")

        with pytest.raises(ValidationError):
            validate_page_id("abc")

        with pytest.raises(ValidationError):
            validate_page_id(None)

    def test_get_ancestors_with_data(self, mock_client, sample_page_with_ancestors):
        """Test retrieving ancestors when they exist."""
        # Mock API response
        mock_client.setup_response("get", sample_page_with_ancestors)

        # Make request
        result = mock_client.get("/api/v2/pages/123456?include=ancestors")

        # Verify ancestors are present
        assert "ancestors" in result
        assert len(result["ancestors"]) == 2
        assert result["ancestors"][0]["title"] == "Root Page"
        assert result["ancestors"][1]["title"] == "Parent Page"

    def test_get_ancestors_root_page(self, mock_client, sample_page):
        """Test retrieving ancestors for root page (no ancestors)."""
        # Root page has no ancestors
        root_page = sample_page.copy()
        root_page["parentId"] = None
        root_page["ancestors"] = []

        mock_client.setup_response("get", root_page)

        # Make request
        result = mock_client.get("/api/v2/pages/123456?include=ancestors")

        # Verify no ancestors
        assert "ancestors" in result
        assert len(result["ancestors"]) == 0

    def test_get_ancestors_page_not_found(self, mock_client, mock_response):
        """Test handling of non-existent page."""

        # Mock 404 response
        error_response = mock_response(
            status_code=404, json_data={"errors": [{"title": "Page not found"}]}
        )
        mock_client.session.get.return_value = error_response

        # Should raise NotFoundError
        with pytest.raises(Exception):
            mock_client.get("/api/v2/pages/999999?include=ancestors")

    def test_ancestors_output_text_format(self, sample_page_with_ancestors):
        """Test formatting ancestors for text output."""
        ancestors = sample_page_with_ancestors["ancestors"]

        # Build text output
        lines = []
        for i, ancestor in enumerate(ancestors):
            lines.append(f"{i + 1}. {ancestor['title']} (ID: {ancestor['id']})")

        output = "\n".join(lines)

        assert "Root Page" in output
        assert "Parent Page" in output
        assert "ID: 100" in output
        assert "ID: 111" in output

    def test_ancestors_output_json_format(self, sample_page_with_ancestors):
        """Test JSON output format."""
        import json

        ancestors = sample_page_with_ancestors["ancestors"]
        json_output = json.dumps(ancestors, indent=2)

        assert "Root Page" in json_output
        assert "Parent Page" in json_output
        assert '"id": "100"' in json_output

    def test_ancestors_breadcrumb_format(self, sample_page_with_ancestors):
        """Test breadcrumb-style output."""
        ancestors = sample_page_with_ancestors["ancestors"]
        current_title = sample_page_with_ancestors["title"]

        # Build breadcrumb
        titles = [a["title"] for a in ancestors]
        titles.append(current_title)
        breadcrumb = " > ".join(titles)

        assert breadcrumb == "Root Page > Parent Page > Child Page"
