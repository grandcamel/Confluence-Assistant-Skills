"""
Unit tests for create_page.py
"""

import pytest


class TestCreatePage:
    """Tests for page creation functionality."""

    def test_validate_space_key_valid(self):
        """Test that valid space keys pass validation."""
        from confluence_as import validate_space_key

        assert validate_space_key("DOCS") == "DOCS"
        assert validate_space_key("kb") == "KB"
        assert validate_space_key("Test_Space") == "TEST_SPACE"

    def test_validate_space_key_invalid(self):
        """Test that invalid space keys fail validation."""
        from confluence_as import ValidationError, validate_space_key

        with pytest.raises(ValidationError):
            validate_space_key("")

        with pytest.raises(ValidationError):
            validate_space_key("A")  # Too short

        with pytest.raises(ValidationError):
            validate_space_key("123")  # Starts with number

    def test_validate_title_valid(self):
        """Test that valid titles pass validation."""
        from confluence_as import validate_title

        assert validate_title("My Page") == "My Page"
        assert validate_title("  Trimmed  ") == "Trimmed"

    def test_validate_title_invalid(self):
        """Test that invalid titles fail validation."""
        from confluence_as import ValidationError, validate_title

        with pytest.raises(ValidationError):
            validate_title("")

        with pytest.raises(ValidationError):
            validate_title("Page:with:colons")

        with pytest.raises(ValidationError):
            validate_title("A" * 300)  # Too long

    def test_create_page_success(self, mock_client, sample_page, sample_space):
        """Test successful page creation."""
        # Setup mock responses
        mock_client.setup_response("get", {"results": [sample_space]})
        mock_client.setup_response("post", sample_page)

        # The actual test would run the script
        # This demonstrates the test structure

    def test_create_page_space_not_found(self, mock_client):
        """Test page creation with non-existent space."""
        mock_client.setup_response("get", {"results": []})

        # Would verify ValidationError is raised

    def test_create_page_from_markdown(
        self, mock_client, sample_page, sample_space, tmp_path
    ):
        """Test page creation from Markdown file."""
        # Create a test Markdown file
        md_file = tmp_path / "test.md"
        md_file.write_text("# Heading\n\nParagraph")

        mock_client.setup_response("get", {"results": [sample_space]})
        mock_client.setup_response("post", sample_page)

        # Would verify Markdown is converted to storage format


class TestMarkdownConversion:
    """Tests for Markdown to storage format conversion."""

    def test_xhtml_basic_paragraph(self):
        """Test basic paragraph conversion."""
        from confluence_as import markdown_to_xhtml

        result = markdown_to_xhtml("Hello world")
        assert "<p>Hello world</p>" in result

    def test_xhtml_heading(self):
        """Test heading conversion."""
        from confluence_as import markdown_to_xhtml

        result = markdown_to_xhtml("# Heading 1")
        assert "<h1>Heading 1</h1>" in result

        result = markdown_to_xhtml("## Heading 2")
        assert "<h2>Heading 2</h2>" in result

    def test_xhtml_bold_italic(self):
        """Test bold and italic conversion."""
        from confluence_as import markdown_to_xhtml

        result = markdown_to_xhtml("**bold** and *italic*")
        assert "<strong>bold</strong>" in result
        assert "<em>italic</em>" in result

    def test_xhtml_code_block(self):
        """Test code block conversion."""
        from confluence_as import markdown_to_xhtml

        result = markdown_to_xhtml("```python\nprint('hello')\n```")
        assert "code" in result.lower()


class TestADFConversion:
    """Tests for ADF conversion."""

    def test_text_to_adf(self):
        """Test plain text to ADF conversion."""
        from confluence_as import text_to_adf

        result = text_to_adf("Hello world")
        assert result["type"] == "doc"
        assert result["version"] == 1
        assert len(result["content"]) > 0

    def test_markdown_to_adf_heading(self):
        """Test Markdown heading to ADF."""
        from confluence_as import markdown_to_adf

        result = markdown_to_adf("# Heading")
        assert result["type"] == "doc"

        # Find heading node
        heading = None
        for node in result["content"]:
            if node.get("type") == "heading":
                heading = node
                break

        assert heading is not None
        assert heading["attrs"]["level"] == 1

    def test_adf_to_markdown(self):
        """Test ADF to Markdown conversion."""
        from confluence_as import adf_to_markdown, markdown_to_adf

        original = "# Test Heading\n\nA paragraph."
        adf = markdown_to_adf(original)
        result = adf_to_markdown(adf)

        assert "# Test Heading" in result
        assert "A paragraph" in result
