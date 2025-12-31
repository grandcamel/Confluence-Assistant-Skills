"""Test suite for Confluence CLI."""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from confluence_assistant_skills.cli.main import cli


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_call_skill():
    """Mock the call_skill_main function."""
    with patch("confluence_assistant_skills.utils.call_skill_main") as mock:
        mock.return_value = 0
        yield mock


class TestCLIRoot:
    """Test the root CLI command."""

    def test_help(self, runner: CliRunner) -> None:
        """Test --help flag."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Confluence Assistant Skills CLI" in result.output
        assert "page" in result.output
        assert "space" in result.output
        assert "search" in result.output

    def test_version(self, runner: CliRunner) -> None:
        """Test --version flag."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "confluence, version" in result.output

    def test_no_command_shows_help(self, runner: CliRunner) -> None:
        """Test that no command shows help."""
        result = runner.invoke(cli, [])
        assert result.exit_code == 0
        assert "Usage:" in result.output


class TestPageCommands:
    """Test page command group."""

    def test_page_help(self, runner: CliRunner) -> None:
        """Test page --help."""
        result = runner.invoke(cli, ["page", "--help"])
        assert result.exit_code == 0
        assert "Manage Confluence pages" in result.output
        assert "get" in result.output
        assert "create" in result.output
        assert "update" in result.output
        assert "delete" in result.output

    def test_page_get(self, runner: CliRunner) -> None:
        """Test page get command."""
        with patch("confluence_assistant_skills.cli.commands.page_cmds.call_skill_main") as mock:
            mock.return_value = 0
            result = runner.invoke(cli, ["page", "get", "12345"])
            assert result.exit_code == 0
            mock.assert_called_once_with(
                "confluence-page",
                "get_page",
                ["12345"],
            )

    def test_page_get_with_options(self, runner: CliRunner) -> None:
        """Test page get command with options."""
        with patch("confluence_assistant_skills.cli.commands.page_cmds.call_skill_main") as mock:
            mock.return_value = 0
            result = runner.invoke(
                cli,
                ["page", "get", "12345", "--body", "--format", "markdown", "--output", "json"],
            )
            assert result.exit_code == 0
            mock.assert_called_once()
            args = mock.call_args[0]
            assert args[0] == "confluence-page"
            assert args[1] == "get_page"
            assert "12345" in args[2]
            assert "--body" in args[2]
            assert "--format" in args[2]
            assert "markdown" in args[2]
            assert "--output" in args[2]
            assert "json" in args[2]

    def test_page_create(self, runner: CliRunner) -> None:
        """Test page create command."""
        with patch("confluence_assistant_skills.cli.commands.page_cmds.call_skill_main") as mock:
            mock.return_value = 0
            result = runner.invoke(
                cli,
                ["page", "create", "DOCS", "Test Page", "--body", "Test content"],
            )
            assert result.exit_code == 0
            mock.assert_called_once()
            args = mock.call_args[0]
            assert args[0] == "confluence-page"
            assert args[1] == "create_page"
            assert "DOCS" in args[2]
            assert "Test Page" in args[2]
            assert "--body" in args[2]

    def test_page_delete(self, runner: CliRunner) -> None:
        """Test page delete command."""
        with patch("confluence_assistant_skills.cli.commands.page_cmds.call_skill_main") as mock:
            mock.return_value = 0
            result = runner.invoke(cli, ["page", "delete", "12345", "--confirm"])
            assert result.exit_code == 0
            mock.assert_called_once()
            args = mock.call_args[0]
            assert args[0] == "confluence-page"
            assert args[1] == "delete_page"
            assert "12345" in args[2]
            assert "--confirm" in args[2]


class TestSpaceCommands:
    """Test space command group."""

    def test_space_help(self, runner: CliRunner) -> None:
        """Test space --help."""
        result = runner.invoke(cli, ["space", "--help"])
        assert result.exit_code == 0
        assert "Manage Confluence spaces" in result.output

    def test_space_list(self, runner: CliRunner) -> None:
        """Test space list command."""
        with patch("confluence_assistant_skills.cli.commands.space_cmds.call_skill_main") as mock:
            mock.return_value = 0
            result = runner.invoke(cli, ["space", "list"])
            assert result.exit_code == 0
            mock.assert_called_once_with(
                "confluence-space",
                "list_spaces",
                [],
            )

    def test_space_get(self, runner: CliRunner) -> None:
        """Test space get command."""
        with patch("confluence_assistant_skills.cli.commands.space_cmds.call_skill_main") as mock:
            mock.return_value = 0
            result = runner.invoke(cli, ["space", "get", "DOCS"])
            assert result.exit_code == 0
            mock.assert_called_once_with(
                "confluence-space",
                "get_space",
                ["DOCS"],
            )


class TestSearchCommands:
    """Test search command group."""

    def test_search_help(self, runner: CliRunner) -> None:
        """Test search --help."""
        result = runner.invoke(cli, ["search", "--help"])
        assert result.exit_code == 0
        assert "Search Confluence content" in result.output

    def test_search_cql(self, runner: CliRunner) -> None:
        """Test search cql command."""
        with patch("confluence_assistant_skills.cli.commands.search_cmds.call_skill_main") as mock:
            mock.return_value = 0
            result = runner.invoke(cli, ["search", "cql", "space = DOCS"])
            assert result.exit_code == 0
            mock.assert_called_once()
            args = mock.call_args[0]
            assert args[0] == "confluence-search"
            assert args[1] == "cql_search"
            assert "space = DOCS" in args[2]

    def test_search_cql_with_options(self, runner: CliRunner) -> None:
        """Test search cql command with options."""
        with patch("confluence_assistant_skills.cli.commands.search_cmds.call_skill_main") as mock:
            mock.return_value = 0
            result = runner.invoke(
                cli,
                ["search", "cql", "space = DOCS", "--limit", "50", "--show-labels"],
            )
            assert result.exit_code == 0
            args = mock.call_args[0]
            assert "--limit" in args[2]
            assert "50" in args[2]
            assert "--show-labels" in args[2]


class TestCommentCommands:
    """Test comment command group."""

    def test_comment_list(self, runner: CliRunner) -> None:
        """Test comment list command."""
        with patch("confluence_assistant_skills.cli.commands.comment_cmds.call_skill_main") as mock:
            mock.return_value = 0
            result = runner.invoke(cli, ["comment", "list", "12345"])
            assert result.exit_code == 0
            mock.assert_called_once()
            args = mock.call_args[0]
            assert args[0] == "confluence-comment"
            assert args[1] == "get_comments"

    def test_comment_add(self, runner: CliRunner) -> None:
        """Test comment add command."""
        with patch("confluence_assistant_skills.cli.commands.comment_cmds.call_skill_main") as mock:
            mock.return_value = 0
            result = runner.invoke(cli, ["comment", "add", "12345", "Test comment"])
            assert result.exit_code == 0
            mock.assert_called_once()
            args = mock.call_args[0]
            assert args[0] == "confluence-comment"
            assert args[1] == "add_comment"


class TestLabelCommands:
    """Test label command group."""

    def test_label_add(self, runner: CliRunner) -> None:
        """Test label add command."""
        with patch("confluence_assistant_skills.cli.commands.label_cmds.call_skill_main") as mock:
            mock.return_value = 0
            result = runner.invoke(cli, ["label", "add", "12345", "tag1", "tag2"])
            assert result.exit_code == 0
            mock.assert_called_once()
            args = mock.call_args[0]
            assert args[0] == "confluence-label"
            assert args[1] == "add_label"
            assert "12345" in args[2]
            assert "tag1" in args[2]
            assert "tag2" in args[2]


class TestAttachmentCommands:
    """Test attachment command group."""

    def test_attachment_list(self, runner: CliRunner) -> None:
        """Test attachment list command."""
        with patch("confluence_assistant_skills.cli.commands.attachment_cmds.call_skill_main") as mock:
            mock.return_value = 0
            result = runner.invoke(cli, ["attachment", "list", "12345"])
            assert result.exit_code == 0
            mock.assert_called_once()
            args = mock.call_args[0]
            assert args[0] == "confluence-attachment"
            assert args[1] == "list_attachments"


class TestHierarchyCommands:
    """Test hierarchy command group."""

    def test_hierarchy_children(self, runner: CliRunner) -> None:
        """Test hierarchy children command."""
        with patch("confluence_assistant_skills.cli.commands.hierarchy_cmds.call_skill_main") as mock:
            mock.return_value = 0
            result = runner.invoke(cli, ["hierarchy", "children", "12345"])
            assert result.exit_code == 0
            mock.assert_called_once()
            args = mock.call_args[0]
            assert args[0] == "confluence-hierarchy"
            assert args[1] == "get_children"

    def test_hierarchy_tree(self, runner: CliRunner) -> None:
        """Test hierarchy tree command."""
        with patch("confluence_assistant_skills.cli.commands.hierarchy_cmds.call_skill_main") as mock:
            mock.return_value = 0
            result = runner.invoke(cli, ["hierarchy", "tree", "12345", "--depth", "5"])
            assert result.exit_code == 0
            args = mock.call_args[0]
            assert args[0] == "confluence-hierarchy"
            assert args[1] == "get_page_tree"
            assert "--depth" in args[2]
            assert "5" in args[2]


class TestAnalyticsCommands:
    """Test analytics command group."""

    def test_analytics_views(self, runner: CliRunner) -> None:
        """Test analytics views command."""
        with patch("confluence_assistant_skills.cli.commands.analytics_cmds.call_skill_main") as mock:
            mock.return_value = 0
            result = runner.invoke(cli, ["analytics", "views", "12345"])
            assert result.exit_code == 0
            mock.assert_called_once()
            args = mock.call_args[0]
            assert args[0] == "confluence-analytics"
            assert args[1] == "get_page_views"


class TestWatchCommands:
    """Test watch command group."""

    def test_watch_page(self, runner: CliRunner) -> None:
        """Test watch page command."""
        with patch("confluence_assistant_skills.cli.commands.watch_cmds.call_skill_main") as mock:
            mock.return_value = 0
            result = runner.invoke(cli, ["watch", "page", "12345"])
            assert result.exit_code == 0
            mock.assert_called_once()
            args = mock.call_args[0]
            assert args[0] == "confluence-watch"
            assert args[1] == "watch_page"


class TestTemplateCommands:
    """Test template command group."""

    def test_template_list(self, runner: CliRunner) -> None:
        """Test template list command."""
        with patch("confluence_assistant_skills.cli.commands.template_cmds.call_skill_main") as mock:
            mock.return_value = 0
            result = runner.invoke(cli, ["template", "list"])
            assert result.exit_code == 0
            mock.assert_called_once()
            args = mock.call_args[0]
            assert args[0] == "confluence-template"
            assert args[1] == "list_templates"


class TestPropertyCommands:
    """Test property command group."""

    def test_property_set(self, runner: CliRunner) -> None:
        """Test property set command."""
        with patch("confluence_assistant_skills.cli.commands.property_cmds.call_skill_main") as mock:
            mock.return_value = 0
            result = runner.invoke(cli, ["property", "set", "12345", "mykey", "myvalue"])
            assert result.exit_code == 0
            mock.assert_called_once()
            args = mock.call_args[0]
            assert args[0] == "confluence-property"
            assert args[1] == "set_property"
            assert "12345" in args[2]
            assert "mykey" in args[2]
            assert "myvalue" in args[2]


class TestPermissionCommands:
    """Test permission command group."""

    def test_permission_page_get(self, runner: CliRunner) -> None:
        """Test permission page get command."""
        with patch("confluence_assistant_skills.cli.commands.permission_cmds.call_skill_main") as mock:
            mock.return_value = 0
            result = runner.invoke(cli, ["permission", "page", "get", "12345"])
            assert result.exit_code == 0
            mock.assert_called_once()
            args = mock.call_args[0]
            assert args[0] == "confluence-permission"
            assert args[1] == "get_page_restrictions"

    def test_permission_space_get(self, runner: CliRunner) -> None:
        """Test permission space get command."""
        with patch("confluence_assistant_skills.cli.commands.permission_cmds.call_skill_main") as mock:
            mock.return_value = 0
            result = runner.invoke(cli, ["permission", "space", "get", "DOCS"])
            assert result.exit_code == 0
            mock.assert_called_once()
            args = mock.call_args[0]
            assert args[0] == "confluence-permission"
            assert args[1] == "get_space_permissions"


class TestJiraCommands:
    """Test jira command group."""

    def test_jira_link(self, runner: CliRunner) -> None:
        """Test jira link command."""
        with patch("confluence_assistant_skills.cli.commands.jira_cmds.call_skill_main") as mock:
            mock.return_value = 0
            result = runner.invoke(cli, ["jira", "link", "12345", "PROJ-123"])
            assert result.exit_code == 0
            mock.assert_called_once()
            args = mock.call_args[0]
            assert args[0] == "confluence-jira"
            assert args[1] == "link_to_jira"
            assert "12345" in args[2]
            assert "PROJ-123" in args[2]


class TestGlobalOptions:
    """Test global CLI options."""

    def test_profile_option(self, runner: CliRunner) -> None:
        """Test --profile global option."""
        with patch("confluence_assistant_skills.cli.commands.page_cmds.call_skill_main") as mock:
            mock.return_value = 0
            result = runner.invoke(cli, ["--profile", "test", "page", "get", "12345"])
            assert result.exit_code == 0
            args = mock.call_args[0]
            # Profile should be passed through context, not directly to the skill
            # The profile is handled in the command itself
            mock.assert_called_once()

    def test_output_option(self, runner: CliRunner) -> None:
        """Test --output global option."""
        with patch("confluence_assistant_skills.cli.commands.space_cmds.call_skill_main") as mock:
            mock.return_value = 0
            result = runner.invoke(cli, ["--output", "json", "space", "list"])
            assert result.exit_code == 0
            mock.assert_called_once()


class TestErrorHandling:
    """Test CLI error handling."""

    def test_nonzero_exit_code(self, runner: CliRunner) -> None:
        """Test that non-zero exit codes from scripts are propagated."""
        with patch("confluence_assistant_skills.cli.commands.page_cmds.call_skill_main") as mock:
            mock.return_value = 1
            result = runner.invoke(cli, ["page", "get", "12345"])
            assert result.exit_code == 1

    def test_missing_required_argument(self, runner: CliRunner) -> None:
        """Test missing required argument."""
        result = runner.invoke(cli, ["page", "get"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "Error" in result.output
