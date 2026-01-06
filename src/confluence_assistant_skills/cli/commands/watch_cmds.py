"""Watch/notification commands."""

from __future__ import annotations

import click

from confluence_assistant_skills.utils import call_skill_main


@click.group()
def watch() -> None:
    """Manage content watching and notifications."""
    pass


@watch.command(name="page")
@click.argument("page_id")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def watch_page(
    ctx: click.Context,
    page_id: str,
    profile: str | None,
    output: str,
) -> None:
    """Start watching a page."""
    argv = [page_id]
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-watch", "watch_page", argv))


@watch.command(name="unwatch-page")
@click.argument("page_id")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def unwatch_page(
    ctx: click.Context,
    page_id: str,
    profile: str | None,
    output: str,
) -> None:
    """Stop watching a page."""
    argv = [page_id]
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-watch", "unwatch_page", argv))


@watch.command(name="space")
@click.argument("space_key")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def watch_space(
    ctx: click.Context,
    space_key: str,
    profile: str | None,
    output: str,
) -> None:
    """Start watching a space."""
    argv = [space_key]
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-watch", "watch_space", argv))


@watch.command(name="status")
@click.argument("page_id")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def am_i_watching(
    ctx: click.Context,
    page_id: str,
    profile: str | None,
    output: str,
) -> None:
    """Check if you're watching a page."""
    argv = [page_id]
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-watch", "am_i_watching", argv))


@watch.command(name="list")
@click.argument("page_id")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def get_watchers(
    ctx: click.Context,
    page_id: str,
    profile: str | None,
    output: str,
) -> None:
    """List watchers of a page."""
    argv = [page_id]
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-watch", "get_watchers", argv))
