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
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def link_to_jira(
    ctx: click.Context,
    page_id: str,
    issue_key: str,
    profile: str | None,
    output: str,
) -> None:
    """Link a Confluence page to a JIRA issue."""
    argv = [page_id, issue_key]
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-jira", "link_to_jira", argv))


@jira.command(name="linked")
@click.argument("page_id")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
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
@click.argument("jql")
@click.option("--columns", help="Columns to display (comma-separated)")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def embed_jira_issues(
    ctx: click.Context,
    page_id: str,
    jql: str,
    columns: str | None,
    profile: str | None,
    output: str,
) -> None:
    """Embed JIRA issues in a page using JQL."""
    argv = [page_id, jql]
    if columns:
        argv.extend(["--columns", columns])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-jira", "embed_jira_issues", argv))


@jira.command(name="create-from-page")
@click.argument("page_id")
@click.option("--project", "-p", required=True, help="JIRA project key")
@click.option("--issue-type", default="Task", help="Issue type (default: Task)")
@click.option("--summary", help="Issue summary (default: page title)")
@click.option("--profile", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def create_jira_from_page(
    ctx: click.Context,
    page_id: str,
    project: str,
    issue_type: str,
    summary: str | None,
    profile: str | None,
    output: str,
) -> None:
    """Create a JIRA issue from a Confluence page."""
    argv = [page_id, "--project", project]
    if issue_type != "Task":
        argv.extend(["--issue-type", issue_type])
    if summary:
        argv.extend(["--summary", summary])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-jira", "create_jira_from_page", argv))


@jira.command(name="sync-macro")
@click.argument("page_id")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def sync_jira_macro(
    ctx: click.Context,
    page_id: str,
    profile: str | None,
    output: str,
) -> None:
    """Refresh JIRA macros on a page."""
    argv = [page_id]
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-jira", "sync_jira_macro", argv))
