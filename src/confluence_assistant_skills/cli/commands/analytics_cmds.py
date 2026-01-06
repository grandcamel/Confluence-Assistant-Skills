"""Analytics commands."""

from __future__ import annotations

import click

from confluence_assistant_skills.utils import call_skill_main


@click.group()
def analytics() -> None:
    """View content analytics."""
    pass


@analytics.command(name="views")
@click.argument("page_id")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def get_page_views(
    ctx: click.Context,
    page_id: str,
    profile: str | None,
    output: str,
) -> None:
    """Get view statistics for a page."""
    argv = [page_id]
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-analytics", "get_page_views", argv))


@analytics.command(name="watchers")
@click.argument("page_id")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def get_content_watchers(
    ctx: click.Context,
    page_id: str,
    profile: str | None,
    output: str,
) -> None:
    """Get users watching a page."""
    argv = [page_id]
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-analytics", "get_content_watchers", argv))


@analytics.command(name="popular")
@click.option("--space", "-s", help="Limit to specific space")
@click.option("--label", help="Filter by label")
@click.option("--type", "content_type", type=click.Choice(["page", "blogpost", "all"]), default="all", help="Content type (default: all)")
@click.option("--sort", type=click.Choice(["created", "modified"]), default="modified", help="Sort by created or modified date (default: modified)")
@click.option("--limit", "-l", type=int, default=10, help="Maximum results (default: 10)")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def get_popular_content(
    ctx: click.Context,
    space: str | None,
    label: str | None,
    content_type: str,
    sort: str,
    limit: int,
    profile: str | None,
    output: str,
) -> None:
    """Get popular content."""
    argv = []
    if space:
        argv.extend(["--space", space])
    if label:
        argv.extend(["--label", label])
    if content_type != "all":
        argv.extend(["--type", content_type])
    if sort != "modified":
        argv.extend(["--sort", sort])
    if limit != 10:
        argv.extend(["--limit", str(limit)])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-analytics", "get_popular_content", argv))


@analytics.command(name="space")
@click.argument("space_key")
@click.option("--days", type=int, help="Limit to content from last N days")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def get_space_analytics(
    ctx: click.Context,
    space_key: str,
    days: int | None,
    profile: str | None,
    output: str,
) -> None:
    """Get analytics for a space."""
    argv = [space_key]
    if days:
        argv.extend(["--days", str(days)])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-analytics", "get_space_analytics", argv))
