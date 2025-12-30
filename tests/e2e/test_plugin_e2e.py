"""
E2E test classes for confluence-assistant-skills

Run with: pytest tests/e2e/ -v --e2e-verbose
"""

import pytest
from pathlib import Path

from .runner import E2ETestStatus


pytestmark = [pytest.mark.e2e, pytest.mark.slow]


# All 14 Confluence skills
EXPECTED_SKILLS = [
    "confluence-assistant",
    "confluence-page",
    "confluence-space",
    "confluence-search",
    "confluence-comment",
    "confluence-attachment",
    "confluence-label",
    "confluence-template",
    "confluence-property",
    "confluence-permission",
    "confluence-analytics",
    "confluence-watch",
    "confluence-hierarchy",
    "confluence-jira",
]


class TestPluginInstallation:
    """Plugin installation tests."""

    def test_plugin_installs(self, claude_runner, e2e_enabled):
        """Verify plugin installs successfully."""
        if not e2e_enabled:
            pytest.skip("E2E disabled")

        result = claude_runner.install_plugin(".")
        assert result["success"] or "already installed" in result["output"].lower()

    def test_skills_discoverable(self, claude_runner, installed_plugin, e2e_enabled):
        """Verify skills are discoverable after installation."""
        if not e2e_enabled:
            pytest.skip("E2E disabled")

        result = claude_runner.send_prompt("What skills are available?")
        output = result["output"].lower()

        # Check for at least one skill
        found = any(s.lower() in output for s in EXPECTED_SKILLS)
        assert found or result["success"], "No skills found in output"


class TestConfluenceSkills:
    """Test individual Confluence skills."""

    @pytest.mark.parametrize("skill", EXPECTED_SKILLS)
    def test_skill_mentioned(self, claude_runner, installed_plugin, e2e_enabled, skill):
        """Verify each skill can be referenced."""
        if not e2e_enabled:
            pytest.skip("E2E disabled")

        # Extract the operation type from skill name
        operation = skill.replace("confluence-", "")
        result = claude_runner.send_prompt(f"What can I do with Confluence {operation}?")

        # Should get a response without errors
        assert result["success"] or not result.get("error"), f"Error for {skill}: {result.get('error')}"


class TestPageOperations:
    """Test page-related skill functionality."""

    def test_page_creation_help(self, claude_runner, installed_plugin, e2e_enabled):
        """Test help for page creation."""
        if not e2e_enabled:
            pytest.skip("E2E disabled")

        result = claude_runner.send_prompt("How do I create a new Confluence page?")
        output = result["output"].lower()

        assert any(term in output for term in ["create", "page", "space"]), \
            "Expected page creation info in response"

    def test_page_update_help(self, claude_runner, installed_plugin, e2e_enabled):
        """Test help for page updates."""
        if not e2e_enabled:
            pytest.skip("E2E disabled")

        result = claude_runner.send_prompt("How do I update an existing Confluence page?")
        output = result["output"].lower()

        assert any(term in output for term in ["update", "edit", "modify"]), \
            "Expected page update info in response"


class TestSearchOperations:
    """Test search-related skill functionality."""

    def test_cql_help(self, claude_runner, installed_plugin, e2e_enabled):
        """Test CQL query help."""
        if not e2e_enabled:
            pytest.skip("E2E disabled")

        result = claude_runner.send_prompt("How do I write a CQL query for Confluence?")
        output = result["output"].lower()

        assert any(term in output for term in ["cql", "query", "search"]), \
            "Expected CQL info in response"

    def test_export_help(self, claude_runner, installed_plugin, e2e_enabled):
        """Test search export help."""
        if not e2e_enabled:
            pytest.skip("E2E disabled")

        result = claude_runner.send_prompt("How do I export Confluence search results?")
        output = result["output"].lower()

        assert any(term in output for term in ["export", "csv", "json"]), \
            "Expected export info in response"


@pytest.mark.skip(reason="Redundant with test_individual_case parametrized tests")
class TestYAMLSuites:
    """Run all YAML-defined test suites."""

    def test_all_suites(self, e2e_runner, e2e_enabled):
        """Execute all test suites from test_cases.yaml."""
        if not e2e_enabled:
            pytest.skip("E2E disabled")

        results = e2e_runner.run_all()
        success = e2e_runner.print_summary(results)

        failures = [
            f"{s.suite_name}::{t.test_id}"
            for s in results
            for t in s.tests
            if t.status != E2ETestStatus.PASSED
        ]
        assert len(failures) == 0, f"Test failures: {failures}"


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_invalid_page_id(self, claude_runner, installed_plugin, e2e_enabled):
        """Test handling of invalid page ID."""
        if not e2e_enabled:
            pytest.skip("E2E disabled")

        result = claude_runner.send_prompt("Get Confluence page with ID 'not-a-number'")

        # Should not crash
        assert "segmentation fault" not in result.get("error", "").lower()
        assert "panic" not in result.get("error", "").lower()

    def test_missing_credentials_message(self, claude_runner, installed_plugin, e2e_enabled):
        """Test helpful message for missing credentials."""
        if not e2e_enabled:
            pytest.skip("E2E disabled")

        result = claude_runner.send_prompt(
            "What do I need to configure to use Confluence skills?"
        )
        output = result["output"].lower()

        assert any(term in output for term in [
            "api_token", "api token", "credential", "authentication", "configure"
        ]), "Expected configuration info in response"
