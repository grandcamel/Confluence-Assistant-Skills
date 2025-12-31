"""Label management commands."""

from __future__ import annotations

import click

from confluence_assistant_skills.utils import call_skill_main


@click.group()
def label() -> None:
    """Manage content labels."""
    pass


@label.command(name="list")
@click.argument("page_id")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def get_labels(
    ctx: click.Context,
    page_id: str,
    profile: str | None,
    output: str,
) -> None:
    """List labels on a page."""
    argv = [page_id]
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-label", "get_labels", argv))


@label.command(name="add")
@click.argument("page_id")
@click.argument("labels", nargs=-1, required=True)
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def add_label(
    ctx: click.Context,
    page_id: str,
    labels: tuple[str, ...],
    profile: str | None,
    output: str,
) -> None:
    """Add labels to a page."""
    argv = [page_id] + list(labels)
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-label", "add_label", argv))


@label.command(name="remove")
@click.argument("page_id")
@click.argument("labels", nargs=-1, required=True)
@click.option("--profile", "-p", help="Confluence profile to use")
@click.pass_context
def remove_label(
    ctx: click.Context,
    page_id: str,
    labels: tuple[str, ...],
    profile: str | None,
) -> None:
    """Remove labels from a page."""
    argv = [page_id] + list(labels)
    if profile:
        argv.extend(["--profile", profile])

    ctx.exit(call_skill_main("confluence-label", "remove_label", argv))


@label.command(name="search")
@click.argument("label")
@click.option("--space", "-s", help="Limit to specific space")
@click.option("--type", "content_type", help="Content type (page, blogpost)")
@click.option("--limit", "-l", type=int, default=25, help="Maximum results")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def search_by_label(
    ctx: click.Context,
    label: str,
    space: str | None,
    content_type: str | None,
    limit: int,
    profile: str | None,
    output: str,
) -> None:
    """Search content by label."""
    argv = [label]
    if space:
        argv.extend(["--space", space])
    if content_type:
        argv.extend(["--type", content_type])
    if limit != 25:
        argv.extend(["--limit", str(limit)])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-label", "search_by_label", argv))


@label.command(name="popular")
@click.option("--space", "-s", help="Limit to specific space")
@click.option("--limit", "-l", type=int, default=25, help="Maximum labels to return")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def list_popular_labels(
    ctx: click.Context,
    space: str | None,
    limit: int,
    profile: str | None,
    output: str,
) -> None:
    """List popular labels."""
    argv = []
    if space:
        argv.extend(["--space", space])
    if limit != 25:
        argv.extend(["--limit", str(limit)])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-label", "list_popular_labels", argv))
