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
@click.option(
    "--sort",
    type=click.Choice(["title", "id", "created"]),
    help="Sort children by field",
)
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def get_children(
    ctx: click.Context,
    page_id: str,
    limit: int,
    sort: str | None,
    profile: str | None,
    output: str,
) -> None:
    """Get child pages of a page."""
    argv = [page_id]
    if limit != 25:
        argv.extend(["--limit", str(limit)])
    if sort:
        argv.extend(["--sort", sort])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-hierarchy", "get_children", argv))


@hierarchy.command(name="ancestors")
@click.argument("page_id")
@click.option("--breadcrumb", is_flag=True, help="Show as breadcrumb path")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def get_ancestors(
    ctx: click.Context,
    page_id: str,
    breadcrumb: bool,
    profile: str | None,
    output: str,
) -> None:
    """Get ancestor pages (parents, grandparents, etc.)."""
    argv = [page_id]
    if breadcrumb:
        argv.append("--breadcrumb")
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-hierarchy", "get_ancestors", argv))


@hierarchy.command(name="descendants")
@click.argument("page_id")
@click.option("--max-depth", "-d", type=int, help="Maximum depth to traverse")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def get_descendants(
    ctx: click.Context,
    page_id: str,
    max_depth: int | None,
    profile: str | None,
    output: str,
) -> None:
    """Get all descendant pages."""
    argv = [page_id]
    if max_depth:
        argv.extend(["--max-depth", str(max_depth)])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-hierarchy", "get_descendants", argv))


@hierarchy.command(name="tree")
@click.argument("page_id")
@click.option(
    "--max-depth", "-d", type=int, help="Maximum depth to traverse (default: unlimited)"
)
@click.option("--stats", is_flag=True, help="Show tree statistics")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def get_page_tree(
    ctx: click.Context,
    page_id: str,
    max_depth: int | None,
    stats: bool,
    profile: str | None,
    output: str,
) -> None:
    """Display page tree structure."""
    argv = [page_id]
    if max_depth:
        argv.extend(["--max-depth", str(max_depth)])
    if stats:
        argv.append("--stats")
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-hierarchy", "get_page_tree", argv))


@hierarchy.command(name="reorder")
@click.argument("parent_id")
@click.argument("order", required=False)
@click.option("--reverse", is_flag=True, help="Reverse current order")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.pass_context
def reorder_children(
    ctx: click.Context,
    parent_id: str,
    order: str | None,
    reverse: bool,
    profile: str | None,
) -> None:
    """Reorder child pages under a parent."""
    argv = [parent_id]
    if order:
        argv.append(order)
    if reverse:
        argv.append("--reverse")
    if profile:
        argv.extend(["--profile", profile])

    ctx.exit(call_skill_main("confluence-hierarchy", "reorder_children", argv))
