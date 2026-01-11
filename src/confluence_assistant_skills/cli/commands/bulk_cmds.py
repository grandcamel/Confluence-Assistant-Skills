"""Bulk operations commands - CLI-only implementation."""

from __future__ import annotations

import time
from typing import Any

import click

from confluence_assistant_skills_lib import (
    ValidationError,
    format_json,
    format_table,
    get_confluence_client,
    handle_errors,
    print_error,
    print_info,
    print_success,
    print_warning,
    validate_limit,
    validate_page_id,
    validate_space_key,
)


def _search_pages_by_cql(
    client: Any,
    cql: str,
    max_pages: int,
) -> list[dict[str, Any]]:
    """Search for pages using CQL query."""
    pages = []
    for result in client.paginate(
        "/rest/api/search",
        params={"cql": cql, "limit": min(max_pages, 25)},
        operation="search pages",
    ):
        content = result.get("content", result)
        pages.append(content)
        if len(pages) >= max_pages:
            break
    return pages


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
def bulk() -> None:
    """Bulk operations for multiple pages."""
    pass


# ============================================================================
# Bulk Label Operations
# ============================================================================

@bulk.group()
def label() -> None:
    """Bulk label operations."""
    pass


@label.command(name="add")
@click.option("--cql", required=True, help="CQL query to select pages")
@click.option("--labels", "-l", required=True, help="Comma-separated labels to add")
@click.option("--dry-run", is_flag=True, help="Preview changes without making them")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.option("--max-pages", type=int, default=100, help="Maximum pages to process (default: 100)")
@click.option("--batch-size", type=int, default=50, help="Batch size for processing (default: 50)")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def bulk_label_add(
    cql: str,
    labels: str,
    dry_run: bool,
    yes: bool,
    max_pages: int,
    batch_size: int,
    output: str,
) -> None:
    """Add labels to multiple pages."""
    max_pages = validate_limit(max_pages, max_value=1000)
    label_list = [l.strip() for l in labels.split(",") if l.strip()]

    if not label_list:
        raise ValidationError("At least one label is required")

    client = get_confluence_client()

    # Find pages
    pages = _search_pages_by_cql(client, cql, max_pages)

    if not pages:
        if output == "json":
            click.echo(format_json({"cql": cql, "pagesFound": 0, "error": "No pages found"}))
        else:
            print_warning(f"No pages found for CQL: {cql}")
        return

    if dry_run:
        if output == "json":
            click.echo(format_json({
                "dryRun": True,
                "cql": cql,
                "labels": label_list,
                "pagesFound": len(pages),
                "pages": [{"id": p.get("id"), "title": p.get("title")} for p in pages],
            }))
        else:
            click.echo(f"\n[DRY RUN] Would add labels {label_list} to {len(pages)} page(s):\n")
            for p in pages[:10]:
                click.echo(f"  - {p.get('title', 'Untitled')} ({p.get('id')})")
            if len(pages) > 10:
                click.echo(f"  ... and {len(pages) - 10} more")
        return

    if not yes:
        click.echo(f"\nAbout to add labels {label_list} to {len(pages)} page(s)")
        if not click.confirm("Continue?", default=True):
            click.echo("Cancelled.")
            return

    # Process in batches
    success_count = 0
    fail_count = 0
    failures = []

    for i, page in enumerate(pages):
        page_id = page.get("id", "")
        try:
            # Add labels using v2 API
            for lbl in label_list:
                client.post(
                    f"/api/v2/pages/{page_id}/labels",
                    json_data={"name": lbl},
                    operation="add label",
                )
            success_count += 1

            if output == "text" and (i + 1) % 10 == 0:
                click.echo(f"  Processed {i + 1}/{len(pages)}...")

        except Exception as e:
            fail_count += 1
            failures.append({"page_id": page_id, "title": page.get("title"), "error": str(e)})

    if output == "json":
        click.echo(format_json({
            "cql": cql,
            "labels": label_list,
            "totalPages": len(pages),
            "success": success_count,
            "failed": fail_count,
            "failures": failures,
        }))
    else:
        click.echo(f"\nBulk Label Add Complete")
        click.echo(f"  Labels: {', '.join(label_list)}")
        click.echo(f"  Success: {success_count}")
        click.echo(f"  Failed: {fail_count}")

        if failures:
            click.echo("\nFailures:")
            for f in failures[:5]:
                click.echo(f"  - {f['title']}: {f['error']}")
            if len(failures) > 5:
                click.echo(f"  ... and {len(failures) - 5} more")

    print_success(f"Added labels to {success_count} page(s)")


@label.command(name="remove")
@click.option("--cql", required=True, help="CQL query to select pages")
@click.option("--labels", "-l", required=True, help="Comma-separated labels to remove")
@click.option("--dry-run", is_flag=True, help="Preview changes without making them")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.option("--max-pages", type=int, default=100, help="Maximum pages to process (default: 100)")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def bulk_label_remove(
    cql: str,
    labels: str,
    dry_run: bool,
    yes: bool,
    max_pages: int,
    output: str,
) -> None:
    """Remove labels from multiple pages."""
    max_pages = validate_limit(max_pages, max_value=1000)
    label_list = [l.strip() for l in labels.split(",") if l.strip()]

    if not label_list:
        raise ValidationError("At least one label is required")

    client = get_confluence_client()

    # Find pages
    pages = _search_pages_by_cql(client, cql, max_pages)

    if not pages:
        if output == "json":
            click.echo(format_json({"cql": cql, "pagesFound": 0, "error": "No pages found"}))
        else:
            print_warning(f"No pages found for CQL: {cql}")
        return

    if dry_run:
        if output == "json":
            click.echo(format_json({
                "dryRun": True,
                "cql": cql,
                "labels": label_list,
                "pagesFound": len(pages),
                "pages": [{"id": p.get("id"), "title": p.get("title")} for p in pages],
            }))
        else:
            click.echo(f"\n[DRY RUN] Would remove labels {label_list} from {len(pages)} page(s):\n")
            for p in pages[:10]:
                click.echo(f"  - {p.get('title', 'Untitled')} ({p.get('id')})")
            if len(pages) > 10:
                click.echo(f"  ... and {len(pages) - 10} more")
        return

    if not yes:
        click.echo(f"\nAbout to remove labels {label_list} from {len(pages)} page(s)")
        if not click.confirm("Continue?", default=True):
            click.echo("Cancelled.")
            return

    # Process pages
    success_count = 0
    fail_count = 0
    failures = []

    for i, page in enumerate(pages):
        page_id = page.get("id", "")
        try:
            # Remove labels using v2 API
            for lbl in label_list:
                try:
                    client.delete(
                        f"/api/v2/pages/{page_id}/labels/{lbl}",
                        operation="remove label",
                    )
                except Exception:
                    # Label might not exist on page, continue
                    pass
            success_count += 1

            if output == "text" and (i + 1) % 10 == 0:
                click.echo(f"  Processed {i + 1}/{len(pages)}...")

        except Exception as e:
            fail_count += 1
            failures.append({"page_id": page_id, "title": page.get("title"), "error": str(e)})

    if output == "json":
        click.echo(format_json({
            "cql": cql,
            "labels": label_list,
            "totalPages": len(pages),
            "success": success_count,
            "failed": fail_count,
            "failures": failures,
        }))
    else:
        click.echo(f"\nBulk Label Remove Complete")
        click.echo(f"  Labels: {', '.join(label_list)}")
        click.echo(f"  Success: {success_count}")
        click.echo(f"  Failed: {fail_count}")

    print_success(f"Removed labels from {success_count} page(s)")


# ============================================================================
# Bulk Move Operations
# ============================================================================

@bulk.command(name="move")
@click.option("--cql", required=True, help="CQL query to select pages")
@click.option("--target-space", help="Target space key")
@click.option("--target-parent", help="Target parent page ID")
@click.option("--dry-run", is_flag=True, help="Preview changes without making them")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.option("--max-pages", type=int, default=100, help="Maximum pages to process (default: 100)")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def bulk_move(
    cql: str,
    target_space: str | None,
    target_parent: str | None,
    dry_run: bool,
    yes: bool,
    max_pages: int,
    output: str,
) -> None:
    """Move multiple pages to a new location."""
    max_pages = validate_limit(max_pages, max_value=500)

    if not target_space and not target_parent:
        raise ValidationError("Either --target-space or --target-parent is required")

    client = get_confluence_client()

    # Validate target space if provided
    target_space_id = None
    if target_space:
        target_space = validate_space_key(target_space)
        space_info = _get_space_by_key(client, target_space)
        target_space_id = space_info.get("id")

    # Validate target parent if provided
    if target_parent:
        target_parent = validate_page_id(target_parent)
        # Verify parent exists
        client.get(f"/api/v2/pages/{target_parent}", operation="verify parent exists")

    # Find pages
    pages = _search_pages_by_cql(client, cql, max_pages)

    if not pages:
        if output == "json":
            click.echo(format_json({"cql": cql, "pagesFound": 0, "error": "No pages found"}))
        else:
            print_warning(f"No pages found for CQL: {cql}")
        return

    if dry_run:
        if output == "json":
            click.echo(format_json({
                "dryRun": True,
                "cql": cql,
                "targetSpace": target_space,
                "targetParent": target_parent,
                "pagesFound": len(pages),
                "pages": [{"id": p.get("id"), "title": p.get("title")} for p in pages],
            }))
        else:
            dest = f"space {target_space}" if target_space else f"under page {target_parent}"
            click.echo(f"\n[DRY RUN] Would move {len(pages)} page(s) to {dest}:\n")
            for p in pages[:10]:
                click.echo(f"  - {p.get('title', 'Untitled')} ({p.get('id')})")
            if len(pages) > 10:
                click.echo(f"  ... and {len(pages) - 10} more")
        return

    if not yes:
        dest = f"space {target_space}" if target_space else f"under page {target_parent}"
        click.echo(f"\nAbout to move {len(pages)} page(s) to {dest}")
        print_warning("This operation modifies content hierarchy!")
        if not click.confirm("Continue?", default=False):
            click.echo("Cancelled.")
            return

    # Process pages
    success_count = 0
    fail_count = 0
    failures = []

    for i, page in enumerate(pages):
        page_id = page.get("id", "")
        try:
            # Get current page to get version
            current = client.get(f"/api/v2/pages/{page_id}", operation="get page")
            version = current.get("version", {}).get("number", 1)

            # Build update data
            update_data: dict[str, Any] = {
                "id": page_id,
                "status": "current",
                "version": {"number": version + 1},
            }

            if target_space_id:
                update_data["spaceId"] = target_space_id
            if target_parent:
                update_data["parentId"] = target_parent

            # Update page location
            client.put(
                f"/api/v2/pages/{page_id}",
                json_data=update_data,
                operation="move page",
            )
            success_count += 1

            if output == "text" and (i + 1) % 10 == 0:
                click.echo(f"  Processed {i + 1}/{len(pages)}...")

        except Exception as e:
            fail_count += 1
            failures.append({"page_id": page_id, "title": page.get("title"), "error": str(e)})

    if output == "json":
        click.echo(format_json({
            "cql": cql,
            "targetSpace": target_space,
            "targetParent": target_parent,
            "totalPages": len(pages),
            "success": success_count,
            "failed": fail_count,
            "failures": failures,
        }))
    else:
        click.echo(f"\nBulk Move Complete")
        click.echo(f"  Success: {success_count}")
        click.echo(f"  Failed: {fail_count}")

        if failures:
            click.echo("\nFailures:")
            for f in failures[:5]:
                click.echo(f"  - {f['title']}: {f['error']}")
            if len(failures) > 5:
                click.echo(f"  ... and {len(failures) - 5} more")

    print_success(f"Moved {success_count} page(s)")


# ============================================================================
# Bulk Delete Operations
# ============================================================================

@bulk.command(name="delete")
@click.option("--cql", required=True, help="CQL query to select pages")
@click.option("--dry-run", is_flag=True, help="Preview changes without making them")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.option("--max-pages", type=int, default=100, help="Maximum pages to process (default: 100)")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def bulk_delete(
    cql: str,
    dry_run: bool,
    yes: bool,
    max_pages: int,
    output: str,
) -> None:
    """Delete multiple pages. USE WITH CAUTION!"""
    max_pages = validate_limit(max_pages, max_value=500)

    client = get_confluence_client()

    # Find pages
    pages = _search_pages_by_cql(client, cql, max_pages)

    if not pages:
        if output == "json":
            click.echo(format_json({"cql": cql, "pagesFound": 0, "error": "No pages found"}))
        else:
            print_warning(f"No pages found for CQL: {cql}")
        return

    if dry_run:
        if output == "json":
            click.echo(format_json({
                "dryRun": True,
                "cql": cql,
                "pagesFound": len(pages),
                "pages": [{"id": p.get("id"), "title": p.get("title")} for p in pages],
            }))
        else:
            click.echo(f"\n[DRY RUN] Would DELETE {len(pages)} page(s):\n")
            for p in pages[:20]:
                click.echo(f"  - {p.get('title', 'Untitled')} ({p.get('id')})")
            if len(pages) > 20:
                click.echo(f"  ... and {len(pages) - 20} more")
            print_warning("\nThis operation is DESTRUCTIVE and cannot be easily undone!")
        return

    if not yes:
        click.echo(f"\n{'=' * 60}")
        print_warning(f"DANGER: About to DELETE {len(pages)} page(s)!")
        click.echo(f"{'=' * 60}\n")

        for p in pages[:10]:
            click.echo(f"  - {p.get('title', 'Untitled')} ({p.get('id')})")
        if len(pages) > 10:
            click.echo(f"  ... and {len(pages) - 10} more")

        print_warning("\nThis operation CANNOT be easily undone!")
        if not click.confirm("\nAre you ABSOLUTELY sure?", default=False):
            click.echo("Cancelled.")
            return

        # Double confirmation for safety
        if len(pages) > 10:
            if not click.confirm(f"Confirm deletion of {len(pages)} pages?", default=False):
                click.echo("Cancelled.")
                return

    # Process pages
    success_count = 0
    fail_count = 0
    failures = []

    for i, page in enumerate(pages):
        page_id = page.get("id", "")
        try:
            # Delete page using v2 API
            client.delete(
                f"/api/v2/pages/{page_id}",
                operation="delete page",
            )
            success_count += 1

            if output == "text" and (i + 1) % 10 == 0:
                click.echo(f"  Deleted {i + 1}/{len(pages)}...")

            # Small delay to avoid rate limiting
            if (i + 1) % 20 == 0:
                time.sleep(0.5)

        except Exception as e:
            fail_count += 1
            failures.append({"page_id": page_id, "title": page.get("title"), "error": str(e)})

    if output == "json":
        click.echo(format_json({
            "cql": cql,
            "totalPages": len(pages),
            "deleted": success_count,
            "failed": fail_count,
            "failures": failures,
        }))
    else:
        click.echo(f"\nBulk Delete Complete")
        click.echo(f"  Deleted: {success_count}")
        click.echo(f"  Failed: {fail_count}")

        if failures:
            click.echo("\nFailures:")
            for f in failures[:5]:
                click.echo(f"  - {f['title']}: {f['error']}")
            if len(failures) > 5:
                click.echo(f"  ... and {len(failures) - 5} more")

    print_success(f"Deleted {success_count} page(s)")


# ============================================================================
# Bulk Permission Operations
# ============================================================================

@bulk.command(name="permission")
@click.option("--cql", required=True, help="CQL query to select pages")
@click.option("--add-group", help="Group to add view permission")
@click.option("--remove-group", help="Group to remove from permissions")
@click.option("--add-user", help="User account ID to add view permission")
@click.option("--remove-user", help="User account ID to remove from permissions")
@click.option("--dry-run", is_flag=True, help="Preview changes without making them")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.option("--max-pages", type=int, default=100, help="Maximum pages to process (default: 100)")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def bulk_permission(
    cql: str,
    add_group: str | None,
    remove_group: str | None,
    add_user: str | None,
    remove_user: str | None,
    dry_run: bool,
    yes: bool,
    max_pages: int,
    output: str,
) -> None:
    """Change permissions on multiple pages."""
    max_pages = validate_limit(max_pages, max_value=500)

    if not any([add_group, remove_group, add_user, remove_user]):
        raise ValidationError(
            "At least one of --add-group, --remove-group, --add-user, or --remove-user is required"
        )

    client = get_confluence_client()

    # Find pages
    pages = _search_pages_by_cql(client, cql, max_pages)

    if not pages:
        if output == "json":
            click.echo(format_json({"cql": cql, "pagesFound": 0, "error": "No pages found"}))
        else:
            print_warning(f"No pages found for CQL: {cql}")
        return

    # Build operation description
    operations = []
    if add_group:
        operations.append(f"add group '{add_group}'")
    if remove_group:
        operations.append(f"remove group '{remove_group}'")
    if add_user:
        operations.append(f"add user '{add_user}'")
    if remove_user:
        operations.append(f"remove user '{remove_user}'")
    op_desc = ", ".join(operations)

    if dry_run:
        if output == "json":
            click.echo(format_json({
                "dryRun": True,
                "cql": cql,
                "operations": {
                    "addGroup": add_group,
                    "removeGroup": remove_group,
                    "addUser": add_user,
                    "removeUser": remove_user,
                },
                "pagesFound": len(pages),
                "pages": [{"id": p.get("id"), "title": p.get("title")} for p in pages],
            }))
        else:
            click.echo(f"\n[DRY RUN] Would {op_desc} on {len(pages)} page(s):\n")
            for p in pages[:10]:
                click.echo(f"  - {p.get('title', 'Untitled')} ({p.get('id')})")
            if len(pages) > 10:
                click.echo(f"  ... and {len(pages) - 10} more")
        return

    if not yes:
        click.echo(f"\nAbout to {op_desc} on {len(pages)} page(s)")
        print_warning("This operation modifies access control!")
        if not click.confirm("Continue?", default=False):
            click.echo("Cancelled.")
            return

    # Process pages
    success_count = 0
    fail_count = 0
    failures = []

    for i, page in enumerate(pages):
        page_id = page.get("id", "")
        try:
            # Get current restrictions
            restrictions = client.get(
                f"/rest/api/content/{page_id}/restriction",
                operation="get restrictions",
            )

            # Apply changes using v1 API
            if add_group:
                client.put(
                    f"/rest/api/content/{page_id}/restriction/byOperation/read/group/{add_group}",
                    operation="add group restriction",
                )

            if remove_group:
                try:
                    client.delete(
                        f"/rest/api/content/{page_id}/restriction/byOperation/read/group/{remove_group}",
                        operation="remove group restriction",
                    )
                except Exception:
                    pass  # Group might not have restriction

            if add_user:
                client.put(
                    f"/rest/api/content/{page_id}/restriction/byOperation/read/user",
                    params={"accountId": add_user},
                    operation="add user restriction",
                )

            if remove_user:
                try:
                    client.delete(
                        f"/rest/api/content/{page_id}/restriction/byOperation/read/user",
                        params={"accountId": remove_user},
                        operation="remove user restriction",
                    )
                except Exception:
                    pass  # User might not have restriction

            success_count += 1

            if output == "text" and (i + 1) % 10 == 0:
                click.echo(f"  Processed {i + 1}/{len(pages)}...")

        except Exception as e:
            fail_count += 1
            failures.append({"page_id": page_id, "title": page.get("title"), "error": str(e)})

    if output == "json":
        click.echo(format_json({
            "cql": cql,
            "operations": {
                "addGroup": add_group,
                "removeGroup": remove_group,
                "addUser": add_user,
                "removeUser": remove_user,
            },
            "totalPages": len(pages),
            "success": success_count,
            "failed": fail_count,
            "failures": failures,
        }))
    else:
        click.echo(f"\nBulk Permission Change Complete")
        click.echo(f"  Operations: {op_desc}")
        click.echo(f"  Success: {success_count}")
        click.echo(f"  Failed: {fail_count}")

        if failures:
            click.echo("\nFailures:")
            for f in failures[:5]:
                click.echo(f"  - {f['title']}: {f['error']}")
            if len(failures) > 5:
                click.echo(f"  ... and {len(failures) - 5} more")

    print_success(f"Updated permissions on {success_count} page(s)")


# ============================================================================
# Bulk Update Operations
# ============================================================================

@bulk.command(name="update")
@click.option("--cql", required=True, help="CQL query to select pages")
@click.option("--title-prefix", help="Prefix to add to titles")
@click.option("--title-suffix", help="Suffix to add to titles")
@click.option("--dry-run", is_flag=True, help="Preview changes without making them")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.option("--max-pages", type=int, default=100, help="Maximum pages to process (default: 100)")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def bulk_update(
    cql: str,
    title_prefix: str | None,
    title_suffix: str | None,
    dry_run: bool,
    yes: bool,
    max_pages: int,
    output: str,
) -> None:
    """Update properties on multiple pages."""
    max_pages = validate_limit(max_pages, max_value=500)

    if not title_prefix and not title_suffix:
        raise ValidationError("At least one of --title-prefix or --title-suffix is required")

    client = get_confluence_client()

    # Find pages
    pages = _search_pages_by_cql(client, cql, max_pages)

    if not pages:
        if output == "json":
            click.echo(format_json({"cql": cql, "pagesFound": 0, "error": "No pages found"}))
        else:
            print_warning(f"No pages found for CQL: {cql}")
        return

    # Build operation description
    ops = []
    if title_prefix:
        ops.append(f"add prefix '{title_prefix}'")
    if title_suffix:
        ops.append(f"add suffix '{title_suffix}'")
    op_desc = " and ".join(ops)

    if dry_run:
        if output == "json":
            preview = []
            for p in pages:
                old_title = p.get("title", "")
                new_title = old_title
                if title_prefix:
                    new_title = title_prefix + new_title
                if title_suffix:
                    new_title = new_title + title_suffix
                preview.append({
                    "id": p.get("id"),
                    "oldTitle": old_title,
                    "newTitle": new_title,
                })

            click.echo(format_json({
                "dryRun": True,
                "cql": cql,
                "titlePrefix": title_prefix,
                "titleSuffix": title_suffix,
                "pagesFound": len(pages),
                "preview": preview,
            }))
        else:
            click.echo(f"\n[DRY RUN] Would {op_desc} on {len(pages)} page(s):\n")
            for p in pages[:10]:
                old_title = p.get("title", "Untitled")
                new_title = old_title
                if title_prefix:
                    new_title = title_prefix + new_title
                if title_suffix:
                    new_title = new_title + title_suffix
                click.echo(f"  - '{old_title}' -> '{new_title}'")
            if len(pages) > 10:
                click.echo(f"  ... and {len(pages) - 10} more")
        return

    if not yes:
        click.echo(f"\nAbout to {op_desc} on {len(pages)} page(s)")
        if not click.confirm("Continue?", default=True):
            click.echo("Cancelled.")
            return

    # Process pages
    success_count = 0
    fail_count = 0
    failures = []

    for i, page in enumerate(pages):
        page_id = page.get("id", "")
        try:
            # Get current page to get version
            current = client.get(f"/api/v2/pages/{page_id}", operation="get page")
            version = current.get("version", {}).get("number", 1)
            old_title = current.get("title", "")

            # Build new title
            new_title = old_title
            if title_prefix:
                new_title = title_prefix + new_title
            if title_suffix:
                new_title = new_title + title_suffix

            # Update page
            client.put(
                f"/api/v2/pages/{page_id}",
                json_data={
                    "id": page_id,
                    "status": "current",
                    "title": new_title,
                    "version": {"number": version + 1},
                },
                operation="update page title",
            )
            success_count += 1

            if output == "text" and (i + 1) % 10 == 0:
                click.echo(f"  Processed {i + 1}/{len(pages)}...")

        except Exception as e:
            fail_count += 1
            failures.append({"page_id": page_id, "title": page.get("title"), "error": str(e)})

    if output == "json":
        click.echo(format_json({
            "cql": cql,
            "titlePrefix": title_prefix,
            "titleSuffix": title_suffix,
            "totalPages": len(pages),
            "success": success_count,
            "failed": fail_count,
            "failures": failures,
        }))
    else:
        click.echo(f"\nBulk Update Complete")
        click.echo(f"  Operation: {op_desc}")
        click.echo(f"  Success: {success_count}")
        click.echo(f"  Failed: {fail_count}")

        if failures:
            click.echo("\nFailures:")
            for f in failures[:5]:
                click.echo(f"  - {f['title']}: {f['error']}")
            if len(failures) > 5:
                click.echo(f"  ... and {len(failures) - 5} more")

    print_success(f"Updated {success_count} page(s)")
