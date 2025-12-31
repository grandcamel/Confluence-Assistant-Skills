"""Content property commands."""

from __future__ import annotations

import click

from confluence_assistant_skills.utils import call_skill_main


@click.group(name="property")
def property_cmd() -> None:
    """Manage content properties (custom metadata)."""
    pass


@property_cmd.command(name="list")
@click.argument("page_id")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def list_properties(
    ctx: click.Context,
    page_id: str,
    profile: str | None,
    output: str,
) -> None:
    """List all properties on a page."""
    argv = [page_id]
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-property", "list_properties", argv))


@property_cmd.command(name="get")
@click.argument("page_id")
@click.argument("key")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def get_properties(
    ctx: click.Context,
    page_id: str,
    key: str,
    profile: str | None,
    output: str,
) -> None:
    """Get a specific property value."""
    argv = [page_id, key]
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-property", "get_properties", argv))


@property_cmd.command(name="set")
@click.argument("page_id")
@click.argument("key")
@click.argument("value")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def set_property(
    ctx: click.Context,
    page_id: str,
    key: str,
    value: str,
    profile: str | None,
    output: str,
) -> None:
    """Set a property value."""
    argv = [page_id, key, value]
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-property", "set_property", argv))


@property_cmd.command(name="delete")
@click.argument("page_id")
@click.argument("key")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.pass_context
def delete_property(
    ctx: click.Context,
    page_id: str,
    key: str,
    confirm: bool,
    profile: str | None,
) -> None:
    """Delete a property."""
    argv = [page_id, key]
    if confirm:
        argv.append("--confirm")
    if profile:
        argv.extend(["--profile", profile])

    ctx.exit(call_skill_main("confluence-property", "delete_property", argv))
