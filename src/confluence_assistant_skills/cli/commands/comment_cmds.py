"""Comment management commands - CLI-only implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from confluence_assistant_skills_lib import (
    ValidationError,
    format_json,
    format_table,
    get_confluence_client,
    handle_errors,
    markdown_to_xhtml,
    print_success,
    print_warning,
    validate_limit,
    validate_page_id,
)


def _format_comment(comment: dict[str, Any], detailed: bool = False) -> dict[str, Any]:
    """Format a comment for display."""
    formatted = {
        "id": comment.get("id", ""),
        "type": comment.get("type", "comment"),
        "status": comment.get("status", ""),
        "created": comment.get("createdAt", "")[:10] if comment.get("createdAt") else "",
        "author": comment.get("author", {}).get("displayName", "Unknown"),
    }

    if detailed:
        body = comment.get("body", {})
        if "storage" in body:
            formatted["body"] = body["storage"].get("value", "")[:200]

    return formatted


def _read_body_from_file(file_path: Path) -> str:
    """Read comment body from a file."""
    if not file_path.exists():
        raise ValidationError(f"File not found: {file_path}")
    return file_path.read_text(encoding="utf-8")


def _is_markdown_file(file_path: Path) -> bool:
    """Check if file is a Markdown file."""
    return file_path.suffix.lower() in (".md", ".markdown")


@click.group()
def comment() -> None:
    """Manage page comments."""
    pass


@comment.command(name="list")
@click.argument("page_id")
@click.option("--limit", "-l", type=int, default=25, help="Maximum comments to return")
@click.option(
    "--sort",
    "-s",
    type=click.Choice(["created", "-created"]),
    default="-created",
    help="Sort order (default: -created for newest first)",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def get_comments(
    page_id: str,
    limit: int | None,
    sort: str,
    output: str,
) -> None:
    """List comments on a page."""
    page_id = validate_page_id(page_id)
    if limit:
        limit = validate_limit(limit, max_value=250)

    client = get_confluence_client()

    # Get page info first
    page = client.get(f"/api/v2/pages/{page_id}", operation="get page")
    page_title = page.get("title", "Unknown")

    # Get footer comments (main page comments)
    params: dict[str, Any] = {
        "limit": min(limit or 25, 25),
        "body-format": "storage",
    }

    if sort == "created":
        params["sort"] = "created-date"
    else:
        params["sort"] = "-created-date"

    comments = []
    for comment_item in client.paginate(
        f"/api/v2/pages/{page_id}/footer-comments",
        params=params,
        operation="get comments",
    ):
        comments.append(comment_item)
        if limit and len(comments) >= limit:
            break

    if output == "json":
        click.echo(format_json({
            "page": {"id": page_id, "title": page_title},
            "comments": comments,
            "count": len(comments),
        }))
    else:
        click.echo(f"\nComments on: {page_title} ({page_id})")
        click.echo(f"{'=' * 60}\n")

        if not comments:
            click.echo("No comments found.")
        else:
            data = []
            for c in comments:
                formatted = _format_comment(c)
                body_preview = ""
                body_data = c.get("body", {})
                if "storage" in body_data:
                    body_preview = body_data["storage"].get("value", "")[:50]
                    body_preview = body_preview.replace("\n", " ")

                data.append({
                    "id": formatted["id"],
                    "author": formatted["author"][:20],
                    "created": formatted["created"],
                    "preview": body_preview,
                })

            click.echo(
                format_table(
                    data,
                    columns=["id", "author", "created", "preview"],
                    headers=["ID", "Author", "Created", "Preview"],
                )
            )

    print_success(f"Found {len(comments)} comment(s)")


@comment.command(name="add")
@click.argument("page_id")
@click.argument("body", required=False)
@click.option(
    "--file",
    "-f",
    "body_file",
    type=click.Path(exists=True, path_type=Path),
    help="Read comment body from file",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def add_comment(
    page_id: str,
    body: str | None,
    body_file: Path | None,
    output: str,
) -> None:
    """Add a comment to a page."""
    page_id = validate_page_id(page_id)

    if not body and not body_file:
        raise ValidationError("Either BODY argument or --file option is required")
    if body and body_file:
        raise ValidationError("Cannot specify both BODY argument and --file option")

    if body_file:
        content = _read_body_from_file(body_file)
        if _is_markdown_file(body_file):
            content = markdown_to_xhtml(content)
    else:
        content = body or ""

    client = get_confluence_client()

    comment_data: dict[str, Any] = {
        "pageId": page_id,
        "body": {
            "representation": "storage",
            "value": content,
        },
    }

    result = client.post(
        f"/api/v2/pages/{page_id}/footer-comments",
        json_data=comment_data,
        operation="add comment",
    )

    if output == "json":
        click.echo(format_json(result))
    else:
        click.echo(f"\nComment added successfully")
        click.echo(f"  ID: {result.get('id')}")
        click.echo(f"  Page: {page_id}")
        click.echo(f"  Created: {result.get('createdAt', '')[:16]}")

    print_success(f"Added comment to page {page_id}")


@comment.command(name="add-inline")
@click.argument("page_id")
@click.argument("selection")
@click.argument("body")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def add_inline_comment(
    page_id: str,
    selection: str,
    body: str,
    output: str,
) -> None:
    """Add an inline comment to specific text in a page.

    SELECTION is the text to highlight/comment on.
    BODY is the comment text.
    """
    page_id = validate_page_id(page_id)

    if not selection:
        raise ValidationError("Selection text is required")
    if not body:
        raise ValidationError("Comment body is required")

    client = get_confluence_client()

    # Get page to find the selection
    page = client.get(
        f"/api/v2/pages/{page_id}",
        params={"body-format": "storage"},
        operation="get page",
    )

    page_body = page.get("body", {}).get("storage", {}).get("value", "")

    # Find selection position
    selection_index = page_body.find(selection)
    if selection_index == -1:
        raise ValidationError(f"Selection text not found in page: '{selection[:50]}...'")

    # Create inline comment
    comment_data: dict[str, Any] = {
        "pageId": page_id,
        "body": {
            "representation": "storage",
            "value": body,
        },
        "inlineProperties": {
            "textSelection": selection,
            "textSelectionMatchCount": 1,
            "textSelectionMatchIndex": 0,
        },
    }

    result = client.post(
        f"/api/v2/pages/{page_id}/inline-comments",
        json_data=comment_data,
        operation="add inline comment",
    )

    if output == "json":
        click.echo(format_json(result))
    else:
        click.echo(f"\nInline comment added successfully")
        click.echo(f"  ID: {result.get('id')}")
        click.echo(f"  Selection: {selection[:50]}...")
        click.echo(f"  Page: {page_id}")

    print_success(f"Added inline comment to page {page_id}")


@comment.command(name="update")
@click.argument("comment_id")
@click.argument("body", required=False)
@click.option(
    "--file",
    "-f",
    "body_file",
    type=click.Path(exists=True, path_type=Path),
    help="Read updated body from file",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def update_comment(
    comment_id: str,
    body: str | None,
    body_file: Path | None,
    output: str,
) -> None:
    """Update an existing comment."""
    comment_id = validate_page_id(comment_id, field_name="comment_id")

    if not body and not body_file:
        raise ValidationError("Either BODY argument or --file option is required")
    if body and body_file:
        raise ValidationError("Cannot specify both BODY argument and --file option")

    if body_file:
        content = _read_body_from_file(body_file)
        if _is_markdown_file(body_file):
            content = markdown_to_xhtml(content)
    else:
        content = body or ""

    client = get_confluence_client()

    # Get current comment to get its version
    current = client.get(
        f"/api/v2/footer-comments/{comment_id}",
        operation="get comment",
    )

    current_version = current.get("version", {}).get("number", 1)

    update_data: dict[str, Any] = {
        "body": {
            "representation": "storage",
            "value": content,
        },
        "version": {
            "number": current_version + 1,
        },
    }

    result = client.put(
        f"/api/v2/footer-comments/{comment_id}",
        json_data=update_data,
        operation="update comment",
    )

    if output == "json":
        click.echo(format_json(result))
    else:
        click.echo(f"\nComment updated successfully")
        click.echo(f"  ID: {result.get('id')}")
        click.echo(f"  Version: {current_version + 1}")

    print_success(f"Updated comment {comment_id}")


@comment.command(name="delete")
@click.argument("comment_id")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
@handle_errors
def delete_comment(
    comment_id: str,
    force: bool,
) -> None:
    """Delete a comment."""
    comment_id = validate_page_id(comment_id, field_name="comment_id")

    client = get_confluence_client()

    # Get comment details first
    try:
        comment_info = client.get(
            f"/api/v2/footer-comments/{comment_id}",
            operation="get comment",
        )
        author = comment_info.get("author", {}).get("displayName", "Unknown")
    except Exception:
        author = "Unknown"

    if not force:
        click.echo(f"\nYou are about to delete comment {comment_id}")
        click.echo(f"Author: {author}")
        print_warning("This action cannot be undone!")

        if not click.confirm("\nAre you sure?", default=False):
            click.echo("Delete cancelled.")
            return

    client.delete(f"/api/v2/footer-comments/{comment_id}", operation="delete comment")

    print_success(f"Deleted comment {comment_id}")


@comment.command(name="resolve")
@click.argument("comment_id")
@click.option(
    "--resolve", "-r", "action", flag_value="resolve", help="Mark comment as resolved"
)
@click.option(
    "--unresolve",
    "-u",
    "action",
    flag_value="unresolve",
    help="Mark comment as unresolved/open",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def resolve_comment(
    comment_id: str,
    action: str | None,
    output: str,
) -> None:
    """Resolve or reopen a comment."""
    comment_id = validate_page_id(comment_id, field_name="comment_id")

    if action is None:
        raise ValidationError("One of --resolve or --unresolve is required")

    client = get_confluence_client()

    # Get current comment
    current = client.get(
        f"/api/v2/footer-comments/{comment_id}",
        operation="get comment",
    )

    current_version = current.get("version", {}).get("number", 1)
    new_status = "resolved" if action == "resolve" else "open"

    update_data: dict[str, Any] = {
        "status": new_status,
        "version": {
            "number": current_version + 1,
        },
    }

    result = client.put(
        f"/api/v2/footer-comments/{comment_id}",
        json_data=update_data,
        operation=f"{action} comment",
    )

    if output == "json":
        click.echo(format_json(result))
    else:
        click.echo(f"\nComment {action}d successfully")
        click.echo(f"  ID: {result.get('id')}")
        click.echo(f"  Status: {new_status}")

    print_success(f"Comment {comment_id} {action}d")
