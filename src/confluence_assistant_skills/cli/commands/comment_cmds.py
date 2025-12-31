"""Comment management commands."""

from __future__ import annotations

import click

from confluence_assistant_skills.utils import call_skill_main


@click.group()
def comment() -> None:
    """Manage page comments."""
    pass


@comment.command(name="list")
@click.argument("page_id")
@click.option("--include-inline", is_flag=True, help="Include inline comments")
@click.option("--limit", "-l", type=int, default=25, help="Maximum comments to return")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def get_comments(
    ctx: click.Context,
    page_id: str,
    include_inline: bool,
    limit: int,
    profile: str | None,
    output: str,
) -> None:
    """List comments on a page."""
    argv = [page_id]
    if include_inline:
        argv.append("--include-inline")
    if limit != 25:
        argv.extend(["--limit", str(limit)])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-comment", "get_comments", argv))


@comment.command(name="add")
@click.argument("page_id")
@click.argument("body")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def add_comment(
    ctx: click.Context,
    page_id: str,
    body: str,
    profile: str | None,
    output: str,
) -> None:
    """Add a comment to a page."""
    argv = [page_id, body]
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-comment", "add_comment", argv))


@comment.command(name="add-inline")
@click.argument("page_id")
@click.argument("body")
@click.option("--selection-start", type=int, required=True, help="Selection start position")
@click.option("--selection-end", type=int, required=True, help="Selection end position")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def add_inline_comment(
    ctx: click.Context,
    page_id: str,
    body: str,
    selection_start: int,
    selection_end: int,
    profile: str | None,
    output: str,
) -> None:
    """Add an inline comment to a page."""
    argv = [page_id, body]
    argv.extend(["--selection-start", str(selection_start)])
    argv.extend(["--selection-end", str(selection_end)])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-comment", "add_inline_comment", argv))


@comment.command(name="update")
@click.argument("comment_id")
@click.argument("body")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def update_comment(
    ctx: click.Context,
    comment_id: str,
    body: str,
    profile: str | None,
    output: str,
) -> None:
    """Update an existing comment."""
    argv = [comment_id, body]
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-comment", "update_comment", argv))


@comment.command(name="delete")
@click.argument("comment_id")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.pass_context
def delete_comment(
    ctx: click.Context,
    comment_id: str,
    confirm: bool,
    profile: str | None,
) -> None:
    """Delete a comment."""
    argv = [comment_id]
    if confirm:
        argv.append("--confirm")
    if profile:
        argv.extend(["--profile", profile])

    ctx.exit(call_skill_main("confluence-comment", "delete_comment", argv))


@comment.command(name="resolve")
@click.argument("comment_id")
@click.option("--reopen", is_flag=True, help="Reopen a resolved comment")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def resolve_comment(
    ctx: click.Context,
    comment_id: str,
    reopen: bool,
    profile: str | None,
    output: str,
) -> None:
    """Resolve or reopen a comment."""
    argv = [comment_id]
    if reopen:
        argv.append("--reopen")
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-comment", "resolve_comment", argv))
