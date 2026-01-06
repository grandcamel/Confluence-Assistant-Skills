"""Attachment management commands."""

from __future__ import annotations

import click

from confluence_assistant_skills.utils import call_skill_main


@click.group()
def attachment() -> None:
    """Manage file attachments."""
    pass


@attachment.command(name="list")
@click.argument("page_id")
@click.option("--limit", "-l", type=int, default=25, help="Maximum attachments to return")
@click.option("--media-type", "-m", help="Filter by media type (e.g., application/pdf)")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json", "table"]), default="text", help="Output format"
)
@click.pass_context
def list_attachments(
    ctx: click.Context,
    page_id: str,
    limit: int,
    media_type: str | None,
    profile: str | None,
    output: str,
) -> None:
    """List attachments on a page."""
    argv = [page_id]
    if limit != 25:
        argv.extend(["--limit", str(limit)])
    if media_type:
        argv.extend(["--media-type", media_type])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-attachment", "list_attachments", argv))


@attachment.command(name="upload")
@click.argument("page_id")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--comment", help="Attachment comment")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def upload_attachment(
    ctx: click.Context,
    page_id: str,
    file_path: str,
    comment: str | None,
    profile: str | None,
    output: str,
) -> None:
    """Upload a file attachment to a page."""
    argv = [page_id, "--file", file_path]
    if comment:
        argv.extend(["--comment", comment])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-attachment", "upload_attachment", argv))


@attachment.command(name="download")
@click.argument("attachment_id")
@click.option("--output", "-o", default=".", help="Output file or directory")
@click.option("--all", "-a", "download_all", is_flag=True, help="Download all attachments from page")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.pass_context
def download_attachment(
    ctx: click.Context,
    attachment_id: str,
    output: str,
    download_all: bool,
    profile: str | None,
) -> None:
    """Download an attachment."""
    argv = [attachment_id]
    if output != ".":
        argv.extend(["--output", output])
    if download_all:
        argv.append("--all")
    if profile:
        argv.extend(["--profile", profile])

    ctx.exit(call_skill_main("confluence-attachment", "download_attachment", argv))


@attachment.command(name="update")
@click.argument("attachment_id")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--comment", help="Update comment")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def update_attachment(
    ctx: click.Context,
    attachment_id: str,
    file_path: str,
    comment: str | None,
    profile: str | None,
    output: str,
) -> None:
    """Update an existing attachment."""
    argv = [attachment_id, "--file", file_path]
    if comment:
        argv.extend(["--comment", comment])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-attachment", "update_attachment", argv))


@attachment.command(name="delete")
@click.argument("attachment_id")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.pass_context
def delete_attachment(
    ctx: click.Context,
    attachment_id: str,
    force: bool,
    profile: str | None,
) -> None:
    """Delete an attachment."""
    argv = [attachment_id]
    if force:
        argv.append("--force")
    if profile:
        argv.extend(["--profile", profile])

    ctx.exit(call_skill_main("confluence-attachment", "delete_attachment", argv))
