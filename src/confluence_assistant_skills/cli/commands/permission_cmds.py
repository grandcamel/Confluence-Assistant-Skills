"""Permission management commands."""

from __future__ import annotations

import click

from confluence_assistant_skills.utils import call_skill_main


@click.group()
def permission() -> None:
    """Manage permissions and restrictions."""
    pass


# Page restrictions
@permission.group(name="page")
def page_permission() -> None:
    """Manage page restrictions."""
    pass


@page_permission.command(name="get")
@click.argument("page_id")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def get_page_restrictions(
    ctx: click.Context,
    page_id: str,
    profile: str | None,
    output: str,
) -> None:
    """Get restrictions on a page."""
    argv = [page_id]
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-permission", "get_page_restrictions", argv))


@page_permission.command(name="add")
@click.argument("page_id")
@click.option("--user", help="User to restrict")
@click.option("--group", "group_name", help="Group to restrict")
@click.option(
    "--operation",
    type=click.Choice(["read", "update"]),
    required=True,
    help="Operation to restrict",
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
def add_page_restriction(
    ctx: click.Context,
    page_id: str,
    user: str | None,
    group_name: str | None,
    operation: str,
    profile: str | None,
    output: str,
) -> None:
    """Add a restriction to a page."""
    argv = [page_id, "--operation", operation]
    if user:
        argv.extend(["--user", user])
    if group_name:
        argv.extend(["--group", group_name])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-permission", "add_page_restriction", argv))


@page_permission.command(name="remove")
@click.argument("page_id")
@click.option("--user", help="User restriction to remove")
@click.option("--group", "group_name", help="Group restriction to remove")
@click.option(
    "--operation",
    type=click.Choice(["read", "update"]),
    required=True,
    help="Operation restriction to remove",
)
@click.option(
    "--all", "remove_all", is_flag=True, help="Remove all restrictions of this type"
)
@click.option("--profile", "-p", help="Confluence profile to use")
@click.pass_context
def remove_page_restriction(
    ctx: click.Context,
    page_id: str,
    user: str | None,
    group_name: str | None,
    operation: str,
    remove_all: bool,
    profile: str | None,
) -> None:
    """Remove a restriction from a page."""
    argv = [page_id, "--operation", operation]
    if user:
        argv.extend(["--user", user])
    if group_name:
        argv.extend(["--group", group_name])
    if remove_all:
        argv.append("--all")
    if profile:
        argv.extend(["--profile", profile])

    ctx.exit(call_skill_main("confluence-permission", "remove_page_restriction", argv))


# Space permissions
@permission.group(name="space")
def space_permission() -> None:
    """Manage space permissions."""
    pass


@space_permission.command(name="get")
@click.argument("space_key")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def get_space_permissions(
    ctx: click.Context,
    space_key: str,
    profile: str | None,
    output: str,
) -> None:
    """Get permissions for a space."""
    argv = [space_key]
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-permission", "get_space_permissions", argv))


@space_permission.command(name="add")
@click.argument("space_key")
@click.option("--user", help="User to grant permission")
@click.option("--group", "group_name", help="Group to grant permission")
@click.option(
    "--operation",
    required=True,
    help="Permission operation (read, write, administer, etc.)",
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
def add_space_permission(
    ctx: click.Context,
    space_key: str,
    user: str | None,
    group_name: str | None,
    operation: str,
    profile: str | None,
    output: str,
) -> None:
    """Add a permission to a space."""
    argv = [space_key, "--operation", operation]
    if user:
        argv.extend(["--user", user])
    if group_name:
        argv.extend(["--group", group_name])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-permission", "add_space_permission", argv))


@space_permission.command(name="remove")
@click.argument("space_key")
@click.option("--user", help="User permission to remove")
@click.option("--group", "group_name", help="Group permission to remove")
@click.option(
    "--operation",
    required=True,
    help="Permission operation to remove",
)
@click.option("--profile", "-p", help="Confluence profile to use")
@click.pass_context
def remove_space_permission(
    ctx: click.Context,
    space_key: str,
    user: str | None,
    group_name: str | None,
    operation: str,
    profile: str | None,
) -> None:
    """Remove a permission from a space."""
    argv = [space_key, "--operation", operation]
    if user:
        argv.extend(["--user", user])
    if group_name:
        argv.extend(["--group", group_name])
    if profile:
        argv.extend(["--profile", profile])

    ctx.exit(call_skill_main("confluence-permission", "remove_space_permission", argv))
