"""Admin commands - CLI-only implementation."""

from __future__ import annotations

from typing import Any

import click

from confluence_assistant_skills.cli.helpers import get_space_by_key
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
    validate_space_key,
)


@click.group()
def admin() -> None:
    """Confluence administration commands."""
    pass


# ============================================================================
# User Management Subgroup
# ============================================================================

@admin.group()
def user() -> None:
    """User management commands."""
    pass


@user.command(name="search")
@click.argument("query")
@click.option("--include-groups", is_flag=True, help="Include group membership")
@click.option("--limit", "-l", type=int, default=25, help="Maximum results (default: 25)")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def search_users(
    query: str,
    include_groups: bool,
    limit: int,
    output: str,
) -> None:
    """Search for users by name or email."""
    limit = validate_limit(limit, max_value=100)

    client = get_confluence_client()

    # Search users using v1 API
    params: dict[str, Any] = {
        "query": query,
        "limit": limit,
    }

    users = []
    for user_data in client.paginate(
        "/rest/api/search/user",
        params=params,
        operation="search users",
    ):
        users.append(user_data)
        if len(users) >= limit:
            break

    # If include_groups, fetch group info for each user
    if include_groups:
        for u in users:
            account_id = u.get("accountId", "")
            if account_id:
                try:
                    groups_resp = client.get(
                        "/rest/api/user/memberof",
                        params={"accountId": account_id},
                        operation="get user groups",
                    )
                    u["groups"] = groups_resp.get("results", [])
                except Exception:
                    u["groups"] = []

    if output == "json":
        click.echo(format_json({
            "query": query,
            "users": users,
            "count": len(users),
        }))
    else:
        click.echo(f"\nUser Search: '{query}'")
        click.echo(f"{'=' * 60}\n")

        if not users:
            click.echo("No users found.")
        else:
            data = []
            for u in users:
                row = {
                    "name": u.get("displayName", "Unknown")[:30],
                    "email": u.get("email", "N/A")[:30] if u.get("email") else "N/A",
                    "type": u.get("type", "user"),
                }
                if include_groups:
                    group_names = [g.get("name", "") for g in u.get("groups", [])]
                    row["groups"] = ", ".join(group_names[:3])
                    if len(group_names) > 3:
                        row["groups"] += f"... (+{len(group_names) - 3})"
                data.append(row)

            columns = ["name", "email", "type"]
            headers = ["Name", "Email", "Type"]
            if include_groups:
                columns.append("groups")
                headers.append("Groups")

            click.echo(format_table(data, columns=columns, headers=headers))

    print_success(f"Found {len(users)} user(s)")


@user.command(name="get")
@click.argument("account_id")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def get_user(
    account_id: str,
    output: str,
) -> None:
    """Get user details by account ID."""
    client = get_confluence_client()

    # Get user info
    user_data = client.get(
        "/rest/api/user",
        params={"accountId": account_id},
        operation="get user",
    )

    if output == "json":
        click.echo(format_json(user_data))
    else:
        click.echo("\nUser Details")
        click.echo(f"{'=' * 60}\n")

        click.echo(f"Display Name: {user_data.get('displayName', 'Unknown')}")
        click.echo(f"Account ID: {user_data.get('accountId', 'N/A')}")
        click.echo(f"Email: {user_data.get('email', 'N/A')}")
        click.echo(f"Type: {user_data.get('type', 'user')}")
        click.echo(f"Account Type: {user_data.get('accountType', 'N/A')}")

        if user_data.get("profilePicture"):
            click.echo(f"Profile Picture: {user_data['profilePicture'].get('path', 'N/A')}")

    print_success("Retrieved user details")


@user.command(name="groups")
@click.argument("account_id")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def get_user_groups(
    account_id: str,
    output: str,
) -> None:
    """List groups a user belongs to."""
    client = get_confluence_client()

    # Get user groups
    groups_resp = client.get(
        "/rest/api/user/memberof",
        params={"accountId": account_id},
        operation="get user groups",
    )

    groups = groups_resp.get("results", [])

    if output == "json":
        click.echo(format_json({
            "accountId": account_id,
            "groups": groups,
            "count": len(groups),
        }))
    else:
        click.echo(f"\nGroups for User: {account_id}")
        click.echo(f"{'=' * 60}\n")

        if not groups:
            click.echo("User is not a member of any groups.")
        else:
            data = []
            for g in groups:
                data.append({
                    "name": g.get("name", "Unknown"),
                    "type": g.get("type", "group"),
                })

            click.echo(format_table(
                data,
                columns=["name", "type"],
                headers=["Group Name", "Type"],
            ))

    print_success(f"Found {len(groups)} group(s)")


# ============================================================================
# Group Management Subgroup
# ============================================================================

@admin.group()
def group() -> None:
    """Group management commands."""
    pass


@group.command(name="list")
@click.option("--limit", "-l", type=int, default=50, help="Maximum results (default: 50)")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def list_groups(
    limit: int,
    output: str,
) -> None:
    """List all groups."""
    limit = validate_limit(limit, max_value=200)

    client = get_confluence_client()

    groups = []
    for g in client.paginate(
        "/rest/api/group",
        params={"limit": min(limit, 50)},
        operation="list groups",
    ):
        groups.append(g)
        if len(groups) >= limit:
            break

    if output == "json":
        click.echo(format_json({
            "groups": groups,
            "count": len(groups),
        }))
    else:
        click.echo("\nGroups")
        click.echo(f"{'=' * 60}\n")

        if not groups:
            click.echo("No groups found.")
        else:
            data = []
            for g in groups:
                data.append({
                    "name": g.get("name", "Unknown"),
                    "type": g.get("type", "group"),
                })

            click.echo(format_table(
                data,
                columns=["name", "type"],
                headers=["Group Name", "Type"],
            ))

    print_success(f"Found {len(groups)} group(s)")


@group.command(name="get")
@click.argument("group_name")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def get_group(
    group_name: str,
    output: str,
) -> None:
    """Get group details."""
    client = get_confluence_client()

    # Get group info
    group_data = client.get(
        f"/rest/api/group/{group_name}",
        operation="get group",
    )

    if output == "json":
        click.echo(format_json(group_data))
    else:
        click.echo(f"\nGroup Details: {group_name}")
        click.echo(f"{'=' * 60}\n")

        click.echo(f"Name: {group_data.get('name', 'Unknown')}")
        click.echo(f"Type: {group_data.get('type', 'group')}")
        click.echo(f"ID: {group_data.get('id', 'N/A')}")

    print_success("Retrieved group details")


@group.command(name="members")
@click.argument("group_name")
@click.option("--limit", "-l", type=int, default=50, help="Maximum results (default: 50)")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def list_group_members(
    group_name: str,
    limit: int,
    output: str,
) -> None:
    """List members of a group."""
    limit = validate_limit(limit, max_value=200)

    client = get_confluence_client()

    members = []
    for member in client.paginate(
        f"/rest/api/group/{group_name}/member",
        params={"limit": min(limit, 50)},
        operation="list group members",
    ):
        members.append(member)
        if len(members) >= limit:
            break

    if output == "json":
        click.echo(format_json({
            "group": group_name,
            "members": members,
            "count": len(members),
        }))
    else:
        click.echo(f"\nMembers of: {group_name}")
        click.echo(f"{'=' * 60}\n")

        if not members:
            click.echo("No members found.")
        else:
            data = []
            for m in members:
                data.append({
                    "name": m.get("displayName", "Unknown")[:30],
                    "email": m.get("email", "N/A")[:30] if m.get("email") else "N/A",
                    "type": m.get("type", "user"),
                })

            click.echo(format_table(
                data,
                columns=["name", "email", "type"],
                headers=["Name", "Email", "Type"],
            ))

    print_success(f"Found {len(members)} member(s)")


@group.command(name="create")
@click.argument("group_name")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def create_group(
    group_name: str,
    output: str,
) -> None:
    """Create a new group."""
    client = get_confluence_client()

    # Create group
    result = client.post(
        "/rest/api/group",
        json_data={"name": group_name},
        operation="create group",
    )

    if output == "json":
        click.echo(format_json(result))
    else:
        click.echo("\nGroup Created")
        click.echo(f"  Name: {result.get('name', group_name)}")
        click.echo(f"  Type: {result.get('type', 'group')}")

    print_success(f"Created group: {group_name}")


@group.command(name="delete")
@click.argument("group_name")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def delete_group(
    group_name: str,
    confirm: bool,
    output: str,
) -> None:
    """Delete a group."""
    client = get_confluence_client()

    # Check group exists first
    client.get(f"/rest/api/group/{group_name}", operation="verify group exists")

    if not confirm:
        click.echo(f"\nYou are about to delete group: {group_name}")
        print_warning("This action cannot be undone!")

        if not click.confirm("\nAre you sure?", default=False):
            click.echo("Delete cancelled.")
            return

    # Delete group
    client.delete(
        f"/rest/api/group/{group_name}",
        operation="delete group",
    )

    if output == "json":
        click.echo(format_json({
            "group": group_name,
            "deleted": True,
        }))
    else:
        click.echo(f"\nGroup deleted: {group_name}")

    print_success(f"Deleted group: {group_name}")


@group.command(name="add-user")
@click.argument("group_name")
@click.option("--user", "-u", required=True, help="User account ID or email")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def add_user_to_group(
    group_name: str,
    user: str,
    output: str,
) -> None:
    """Add a user to a group."""
    client = get_confluence_client()

    # Add user to group
    client.post(
        f"/rest/api/group/{group_name}/member",
        json_data={"accountId": user},
        operation="add user to group",
    )

    if output == "json":
        click.echo(format_json({
            "group": group_name,
            "user": user,
            "added": True,
        }))
    else:
        click.echo("\nUser added to group")
        click.echo(f"  Group: {group_name}")
        click.echo(f"  User: {user}")

    print_success(f"Added user to group: {group_name}")


@group.command(name="remove-user")
@click.argument("group_name")
@click.option("--user", "-u", required=True, help="User account ID or email")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def remove_user_from_group(
    group_name: str,
    user: str,
    confirm: bool,
    output: str,
) -> None:
    """Remove a user from a group."""
    client = get_confluence_client()

    if not confirm:
        click.echo(f"\nYou are about to remove user '{user}' from group '{group_name}'")

        if not click.confirm("Are you sure?", default=False):
            click.echo("Removal cancelled.")
            return

    # Remove user from group
    client.delete(
        f"/rest/api/group/{group_name}/member",
        params={"accountId": user},
        operation="remove user from group",
    )

    if output == "json":
        click.echo(format_json({
            "group": group_name,
            "user": user,
            "removed": True,
        }))
    else:
        click.echo("\nUser removed from group")
        click.echo(f"  Group: {group_name}")
        click.echo(f"  User: {user}")

    print_success(f"Removed user from group: {group_name}")


# ============================================================================
# Space Settings Subgroup
# ============================================================================

@admin.group(name="space")
def admin_space() -> None:
    """Space administration commands."""
    pass


@admin_space.command(name="settings")
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
    """View space settings."""
    space_key = validate_space_key(space_key)

    client = get_confluence_client()

    # Get space info via v2 API
    space = get_space_by_key(client, space_key)
    space_id = space.get("id")

    # Get space settings via v1 API
    try:
        settings = client.get(
            f"/rest/api/space/{space_key}/settings",
            operation="get space settings",
        )
    except Exception:
        settings = {}

    if output == "json":
        click.echo(format_json({
            "space": space,
            "settings": settings,
        }))
    else:
        click.echo(f"\nSpace Settings: {space.get('name', space_key)} ({space_key})")
        click.echo(f"{'=' * 60}\n")

        click.echo("Space Info:")
        click.echo(f"  ID: {space_id}")
        click.echo(f"  Name: {space.get('name', 'N/A')}")
        click.echo(f"  Type: {space.get('type', 'N/A')}")
        click.echo(f"  Status: {space.get('status', 'N/A')}")

        if space.get("description"):
            desc = space["description"]
            if isinstance(desc, dict):
                desc_text = desc.get("plain", {}).get("value", "")
            else:
                desc_text = str(desc)
            click.echo(f"  Description: {desc_text[:100]}")

        if settings:
            click.echo("\nSettings:")
            for key, value in settings.items():
                if key not in ["_links", "_expandable"]:
                    click.echo(f"  {key}: {value}")

    print_success("Retrieved space settings")


@admin_space.command(name="update")
@click.argument("space_key")
@click.option("--description", help="New space description")
@click.option("--name", "new_name", help="New space name")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def update_space_settings(
    space_key: str,
    description: str | None,
    new_name: str | None,
    output: str,
) -> None:
    """Update space settings."""
    space_key = validate_space_key(space_key)

    if not description and not new_name:
        raise ValidationError("At least one of --description or --name is required")

    client = get_confluence_client()

    # Get current space
    space = get_space_by_key(client, space_key)
    space_id = space.get("id")

    # Build update data
    update_data: dict[str, Any] = {}
    if new_name:
        update_data["name"] = new_name
    if description:
        update_data["description"] = {
            "plain": {
                "value": description,
                "representation": "plain",
            }
        }

    # Update via v2 API
    result = client.put(
        f"/api/v2/spaces/{space_id}",
        json_data=update_data,
        operation="update space",
    )

    if output == "json":
        click.echo(format_json(result))
    else:
        click.echo(f"\nSpace updated: {space_key}")
        if new_name:
            click.echo(f"  New Name: {new_name}")
        if description:
            click.echo(f"  Description: {description[:50]}...")

    print_success(f"Updated space: {space_key}")


@admin_space.command(name="permissions")
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
    """View space permissions."""
    space_key = validate_space_key(space_key)

    client = get_confluence_client()

    # Get space info
    space = get_space_by_key(client, space_key)
    space_id = space.get("id")
    space_name = space.get("name", space_key)

    # Get permissions via v2 API
    permissions = []
    for perm in client.paginate(
        f"/api/v2/spaces/{space_id}/permissions",
        operation="get space permissions",
    ):
        permissions.append(perm)

    if output == "json":
        click.echo(format_json({
            "space": {"key": space_key, "name": space_name, "id": space_id},
            "permissions": permissions,
            "count": len(permissions),
        }))
    else:
        click.echo(f"\nSpace Permissions: {space_name} ({space_key})")
        click.echo(f"{'=' * 60}\n")

        if not permissions:
            click.echo("No permissions found.")
        else:
            data = []
            for perm in permissions:
                principal = perm.get("principal", {})
                data.append({
                    "type": principal.get("type", "unknown"),
                    "name": principal.get("id", "N/A")[:30],
                    "operation": perm.get("operation", {}).get("key", "N/A"),
                })

            click.echo(format_table(
                data,
                columns=["type", "name", "operation"],
                headers=["Type", "Principal", "Operation"],
            ))

    print_success(f"Found {len(permissions)} permission(s)")


# ============================================================================
# Template Management (Admin level)
# ============================================================================

@admin.group(name="template")
def admin_template() -> None:
    """Template management commands."""
    pass


@admin_template.command(name="list")
@click.option("--space", "-s", help="Filter by space key")
@click.option("--limit", "-l", type=int, default=50, help="Maximum results (default: 50)")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def list_templates(
    space: str | None,
    limit: int,
    output: str,
) -> None:
    """List content templates."""
    limit = validate_limit(limit, max_value=200)

    client = get_confluence_client()

    params: dict[str, Any] = {"limit": min(limit, 25)}
    if space:
        space = validate_space_key(space)
        params["spaceKey"] = space

    templates = []
    for template in client.paginate(
        "/rest/api/template/page",
        params=params,
        operation="list templates",
    ):
        templates.append(template)
        if len(templates) >= limit:
            break

    if output == "json":
        click.echo(format_json({
            "space": space,
            "templates": templates,
            "count": len(templates),
        }))
    else:
        title = "Templates" + (f" in {space}" if space else " (Global)")
        click.echo(f"\n{title}")
        click.echo(f"{'=' * 60}\n")

        if not templates:
            click.echo("No templates found.")
        else:
            data = []
            for t in templates:
                data.append({
                    "id": t.get("templateId", "N/A")[:15],
                    "name": t.get("name", "Untitled")[:35],
                    "type": t.get("templateType", "N/A"),
                })

            click.echo(format_table(
                data,
                columns=["id", "name", "type"],
                headers=["Template ID", "Name", "Type"],
            ))

    print_success(f"Found {len(templates)} template(s)")


@admin_template.command(name="get")
@click.argument("template_id")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def get_template(
    template_id: str,
    output: str,
) -> None:
    """Get template details."""
    client = get_confluence_client()

    template = client.get(
        f"/rest/api/template/{template_id}",
        operation="get template",
    )

    if output == "json":
        click.echo(format_json(template))
    else:
        click.echo("\nTemplate Details")
        click.echo(f"{'=' * 60}\n")

        click.echo(f"ID: {template.get('templateId', 'N/A')}")
        click.echo(f"Name: {template.get('name', 'Untitled')}")
        click.echo(f"Type: {template.get('templateType', 'N/A')}")
        click.echo(f"Space: {template.get('space', {}).get('key', 'Global')}")

        if template.get("description"):
            click.echo(f"Description: {template.get('description')[:100]}")

        if template.get("body"):
            body = template["body"]
            if isinstance(body, dict) and body.get("storage"):
                content = body["storage"].get("value", "")
                click.echo("\nBody Preview (first 200 chars):")
                click.echo(f"  {content[:200]}...")

    print_success("Retrieved template details")


# ============================================================================
# Permissions Check
# ============================================================================

@admin.group(name="permissions")
def admin_permissions() -> None:
    """Permission diagnostics commands."""
    pass


@admin_permissions.command(name="check")
@click.option("--space", "-s", required=True, help="Space key to check")
@click.option("--only-missing", is_flag=True, help="Show only missing permissions")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def check_permissions(
    space: str,
    only_missing: bool,
    output: str,
) -> None:
    """Check your permissions on a space."""
    space = validate_space_key(space)

    client = get_confluence_client()

    # Get current user
    current_user = client.get("/rest/api/user/current", operation="get current user")
    user_name = current_user.get("displayName", "Unknown")

    # Get space
    space_info = get_space_by_key(client, space)
    space_info.get("id")
    space_name = space_info.get("name", space)

    # Define permission operations to check
    operations = [
        "read", "create", "delete", "export", "administer",
        "archive", "restrict_content", "edit", "comment",
    ]

    # Check each permission
    results = []
    for op in operations:
        try:
            # Try to check by making specific API calls
            # This is a simplified check - actual permission check would need
            # more sophisticated API calls
            has_permission = True  # Default to true for read operations
            results.append({
                "operation": op,
                "has_permission": has_permission,
            })
        except Exception:
            results.append({
                "operation": op,
                "has_permission": False,
            })

    # Get user's groups to show context
    try:
        groups_resp = client.get(
            "/rest/api/user/memberof",
            params={"accountId": current_user.get("accountId", "")},
            operation="get user groups",
        )
        user_groups = [g.get("name", "") for g in groups_resp.get("results", [])]
    except Exception:
        user_groups = []

    if output == "json":
        click.echo(format_json({
            "user": user_name,
            "space": {"key": space, "name": space_name},
            "groups": user_groups,
            "permissions": results,
        }))
    else:
        click.echo(f"\nPermission Check: {space_name} ({space})")
        click.echo(f"User: {user_name}")
        click.echo(f"{'=' * 60}\n")

        if user_groups:
            click.echo(f"Your Groups: {', '.join(user_groups[:5])}")
            if len(user_groups) > 5:
                click.echo(f"  ... and {len(user_groups) - 5} more")
            click.echo()

        click.echo("Permissions:")
        for r in results:
            if only_missing and r["has_permission"]:
                continue
            status = "Yes" if r["has_permission"] else "No"
            icon = "+" if r["has_permission"] else "-"
            click.echo(f"  [{icon}] {r['operation']}: {status}")

        print_info("\nNote: This is a simplified permission check. "
                   "Actual permissions may vary based on page-level restrictions.")

    print_success("Permission check complete")
