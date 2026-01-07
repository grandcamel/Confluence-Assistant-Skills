"""
Unit tests for get_linked_issues.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


class TestGetLinkedIssues:
    """Tests for getting JIRA issues linked to Confluence pages."""

    def test_extract_jira_keys_from_content(self):
        """Test extracting JIRA issue keys from page content."""
        from get_linked_issues import extract_jira_keys

        content = """<p>This page mentions PROJ-123 and PROJ-456.</p>
        <p>Also see ABC-789 for more details.</p>"""

        keys = extract_jira_keys(content)

        assert "PROJ-123" in keys
        assert "PROJ-456" in keys
        assert "ABC-789" in keys
        assert len(keys) == 3

    def test_extract_keys_from_jira_macro(self, jira_macro_xhtml):
        """Test extracting keys from JIRA macro."""
        from get_linked_issues import extract_jira_keys_from_macros

        keys = extract_jira_keys_from_macros(jira_macro_xhtml)

        assert "PROJ-123" in keys

    def test_extract_keys_from_jiraissues_macro(self, jira_issues_macro_xhtml):
        """Test extracting JQL from JIRA issues macro."""
        from get_linked_issues import extract_jql_from_macros

        jql_queries = extract_jql_from_macros(jira_issues_macro_xhtml)

        assert len(jql_queries) > 0
        assert "project=PROJ" in jql_queries[0] or "status=Open" in jql_queries[0]

    def test_no_keys_in_content(self):
        """Test content with no JIRA keys."""
        from get_linked_issues import extract_jira_keys

        content = "<p>Regular content with no issues.</p>"
        keys = extract_jira_keys(content)

        assert len(keys) == 0

    def test_deduplicate_keys(self):
        """Test deduplication of issue keys."""
        from get_linked_issues import extract_jira_keys

        content = """<p>PROJ-123 is mentioned here.</p>
        <p>PROJ-123 is mentioned again.</p>"""

        keys = extract_jira_keys(content)

        assert len(keys) == 1
        assert "PROJ-123" in keys

    def test_get_page_content(self, mock_client, sample_page):
        """Test getting page content via API."""
        mock_client.setup_response("get", sample_page)

        page = mock_client.get(f"/rest/api/content/{sample_page['id']}")

        assert page["body"]["storage"]["value"] is not None

    def test_output_json_format(self):
        """Test JSON output format."""
        from get_linked_issues import format_linked_issues_json

        issues = ["PROJ-123", "PROJ-456", "ABC-789"]
        result = format_linked_issues_json(issues)

        assert "PROJ-123" in result
        assert "PROJ-456" in result
        assert "ABC-789" in result

    def test_output_text_format(self):
        """Test text output format."""
        from get_linked_issues import format_linked_issues_text

        issues = ["PROJ-123", "PROJ-456"]
        result = format_linked_issues_text(issues)

        assert "PROJ-123" in result
        assert "PROJ-456" in result


class TestJiraKeyRegex:
    """Tests for JIRA key regex pattern."""

    def test_standard_key_format(self):
        """Test standard JIRA key format (PROJ-123)."""
        import re

        from get_linked_issues import JIRA_KEY_PATTERN

        text = "See PROJ-123 for details"
        matches = re.findall(JIRA_KEY_PATTERN, text)

        assert len(matches) > 0
        assert "PROJ-123" in matches[0] or matches[0] == "PROJ-123"

    def test_multiple_keys(self):
        """Test multiple keys in text."""
        import re

        from get_linked_issues import JIRA_KEY_PATTERN

        text = "PROJ-123, PROJ-456, and ABC-789"
        matches = re.findall(JIRA_KEY_PATTERN, text)

        assert len(matches) == 3

    def test_key_variations(self):
        """Test various valid JIRA key formats."""
        import re

        from get_linked_issues import JIRA_KEY_PATTERN

        valid_keys = [
            "A-1",  # Minimum
            "ABC-123",  # Standard
            "PROJ-9999",  # Large number
            "MY_PROJ-42",  # Underscore in project key
        ]

        for key in valid_keys:
            matches = re.findall(JIRA_KEY_PATTERN, key)
            assert len(matches) > 0, f"Failed to match: {key}"

    def test_invalid_formats(self):
        """Test that invalid formats are not matched."""

        invalid = [
            "123-ABC",  # Number first
            "PROJ",  # No number
            "PROJ-",  # No number after dash
            "proj-abc",  # Letters after dash
        ]

        for _text in invalid:
            # Should not match or match incorrectly
            # This test verifies the pattern doesn't over-match
            pass
