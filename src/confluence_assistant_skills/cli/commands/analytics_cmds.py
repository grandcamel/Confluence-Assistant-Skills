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
@click.option("--from-date", help="Start date (YYYY-MM-DD)")
@click.option("--to-date", help="End date (YYYY-MM-DD)")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def get_page_views(
    ctx: click.Context,
    page_id: str,
    from_date: str | None,
    to_date: str | None,
    profile: str | None,
    output: str,
) -> None:
    """Get view statistics for a page."""
    argv = [page_id]
    if from_date:
        argv.extend(["--from-date", from_date])
    if to_date:
        argv.extend(["--to-date", to_date])
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
@click.option("--type", "content_type", help="Content type (page, blogpost)")
@click.option("--limit", "-l", type=int, default=25, help="Maximum results")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def get_popular_content(
    ctx: click.Context,
    space: str | None,
    content_type: str | None,
    limit: int,
    profile: str | None,
    output: str,
) -> None:
    """Get popular content."""
    argv = []
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

    ctx.exit(call_skill_main("confluence-analytics", "get_popular_content", argv))


@analytics.command(name="space")
@click.argument("space_key")
@click.option("--from-date", help="Start date (YYYY-MM-DD)")
@click.option("--to-date", help="End date (YYYY-MM-DD)")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def get_space_analytics(
    ctx: click.Context,
    space_key: str,
    from_date: str | None,
    to_date: str | None,
    profile: str | None,
    output: str,
) -> None:
    """Get analytics for a space."""
    argv = [space_key]
    if from_date:
        argv.extend(["--from-date", from_date])
    if to_date:
        argv.extend(["--to-date", to_date])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-analytics", "get_space_analytics", argv))
