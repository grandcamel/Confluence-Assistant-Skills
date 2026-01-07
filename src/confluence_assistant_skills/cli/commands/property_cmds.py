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
@click.option("--prefix", help="Filter properties by key prefix")
@click.option("--pattern", help="Filter properties by regex pattern")
@click.option(
    "--sort",
    type=click.Choice(["key", "version"]),
    default="key",
    help="Sort properties by field",
)
@click.option("--expand", help="Comma-separated fields to expand (e.g., version)")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def list_properties(
    ctx: click.Context,
    page_id: str,
    prefix: str | None,
    pattern: str | None,
    sort: str,
    expand: str | None,
    verbose: bool,
    output: str,
) -> None:
    """List all properties on a page."""
    argv = [page_id]
    if prefix:
        argv.extend(["--prefix", prefix])
    if pattern:
        argv.extend(["--pattern", pattern])
    if sort != "key":
        argv.extend(["--sort", sort])
    if expand:
        argv.extend(["--expand", expand])
    if verbose:
        argv.append("--verbose")
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-property", "list_properties", argv))


@property_cmd.command(name="get")
@click.argument("page_id")
@click.option("--key", "-k", help="Specific property key to retrieve")
@click.option("--expand", help="Comma-separated fields to expand (e.g., version)")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def get_properties(
    ctx: click.Context,
    page_id: str,
    key: str | None,
    expand: str | None,
    output: str,
) -> None:
    """Get properties from a page. Optionally filter by key."""
    argv = [page_id]
    if key:
        argv.extend(["--key", key])
    if expand:
        argv.extend(["--expand", expand])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-property", "get_properties", argv))


@property_cmd.command(name="set")
@click.argument("page_id")
@click.argument("key")
@click.option("--value", "-v", help="Property value (string or JSON)")
@click.option("--file", "-f", "file_path", help="Read value from JSON file")
@click.option(
    "--update", is_flag=True, help="Update existing property (fetches current version)"
)
@click.option("--version", type=int, help="Explicit version number for update")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def set_property(
    ctx: click.Context,
    page_id: str,
    key: str,
    value: str | None,
    file_path: str | None,
    update: bool,
    version: int | None,
    output: str,
) -> None:
    """Set a property value."""
    argv = [page_id, key]
    if value:
        argv.extend(["--value", value])
    if file_path:
        argv.extend(["--file", file_path])
    if update:
        argv.append("--update")
    if version is not None:
        argv.extend(["--version", str(version)])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-property", "set_property", argv))


@property_cmd.command(name="delete")
@click.argument("page_id")
@click.argument("key")
@click.option("--force", is_flag=True, help="Delete without confirmation")
@click.pass_context
def delete_property(
    ctx: click.Context,
    page_id: str,
    key: str,
    force: bool,
) -> None:
    """Delete a property."""
    argv = [page_id, key]
    if force:
        argv.append("--force")

    ctx.exit(call_skill_main("confluence-property", "delete_property", argv))
