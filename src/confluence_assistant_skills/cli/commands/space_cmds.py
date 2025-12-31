"""Space management commands."""

from __future__ import annotations

import click

from confluence_assistant_skills.utils import call_skill_main


@click.group()
def space() -> None:
    """Manage Confluence spaces."""
    pass


@space.command(name="list")
@click.option("--type", "space_type", help="Filter by space type (global, personal)")
@click.option("--status", help="Filter by status (current, archived)")
@click.option("--limit", "-l", type=int, default=25, help="Maximum spaces to return")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def list_spaces(
    ctx: click.Context,
    space_type: str | None,
    status: str | None,
    limit: int,
    profile: str | None,
    output: str,
) -> None:
    """List all accessible Confluence spaces."""
    argv = []
    if space_type:
        argv.extend(["--type", space_type])
    if status:
        argv.extend(["--status", status])
    if limit != 25:
        argv.extend(["--limit", str(limit)])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-space", "list_spaces", argv))


@space.command(name="get")
@click.argument("space_key")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def get_space(
    ctx: click.Context,
    space_key: str,
    profile: str | None,
    output: str,
) -> None:
    """Get details for a specific space."""
    argv = [space_key]
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-space", "get_space", argv))


@space.command(name="create")
@click.argument("space_key")
@click.argument("name")
@click.option("--description", help="Space description")
@click.option("--type", "space_type", default="global", help="Space type (global or personal)")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def create_space(
    ctx: click.Context,
    space_key: str,
    name: str,
    description: str | None,
    space_type: str,
    profile: str | None,
    output: str,
) -> None:
    """Create a new Confluence space."""
    argv = [space_key, name]
    if description:
        argv.extend(["--description", description])
    if space_type != "global":
        argv.extend(["--type", space_type])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-space", "create_space", argv))


@space.command(name="update")
@click.argument("space_key")
@click.option("--name", help="New space name")
@click.option("--description", help="New space description")
@click.option("--homepage-id", help="New homepage page ID")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def update_space(
    ctx: click.Context,
    space_key: str,
    name: str | None,
    description: str | None,
    homepage_id: str | None,
    profile: str | None,
    output: str,
) -> None:
    """Update a Confluence space."""
    argv = [space_key]
    if name:
        argv.extend(["--name", name])
    if description:
        argv.extend(["--description", description])
    if homepage_id:
        argv.extend(["--homepage-id", homepage_id])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-space", "update_space", argv))


@space.command(name="delete")
@click.argument("space_key")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.pass_context
def delete_space(
    ctx: click.Context,
    space_key: str,
    confirm: bool,
    profile: str | None,
) -> None:
    """Delete a Confluence space."""
    argv = [space_key]
    if confirm:
        argv.append("--confirm")
    if profile:
        argv.extend(["--profile", profile])

    ctx.exit(call_skill_main("confluence-space", "delete_space", argv))


@space.command(name="content")
@click.argument("space_key")
@click.option("--type", "content_type", help="Filter by content type (page, blogpost)")
@click.option("--depth", help="Tree depth (root, all)")
@click.option("--limit", "-l", type=int, default=25, help="Maximum items to return")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def get_space_content(
    ctx: click.Context,
    space_key: str,
    content_type: str | None,
    depth: str | None,
    limit: int,
    profile: str | None,
    output: str,
) -> None:
    """Get content in a space."""
    argv = [space_key]
    if content_type:
        argv.extend(["--type", content_type])
    if depth:
        argv.extend(["--depth", depth])
    if limit != 25:
        argv.extend(["--limit", str(limit)])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-space", "get_space_content", argv))


@space.command(name="settings")
@click.argument("space_key")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def get_space_settings(
    ctx: click.Context,
    space_key: str,
    profile: str | None,
    output: str,
) -> None:
    """Get settings for a space."""
    argv = [space_key]
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-space", "get_space_settings", argv))
