"""
E2E test classes for confluence-assistant-skills

Run with: pytest tests/e2e/ -v --e2e-verbose
Save responses: pytest tests/e2e/ -v --e2e-save-responses
"""

from pathlib import Path

import pytest

from .conftest import assert_response_contains
from .runner import E2ETestStatus

pytestmark = [pytest.mark.e2e, pytest.mark.slow]


def _discover_skills() -> list[str]:
    """Dynamically discover skills from plugin directory."""
    skills_dir = Path(__file__).parent.parent.parent / "skills"
    if not skills_dir.exists():
        return []
    return sorted(
        d.name
        for d in skills_dir.iterdir()
        if d.is_dir() and d.name.startswith("confluence-")
    )


# Dynamically discover all Confluence skills
EXPECTED_SKILLS = _discover_skills()


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

        # Check for at least one skill mentioned
        assert_response_contains(
            result,
            EXPECTED_SKILLS,
            "No Confluence skills found in output",
            match_any=True,
        )


class TestConfluenceSkills:
    """Test individual Confluence skills."""

    @pytest.mark.parametrize("skill", EXPECTED_SKILLS)
    def test_skill_mentioned(self, claude_runner, installed_plugin, e2e_enabled, skill):
        """Verify each skill can be referenced."""
        if not e2e_enabled:
            pytest.skip("E2E disabled")

        # Extract the operation type from skill name
        operation = skill.replace("confluence-", "")
        result = claude_runner.send_prompt(
            f"Without reading any files, in one sentence: what does the confluence-{operation} skill do?"
        )

        # Should get a response without errors
        assert result["success"] or not result.get("error"), (
            f"Error for {skill}: {result.get('error')}"
        )


class TestPageOperations:
    """Test page-related skill functionality."""

    def test_page_creation_help(self, claude_runner, installed_plugin, e2e_enabled):
        """Test help for page creation."""
        if not e2e_enabled:
            pytest.skip("E2E disabled")

        result = claude_runner.send_prompt(
            "Without reading any files, briefly explain: what CLI command creates a Confluence page?"
        )

        assert_response_contains(
            result,
            ["create", "page", "space", "confluence"],
            "Expected page creation info in response",
        )

    def test_page_update_help(self, claude_runner, installed_plugin, e2e_enabled):
        """Test help for page updates."""
        if not e2e_enabled:
            pytest.skip("E2E disabled")

        result = claude_runner.send_prompt(
            "Without reading any files, briefly explain: what CLI command updates a Confluence page?"
        )

        assert_response_contains(
            result,
            ["update", "edit", "modify", "page", "content"],
            "Expected page update info in response",
        )


class TestSearchOperations:
    """Test search-related skill functionality."""

    def test_cql_help(self, claude_runner, installed_plugin, e2e_enabled):
        """Test CQL query help."""
        if not e2e_enabled:
            pytest.skip("E2E disabled")

        result = claude_runner.send_prompt("How do I write a CQL query for Confluence?")

        assert_response_contains(
            result,
            ["cql", "query", "search", "confluence"],
            "Expected CQL info in response",
        )

    def test_export_help(self, claude_runner, installed_plugin, e2e_enabled):
        """Test search export help."""
        if not e2e_enabled:
            pytest.skip("E2E disabled")

        result = claude_runner.send_prompt(
            "Without reading any files, briefly explain: what CLI command exports Confluence search results to CSV?"
        )

        assert_response_contains(
            result,
            ["export", "csv", "json", "results", "search"],
            "Expected export info in response",
        )


@pytest.mark.skip(reason="Redundant with test_individual_case parametrized tests")
class TestYAMLSuites:
    """Run all YAML-defined test suites."""

    def test_all_suites(self, e2e_runner, e2e_enabled):
        """Execute all test suites from test_cases.yaml."""
        if not e2e_enabled:
            pytest.skip("E2E disabled")

        results = e2e_runner.run_all()
        e2e_runner.print_summary(results)

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

    def test_missing_credentials_message(
        self, claude_runner, installed_plugin, e2e_enabled
    ):
        """Test helpful message for missing credentials."""
        if not e2e_enabled:
            pytest.skip("E2E disabled")

        result = claude_runner.send_prompt(
            "What do I need to configure to use Confluence skills?"
        )

        assert_response_contains(
            result,
            [
                "api_token",
                "api token",
                "credential",
                "authentication",
                "configure",
                "token",
                "url",
                "email",
                "settings",
                "environment",
            ],
            "Expected configuration info in response",
        )
