"""Attachment management commands - CLI-only implementation."""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any

import click

from confluence_assistant_skills_lib import (
    ValidationError,
    format_json,
    format_table,
    get_confluence_client,
    handle_errors,
    print_info,
    print_success,
    print_warning,
    validate_limit,
    validate_page_id,
)


def _format_attachment(attachment: dict[str, Any]) -> dict[str, Any]:
    """Format an attachment for display."""
    return {
        "id": attachment.get("id", ""),
        "title": attachment.get("title", "Untitled"),
        "mediaType": attachment.get("mediaType", "unknown"),
        "fileSize": _format_file_size(attachment.get("fileSize", 0)),
        "version": attachment.get("version", {}).get("number", 1),
    }


def _format_file_size(size_bytes: int) -> str:
    """Format file size for human readability."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


@click.group()
def attachment() -> None:
    """Manage file attachments."""
    pass


@attachment.command(name="list")
@click.argument("page_id")
@click.option(
    "--limit", "-l", type=int, default=25, help="Maximum attachments to return"
)
@click.option("--media-type", "-m", help="Filter by media type (e.g., application/pdf)")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json", "table"]),
    default="text",
    help="Output format",
)
@handle_errors
def list_attachments(
    page_id: str,
    limit: int,
    media_type: str | None,
    output: str,
) -> None:
    """List attachments on a page."""
    page_id = validate_page_id(page_id)
    limit = validate_limit(limit, max_value=250)

    client = get_confluence_client()

    # Get page info
    page = client.get(f"/api/v2/pages/{page_id}", operation="get page")
    page_title = page.get("title", "Unknown")

    params: dict[str, Any] = {
        "limit": min(limit, 25),
    }

    if media_type:
        params["mediaType"] = media_type

    attachments = []
    for att in client.paginate(
        f"/api/v2/pages/{page_id}/attachments",
        params=params,
        operation="list attachments",
    ):
        attachments.append(att)
        if len(attachments) >= limit:
            break

    if output == "json":
        click.echo(format_json({
            "page": {"id": page_id, "title": page_title},
            "attachments": attachments,
            "count": len(attachments),
        }))
    else:
        click.echo(f"\nAttachments on: {page_title} ({page_id})")
        click.echo(f"{'=' * 60}\n")

        if not attachments:
            click.echo("No attachments found.")
        else:
            data = []
            for a in attachments:
                formatted = _format_attachment(a)
                data.append({
                    "id": formatted["id"],
                    "title": formatted["title"][:30],
                    "type": formatted["mediaType"][:20],
                    "size": formatted["fileSize"],
                    "ver": formatted["version"],
                })

            click.echo(
                format_table(
                    data,
                    columns=["id", "title", "type", "size", "ver"],
                    headers=["ID", "Name", "Type", "Size", "Ver"],
                )
            )

    print_success(f"Found {len(attachments)} attachment(s)")


@attachment.command(name="upload")
@click.argument("page_id")
@click.argument("file_path", type=click.Path(exists=True, path_type=Path))
@click.option("--comment", help="Attachment comment")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def upload_attachment(
    page_id: str,
    file_path: Path,
    comment: str | None,
    output: str,
) -> None:
    """Upload a file attachment to a page."""
    page_id = validate_page_id(page_id)

    if not file_path.exists():
        raise ValidationError(f"File not found: {file_path}")

    if not file_path.is_file():
        raise ValidationError(f"Path is not a file: {file_path}")

    # Determine content type
    content_type, _ = mimetypes.guess_type(str(file_path))
    if not content_type:
        content_type = "application/octet-stream"

    client = get_confluence_client()

    # Read file content
    file_content = file_path.read_bytes()
    file_name = file_path.name

    print_info(f"Uploading {file_name} ({_format_file_size(len(file_content))})...")

    # Use v1 API for file upload as v2 API has different semantics
    result = client.upload_attachment(
        page_id=page_id,
        file_path=str(file_path),
        comment=comment,
    )

    if output == "json":
        click.echo(format_json(result))
    else:
        # Result may be a list or a single item
        if isinstance(result, list):
            result = result[0] if result else {}

        click.echo(f"\nAttachment uploaded successfully")
        click.echo(f"  ID: {result.get('id', 'N/A')}")
        click.echo(f"  Name: {file_name}")
        click.echo(f"  Page: {page_id}")

    print_success(f"Uploaded {file_name} to page {page_id}")


@attachment.command(name="download")
@click.argument("attachment_id")
@click.option("--output", "-o", "output_path", default=".", help="Output file or directory")
@click.option(
    "--all",
    "-a",
    "download_all",
    is_flag=True,
    help="Download all attachments from page (attachment_id is page_id)",
)
@handle_errors
def download_attachment(
    attachment_id: str,
    output_path: str,
    download_all: bool,
) -> None:
    """Download an attachment."""
    attachment_id = validate_page_id(attachment_id, field_name="attachment_id")
    output_dir = Path(output_path)

    client = get_confluence_client()

    if download_all:
        # attachment_id is actually page_id
        page_id = attachment_id

        if output_dir.exists() and not output_dir.is_dir():
            raise ValidationError("Output must be a directory when downloading all")

        output_dir.mkdir(parents=True, exist_ok=True)

        attachments = list(client.paginate(
            f"/api/v2/pages/{page_id}/attachments",
            operation="list attachments",
        ))

        if not attachments:
            click.echo("No attachments found on page.")
            return

        print_info(f"Downloading {len(attachments)} attachment(s)...")

        for att in attachments:
            att_id = att.get("id")
            title = att.get("title", "attachment")
            download_url = att.get("downloadLink", att.get("_links", {}).get("download"))

            if download_url:
                content = client.download_attachment(att_id)
                file_path = output_dir / title
                file_path.write_bytes(content)
                print_info(f"  Downloaded: {title}")

        print_success(f"Downloaded {len(attachments)} attachment(s) to {output_dir}")

    else:
        # Download single attachment
        att_info = client.get(
            f"/api/v2/attachments/{attachment_id}",
            operation="get attachment",
        )

        title = att_info.get("title", "attachment")

        if output_dir.is_dir():
            file_path = output_dir / title
        else:
            file_path = output_dir

        file_path.parent.mkdir(parents=True, exist_ok=True)

        content = client.download_attachment(attachment_id)
        file_path.write_bytes(content)

        print_success(f"Downloaded {title} to {file_path}")


@attachment.command(name="update")
@click.argument("attachment_id")
@click.argument("file_path", type=click.Path(exists=True, path_type=Path))
@click.option("--comment", help="Update comment")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def update_attachment(
    attachment_id: str,
    file_path: Path,
    comment: str | None,
    output: str,
) -> None:
    """Update an existing attachment."""
    attachment_id = validate_page_id(attachment_id, field_name="attachment_id")

    if not file_path.exists():
        raise ValidationError(f"File not found: {file_path}")

    client = get_confluence_client()

    # Get current attachment info
    att_info = client.get(
        f"/api/v2/attachments/{attachment_id}",
        operation="get attachment",
    )

    page_id = att_info.get("pageId")
    if not page_id:
        raise ValidationError("Could not determine page ID for attachment")

    print_info(f"Updating attachment {att_info.get('title', attachment_id)}...")

    # Use v1 API for file update
    result = client.update_attachment(
        attachment_id=attachment_id,
        page_id=page_id,
        file_path=str(file_path),
        comment=comment,
    )

    if output == "json":
        click.echo(format_json(result))
    else:
        if isinstance(result, list):
            result = result[0] if result else {}

        click.echo(f"\nAttachment updated successfully")
        click.echo(f"  ID: {result.get('id', attachment_id)}")
        click.echo(f"  Name: {file_path.name}")

    print_success(f"Updated attachment {attachment_id}")


@attachment.command(name="delete")
@click.argument("attachment_id")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
@handle_errors
def delete_attachment(
    attachment_id: str,
    force: bool,
) -> None:
    """Delete an attachment."""
    attachment_id = validate_page_id(attachment_id, field_name="attachment_id")

    client = get_confluence_client()

    # Get attachment info
    try:
        att_info = client.get(
            f"/api/v2/attachments/{attachment_id}",
            operation="get attachment",
        )
        title = att_info.get("title", "Unknown")
    except Exception:
        title = "Unknown"

    if not force:
        click.echo(f"\nYou are about to delete attachment: {title}")
        click.echo(f"ID: {attachment_id}")
        print_warning("This action cannot be undone!")

        if not click.confirm("\nAre you sure?", default=False):
            click.echo("Delete cancelled.")
            return

    client.delete(f"/api/v2/attachments/{attachment_id}", operation="delete attachment")

    print_success(f"Deleted attachment {title} ({attachment_id})")
