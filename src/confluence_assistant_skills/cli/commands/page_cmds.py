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
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def get_page(
    ctx: click.Context,
    page_id: str,
    body: bool,
    body_format: str,
    output: str,
) -> None:
    """Get a Confluence page by ID."""
    argv = [page_id]
    if body:
        argv.append("--body")
    if body_format != "storage":
        argv.extend(["--format", body_format])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-page", "get_page", argv))


@page.command(name="create")
@click.option("--space", "-s", required=True, help="Space key")
@click.option("--title", "-t", required=True, help="Page title")
@click.option("--body", "-b", help="Page body content (Markdown or XHTML)")
@click.option(
    "--file",
    "-f",
    "body_file",
    type=click.Path(exists=True),
    help="Read body from file",
)
@click.option("--parent", "-p", "parent_id", help="Parent page ID")
@click.option(
    "--status",
    type=click.Choice(["current", "draft"]),
    default="current",
    help="Page status",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def create_page(
    ctx: click.Context,
    space: str,
    title: str,
    body: str | None,
    body_file: str | None,
    parent_id: str | None,
    status: str,
    output: str,
) -> None:
    """Create a new Confluence page."""
    argv = ["--space", space, "--title", title]
    if body:
        argv.extend(["--body", body])
    if body_file:
        argv.extend(["--file", body_file])
    if parent_id:
        argv.extend(["--parent", parent_id])
    if status != "current":
        argv.extend(["--status", status])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-page", "create_page", argv))


@page.command(name="update")
@click.argument("page_id")
@click.option("--title", "-t", help="New page title")
@click.option("--body", "-b", help="New page body content")
@click.option(
    "--file",
    "-f",
    "body_file",
    type=click.Path(exists=True),
    help="Read body from file",
)
@click.option("--message", "-m", "version_message", help="Version change message")
@click.option(
    "--status", type=click.Choice(["current", "draft"]), help="Change page status"
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def update_page(
    ctx: click.Context,
    page_id: str,
    title: str | None,
    body: str | None,
    body_file: str | None,
    version_message: str | None,
    status: str | None,
    output: str,
) -> None:
    """Update an existing Confluence page."""
    argv = [page_id]
    if title:
        argv.extend(["--title", title])
    if body:
        argv.extend(["--body", body])
    if body_file:
        argv.extend(["--file", body_file])
    if version_message:
        argv.extend(["--message", version_message])
    if status:
        argv.extend(["--status", status])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-page", "update_page", argv))


@page.command(name="delete")
@click.argument("page_id")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
@click.option(
    "--permanent", is_flag=True, help="Permanently delete (cannot be recovered)"
)
@click.pass_context
def delete_page(
    ctx: click.Context,
    page_id: str,
    force: bool,
    permanent: bool,
) -> None:
    """Delete a Confluence page."""
    argv = [page_id]
    if force:
        argv.append("--force")
    if permanent:
        argv.append("--permanent")

    ctx.exit(call_skill_main("confluence-page", "delete_page", argv))


@page.command(name="copy")
@click.argument("page_id")
@click.option("--title", "-t", help="New page title (default: 'Copy of [original]')")
@click.option("--space", "-s", help="Target space key")
@click.option("--parent", "-p", "parent_id", help="Target parent page ID")
@click.option("--include-children", is_flag=True, help="Copy child pages recursively")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def copy_page(
    ctx: click.Context,
    page_id: str,
    title: str | None,
    space: str | None,
    parent_id: str | None,
    include_children: bool,
    output: str,
) -> None:
    """Copy a Confluence page."""
    argv = [page_id]
    if title:
        argv.extend(["--title", title])
    if space:
        argv.extend(["--space", space])
    if parent_id:
        argv.extend(["--parent", parent_id])
    if include_children:
        argv.append("--include-children")
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-page", "copy_page", argv))


@page.command(name="move")
@click.argument("page_id")
@click.option("--space", "-s", help="Target space key")
@click.option("--parent", "-p", "parent_id", help="Target parent page ID")
@click.option("--root", is_flag=True, help="Move to space root (no parent)")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def move_page(
    ctx: click.Context,
    page_id: str,
    space: str | None,
    parent_id: str | None,
    root: bool,
    output: str,
) -> None:
    """Move a Confluence page."""
    argv = [page_id]
    if space:
        argv.extend(["--space", space])
    if parent_id:
        argv.extend(["--parent", parent_id])
    if root:
        argv.append("--root")
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-page", "move_page", argv))


@page.command(name="versions")
@click.argument("page_id")
@click.option(
    "--limit",
    "-l",
    type=int,
    default=25,
    help="Maximum versions to return (default: 25)",
)
@click.option("--detailed", is_flag=True, help="Show full version details")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def get_page_versions(
    ctx: click.Context,
    page_id: str,
    limit: int,
    detailed: bool,
    output: str,
) -> None:
    """Get version history for a page."""
    argv = [page_id]
    if limit != 25:
        argv.extend(["--limit", str(limit)])
    if detailed:
        argv.append("--detailed")
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-page", "get_page_versions", argv))


@page.command(name="restore")
@click.argument("page_id")
@click.option(
    "--version", "-v", type=int, required=True, help="Version number to restore"
)
@click.option("--message", "-m", help="Version message for the restoration")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def restore_version(
    ctx: click.Context,
    page_id: str,
    version: int,
    message: str | None,
    output: str,
) -> None:
    """Restore a page to a previous version."""
    argv = [page_id, "--version", str(version)]
    if message:
        argv.extend(["--message", message])
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
@click.option(
    "--format",
    "body_format",
    type=click.Choice(["storage", "view", "markdown"]),
    default="storage",
    help="Body format (default: storage)",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def get_blogpost(
    ctx: click.Context,
    blogpost_id: str,
    body: bool,
    body_format: str,
    output: str,
) -> None:
    """Get a blog post by ID."""
    argv = [blogpost_id]
    if body:
        argv.append("--body")
    if body_format != "storage":
        argv.extend(["--format", body_format])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-page", "get_blogpost", argv))


@blog.command(name="create")
@click.option("--space", "-s", required=True, help="Space key")
@click.option("--title", "-t", required=True, help="Blog post title")
@click.option("--body", "-b", help="Blog post body content")
@click.option(
    "--file",
    "-f",
    "body_file",
    type=click.Path(exists=True),
    help="Read body from file",
)
@click.option(
    "--status",
    type=click.Choice(["current", "draft"]),
    default="current",
    help="Blog post status",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def create_blogpost(
    ctx: click.Context,
    space: str,
    title: str,
    body: str | None,
    body_file: str | None,
    status: str,
    output: str,
) -> None:
    """Create a new blog post."""
    argv = ["--space", space, "--title", title]
    if body:
        argv.extend(["--body", body])
    if body_file:
        argv.extend(["--file", body_file])
    if status != "current":
        argv.extend(["--status", status])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-page", "create_blogpost", argv))
