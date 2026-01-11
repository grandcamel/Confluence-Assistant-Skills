"""Watch/notification commands - CLI-only implementation."""

from __future__ import annotations

from typing import Any

import click

from confluence_assistant_skills_lib import (
    ValidationError,
    format_json,
    format_table,
    get_confluence_client,
    handle_errors,
    print_success,
    validate_page_id,
    validate_space_key,
)


def _get_current_user(client: Any) -> dict[str, Any]:
    """Get current user info."""
    return client.get("/rest/api/user/current", operation="get current user")


def _get_space_by_key(client: Any, space_key: str) -> dict[str, Any]:
    """Get space by key."""
    spaces = list(client.paginate(
        "/api/v2/spaces",
        params={"keys": space_key},
        operation="get space",
    ))
    if not spaces:
        raise ValidationError(f"Space not found: {space_key}")
    return spaces[0]


@click.group()
def watch() -> None:
    """Manage content watching and notifications."""
    pass


@watch.command(name="page")
@click.argument("page_id")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def watch_page(
    page_id: str,
    output: str,
) -> None:
    """Start watching a page.

    You will receive notifications when the page is updated.
    """
    page_id = validate_page_id(page_id)

    client = get_confluence_client()

    # Get page info
    page = client.get(f"/api/v2/pages/{page_id}", operation="get page")
    page_title = page.get("title", "Unknown")

    # Get current user
    user = _get_current_user(client)
    user_key = user.get("accountId", user.get("userKey", ""))

    # Add watch using v1 API
    client.post(
        f"/rest/api/user/watch/content/{page_id}",
        operation="watch page",
    )

    if output == "json":
        click.echo(format_json({
            "page": {"id": page_id, "title": page_title},
            "watching": True,
            "user": user.get("displayName", "Current user"),
        }))
    else:
        click.echo(f"\nNow watching: {page_title}")
        click.echo(f"  Page ID: {page_id}")
        click.echo("  You will receive notifications for updates to this page.")

    print_success(f"Started watching page {page_id}")


@watch.command(name="unwatch-page")
@click.argument("page_id")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def unwatch_page(
    page_id: str,
    output: str,
) -> None:
    """Stop watching a page.

    You will no longer receive notifications for this page.
    """
    page_id = validate_page_id(page_id)

    client = get_confluence_client()

    # Get page info
    page = client.get(f"/api/v2/pages/{page_id}", operation="get page")
    page_title = page.get("title", "Unknown")

    # Remove watch using v1 API
    client.delete(
        f"/rest/api/user/watch/content/{page_id}",
        operation="unwatch page",
    )

    if output == "json":
        click.echo(format_json({
            "page": {"id": page_id, "title": page_title},
            "watching": False,
        }))
    else:
        click.echo(f"\nStopped watching: {page_title}")
        click.echo(f"  Page ID: {page_id}")
        click.echo("  You will no longer receive notifications for this page.")

    print_success(f"Stopped watching page {page_id}")


@watch.command(name="space")
@click.argument("space_key")
@click.option("--unwatch", "-u", is_flag=True, help="Stop watching the space instead of starting")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def watch_space(
    space_key: str,
    unwatch: bool,
    output: str,
) -> None:
    """Start or stop watching a space.

    When watching a space, you receive notifications for all content changes.
    """
    space_key = validate_space_key(space_key)

    client = get_confluence_client()

    # Get space info
    space = _get_space_by_key(client, space_key)
    space_name = space.get("name", space_key)

    if unwatch:
        # Remove space watch
        client.delete(
            f"/rest/api/user/watch/space/{space_key}",
            operation="unwatch space",
        )
        action = "Stopped watching"
        watching = False
    else:
        # Add space watch
        client.post(
            f"/rest/api/user/watch/space/{space_key}",
            operation="watch space",
        )
        action = "Now watching"
        watching = True

    if output == "json":
        click.echo(format_json({
            "space": {"key": space_key, "name": space_name},
            "watching": watching,
        }))
    else:
        click.echo(f"\n{action}: {space_name}")
        click.echo(f"  Space Key: {space_key}")
        if watching:
            click.echo("  You will receive notifications for all content in this space.")
        else:
            click.echo("  You will no longer receive space-wide notifications.")

    if watching:
        print_success(f"Started watching space {space_key}")
    else:
        print_success(f"Stopped watching space {space_key}")


@watch.command(name="status")
@click.argument("page_id")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def am_i_watching(
    page_id: str,
    output: str,
) -> None:
    """Check if you're watching a page."""
    page_id = validate_page_id(page_id)

    client = get_confluence_client()

    # Get page info
    page = client.get(f"/api/v2/pages/{page_id}", operation="get page")
    page_title = page.get("title", "Unknown")

    # Check watch status using v1 API
    try:
        watch_status = client.get(
            f"/rest/api/user/watch/content/{page_id}",
            operation="check watch status",
        )
        is_watching = watch_status.get("watching", False)
    except Exception:
        # If endpoint returns 404, user is not watching
        is_watching = False

    if output == "json":
        click.echo(format_json({
            "page": {"id": page_id, "title": page_title},
            "watching": is_watching,
        }))
    else:
        click.echo(f"\nWatch Status: {page_title}")
        click.echo(f"  Page ID: {page_id}")
        if is_watching:
            click.echo("  Status: Watching")
            click.echo("  You will receive notifications for this page.")
        else:
            click.echo("  Status: Not watching")
            click.echo("  Use 'confluence watch page' to start watching.")

    print_success("Retrieved watch status")


@watch.command(name="list")
@click.argument("page_id")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def get_watchers(
    page_id: str,
    output: str,
) -> None:
    """List watchers of a page."""
    page_id = validate_page_id(page_id)

    client = get_confluence_client()

    # Get page info
    page = client.get(f"/api/v2/pages/{page_id}", operation="get page")
    page_title = page.get("title", "Unknown")

    # Get watchers using v1 API
    # Note: This endpoint requires admin permissions in some configurations
    try:
        watchers_response = client.get(
            f"/rest/api/content/{page_id}/notification/child-created",
            operation="get watchers",
        )
        watchers = watchers_response.get("results", [])
    except Exception:
        # Try alternative endpoint
        watchers_response = client.get(
            f"/rest/api/content/{page_id}/notification/created",
            operation="get watchers",
        )
        watchers = watchers_response.get("results", [])

    if output == "json":
        click.echo(format_json({
            "page": {"id": page_id, "title": page_title},
            "watchers": watchers,
            "count": len(watchers),
        }))
    else:
        click.echo(f"\nWatchers of: {page_title} ({page_id})")
        click.echo(f"{'=' * 60}\n")

        if not watchers:
            click.echo("No watchers found (or you may not have permission to view watchers).")
        else:
            data = []
            for watcher_item in watchers:
                watcher = watcher_item.get("user", watcher_item)
                data.append({
                    "name": watcher.get("displayName", "Unknown"),
                    "type": watcher.get("type", "user"),
                })

            click.echo(format_table(
                data,
                columns=["name", "type"],
                headers=["Name", "Type"],
            ))

    print_success(f"Found {len(watchers)} watcher(s)")
