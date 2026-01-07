"""
Unit tests for embed_jira_issues.py
"""

import sys
from pathlib import Path

import pytest

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


class TestEmbedJiraIssues:
    """Tests for embedding JIRA issues in Confluence pages."""

    def test_validate_jql_query(self):
        """Test JQL query validation."""
        from confluence_assistant_skills_lib import validate_jql_query

        # Valid queries
        assert validate_jql_query("project = PROJ")
        assert validate_jql_query("status = Open AND assignee = currentUser()")

    def test_validate_issue_keys(self):
        """Test JIRA issue key validation."""
        from confluence_assistant_skills_lib import validate_issue_key

        # Valid issue keys
        assert validate_issue_key("PROJ-123") == "PROJ-123"
        assert validate_issue_key("ABC-1") == "ABC-1"
        assert validate_issue_key("proj-456") == "PROJ-456"  # Normalize to uppercase

    def test_validate_issue_keys_invalid(self):
        """Test invalid issue keys."""
        from confluence_assistant_skills_lib import ValidationError, validate_issue_key

        with pytest.raises(ValidationError):
            validate_issue_key("")

        with pytest.raises(ValidationError):
            validate_issue_key("INVALID")  # No number

        with pytest.raises(ValidationError):
            validate_issue_key("123-ABC")  # Wrong format

    def test_create_jira_macro_single_issue(self):
        """Test creating JIRA macro for a single issue."""
        from embed_jira_issues import create_jira_macro

        result = create_jira_macro(issue_key="PROJ-123")

        assert "ac:structured-macro" in result
        assert 'ac:name="jira"' in result
        assert "PROJ-123" in result

    def test_create_jira_issues_macro_jql(self):
        """Test creating JIRA issues macro with JQL."""
        from embed_jira_issues import create_jira_issues_macro

        jql = "project = PROJ AND status = Open"
        result = create_jira_issues_macro(jql=jql)

        assert "ac:structured-macro" in result
        assert 'ac:name="jira"' in result
        assert "jqlQuery" in result
        assert jql in result

    def test_create_jira_issues_macro_multiple_keys(self):
        """Test creating JIRA issues macro with multiple issue keys."""
        from embed_jira_issues import create_jira_issues_macro

        keys = ["PROJ-123", "PROJ-456", "PROJ-789"]
        result = create_jira_issues_macro(issue_keys=keys)

        assert "ac:structured-macro" in result
        assert 'ac:name="jira"' in result
        assert "jqlQuery" in result
        # Should contain keys in JQL format
        for key in keys:
            assert key in result

    def test_embed_issues_get_page(self, mock_client, sample_page):
        """Test getting existing page content."""
        mock_client.setup_response("get", sample_page)

        page = mock_client.get(f"/rest/api/content/{sample_page['id']}")

        assert page["id"] == sample_page["id"]
        assert page["title"] == sample_page["title"]

    def test_embed_issues_update_page(self, mock_client, sample_page):
        """Test updating page with JIRA macro."""
        # Setup - get page first
        mock_client.setup_response("get", sample_page)

        # Then update
        updated_page = {**sample_page, "version": {"number": 2}}
        mock_client.setup_response("put", updated_page)

        # This would be called by the script
        # Verify the structure is correct

    def test_append_mode(self):
        """Test appending JIRA macro to existing content."""
        from embed_jira_issues import append_jira_macro

        original_content = "<p>Existing content</p>"
        macro = '<ac:structured-macro ac:name="jira"><ac:parameter ac:name="key">PROJ-123</ac:parameter></ac:structured-macro>'

        result = append_jira_macro(original_content, macro)

        assert "Existing content" in result
        assert "PROJ-123" in result
        assert result.index("Existing content") < result.index("PROJ-123")

    def test_replace_mode(self):
        """Test replacing page content with JIRA macro."""
        from embed_jira_issues import replace_with_jira_macro

        original_content = "<p>Old content</p>"
        macro = '<ac:structured-macro ac:name="jira"><ac:parameter ac:name="key">PROJ-123</ac:parameter></ac:structured-macro>'

        result = replace_with_jira_macro(original_content, macro)

        assert "Old content" not in result
        assert "PROJ-123" in result


class TestJQLBuilder:
    """Tests for JQL query building."""

    def test_build_jql_from_keys(self):
        """Test building JQL from issue keys."""
        from embed_jira_issues import build_jql_from_keys

        keys = ["PROJ-123", "PROJ-456"]
        result = build_jql_from_keys(keys)

        # Should create an OR query
        assert "PROJ-123" in result
        assert "PROJ-456" in result
        assert " OR " in result or "," in result

    def test_build_jql_single_key(self):
        """Test building JQL from single key."""
        from embed_jira_issues import build_jql_from_keys

        keys = ["PROJ-123"]
        result = build_jql_from_keys(keys)

        assert "PROJ-123" in result


class TestMacroParameters:
    """Tests for JIRA macro parameter handling."""

    def test_macro_with_server_id(self):
        """Test macro includes server ID when provided."""
        from embed_jira_issues import create_jira_macro

        result = create_jira_macro(issue_key="PROJ-123", server_id="abc-123-def-456")

        assert "server" in result.lower() or "serverid" in result.lower()
        assert "abc-123-def-456" in result

    def test_macro_with_columns(self):
        """Test JIRA issues macro with custom columns."""
        from embed_jira_issues import create_jira_issues_macro

        columns = ["key", "summary", "status", "assignee"]
        result = create_jira_issues_macro(jql="project = PROJ", columns=columns)

        # Check if columns are included
        for col in columns:
            assert col in result.lower()

    def test_macro_with_count(self):
        """Test JIRA issues macro with result count."""
        from embed_jira_issues import create_jira_issues_macro

        result = create_jira_issues_macro(jql="project = PROJ", max_results=10)

        assert "10" in result or "count" in result.lower()
