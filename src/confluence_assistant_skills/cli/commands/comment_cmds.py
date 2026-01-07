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
@click.option("--limit", "-l", type=int, help="Maximum comments to return")
@click.option(
    "--sort",
    "-s",
    type=click.Choice(["created", "-created"]),
    default="-created",
    help="Sort order (default: -created for newest first)",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def get_comments(
    ctx: click.Context,
    page_id: str,
    limit: int | None,
    sort: str,
    output: str,
) -> None:
    """List comments on a page."""
    argv = [page_id]
    if limit is not None:
        argv.extend(["--limit", str(limit)])
    if sort != "-created":
        argv.extend(["--sort", sort])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-comment", "get_comments", argv))


@comment.command(name="add")
@click.argument("page_id")
@click.argument("body", required=False)
@click.option(
    "--file", "-f", type=click.Path(exists=True), help="Read comment body from file"
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def add_comment(
    ctx: click.Context,
    page_id: str,
    body: str | None,
    file: str | None,
    output: str,
) -> None:
    """Add a comment to a page."""
    if not body and not file:
        raise click.UsageError("Either BODY argument or --file option is required")
    if body and file:
        raise click.UsageError("Cannot specify both BODY argument and --file option")

    argv = [page_id]
    if file:
        argv.extend(["--file", file])
    else:
        argv.append(body)
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-comment", "add_comment", argv))


@comment.command(name="add-inline")
@click.argument("page_id")
@click.argument("selection")
@click.argument("body")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def add_inline_comment(
    ctx: click.Context,
    page_id: str,
    selection: str,
    body: str,
    output: str,
) -> None:
    """Add an inline comment to specific text in a page."""
    argv = [page_id, selection, body]
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-comment", "add_inline_comment", argv))


@comment.command(name="update")
@click.argument("comment_id")
@click.argument("body", required=False)
@click.option(
    "--file", "-f", type=click.Path(exists=True), help="Read updated body from file"
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def update_comment(
    ctx: click.Context,
    comment_id: str,
    body: str | None,
    file: str | None,
    output: str,
) -> None:
    """Update an existing comment."""
    if not body and not file:
        raise click.UsageError("Either BODY argument or --file option is required")
    if body and file:
        raise click.UsageError("Cannot specify both BODY argument and --file option")

    argv = [comment_id]
    if file:
        argv.extend(["--file", file])
    else:
        argv.append(body)
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-comment", "update_comment", argv))


@comment.command(name="delete")
@click.argument("comment_id")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def delete_comment(
    ctx: click.Context,
    comment_id: str,
    force: bool,
) -> None:
    """Delete a comment."""
    argv = [comment_id]
    if force:
        argv.append("--force")

    ctx.exit(call_skill_main("confluence-comment", "delete_comment", argv))


@comment.command(name="resolve")
@click.argument("comment_id")
@click.option(
    "--resolve", "-r", "action", flag_value="resolve", help="Mark comment as resolved"
)
@click.option(
    "--unresolve",
    "-u",
    "action",
    flag_value="unresolve",
    help="Mark comment as unresolved/open",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def resolve_comment(
    ctx: click.Context,
    comment_id: str,
    action: str | None,
    output: str,
) -> None:
    """Resolve or reopen a comment."""
    if action is None:
        raise click.UsageError("One of --resolve or --unresolve is required")

    argv = [comment_id]
    if action == "resolve":
        argv.append("--resolve")
    else:
        argv.append("--unresolve")
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-comment", "resolve_comment", argv))
