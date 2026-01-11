"""Page management commands - CLI-only implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from confluence_assistant_skills.cli.helpers import (
    get_space_id,
    is_markdown_file,
    read_file_content,
)
from confluence_assistant_skills_lib import (
    ValidationError,
    format_blogpost,
    format_json,
    format_page,
    format_table,
    format_version,
    get_confluence_client,
    handle_errors,
    markdown_to_xhtml,
    print_info,
    print_success,
    print_warning,
    validate_limit,
    validate_page_id,
    validate_space_key,
    validate_title,
    xhtml_to_markdown,
)


def _copy_children(
    client: Any, source_parent_id: str, target_parent_id: str, target_space_id: str
) -> None:
    """Recursively copy child pages."""
    children = list(
        client.paginate(
            f"/api/v2/pages/{source_parent_id}/children",
            params={"body-format": "storage"},
            operation="get children",
        )
    )

    for child in children:
        child_id = child["id"]
        child_title = child.get("title", "Untitled")

        full_child = client.get(
            f"/api/v2/pages/{child_id}",
            params={"body-format": "storage"},
            operation="get child page",
        )

        child_copy_data = {
            "spaceId": target_space_id,
            "status": full_child.get("status", "current"),
            "title": child_title,
            "parentId": target_parent_id,
            "body": full_child.get("body", {}),
        }

        new_child = client.post(
            "/api/v2/pages", json_data=child_copy_data, operation="copy child page"
        )

        print_info(f"  Copied child: {child_title}")
        _copy_children(client, child_id, new_child["id"], target_space_id)


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
@handle_errors
def get_page(
    page_id: str,
    body: bool,
    body_format: str,
    output: str,
) -> None:
    """Get a Confluence page by ID."""
    page_id = validate_page_id(page_id)
    client = get_confluence_client()

    params = {}
    if body:
        params["body-format"] = "storage"

    result = client.get(f"/api/v2/pages/{page_id}", params=params, operation="get page")

    if body and body_format == "markdown":
        body_data = result.get("body", {})
        storage = body_data.get("storage", {}).get("value", "")
        if storage:
            result["body"]["markdown"] = xhtml_to_markdown(storage)

    if output == "json":
        click.echo(format_json(result))
    else:
        click.echo(format_page(result, detailed=body))

        if body:
            click.echo("\n--- Content ---")
            body_data = result.get("body", {})

            if body_format == "markdown" and "markdown" in body_data:
                click.echo(body_data["markdown"])
            elif "storage" in body_data:
                click.echo(body_data["storage"].get("value", ""))

    print_success(f"Retrieved page {page_id}")


@page.command(name="create")
@click.option("--space", "-s", required=True, help="Space key")
@click.option("--title", "-t", required=True, help="Page title")
@click.option("--body", "-b", "body_content", help="Page body content (Markdown or XHTML)")
@click.option(
    "--file",
    "-f",
    "body_file",
    type=click.Path(exists=True, path_type=Path),  # type: ignore[type-var]
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
@handle_errors
def create_page(
    space: str,
    title: str,
    body_content: str | None,
    body_file: Path | None,
    parent_id: str | None,
    status: str,
    output: str,
) -> None:
    """Create a new Confluence page."""
    space_key = validate_space_key(space)
    title = validate_title(title)

    if parent_id:
        parent_id = validate_page_id(parent_id, field_name="parent")

    if body_file:
        content = read_file_content(body_file)
        is_markdown = is_markdown_file(body_file)
    elif body_content:
        content = body_content
        is_markdown = False
    else:
        raise ValidationError("Either --body or --file is required")

    client = get_confluence_client()
    space_id = get_space_id(client, space_key)

    if is_markdown:
        content = markdown_to_xhtml(content)

    page_data: dict[str, Any] = {
        "spaceId": space_id,
        "status": status,
        "title": title,
        "body": {
            "representation": "storage",
            "value": content,
        },
    }

    if parent_id:
        page_data["parentId"] = parent_id

    result = client.post("/api/v2/pages", json_data=page_data, operation="create page")

    if output == "json":
        click.echo(format_json(result))
    else:
        click.echo(format_page(result))

    print_success(f"Created page '{title}' with ID {result['id']}")


@page.command(name="update")
@click.argument("page_id")
@click.option("--title", "-t", help="New page title")
@click.option("--body", "-b", "body_content", help="New page body content")
@click.option(
    "--file",
    "-f",
    "body_file",
    type=click.Path(exists=True, path_type=Path),  # type: ignore[type-var]
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
@handle_errors
def update_page(
    page_id: str,
    title: str | None,
    body_content: str | None,
    body_file: Path | None,
    version_message: str | None,
    status: str | None,
    output: str,
) -> None:
    """Update an existing Confluence page."""
    page_id = validate_page_id(page_id)

    if title:
        title = validate_title(title)

    if not any([title, body_content, body_file, status]):
        raise ValidationError(
            "At least one of --title, --body, --file, or --status is required"
        )

    content = None
    is_markdown = False

    if body_file:
        content = read_file_content(body_file)
        is_markdown = is_markdown_file(body_file)
    elif body_content:
        content = body_content

    client = get_confluence_client()
    current_page = client.get(f"/api/v2/pages/{page_id}", operation="get current page")
    current_version = current_page.get("version", {}).get("number", 1)

    update_data: dict[str, Any] = {
        "id": page_id,
        "status": status or current_page.get("status", "current"),
        "title": title or current_page.get("title"),
        "version": {"number": current_version + 1},
    }

    if version_message:
        update_data["version"]["message"] = version_message

    if content:
        if is_markdown:
            content = markdown_to_xhtml(content)
        update_data["body"] = {"representation": "storage", "value": content}

    result = client.put(
        f"/api/v2/pages/{page_id}", json_data=update_data, operation="update page"
    )

    if output == "json":
        click.echo(format_json(result))
    else:
        click.echo(format_page(result))

    print_success(f"Updated page {page_id} to version {current_version + 1}")


@page.command(name="delete")
@click.argument("page_id")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
@click.option(
    "--permanent", is_flag=True, help="Permanently delete (cannot be recovered)"
)
@handle_errors
def delete_page(
    page_id: str,
    force: bool,
    permanent: bool,
) -> None:
    """Delete a Confluence page."""
    page_id = validate_page_id(page_id)
    client = get_confluence_client()

    page = client.get(f"/api/v2/pages/{page_id}", operation="get page")
    page_title = page.get("title", "Unknown")

    if not force:
        action = "permanently delete" if permanent else "move to trash"
        click.echo(f"\nYou are about to {action} the page: {page_title}")

        if permanent:
            print_warning("This action cannot be undone!")

        if not click.confirm("\nAre you sure?", default=False):
            click.echo("Delete cancelled.")
            return

    params = {}
    if permanent:
        params["purge"] = "true"

    client.delete(f"/api/v2/pages/{page_id}", params=params, operation="delete page")

    if permanent:
        print_success(f"Permanently deleted page '{page_title}' (ID: {page_id})")
    else:
        print_success(f"Moved page '{page_title}' to trash (ID: {page_id})")


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
@handle_errors
def copy_page(
    page_id: str,
    title: str | None,
    space: str | None,
    parent_id: str | None,
    include_children: bool,
    output: str,
) -> None:
    """Copy a Confluence page."""
    source_page_id = validate_page_id(page_id)

    if parent_id:
        parent_id = validate_page_id(parent_id, field_name="parent")

    client = get_confluence_client()

    source_page = client.get(
        f"/api/v2/pages/{source_page_id}",
        params={"body-format": "storage"},
        operation="get source page",
    )

    source_title = source_page.get("title", "Untitled")
    source_space_id = source_page.get("spaceId")

    if title:
        new_title = validate_title(title)
    else:
        new_title = f"Copy of {source_title}"

    target_space_id = source_space_id
    if space:
        space_key = validate_space_key(space)
        target_space_id = get_space_id(client, space_key)

    copy_data: dict[str, Any] = {
        "spaceId": target_space_id,
        "status": source_page.get("status", "current"),
        "title": new_title,
        "body": source_page.get("body", {}),
    }

    if parent_id:
        copy_data["parentId"] = parent_id

    print_info(f"Copying page '{source_title}' to '{new_title}'...")

    result = client.post("/api/v2/pages", json_data=copy_data, operation="copy page")

    if include_children:
        print_info("Copying child pages...")
        _copy_children(client, source_page_id, result["id"], target_space_id)

    if output == "json":
        click.echo(format_json(result))
    else:
        click.echo(format_page(result))

    print_success(f"Copied page to '{new_title}' with ID {result['id']}")


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
@handle_errors
def move_page(
    page_id: str,
    space: str | None,
    parent_id: str | None,
    root: bool,
    output: str,
) -> None:
    """Move a Confluence page."""
    page_id = validate_page_id(page_id)

    if parent_id:
        parent_id = validate_page_id(parent_id, field_name="parent")

    if not space and not parent_id and not root:
        raise ValidationError(
            "At least one of --space, --parent, or --root is required"
        )

    if parent_id and root:
        raise ValidationError("Cannot specify both --parent and --root")

    client = get_confluence_client()
    current_page = client.get(f"/api/v2/pages/{page_id}", operation="get current page")
    current_version = current_page.get("version", {}).get("number", 1)

    if space:
        space_key = validate_space_key(space)
        target_space_id = get_space_id(client, space_key)
    else:
        target_space_id = current_page.get("spaceId")

    update_data: dict[str, Any] = {
        "id": page_id,
        "status": current_page.get("status", "current"),
        "title": current_page.get("title"),
        "spaceId": target_space_id,
        "version": {"number": current_version + 1, "message": "Page moved"},
    }

    if root:
        pass  # Don't include parentId to move to root
    elif parent_id:
        update_data["parentId"] = parent_id
    elif current_page.get("parentId"):
        update_data["parentId"] = current_page["parentId"]

    result = client.put(
        f"/api/v2/pages/{page_id}", json_data=update_data, operation="move page"
    )

    if output == "json":
        click.echo(format_json(result))
    else:
        click.echo(format_page(result))

    destination = []
    if space:
        destination.append(f"space {space}")
    if parent_id:
        destination.append(f"under parent {parent_id}")
    elif root:
        destination.append("to space root")

    print_success(f"Moved page '{result['title']}' {' '.join(destination)}")


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
@handle_errors
def get_page_versions(
    page_id: str,
    limit: int,
    detailed: bool,
    output: str,
) -> None:
    """Get version history for a page."""
    page_id = validate_page_id(page_id)
    limit = validate_limit(limit, max_value=100)

    client = get_confluence_client()

    page = client.get(f"/api/v2/pages/{page_id}", operation="get page")

    versions_response = client.get(
        f"/rest/api/content/{page_id}/version",
        params={"limit": limit},
        operation="get versions",
    )

    versions = versions_response.get("results", [])

    if output == "json":
        click.echo(
            format_json(
                {
                    "page": {
                        "id": page_id,
                        "title": page.get("title"),
                        "currentVersion": page.get("version", {}).get("number"),
                    },
                    "versions": versions,
                }
            )
        )
    else:
        click.echo(f"\nPage: {page.get('title')}")
        click.echo(f"ID: {page_id}")
        click.echo(f"Current Version: {page.get('version', {}).get('number', 1)}")
        click.echo(f"\n{'=' * 60}")
        click.echo("Version History:")
        click.echo(f"{'=' * 60}\n")

        if not versions:
            click.echo("No version history available.")
        elif detailed:
            for version in versions:
                click.echo(format_version(version))
                click.echo()
        else:
            data = []
            for v in versions:
                data.append(
                    {
                        "version": v.get("number", "?"),
                        "when": v.get("when", "")[:16] if v.get("when") else "N/A",
                        "by": v.get("by", {}).get(
                            "displayName",
                            v.get("by", {}).get("username", "Unknown"),
                        ),
                        "message": v.get("message", "")[:40] or "-",
                    }
                )

            click.echo(
                format_table(
                    data,
                    columns=["version", "when", "by", "message"],
                    headers=["Version", "Date", "Author", "Message"],
                )
            )

    print_success(f"Retrieved {len(versions)} version(s) for page {page_id}")


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
@handle_errors
def restore_version(
    page_id: str,
    version: int,
    message: str | None,
    output: str,
) -> None:
    """Restore a page to a previous version."""
    page_id = validate_page_id(page_id)

    if version < 1:
        raise ValidationError("Version number must be at least 1")

    client = get_confluence_client()
    current_page = client.get(f"/api/v2/pages/{page_id}", operation="get current page")
    current_version = current_page.get("version", {}).get("number", 1)

    if version >= current_version:
        raise ValidationError(
            f"Cannot restore to version {version}. "
            f"Current version is {current_version}. "
            f"Specify a version less than {current_version}."
        )

    historical = client.get(
        f"/rest/api/content/{page_id}",
        params={"version": version, "expand": "body.storage,version"},
        operation="get historical version",
    )

    historical_body = historical.get("body", {}).get("storage", {}).get("value", "")

    if not historical_body:
        raise ValidationError(f"Could not retrieve content for version {version}")

    version_message = message or f"Restored to version {version}"

    restore_data: dict[str, Any] = {
        "id": page_id,
        "status": current_page.get("status", "current"),
        "title": current_page.get("title"),
        "version": {"number": current_version + 1, "message": version_message},
        "body": {"representation": "storage", "value": historical_body},
    }

    print_warning(
        f"Restoring page '{current_page.get('title')}' from version {current_version} to version {version}"
    )

    result = client.put(
        f"/api/v2/pages/{page_id}", json_data=restore_data, operation="restore version"
    )

    if output == "json":
        click.echo(format_json(result))
    else:
        click.echo(format_page(result))

    print_success(
        f"Restored page to version {version} content. "
        f"New version number: {current_version + 1}"
    )


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
@handle_errors
def get_blogpost(
    blogpost_id: str,
    body: bool,
    body_format: str,
    output: str,
) -> None:
    """Get a blog post by ID."""
    blogpost_id = validate_page_id(blogpost_id, field_name="blogpost_id")

    client = get_confluence_client()

    params = {}
    if body:
        params["body-format"] = "storage"

    result = client.get(
        f"/api/v2/blogposts/{blogpost_id}", params=params, operation="get blog post"
    )

    if body and body_format == "markdown":
        body_data = result.get("body", {})
        storage = body_data.get("storage", {}).get("value", "")
        if storage:
            result["body"]["markdown"] = xhtml_to_markdown(storage)

    if output == "json":
        click.echo(format_json(result))
    else:
        click.echo(format_blogpost(result, detailed=body))

        if body:
            click.echo("\n--- Content ---")
            body_data = result.get("body", {})

            if body_format == "markdown" and "markdown" in body_data:
                click.echo(body_data["markdown"])
            elif "storage" in body_data:
                click.echo(body_data["storage"].get("value", ""))

    print_success(f"Retrieved blog post {blogpost_id}")


@blog.command(name="create")
@click.option("--space", "-s", required=True, help="Space key")
@click.option("--title", "-t", required=True, help="Blog post title")
@click.option("--body", "-b", "body_content", help="Blog post body content")
@click.option(
    "--file",
    "-f",
    "body_file",
    type=click.Path(exists=True, path_type=Path),  # type: ignore[type-var]
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
@handle_errors
def create_blogpost(
    space: str,
    title: str,
    body_content: str | None,
    body_file: Path | None,
    status: str,
    output: str,
) -> None:
    """Create a new blog post."""
    space_key = validate_space_key(space)
    title = validate_title(title)

    if body_file:
        content = read_file_content(body_file)
        is_markdown = is_markdown_file(body_file)
    elif body_content:
        content = body_content
        is_markdown = False
    else:
        raise ValidationError("Either --body or --file is required")

    client = get_confluence_client()
    space_id = get_space_id(client, space_key)

    if is_markdown:
        content = markdown_to_xhtml(content)

    blogpost_data: dict[str, Any] = {
        "spaceId": space_id,
        "status": status,
        "title": title,
        "body": {"representation": "storage", "value": content},
    }

    result = client.post(
        "/api/v2/blogposts", json_data=blogpost_data, operation="create blog post"
    )

    if output == "json":
        click.echo(format_json(result))
    else:
        click.echo(format_blogpost(result))

    print_success(f"Created blog post '{title}' with ID {result['id']}")
