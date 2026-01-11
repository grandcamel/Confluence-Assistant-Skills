"""Permission management commands - CLI-only implementation."""

from __future__ import annotations

from typing import Any

import click

from confluence_assistant_skills_lib import (
    format_json,
    format_table,
    get_confluence_client,
    handle_errors,
    print_success,
    print_warning,
    validate_page_id,
    validate_space_key,
)

from confluence_assistant_skills.cli.helpers import get_space_by_key


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
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def get_page_restrictions(
    page_id: str,
    output: str,
) -> None:
    """Get restrictions on a page."""
    page_id = validate_page_id(page_id)

    client = get_confluence_client()

    # Get page info
    page = client.get(f"/api/v2/pages/{page_id}", operation="get page")
    page_title = page.get("title", "Unknown")

    # Get restrictions using v1 API (v2 doesn't have full restriction support)
    restrictions = client.get(
        f"/rest/api/content/{page_id}/restriction",
        operation="get restrictions",
    )

    if output == "json":
        click.echo(format_json({
            "page": {"id": page_id, "title": page_title},
            "restrictions": restrictions,
        }))
    else:
        click.echo(f"\nRestrictions on: {page_title} ({page_id})")
        click.echo(f"{'=' * 60}\n")

        results = restrictions.get("results", restrictions)
        if isinstance(results, dict):
            # v1 API returns nested structure
            read_restrictions = results.get("read", {}).get("restrictions", {})
            update_restrictions = results.get("update", {}).get("restrictions", {})

            # Read restrictions
            read_users = read_restrictions.get("user", {}).get("results", [])
            read_groups = read_restrictions.get("group", {}).get("results", [])

            # Update restrictions
            update_users = update_restrictions.get("user", {}).get("results", [])
            update_groups = update_restrictions.get("group", {}).get("results", [])

            has_restrictions = read_users or read_groups or update_users or update_groups

            if not has_restrictions:
                click.echo("No restrictions set on this page.")
            else:
                if read_users or read_groups:
                    click.echo("READ restrictions:")
                    for user in read_users:
                        click.echo(f"  - User: {user.get('displayName', user.get('username', 'Unknown'))}")
                    for group in read_groups:
                        click.echo(f"  - Group: {group.get('name', 'Unknown')}")
                    click.echo()

                if update_users or update_groups:
                    click.echo("UPDATE restrictions:")
                    for user in update_users:
                        click.echo(f"  - User: {user.get('displayName', user.get('username', 'Unknown'))}")
                    for group in update_groups:
                        click.echo(f"  - Group: {group.get('name', 'Unknown')}")
        else:
            click.echo("No restrictions found.")

    print_success("Retrieved page restrictions")


@page_permission.command(name="add")
@click.argument("page_id")
@click.option("--user", help="User to restrict (account ID or username)")
@click.option("--group", "group_name", help="Group to restrict")
@click.option(
    "--operation",
    type=click.Choice(["read", "update"]),
    required=True,
    help="Operation to restrict",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def add_page_restriction(
    page_id: str,
    user: str | None,
    group_name: str | None,
    operation: str,
    output: str,
) -> None:
    """Add a restriction to a page.

    When adding restrictions, only specified users/groups will be able
    to perform the restricted operation.
    """
    page_id = validate_page_id(page_id)

    if not user and not group_name:
        raise ValidationError("Either --user or --group must be specified")

    client = get_confluence_client()

    # Get page info
    page = client.get(f"/api/v2/pages/{page_id}", operation="get page")
    page_title = page.get("title", "Unknown")

    # Build restriction data
    restriction_data: dict[str, Any] = {
        "operation": operation,
    }

    if user:
        restriction_data["restrictions"] = {
            "user": [{"type": "known", "accountId": user}]
        }
    elif group_name:
        restriction_data["restrictions"] = {
            "group": [{"type": "group", "name": group_name}]
        }

    # Add restriction using v1 API
    result = client.post(
        f"/rest/api/content/{page_id}/restriction",
        json_data=[restriction_data],
        operation="add restriction",
    )

    if output == "json":
        click.echo(format_json({
            "page": {"id": page_id, "title": page_title},
            "operation": operation,
            "user": user,
            "group": group_name,
            "result": result,
        }))
    else:
        click.echo(f"\nRestriction added to: {page_title}")
        click.echo(f"  Operation: {operation}")
        if user:
            click.echo(f"  User: {user}")
        if group_name:
            click.echo(f"  Group: {group_name}")

    print_success(f"Added {operation} restriction to page {page_id}")


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
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def remove_page_restriction(
    page_id: str,
    user: str | None,
    group_name: str | None,
    operation: str,
    remove_all: bool,
    output: str,
) -> None:
    """Remove a restriction from a page."""
    page_id = validate_page_id(page_id)

    if not user and not group_name and not remove_all:
        raise ValidationError("Either --user, --group, or --all must be specified")

    client = get_confluence_client()

    # Get page info
    page = client.get(f"/api/v2/pages/{page_id}", operation="get page")
    page_title = page.get("title", "Unknown")

    removed_count = 0

    if remove_all:
        # Remove all restrictions for operation
        client.delete(
            f"/rest/api/content/{page_id}/restriction/byOperation/{operation}",
            operation="remove all restrictions",
        )
        removed_count = 1  # At least the operation restriction set
    else:
        # Remove specific user or group
        if user:
            client.delete(
                f"/rest/api/content/{page_id}/restriction/byOperation/{operation}/user",
                params={"accountId": user},
                operation="remove user restriction",
            )
            removed_count += 1
        if group_name:
            client.delete(
                f"/rest/api/content/{page_id}/restriction/byOperation/{operation}/group/{group_name}",
                operation="remove group restriction",
            )
            removed_count += 1

    if output == "json":
        click.echo(format_json({
            "page": {"id": page_id, "title": page_title},
            "operation": operation,
            "removedUser": user,
            "removedGroup": group_name,
            "removedAll": remove_all,
        }))
    else:
        click.echo(f"\nRestriction removed from: {page_title}")
        click.echo(f"  Operation: {operation}")
        if remove_all:
            click.echo("  Removed: All restrictions for this operation")
        else:
            if user:
                click.echo(f"  User: {user}")
            if group_name:
                click.echo(f"  Group: {group_name}")

    print_success(f"Removed {operation} restriction(s) from page {page_id}")


# Space permissions
@permission.group(name="space")
def space_permission() -> None:
    """Manage space permissions."""
    pass


@space_permission.command(name="get")
@click.argument("space_key")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def get_space_permissions(
    space_key: str,
    output: str,
) -> None:
    """Get permissions for a space."""
    space_key = validate_space_key(space_key)

    client = get_confluence_client()

    # Get space info
    space = get_space_by_key(client, space_key)
    space_name = space.get("name", space_key)
    space_id = space.get("id")

    # Get permissions using v2 API
    permissions = list(client.paginate(
        f"/api/v2/spaces/{space_id}/permissions",
        operation="get space permissions",
    ))

    if output == "json":
        click.echo(format_json({
            "space": {"key": space_key, "name": space_name, "id": space_id},
            "permissions": permissions,
            "count": len(permissions),
        }))
    else:
        click.echo(f"\nPermissions for: {space_name} ({space_key})")
        click.echo(f"{'=' * 60}\n")

        if not permissions:
            click.echo("No explicit permissions set.")
        else:
            # Group by principal type
            user_perms: list[dict[str, Any]] = []
            group_perms: list[dict[str, Any]] = []

            for perm in permissions:
                principal = perm.get("principal", {})
                principal_type = principal.get("type", "unknown")
                operation = perm.get("operation", {})
                op_key = operation.get("key", "unknown")
                op_target = operation.get("targetType", "")

                entry = {
                    "id": perm.get("id", ""),
                    "operation": f"{op_key} ({op_target})" if op_target else op_key,
                    "name": principal.get("id", "Unknown"),
                }

                if principal_type == "user":
                    user_perms.append(entry)
                elif principal_type == "group":
                    entry["name"] = principal.get("id", "Unknown")
                    group_perms.append(entry)

            if user_perms:
                click.echo("User Permissions:")
                click.echo(format_table(
                    user_perms,
                    columns=["name", "operation"],
                    headers=["User", "Operation"],
                ))
                click.echo()

            if group_perms:
                click.echo("Group Permissions:")
                click.echo(format_table(
                    group_perms,
                    columns=["name", "operation"],
                    headers=["Group", "Operation"],
                ))

    print_success(f"Found {len(permissions)} permission(s)")


@space_permission.command(name="add")
@click.argument("space_key")
@click.option("--user", help="User to grant permission (account ID)")
@click.option("--group", "group_name", help="Group to grant permission")
@click.option(
    "--operation",
    required=True,
    help="Permission operation (read, create, delete, administer, etc.)",
)
@click.option(
    "--target",
    default="space",
    help="Target type (space, page, blogpost, comment, attachment)",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def add_space_permission(
    space_key: str,
    user: str | None,
    group_name: str | None,
    operation: str,
    target: str,
    output: str,
) -> None:
    """Add a permission to a space.

    Operations: read, create, delete, administer, archive, restrict_content, export
    Targets: space, page, blogpost, comment, attachment
    """
    space_key = validate_space_key(space_key)

    if not user and not group_name:
        raise ValidationError("Either --user or --group must be specified")

    client = get_confluence_client()

    # Get space info
    space = get_space_by_key(client, space_key)
    space_name = space.get("name", space_key)
    space_id = space.get("id")

    # Build permission data
    permission_data: dict[str, Any] = {
        "operation": {
            "key": operation,
            "targetType": target,
        },
    }

    if user:
        permission_data["principal"] = {
            "type": "user",
            "id": user,
        }
    elif group_name:
        permission_data["principal"] = {
            "type": "group",
            "id": group_name,
        }

    # Add permission using v2 API
    result = client.post(
        f"/api/v2/spaces/{space_id}/permissions",
        json_data=permission_data,
        operation="add space permission",
    )

    if output == "json":
        click.echo(format_json({
            "space": {"key": space_key, "name": space_name, "id": space_id},
            "permission": result,
        }))
    else:
        click.echo(f"\nPermission added to: {space_name}")
        click.echo(f"  Operation: {operation} ({target})")
        if user:
            click.echo(f"  User: {user}")
        if group_name:
            click.echo(f"  Group: {group_name}")
        click.echo(f"  Permission ID: {result.get('id', 'N/A')}")

    print_success(f"Added {operation} permission to space {space_key}")


@space_permission.command(name="remove")
@click.argument("space_key")
@click.option("--permission-id", "-p", help="Permission ID to remove")
@click.option("--user", help="User permission to remove (with --operation)")
@click.option("--group", "group_name", help="Group permission to remove (with --operation)")
@click.option("--operation", help="Operation to match (required with --user or --group)")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def remove_space_permission(
    space_key: str,
    permission_id: str | None,
    user: str | None,
    group_name: str | None,
    operation: str | None,
    output: str,
) -> None:
    """Remove a permission from a space.

    Either specify --permission-id directly, or use --user/--group with --operation
    to find and remove matching permissions.
    """
    space_key = validate_space_key(space_key)

    if not permission_id and not user and not group_name:
        raise ValidationError("Either --permission-id, --user, or --group must be specified")

    if (user or group_name) and not operation:
        raise ValidationError("--operation is required when using --user or --group")

    client = get_confluence_client()

    # Get space info
    space = get_space_by_key(client, space_key)
    space_name = space.get("name", space_key)
    space_id = space.get("id")

    removed_ids: list[str] = []

    if permission_id:
        # Direct removal by ID
        client.delete(
            f"/api/v2/spaces/{space_id}/permissions/{permission_id}",
            operation="remove permission",
        )
        removed_ids.append(permission_id)
    else:
        # Find and remove matching permissions
        permissions = list(client.paginate(
            f"/api/v2/spaces/{space_id}/permissions",
            operation="get permissions",
        ))

        for perm in permissions:
            principal = perm.get("principal", {})
            perm_op = perm.get("operation", {}).get("key", "")

            if perm_op != operation:
                continue

            if user and principal.get("type") == "user" and principal.get("id") == user:
                client.delete(
                    f"/api/v2/spaces/{space_id}/permissions/{perm['id']}",
                    operation="remove user permission",
                )
                removed_ids.append(perm["id"])
            elif group_name and principal.get("type") == "group" and principal.get("id") == group_name:
                client.delete(
                    f"/api/v2/spaces/{space_id}/permissions/{perm['id']}",
                    operation="remove group permission",
                )
                removed_ids.append(perm["id"])

    if output == "json":
        click.echo(format_json({
            "space": {"key": space_key, "name": space_name, "id": space_id},
            "removedPermissions": removed_ids,
            "count": len(removed_ids),
        }))
    else:
        click.echo(f"\nPermission(s) removed from: {space_name}")
        if permission_id:
            click.echo(f"  Permission ID: {permission_id}")
        else:
            if user:
                click.echo(f"  User: {user}")
            if group_name:
                click.echo(f"  Group: {group_name}")
            click.echo(f"  Operation: {operation}")

        if not removed_ids:
            print_warning("No matching permissions found to remove")
        else:
            click.echo(f"  Removed: {len(removed_ids)} permission(s)")

    if removed_ids:
        print_success(f"Removed {len(removed_ids)} permission(s) from space {space_key}")
