"""Label management commands - CLI-only implementation."""

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
    validate_limit,
    validate_page_id,
    validate_space_key,
)


@click.group()
def label() -> None:
    """Manage content labels."""
    pass


@label.command(name="list")
@click.argument("page_id")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def get_labels(
    page_id: str,
    output: str,
) -> None:
    """List labels on a page."""
    page_id = validate_page_id(page_id)

    client = get_confluence_client()

    # Get page info
    page = client.get(f"/api/v2/pages/{page_id}", operation="get page")
    page_title = page.get("title", "Unknown")

    # Get labels
    labels = list(client.paginate(
        f"/api/v2/pages/{page_id}/labels",
        operation="get labels",
    ))

    if output == "json":
        click.echo(format_json({
            "page": {"id": page_id, "title": page_title},
            "labels": labels,
            "count": len(labels),
        }))
    else:
        click.echo(f"\nLabels on: {page_title} ({page_id})")
        click.echo(f"{'=' * 60}\n")

        if not labels:
            click.echo("No labels found.")
        else:
            label_names = [lbl.get("name", "") for lbl in labels]
            click.echo(f"Labels: {', '.join(label_names)}")

    print_success(f"Found {len(labels)} label(s)")


@label.command(name="add")
@click.argument("page_id")
@click.argument("labels", nargs=-1)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def add_label(
    page_id: str,
    labels: tuple[str, ...],
    output: str,
) -> None:
    """Add labels to a page.

    Examples:
        confluence label add 12345 documentation
        confluence label add 12345 doc approved v2
    """
    page_id = validate_page_id(page_id)

    if not labels:
        raise ValidationError("At least one label is required")

    # Validate label names
    for label_name in labels:
        if not label_name or not label_name.strip():
            raise ValidationError("Label name cannot be empty")
        if " " in label_name:
            raise ValidationError(f"Label name cannot contain spaces: '{label_name}'")

    client = get_confluence_client()

    # Add labels
    label_data = [{"name": name.strip()} for name in labels]

    result = client.post(
        f"/api/v2/pages/{page_id}/labels",
        json_data=label_data,
        operation="add labels",
    )

    if output == "json":
        click.echo(format_json(result))
    else:
        click.echo("\nLabels added successfully")
        click.echo(f"  Page: {page_id}")
        click.echo(f"  Added: {', '.join(labels)}")

    print_success(f"Added {len(labels)} label(s) to page {page_id}")


@label.command(name="remove")
@click.argument("page_id")
@click.argument("label_name")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def remove_label(
    page_id: str,
    label_name: str,
    output: str,
) -> None:
    """Remove a label from a page.

    Examples:
        confluence label remove 12345 draft
    """
    page_id = validate_page_id(page_id)

    if not label_name or not label_name.strip():
        raise ValidationError("Label name is required")

    client = get_confluence_client()

    # Remove label
    client.delete(
        f"/api/v2/pages/{page_id}/labels/{label_name.strip()}",
        operation="remove label",
    )

    if output == "json":
        click.echo(format_json({"success": True, "label": label_name, "pageId": page_id}))
    else:
        click.echo("\nLabel removed successfully")
        click.echo(f"  Page: {page_id}")
        click.echo(f"  Removed: {label_name}")

    print_success(f"Removed label '{label_name}' from page {page_id}")


@label.command(name="search")
@click.argument("label_name")
@click.option("--space", "-s", help="Limit to specific space")
@click.option("--type", "content_type", help="Content type (page, blogpost)")
@click.option("--limit", "-l", type=int, default=25, help="Maximum results")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def search_by_label(
    label_name: str,
    space: str | None,
    content_type: str | None,
    limit: int,
    output: str,
) -> None:
    """Search content by label."""
    if not label_name or not label_name.strip():
        raise ValidationError("Label name is required")

    if space:
        space = validate_space_key(space)

    limit = validate_limit(limit, max_value=250)

    # Build CQL query
    cql_parts = [f'label = "{label_name.strip()}"']

    if space:
        cql_parts.append(f'space = "{space}"')

    if content_type:
        if content_type.lower() not in ("page", "blogpost"):
            raise ValidationError("Content type must be 'page' or 'blogpost'")
        cql_parts.append(f"type = {content_type.lower()}")

    cql = " AND ".join(cql_parts)

    client = get_confluence_client()

    params: dict[str, Any] = {
        "cql": cql,
        "limit": min(limit, 25),
    }

    results = []
    for result in client.paginate(
        "/rest/api/search", params=params, operation="search by label"
    ):
        results.append(result)
        if len(results) >= limit:
            break

    if output == "json":
        click.echo(format_json({
            "label": label_name,
            "cql": cql,
            "count": len(results),
            "results": results,
        }))
    else:
        click.echo(f"\nContent with label: {label_name}")
        if space:
            click.echo(f"Space: {space}")
        click.echo(f"{'=' * 60}\n")

        if not results:
            click.echo("No content found with this label.")
        else:
            data = []
            for r in results:
                content = r.get("content", r)
                data.append({
                    "id": content.get("id", ""),
                    "title": content.get("title", "")[:40],
                    "type": content.get("type", ""),
                    "space": content.get("space", {}).get("key", ""),
                })

            click.echo(format_table(
                data,
                columns=["id", "title", "type", "space"],
                headers=["ID", "Title", "Type", "Space"],
            ))

    print_success(f"Found {len(results)} result(s) with label '{label_name}'")


@label.command(name="popular")
@click.option("--space", "-s", help="Limit to specific space")
@click.option("--limit", "-l", type=int, default=25, help="Maximum labels to return")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def list_popular_labels(
    space: str | None,
    limit: int,
    output: str,
) -> None:
    """List popular labels."""
    if space:
        space = validate_space_key(space)

    limit = validate_limit(limit, max_value=100)

    client = get_confluence_client()

    # Use v1 API for label statistics

    if space:
        # Get space info first
        spaces = list(client.paginate(
            "/api/v2/spaces", params={"keys": space}, operation="get space"
        ))
        if not spaces:
            raise ValidationError(f"Space not found: {space}")

        # Get labels from space pages
        # Note: This is a simplified implementation
        # A full implementation would aggregate labels from space content
        cql = f'space = "{space}" AND type = page'
        results = list(client.paginate(
            "/rest/api/search",
            params={"cql": cql, "expand": "content.metadata.labels", "limit": 100},
            operation="get space content",
        ))

        # Aggregate labels
        label_counts: dict[str, int] = {}
        for r in results:
            content = r.get("content", {})
            labels = content.get("metadata", {}).get("labels", {}).get("results", [])
            for label_item in labels:
                name = label_item.get("name", "")
                if name:
                    label_counts[name] = label_counts.get(name, 0) + 1

        # Sort by count
        sorted_labels = sorted(label_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
        labels = [{"name": name, "count": count} for name, count in sorted_labels]
    else:
        # Without space filter, we need to use a different approach
        # Get labels from recent content
        results = list(client.paginate(
            "/rest/api/search",
            params={"cql": "type = page", "expand": "content.metadata.labels", "limit": 200},
            operation="get recent content",
        ))

        label_counts = {}
        for r in results:
            content = r.get("content", {})
            labels_data = content.get("metadata", {}).get("labels", {}).get("results", [])
            for label_item in labels_data:
                name = label_item.get("name", "")
                if name:
                    label_counts[name] = label_counts.get(name, 0) + 1

        sorted_labels = sorted(label_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
        labels = [{"name": name, "count": count} for name, count in sorted_labels]

    if output == "json":
        click.echo(format_json({
            "space": space,
            "labels": labels,
            "count": len(labels),
        }))
    else:
        click.echo("\nPopular Labels")
        if space:
            click.echo(f"Space: {space}")
        click.echo(f"{'=' * 60}\n")

        if not labels:
            click.echo("No labels found.")
        else:
            data = []
            for lbl in labels:
                data.append({
                    "name": lbl["name"],
                    "count": lbl["count"],
                })

            click.echo(format_table(
                data,
                columns=["name", "count"],
                headers=["Label", "Count"],
            ))

    print_success(f"Found {len(labels)} popular label(s)")
