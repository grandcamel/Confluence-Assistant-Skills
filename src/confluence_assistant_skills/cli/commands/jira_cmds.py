"""JIRA integration commands."""

from __future__ import annotations

import click

from confluence_assistant_skills.utils import call_skill_main


@click.group()
def jira() -> None:
    """JIRA integration commands."""
    pass


@jira.command(name="link")
@click.argument("page_id")
@click.argument("issue_key")
@click.option(
    "--jira-url", required=True, help="Base JIRA URL (e.g., https://jira.example.com)"
)
@click.option(
    "--relationship",
    default="relates to",
    help="Relationship type (default: relates to)",
)
@click.option("--skip-if-exists", is_flag=True, help="Skip if link already exists")
@click.option("--profile", help="Confluence profile to use")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def link_to_jira(
    ctx: click.Context,
    page_id: str,
    issue_key: str,
    jira_url: str,
    relationship: str,
    skip_if_exists: bool,
    profile: str | None,
    output: str,
) -> None:
    """Link a Confluence page to a JIRA issue."""
    argv = [page_id, issue_key]
    argv.extend(["--jira-url", jira_url])
    if relationship != "relates to":
        argv.extend(["--relationship", relationship])
    if skip_if_exists:
        argv.append("--skip-if-exists")
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-jira", "link_to_jira", argv))


@jira.command(name="linked")
@click.argument("page_id")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def get_linked_issues(
    ctx: click.Context,
    page_id: str,
    profile: str | None,
    output: str,
) -> None:
    """Get JIRA issues linked to a page."""
    argv = [page_id]
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-jira", "get_linked_issues", argv))


@jira.command(name="embed")
@click.argument("page_id")
@click.option("--jql", help="JQL query to filter issues")
@click.option(
    "--issues", help="Comma-separated list of issue keys (e.g., PROJ-123,PROJ-456)"
)
@click.option(
    "--mode",
    type=click.Choice(["append", "replace"]),
    default="append",
    help="How to add the macro (default: append)",
)
@click.option("--server-id", help="JIRA server ID (optional)")
@click.option("--columns", help="Columns to display (comma-separated)")
@click.option(
    "--max-results", type=int, default=20, help="Maximum number of issues (default: 20)"
)
@click.option("--profile", help="Confluence profile to use")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def embed_jira_issues(
    ctx: click.Context,
    page_id: str,
    jql: str | None,
    issues: str | None,
    mode: str,
    server_id: str | None,
    columns: str | None,
    max_results: int,
    profile: str | None,
    output: str,
) -> None:
    """Embed JIRA issues in a page using JQL or issue keys.

    Either --jql or --issues must be provided.
    """
    # Validate that at least one of --jql or --issues is provided
    if not jql and not issues:
        raise click.UsageError("Either --jql or --issues must be provided")

    argv = [page_id]
    if jql:
        argv.extend(["--jql", jql])
    if issues:
        argv.extend(["--issues", issues])
    if mode != "append":
        argv.extend(["--mode", mode])
    if server_id:
        argv.extend(["--server-id", server_id])
    if columns:
        argv.extend(["--columns", columns])
    if max_results != 20:
        argv.extend(["--max-results", str(max_results)])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-jira", "embed_jira_issues", argv))


@jira.command(name="create-from-page")
@click.argument("page_id")
@click.option("--project", "-p", required=True, help="JIRA project key")
@click.option(
    "--type", "-t", "issue_type", default="Task", help="Issue type (default: Task)"
)
@click.option("--priority", help="Priority (e.g., High, Medium, Low)")
@click.option("--assignee", help="Assignee username")
@click.option("--jira-url", help="JIRA base URL (or set JIRA_URL env var)")
@click.option("--jira-email", help="JIRA email (or set JIRA_EMAIL env var)")
@click.option("--jira-token", help="JIRA API token (or set JIRA_API_TOKEN env var)")
@click.option("--profile", help="Confluence profile to use")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def create_jira_from_page(
    ctx: click.Context,
    page_id: str,
    project: str,
    issue_type: str,
    priority: str | None,
    assignee: str | None,
    jira_url: str | None,
    jira_email: str | None,
    jira_token: str | None,
    profile: str | None,
    output: str,
) -> None:
    """Create a JIRA issue from a Confluence page.

    Requires JIRA credentials via options or environment variables
    (JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN).
    """
    argv = [page_id, "--project", project]
    if issue_type != "Task":
        argv.extend(["--type", issue_type])
    if priority:
        argv.extend(["--priority", priority])
    if assignee:
        argv.extend(["--assignee", assignee])
    if jira_url:
        argv.extend(["--jira-url", jira_url])
    if jira_email:
        argv.extend(["--jira-email", jira_email])
    if jira_token:
        argv.extend(["--jira-token", jira_token])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-jira", "create_jira_from_page", argv))


@jira.command(name="sync-macro")
@click.argument("page_id")
@click.option("--update-jql", help="Update JQL query in macros")
@click.option(
    "--macro-index", type=int, help="Index of macro to update (0-based, default: all)"
)
@click.option("--profile", help="Confluence profile to use")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def sync_jira_macro(
    ctx: click.Context,
    page_id: str,
    update_jql: str | None,
    macro_index: int | None,
    profile: str | None,
    output: str,
) -> None:
    """Refresh JIRA macros on a page.

    Force a page update to trigger macro refresh, or update macro JQL queries.
    """
    argv = [page_id]
    if update_jql:
        argv.extend(["--update-jql", update_jql])
    if macro_index is not None:
        argv.extend(["--macro-index", str(macro_index)])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-jira", "sync_jira_macro", argv))
