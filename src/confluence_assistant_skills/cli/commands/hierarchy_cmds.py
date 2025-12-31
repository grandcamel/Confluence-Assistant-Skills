"""Hierarchy management commands."""

from __future__ import annotations

import click

from confluence_assistant_skills.utils import call_skill_main


@click.group()
def hierarchy() -> None:
    """Navigate content hierarchy."""
    pass


@hierarchy.command(name="children")
@click.argument("page_id")
@click.option("--limit", "-l", type=int, default=25, help="Maximum children to return")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def get_children(
    ctx: click.Context,
    page_id: str,
    limit: int,
    profile: str | None,
    output: str,
) -> None:
    """Get child pages of a page."""
    argv = [page_id]
    if limit != 25:
        argv.extend(["--limit", str(limit)])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-hierarchy", "get_children", argv))


@hierarchy.command(name="ancestors")
@click.argument("page_id")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def get_ancestors(
    ctx: click.Context,
    page_id: str,
    profile: str | None,
    output: str,
) -> None:
    """Get ancestor pages (parents, grandparents, etc.)."""
    argv = [page_id]
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-hierarchy", "get_ancestors", argv))


@hierarchy.command(name="descendants")
@click.argument("page_id")
@click.option("--depth", type=int, help="Maximum depth to traverse")
@click.option("--limit", "-l", type=int, default=100, help="Maximum descendants to return")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def get_descendants(
    ctx: click.Context,
    page_id: str,
    depth: int | None,
    limit: int,
    profile: str | None,
    output: str,
) -> None:
    """Get all descendant pages."""
    argv = [page_id]
    if depth:
        argv.extend(["--depth", str(depth)])
    if limit != 100:
        argv.extend(["--limit", str(limit)])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-hierarchy", "get_descendants", argv))


@hierarchy.command(name="tree")
@click.argument("page_id")
@click.option("--depth", type=int, default=3, help="Tree depth to display")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def get_page_tree(
    ctx: click.Context,
    page_id: str,
    depth: int,
    profile: str | None,
    output: str,
) -> None:
    """Display page tree structure."""
    argv = [page_id]
    if depth != 3:
        argv.extend(["--depth", str(depth)])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-hierarchy", "get_page_tree", argv))


@hierarchy.command(name="reorder")
@click.argument("parent_id")
@click.argument("child_ids", nargs=-1, required=True)
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def reorder_children(
    ctx: click.Context,
    parent_id: str,
    child_ids: tuple[str, ...],
    profile: str | None,
    output: str,
) -> None:
    """Reorder child pages under a parent."""
    argv = [parent_id] + list(child_ids)
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-hierarchy", "reorder_children", argv))
