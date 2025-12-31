"""Page management commands."""

from __future__ import annotations

import click

from confluence_assistant_skills.utils import call_skill_main


@click.group()
def page() -> None:
    """Manage Confluence pages and blog posts."""
    pass


@page.command(name="get")
@click.argument("page_id")
@click.option("--body", is_flag=True, help="Include body content in output")
@click.option(
    "--format",
    "body_format",
    type=click.Choice(["storage", "view", "markdown"]),
    default="storage",
    help="Body format (default: storage)",
)
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def get_page(
    ctx: click.Context,
    page_id: str,
    body: bool,
    body_format: str,
    profile: str | None,
    output: str,
) -> None:
    """Get a Confluence page by ID."""
    argv = [page_id]
    if body:
        argv.append("--body")
    if body_format != "storage":
        argv.extend(["--format", body_format])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-page", "get_page", argv))


@page.command(name="create")
@click.argument("space_key")
@click.argument("title")
@click.option("--body", help="Page body content (Markdown or XHTML)")
@click.option("--body-file", type=click.Path(exists=True), help="Read body from file")
@click.option("--parent-id", help="Parent page ID")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def create_page(
    ctx: click.Context,
    space_key: str,
    title: str,
    body: str | None,
    body_file: str | None,
    parent_id: str | None,
    profile: str | None,
    output: str,
) -> None:
    """Create a new Confluence page."""
    argv = [space_key, title]
    if body:
        argv.extend(["--body", body])
    if body_file:
        argv.extend(["--body-file", body_file])
    if parent_id:
        argv.extend(["--parent-id", parent_id])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-page", "create_page", argv))


@page.command(name="update")
@click.argument("page_id")
@click.option("--title", help="New page title")
@click.option("--body", help="New page body content")
@click.option("--body-file", type=click.Path(exists=True), help="Read body from file")
@click.option("--version-message", help="Version change message")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def update_page(
    ctx: click.Context,
    page_id: str,
    title: str | None,
    body: str | None,
    body_file: str | None,
    version_message: str | None,
    profile: str | None,
    output: str,
) -> None:
    """Update an existing Confluence page."""
    argv = [page_id]
    if title:
        argv.extend(["--title", title])
    if body:
        argv.extend(["--body", body])
    if body_file:
        argv.extend(["--body-file", body_file])
    if version_message:
        argv.extend(["--version-message", version_message])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-page", "update_page", argv))


@page.command(name="delete")
@click.argument("page_id")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.pass_context
def delete_page(
    ctx: click.Context,
    page_id: str,
    confirm: bool,
    profile: str | None,
) -> None:
    """Delete a Confluence page."""
    argv = [page_id]
    if confirm:
        argv.append("--confirm")
    if profile:
        argv.extend(["--profile", profile])

    ctx.exit(call_skill_main("confluence-page", "delete_page", argv))


@page.command(name="copy")
@click.argument("page_id")
@click.option("--destination-space", help="Destination space key")
@click.option("--destination-parent-id", help="Destination parent page ID")
@click.option("--new-title", help="New title for copied page")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def copy_page(
    ctx: click.Context,
    page_id: str,
    destination_space: str | None,
    destination_parent_id: str | None,
    new_title: str | None,
    profile: str | None,
    output: str,
) -> None:
    """Copy a Confluence page."""
    argv = [page_id]
    if destination_space:
        argv.extend(["--destination-space", destination_space])
    if destination_parent_id:
        argv.extend(["--destination-parent-id", destination_parent_id])
    if new_title:
        argv.extend(["--new-title", new_title])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-page", "copy_page", argv))


@page.command(name="move")
@click.argument("page_id")
@click.option("--target-space", help="Target space key")
@click.option("--target-parent-id", help="Target parent page ID")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def move_page(
    ctx: click.Context,
    page_id: str,
    target_space: str | None,
    target_parent_id: str | None,
    profile: str | None,
    output: str,
) -> None:
    """Move a Confluence page."""
    argv = [page_id]
    if target_space:
        argv.extend(["--target-space", target_space])
    if target_parent_id:
        argv.extend(["--target-parent-id", target_parent_id])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-page", "move_page", argv))


@page.command(name="versions")
@click.argument("page_id")
@click.option("--limit", "-l", type=int, default=10, help="Maximum versions to show")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def get_page_versions(
    ctx: click.Context,
    page_id: str,
    limit: int,
    profile: str | None,
    output: str,
) -> None:
    """Get version history for a page."""
    argv = [page_id]
    if limit != 10:
        argv.extend(["--limit", str(limit)])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-page", "get_page_versions", argv))


@page.command(name="restore")
@click.argument("page_id")
@click.argument("version", type=int)
@click.option("--message", help="Restore message")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def restore_version(
    ctx: click.Context,
    page_id: str,
    version: int,
    message: str | None,
    profile: str | None,
    output: str,
) -> None:
    """Restore a page to a previous version."""
    argv = [page_id, str(version)]
    if message:
        argv.extend(["--message", message])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-page", "restore_version", argv))


# Blog post commands
@page.group(name="blog")
def blog() -> None:
    """Manage blog posts."""
    pass


@blog.command(name="get")
@click.argument("blogpost_id")
@click.option("--body", is_flag=True, help="Include body content")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def get_blogpost(
    ctx: click.Context,
    blogpost_id: str,
    body: bool,
    profile: str | None,
    output: str,
) -> None:
    """Get a blog post by ID."""
    argv = [blogpost_id]
    if body:
        argv.append("--body")
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-page", "get_blogpost", argv))


@blog.command(name="create")
@click.argument("space_key")
@click.argument("title")
@click.option("--body", help="Blog post body content")
@click.option("--body-file", type=click.Path(exists=True), help="Read body from file")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def create_blogpost(
    ctx: click.Context,
    space_key: str,
    title: str,
    body: str | None,
    body_file: str | None,
    profile: str | None,
    output: str,
) -> None:
    """Create a new blog post."""
    argv = [space_key, title]
    if body:
        argv.extend(["--body", body])
    if body_file:
        argv.extend(["--body-file", body_file])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-page", "create_blogpost", argv))
