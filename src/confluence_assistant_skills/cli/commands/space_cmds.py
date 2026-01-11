"""Space management commands - CLI-only implementation."""

from __future__ import annotations

from typing import Any

import click

from confluence_assistant_skills_lib import (
    ValidationError,
    format_json,
    format_page,
    format_space,
    format_table,
    get_confluence_client,
    handle_errors,
    print_info,
    print_success,
    print_warning,
    validate_limit,
    validate_space_key,
)


def _get_space_by_key(client: Any, space_key: str) -> dict[str, Any]:
    """Get space details by space key."""
    spaces = list(
        client.paginate(
            "/api/v2/spaces", params={"keys": space_key}, operation="get space"
        )
    )
    if not spaces:
        raise ValidationError(f"Space not found: {space_key}")
    return spaces[0]


@click.group()
def space() -> None:
    """Manage Confluence spaces."""
    pass


@space.command(name="list")
@click.option("--type", "space_type", help="Filter by space type (global, personal)")
@click.option("--query", "-q", help="Search query")
@click.option("--status", help="Filter by status (current, archived)")
@click.option("--limit", "-l", type=int, default=50, help="Maximum spaces to return")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def list_spaces(
    space_type: str | None,
    query: str | None,
    status: str | None,
    limit: int,
    output: str,
) -> None:
    """List all accessible Confluence spaces."""
    limit = validate_limit(limit, max_value=250)

    client = get_confluence_client()

    params: dict[str, Any] = {"limit": min(limit, 25)}  # API max per request

    if space_type:
        if space_type.lower() not in ("global", "personal"):
            raise ValidationError("Space type must be 'global' or 'personal'")
        params["type"] = space_type.lower()

    if status:
        if status.lower() not in ("current", "archived"):
            raise ValidationError("Status must be 'current' or 'archived'")
        params["status"] = status.lower()

    spaces = []
    for space_item in client.paginate("/api/v2/spaces", params=params, operation="list spaces"):
        if query:
            # Filter by name locally since API doesn't support name search well
            if query.lower() not in space_item.get("name", "").lower():
                continue
        spaces.append(space_item)
        if len(spaces) >= limit:
            break

    if output == "json":
        click.echo(format_json({"spaces": spaces, "count": len(spaces)}))
    else:
        if not spaces:
            click.echo("No spaces found matching criteria.")
        else:
            data = []
            for s in spaces:
                data.append({
                    "key": s.get("key", ""),
                    "name": s.get("name", ""),
                    "type": s.get("type", ""),
                    "status": s.get("status", ""),
                })

            click.echo(
                format_table(
                    data,
                    columns=["key", "name", "type", "status"],
                    headers=["Key", "Name", "Type", "Status"],
                )
            )

    print_success(f"Found {len(spaces)} space(s)")


@space.command(name="get")
@click.argument("space_key")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def get_space(
    space_key: str,
    output: str,
) -> None:
    """Get details for a specific space."""
    space_key = validate_space_key(space_key)
    client = get_confluence_client()

    result = _get_space_by_key(client, space_key)

    if output == "json":
        click.echo(format_json(result))
    else:
        click.echo(format_space(result))

    print_success(f"Retrieved space {space_key}")


@space.command(name="create")
@click.option(
    "--key", "-k", required=True, help="Space key (2-255 chars, alphanumeric)"
)
@click.option("--name", "-n", required=True, help="Space name")
@click.option("--description", "-d", help="Space description")
@click.option(
    "--type", "space_type", default="global", help="Space type (global or personal)"
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def create_space(
    key: str,
    name: str,
    description: str | None,
    space_type: str,
    output: str,
) -> None:
    """Create a new Confluence space."""
    # Validate space key
    key = validate_space_key(key)

    if not name or not name.strip():
        raise ValidationError("Space name is required")

    if space_type.lower() not in ("global", "personal"):
        raise ValidationError("Space type must be 'global' or 'personal'")

    client = get_confluence_client()

    space_data: dict[str, Any] = {
        "key": key,
        "name": name.strip(),
        "type": space_type.lower(),
    }

    if description:
        space_data["description"] = {
            "representation": "plain",
            "value": description.strip(),
        }

    result = client.post("/api/v2/spaces", json_data=space_data, operation="create space")

    if output == "json":
        click.echo(format_json(result))
    else:
        click.echo(format_space(result))

    print_success(f"Created space '{name}' with key {key}")


@space.command(name="update")
@click.argument("space_key")
@click.option("--name", "-n", help="New space name")
@click.option("--description", "-d", help="New space description")
@click.option("--homepage", help="Homepage page ID")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def update_space(
    space_key: str,
    name: str | None,
    description: str | None,
    homepage: str | None,
    output: str,
) -> None:
    """Update a Confluence space."""
    space_key = validate_space_key(space_key)

    if not any([name, description, homepage]):
        raise ValidationError(
            "At least one of --name, --description, or --homepage is required"
        )

    client = get_confluence_client()

    # Get current space
    current_space = _get_space_by_key(client, space_key)
    space_id = current_space["id"]

    update_data: dict[str, Any] = {
        "name": name.strip() if name else current_space.get("name"),
        "type": current_space.get("type", "global"),
    }

    if description is not None:
        update_data["description"] = {
            "representation": "plain",
            "value": description.strip(),
        }

    if homepage:
        update_data["homepageId"] = homepage

    result = client.put(
        f"/api/v2/spaces/{space_id}", json_data=update_data, operation="update space"
    )

    if output == "json":
        click.echo(format_json(result))
    else:
        click.echo(format_space(result))

    print_success(f"Updated space {space_key}")


@space.command(name="delete")
@click.argument("space_key")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
@handle_errors
def delete_space(
    space_key: str,
    force: bool,
) -> None:
    """Delete a Confluence space.

    WARNING: This action is IRREVERSIBLE. All pages, blog posts,
    attachments, and other content will be permanently deleted.
    """
    space_key = validate_space_key(space_key)
    client = get_confluence_client()

    # Get space details first
    current_space = _get_space_by_key(client, space_key)
    space_id = current_space["id"]
    space_name = current_space.get("name", space_key)

    if not force:
        click.echo(f"\n⚠️⚠️⚠️  WARNING: IRREVERSIBLE ACTION ⚠️⚠️⚠️")
        click.echo(f"\nYou are about to DELETE the space: {space_name} ({space_key})")
        click.echo("\nThis will PERMANENTLY delete:")
        click.echo("  - ALL pages in the space")
        click.echo("  - ALL blog posts")
        click.echo("  - ALL attachments")
        click.echo("  - ALL comments")
        click.echo("  - ALL page history")
        print_warning("\nThis action CANNOT be undone!")

        if not click.confirm("\nAre you ABSOLUTELY sure?", default=False):
            click.echo("Delete cancelled.")
            return

        # Double confirmation for safety
        if not click.confirm(
            f"\nType 'yes' to confirm deletion of space {space_key}",
            default=False,
        ):
            click.echo("Delete cancelled.")
            return

    # Start async deletion task
    client.delete(f"/api/v2/spaces/{space_id}", operation="delete space")

    print_success(f"Space '{space_name}' ({space_key}) deletion started")
    print_info("Note: Space deletion may take some time to complete depending on content volume.")


@space.command(name="content")
@click.argument("space_key")
@click.option("--depth", help="Tree depth (root, children, all)")
@click.option("--status", help="Filter by status (current, archived, draft)")
@click.option("--include-archived", is_flag=True, help="Include archived content")
@click.option("--limit", "-l", type=int, default=50, help="Maximum items to return")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def get_space_content(
    space_key: str,
    depth: str | None,
    status: str | None,
    include_archived: bool,
    limit: int,
    output: str,
) -> None:
    """Get content in a space."""
    space_key = validate_space_key(space_key)
    limit = validate_limit(limit, max_value=250)

    client = get_confluence_client()

    # Get space to verify it exists and get ID
    current_space = _get_space_by_key(client, space_key)
    space_id = current_space["id"]

    params: dict[str, Any] = {"limit": min(limit, 25)}

    if status:
        if status.lower() not in ("current", "archived", "draft"):
            raise ValidationError("Status must be 'current', 'archived', or 'draft'")
        params["status"] = status.lower()

    if depth:
        if depth.lower() not in ("root", "children", "all"):
            raise ValidationError("Depth must be 'root', 'children', or 'all'")
        if depth.lower() == "root":
            params["depth"] = "root"

    pages = []
    for page in client.paginate(
        f"/api/v2/spaces/{space_id}/pages", params=params, operation="get space content"
    ):
        if not include_archived and page.get("status") == "archived":
            continue
        pages.append(page)
        if len(pages) >= limit:
            break

    if output == "json":
        click.echo(format_json({
            "space": {"key": space_key, "name": current_space.get("name")},
            "pages": pages,
            "count": len(pages),
        }))
    else:
        click.echo(f"\nSpace: {current_space.get('name')} ({space_key})")
        click.echo(f"{'=' * 60}\n")

        if not pages:
            click.echo("No content found matching criteria.")
        else:
            data = []
            for p in pages:
                data.append({
                    "id": p.get("id", ""),
                    "title": p.get("title", "")[:50],
                    "status": p.get("status", ""),
                    "version": p.get("version", {}).get("number", "?"),
                })

            click.echo(
                format_table(
                    data,
                    columns=["id", "title", "status", "version"],
                    headers=["ID", "Title", "Status", "Version"],
                )
            )

    print_success(f"Found {len(pages)} page(s) in space {space_key}")


@space.command(name="settings")
@click.argument("space_key")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def get_space_settings(
    space_key: str,
    output: str,
) -> None:
    """Get settings for a space."""
    space_key = validate_space_key(space_key)
    client = get_confluence_client()

    # Get space details with expanded info
    current_space = _get_space_by_key(client, space_key)
    space_id = current_space["id"]

    # Use v1 API for settings as v2 doesn't have a dedicated settings endpoint
    # The space details from v2 already contain most settings
    settings = {
        "space": {
            "id": space_id,
            "key": current_space.get("key"),
            "name": current_space.get("name"),
            "type": current_space.get("type"),
            "status": current_space.get("status"),
            "homepageId": current_space.get("homepageId"),
        },
        "description": current_space.get("description"),
        "icon": current_space.get("icon"),
        "createdAt": current_space.get("createdAt"),
    }

    if output == "json":
        click.echo(format_json(settings))
    else:
        click.echo(f"\nSpace Settings: {current_space.get('name')} ({space_key})")
        click.echo(f"{'=' * 60}\n")

        click.echo(f"ID: {space_id}")
        click.echo(f"Key: {current_space.get('key')}")
        click.echo(f"Name: {current_space.get('name')}")
        click.echo(f"Type: {current_space.get('type')}")
        click.echo(f"Status: {current_space.get('status')}")

        homepage_id = current_space.get("homepageId")
        if homepage_id:
            click.echo(f"Homepage ID: {homepage_id}")

        desc = current_space.get("description", {})
        if desc and desc.get("value"):
            click.echo(f"\nDescription: {desc.get('value')}")

        created_at = current_space.get("createdAt")
        if created_at:
            click.echo(f"\nCreated: {created_at[:10]}")

    print_success(f"Retrieved settings for space {space_key}")
