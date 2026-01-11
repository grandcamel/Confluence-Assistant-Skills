"""Test suite for Confluence CLI.

Tests the CLI commands with mocked API client. After the CLI-only refactoring,
commands make direct API calls rather than delegating to skill scripts.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from confluence_assistant_skills.cli.main import cli


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner()


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
        with patch("confluence_assistant_skills.cli.commands.page_cmds.get_confluence_client") as mock:
            client = MagicMock()
            mock.return_value = client
            client.get.return_value = {
                "id": "12345",
                "title": "Test Page",
                "status": "current",
                "spaceId": "123",
                "_links": {"webui": "/wiki/test"}
            }
            result = runner.invoke(cli, ["page", "get", "12345"])
            assert result.exit_code == 0
            client.get.assert_called()

    def test_page_get_with_body(self, runner: CliRunner) -> None:
        """Test page get command with --body option."""
        with patch("confluence_assistant_skills.cli.commands.page_cmds.get_confluence_client") as mock:
            client = MagicMock()
            mock.return_value = client
            client.get.return_value = {
                "id": "12345",
                "title": "Test Page",
                "status": "current",
                "spaceId": "123",
                "body": {"storage": {"value": "<p>Content</p>"}},
                "_links": {"webui": "/wiki/test"}
            }
            result = runner.invoke(cli, ["page", "get", "12345", "--body"])
            assert result.exit_code == 0

    def test_page_create(self, runner: CliRunner) -> None:
        """Test page create command."""
        with patch("confluence_assistant_skills.cli.commands.page_cmds.get_confluence_client") as mock:
            client = MagicMock()
            mock.return_value = client
            # Mock space lookup by key
            client.paginate.return_value = iter([{"id": "100", "key": "DOCS", "name": "Documentation"}])
            # Mock page creation
            client.post.return_value = {
                "id": "12345",
                "title": "Test Page",
                "status": "current",
                "spaceId": "100",
                "_links": {"webui": "/wiki/test"}
            }
            result = runner.invoke(
                cli,
                ["page", "create", "--space", "DOCS", "--title", "Test Page", "--body", "Test content"],
            )
            assert result.exit_code == 0
            client.post.assert_called()

    def test_page_delete(self, runner: CliRunner) -> None:
        """Test page delete command."""
        with patch("confluence_assistant_skills.cli.commands.page_cmds.get_confluence_client") as mock:
            client = MagicMock()
            mock.return_value = client
            # Mock getting page info first
            client.get.return_value = {
                "id": "12345",
                "title": "Test Page",
                "status": "current"
            }
            client.delete.return_value = None
            result = runner.invoke(cli, ["page", "delete", "12345", "--force"])
            assert result.exit_code == 0
            client.delete.assert_called()


class TestSpaceCommands:
    """Test space command group."""

    def test_space_help(self, runner: CliRunner) -> None:
        """Test space --help."""
        result = runner.invoke(cli, ["space", "--help"])
        assert result.exit_code == 0
        assert "Manage Confluence spaces" in result.output

    def test_space_list(self, runner: CliRunner) -> None:
        """Test space list command."""
        with patch("confluence_assistant_skills.cli.commands.space_cmds.get_confluence_client") as mock:
            client = MagicMock()
            mock.return_value = client
            client.paginate.return_value = iter([
                {"id": "1", "key": "DOCS", "name": "Documentation", "type": "global"},
                {"id": "2", "key": "KB", "name": "Knowledge Base", "type": "global"}
            ])
            result = runner.invoke(cli, ["space", "list"])
            assert result.exit_code == 0
            client.paginate.assert_called()

    def test_space_get(self, runner: CliRunner) -> None:
        """Test space get command."""
        with patch("confluence_assistant_skills.cli.commands.space_cmds.get_confluence_client") as mock:
            client = MagicMock()
            mock.return_value = client
            client.paginate.return_value = iter([{
                "id": "1",
                "key": "DOCS",
                "name": "Documentation",
                "type": "global"
            }])
            result = runner.invoke(cli, ["space", "get", "DOCS"])
            assert result.exit_code == 0
            client.paginate.assert_called()


class TestSearchCommands:
    """Test search command group."""

    def test_search_help(self, runner: CliRunner) -> None:
        """Test search --help."""
        result = runner.invoke(cli, ["search", "--help"])
        assert result.exit_code == 0
        assert "Search Confluence content" in result.output

    def test_search_cql(self, runner: CliRunner) -> None:
        """Test search cql command."""
        with patch("confluence_assistant_skills.cli.commands.search_cmds.get_confluence_client") as mock:
            client = MagicMock()
            mock.return_value = client
            client.paginate.return_value = iter([
                {"content": {"id": "1", "title": "Page 1", "type": "page"}}
            ])
            result = runner.invoke(cli, ["search", "cql", "space = DOCS"])
            assert result.exit_code == 0
            client.paginate.assert_called()

    def test_search_cql_with_options(self, runner: CliRunner) -> None:
        """Test search cql command with options."""
        with patch("confluence_assistant_skills.cli.commands.search_cmds.get_confluence_client") as mock:
            client = MagicMock()
            mock.return_value = client
            client.paginate.return_value = iter([])
            result = runner.invoke(
                cli,
                ["search", "cql", "space = DOCS", "--limit", "50"],
            )
            assert result.exit_code == 0


class TestCommentCommands:
    """Test comment command group."""

    def test_comment_list(self, runner: CliRunner) -> None:
        """Test comment list command."""
        with patch("confluence_assistant_skills.cli.commands.comment_cmds.get_confluence_client") as mock:
            client = MagicMock()
            mock.return_value = client
            client.get.return_value = {
                "results": [],
                "_links": {}
            }
            result = runner.invoke(cli, ["comment", "list", "12345"])
            assert result.exit_code == 0
            client.get.assert_called()

    def test_comment_add(self, runner: CliRunner) -> None:
        """Test comment add command."""
        with patch("confluence_assistant_skills.cli.commands.comment_cmds.get_confluence_client") as mock:
            client = MagicMock()
            mock.return_value = client
            client.post.return_value = {
                "id": "999",
                "body": {"storage": {"value": "Test comment"}}
            }
            result = runner.invoke(cli, ["comment", "add", "12345", "Test comment"])
            assert result.exit_code == 0
            client.post.assert_called()


class TestLabelCommands:
    """Test label command group."""

    def test_label_add_single(self, runner: CliRunner) -> None:
        """Test label add command with single label (positional argument)."""
        with patch("confluence_assistant_skills.cli.commands.label_cmds.get_confluence_client") as mock:
            client = MagicMock()
            mock.return_value = client
            client.post.return_value = {"results": [{"name": "documentation"}]}
            result = runner.invoke(cli, ["label", "add", "12345", "documentation"])
            assert result.exit_code == 0
            client.post.assert_called()

    def test_label_add_multiple(self, runner: CliRunner) -> None:
        """Test label add command with multiple labels (positional arguments)."""
        with patch("confluence_assistant_skills.cli.commands.label_cmds.get_confluence_client") as mock:
            client = MagicMock()
            mock.return_value = client
            client.post.return_value = {"results": [{"name": "doc"}, {"name": "approved"}]}
            result = runner.invoke(cli, ["label", "add", "12345", "doc", "approved", "v2"])
            assert result.exit_code == 0
            client.post.assert_called()

    def test_label_add_requires_at_least_one_label(self, runner: CliRunner) -> None:
        """Test label add command requires at least one label."""
        result = runner.invoke(cli, ["label", "add", "12345"])
        assert result.exit_code != 0
        # Should fail with validation error about missing labels
        assert "label" in result.output.lower() or "required" in result.output.lower()

    def test_label_remove(self, runner: CliRunner) -> None:
        """Test label remove command (positional arguments)."""
        with patch("confluence_assistant_skills.cli.commands.label_cmds.get_confluence_client") as mock:
            client = MagicMock()
            mock.return_value = client
            client.delete.return_value = None
            result = runner.invoke(cli, ["label", "remove", "12345", "draft"])
            assert result.exit_code == 0
            client.delete.assert_called()

    def test_label_remove_requires_label_name(self, runner: CliRunner) -> None:
        """Test label remove command requires label name argument."""
        result = runner.invoke(cli, ["label", "remove", "12345"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output


class TestAttachmentCommands:
    """Test attachment command group."""

    def test_attachment_list(self, runner: CliRunner) -> None:
        """Test attachment list command."""
        with patch("confluence_assistant_skills.cli.commands.attachment_cmds.get_confluence_client") as mock:
            client = MagicMock()
            mock.return_value = client
            client.get.return_value = {
                "results": [],
                "_links": {}
            }
            result = runner.invoke(cli, ["attachment", "list", "12345"])
            assert result.exit_code == 0
            client.get.assert_called()


class TestHierarchyCommands:
    """Test hierarchy command group."""

    def test_hierarchy_children(self, runner: CliRunner) -> None:
        """Test hierarchy children command."""
        with patch("confluence_assistant_skills.cli.commands.hierarchy_cmds.get_confluence_client") as mock:
            client = MagicMock()
            mock.return_value = client
            client.get.return_value = {
                "results": [],
                "_links": {}
            }
            result = runner.invoke(cli, ["hierarchy", "children", "12345"])
            assert result.exit_code == 0
            client.get.assert_called()

    def test_hierarchy_tree(self, runner: CliRunner) -> None:
        """Test hierarchy tree command."""
        with patch("confluence_assistant_skills.cli.commands.hierarchy_cmds.get_confluence_client") as mock:
            client = MagicMock()
            mock.return_value = client
            # Mock get page
            client.get.side_effect = [
                {"id": "12345", "title": "Root Page", "status": "current"},
                {"results": [], "_links": {}},  # Children request
            ]
            result = runner.invoke(cli, ["hierarchy", "tree", "12345", "--max-depth", "5"])
            assert result.exit_code == 0


class TestAnalyticsCommands:
    """Test analytics command group."""

    def test_analytics_views(self, runner: CliRunner) -> None:
        """Test analytics views command."""
        with patch("confluence_assistant_skills.cli.commands.analytics_cmds.get_confluence_client") as mock:
            client = MagicMock()
            mock.return_value = client
            client.get.return_value = {
                "id": "12345",
                "count": 100
            }
            result = runner.invoke(cli, ["analytics", "views", "12345"])
            assert result.exit_code == 0
            client.get.assert_called()


class TestWatchCommands:
    """Test watch command group."""

    def test_watch_page(self, runner: CliRunner) -> None:
        """Test watch page command."""
        with patch("confluence_assistant_skills.cli.commands.watch_cmds.get_confluence_client") as mock:
            client = MagicMock()
            mock.return_value = client
            client.post.return_value = {}
            result = runner.invoke(cli, ["watch", "page", "12345"])
            assert result.exit_code == 0
            client.post.assert_called()


class TestTemplateCommands:
    """Test template command group."""

    def test_template_list(self, runner: CliRunner) -> None:
        """Test template list command."""
        with patch("confluence_assistant_skills.cli.commands.template_cmds.get_confluence_client") as mock:
            client = MagicMock()
            mock.return_value = client
            client.paginate.return_value = iter([])
            result = runner.invoke(cli, ["template", "list"])
            assert result.exit_code == 0
            client.paginate.assert_called()


class TestPropertyCommands:
    """Test property command group."""

    def test_property_set(self, runner: CliRunner) -> None:
        """Test property set command."""
        with patch("confluence_assistant_skills.cli.commands.property_cmds.get_confluence_client") as mock:
            client = MagicMock()
            mock.return_value = client
            # Mock get - first call gets page, second could be property check
            client.get.return_value = {
                "id": "12345",
                "title": "Test Page",
                "status": "current"
            }
            client.post.return_value = {
                "key": "mykey",
                "value": "myvalue"
            }
            result = runner.invoke(cli, ["property", "set", "12345", "mykey", "--value", "myvalue"])
            assert result.exit_code == 0


class TestPermissionCommands:
    """Test permission command group."""

    def test_permission_page_get(self, runner: CliRunner) -> None:
        """Test permission page get command."""
        with patch("confluence_assistant_skills.cli.commands.permission_cmds.get_confluence_client") as mock:
            client = MagicMock()
            mock.return_value = client
            client.get.return_value = {
                "results": [],
                "_links": {}
            }
            result = runner.invoke(cli, ["permission", "page", "get", "12345"])
            assert result.exit_code == 0
            client.get.assert_called()

    def test_permission_space_get(self, runner: CliRunner) -> None:
        """Test permission space get command."""
        with patch("confluence_assistant_skills.cli.commands.permission_cmds.get_confluence_client") as mock:
            client = MagicMock()
            mock.return_value = client
            # Mock space lookup
            client.paginate.return_value = iter([{"id": "100", "key": "DOCS"}])
            # Mock permissions
            client.get.return_value = {
                "results": [],
                "_links": {}
            }
            result = runner.invoke(cli, ["permission", "space", "get", "DOCS"])
            assert result.exit_code == 0


class TestJiraCommands:
    """Test jira command group."""

    def test_jira_link(self, runner: CliRunner) -> None:
        """Test jira link command."""
        with patch("confluence_assistant_skills.cli.commands.jira_cmds.get_confluence_client") as mock:
            client = MagicMock()
            mock.return_value = client
            # Mock page get
            client.get.return_value = {
                "id": "12345",
                "title": "Test Page",
                "body": {"storage": {"value": "<p>Content</p>"}},
                "version": {"number": 1}
            }
            # Mock page update
            client.put.return_value = {
                "id": "12345",
                "title": "Test Page"
            }
            result = runner.invoke(cli, ["jira", "link", "12345", "PROJ-123", "--jira-url", "https://jira.example.com"])
            assert result.exit_code == 0


class TestAdminCommands:
    """Test admin command group."""

    def test_admin_help(self, runner: CliRunner) -> None:
        """Test admin help output."""
        result = runner.invoke(cli, ["admin", "--help"])
        assert result.exit_code == 0
        assert "user" in result.output
        assert "group" in result.output
        assert "space" in result.output
        assert "template" in result.output

    def test_admin_user_search(self, runner: CliRunner) -> None:
        """Test admin user search command."""
        with patch("confluence_assistant_skills.cli.commands.admin_cmds.get_confluence_client") as mock:
            client = MagicMock()
            mock.return_value = client
            client.get.return_value = {
                "results": [{"accountId": "123", "displayName": "Test User", "email": "test@example.com"}]
            }
            result = runner.invoke(cli, ["admin", "user", "search", "test"])
            assert result.exit_code == 0

    def test_admin_group_list(self, runner: CliRunner) -> None:
        """Test admin group list command."""
        with patch("confluence_assistant_skills.cli.commands.admin_cmds.get_confluence_client") as mock:
            client = MagicMock()
            mock.return_value = client
            client.get.return_value = {
                "results": [{"name": "confluence-users", "id": "group-1"}],
                "_links": {}
            }
            result = runner.invoke(cli, ["admin", "group", "list"])
            assert result.exit_code == 0

    def test_admin_template_list(self, runner: CliRunner) -> None:
        """Test admin template list command."""
        with patch("confluence_assistant_skills.cli.commands.admin_cmds.get_confluence_client") as mock:
            client = MagicMock()
            mock.return_value = client
            client.paginate.return_value = iter([{"id": "100", "key": "DOCS"}])
            client.get.return_value = {
                "results": [{"templateId": "1", "name": "Meeting Notes"}],
                "_links": {}
            }
            result = runner.invoke(cli, ["admin", "template", "list", "--space", "DOCS"])
            assert result.exit_code == 0


class TestBulkCommands:
    """Test bulk command group."""

    def test_bulk_help(self, runner: CliRunner) -> None:
        """Test bulk help output."""
        result = runner.invoke(cli, ["bulk", "--help"])
        assert result.exit_code == 0
        assert "label" in result.output
        assert "move" in result.output
        assert "delete" in result.output

    def test_bulk_label_add_dry_run(self, runner: CliRunner) -> None:
        """Test bulk label add with dry-run."""
        with patch("confluence_assistant_skills.cli.commands.bulk_cmds.get_confluence_client") as mock:
            client = MagicMock()
            mock.return_value = client
            client.paginate.return_value = iter([
                {"content": {"id": "1", "title": "Page 1"}},
                {"content": {"id": "2", "title": "Page 2"}},
            ])
            result = runner.invoke(cli, ["bulk", "label", "add", "--labels", "test-label", "--cql", "space=TEST", "--dry-run"])
            assert result.exit_code == 0
            assert "dry" in result.output.lower() or "would" in result.output.lower()

    def test_bulk_delete_dry_run(self, runner: CliRunner) -> None:
        """Test bulk delete with dry-run."""
        with patch("confluence_assistant_skills.cli.commands.bulk_cmds.get_confluence_client") as mock:
            client = MagicMock()
            mock.return_value = client
            client.paginate.return_value = iter([
                {"content": {"id": "1", "title": "Page 1"}},
            ])
            result = runner.invoke(cli, ["bulk", "delete", "--cql", "space=TEST AND label=delete-me", "--dry-run"])
            assert result.exit_code == 0


class TestOpsCommands:
    """Test ops command group."""

    def test_ops_help(self, runner: CliRunner) -> None:
        """Test ops help output."""
        result = runner.invoke(cli, ["ops", "--help"])
        assert result.exit_code == 0
        assert "cache" in result.output
        assert "health" in result.output

    def test_ops_cache_status(self, runner: CliRunner) -> None:
        """Test ops cache-status command."""
        result = runner.invoke(cli, ["ops", "cache-status"])
        assert result.exit_code == 0
        # Should output cache statistics
        assert "cache" in result.output.lower() or "status" in result.output.lower()

    def test_ops_health_check(self, runner: CliRunner) -> None:
        """Test ops health-check command."""
        with patch("confluence_assistant_skills.cli.commands.ops_cmds.get_confluence_client") as mock:
            client = MagicMock()
            mock.return_value = client
            client.get.return_value = {"accountId": "123", "displayName": "Test User"}
            result = runner.invoke(cli, ["ops", "health-check"])
            assert result.exit_code == 0


class TestGlobalOptions:
    """Test global CLI options."""

    def test_output_option(self, runner: CliRunner) -> None:
        """Test --output global option."""
        with patch("confluence_assistant_skills.cli.commands.space_cmds.get_confluence_client") as mock:
            client = MagicMock()
            mock.return_value = client
            client.paginate.return_value = iter([])
            result = runner.invoke(cli, ["--output", "json", "space", "list"])
            assert result.exit_code == 0


class TestErrorHandling:
    """Test CLI error handling."""

    def test_api_error_handling(self, runner: CliRunner) -> None:
        """Test that API errors are handled gracefully."""
        with patch("confluence_assistant_skills.cli.commands.page_cmds.get_confluence_client") as mock:
            client = MagicMock()
            mock.return_value = client
            from confluence_assistant_skills_lib import NotFoundError
            client.get.side_effect = NotFoundError("Page not found")
            result = runner.invoke(cli, ["page", "get", "99999"])
            assert result.exit_code != 0
            assert "not found" in result.output.lower() or "error" in result.output.lower()

    def test_missing_required_argument(self, runner: CliRunner) -> None:
        """Test missing required argument."""
        result = runner.invoke(cli, ["page", "get"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "Error" in result.output
