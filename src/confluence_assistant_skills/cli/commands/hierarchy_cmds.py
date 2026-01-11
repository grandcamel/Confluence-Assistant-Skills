"""Hierarchy management commands - CLI-only implementation."""

from __future__ import annotations

from typing import Any, cast

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
)


def _get_page_info(client: Any, page_id: str) -> dict[str, Any]:
    """Get basic page info."""
    return cast(dict[str, Any], client.get(f"/api/v2/pages/{page_id}", operation="get page"))


@click.group()
def hierarchy() -> None:
    """Navigate content hierarchy."""
    pass


@hierarchy.command(name="children")
@click.argument("page_id")
@click.option("--limit", "-l", type=int, default=25, help="Maximum children to return")
@click.option(
    "--sort",
    type=click.Choice(["title", "id", "created"]),
    help="Sort children by field",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def get_children(
    page_id: str,
    limit: int,
    sort: str | None,
    output: str,
) -> None:
    """Get child pages of a page."""
    page_id = validate_page_id(page_id)
    limit = validate_limit(limit, max_value=250)

    client = get_confluence_client()

    # Get page info
    page = _get_page_info(client, page_id)
    page_title = page.get("title", "Unknown")

    # Get children
    params: dict[str, Any] = {
        "limit": min(limit, 25),
    }

    if sort:
        sort_map = {
            "title": "title",
            "id": "id",
            "created": "created-date",
        }
        params["sort"] = sort_map.get(sort, "title")

    children = []
    for child in client.paginate(
        f"/api/v2/pages/{page_id}/children",
        params=params,
        operation="get children",
    ):
        children.append(child)
        if len(children) >= limit:
            break

    if output == "json":
        click.echo(format_json({
            "page": {"id": page_id, "title": page_title},
            "children": children,
            "count": len(children),
        }))
    else:
        click.echo(f"\nChildren of: {page_title} ({page_id})")
        click.echo(f"{'=' * 60}\n")

        if not children:
            click.echo("No child pages found.")
        else:
            data = []
            for child in children:
                data.append({
                    "id": child.get("id", ""),
                    "title": child.get("title", "")[:40],
                    "status": child.get("status", ""),
                })

            click.echo(format_table(
                data,
                columns=["id", "title", "status"],
                headers=["ID", "Title", "Status"],
            ))

    print_success(f"Found {len(children)} child page(s)")


@hierarchy.command(name="ancestors")
@click.argument("page_id")
@click.option("--breadcrumb", is_flag=True, help="Show as breadcrumb path")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def get_ancestors(
    page_id: str,
    breadcrumb: bool,
    output: str,
) -> None:
    """Get ancestor pages (parents, grandparents, etc.)."""
    page_id = validate_page_id(page_id)

    client = get_confluence_client()

    # Get page info with ancestors
    page = _get_page_info(client, page_id)
    page_title = page.get("title", "Unknown")

    # Get ancestors
    ancestors = list(client.paginate(
        f"/api/v2/pages/{page_id}/ancestors",
        operation="get ancestors",
    ))

    if output == "json":
        click.echo(format_json({
            "page": {"id": page_id, "title": page_title},
            "ancestors": ancestors,
            "count": len(ancestors),
        }))
    else:
        click.echo(f"\nAncestors of: {page_title} ({page_id})")
        click.echo(f"{'=' * 60}\n")

        if not ancestors:
            click.echo("No ancestor pages found (this is a root page).")
        elif breadcrumb:
            # Display as breadcrumb path
            path_parts = [a.get("title", "Unknown") for a in ancestors]
            path_parts.append(page_title)
            click.echo(" > ".join(path_parts))
        else:
            data = []
            for i, ancestor in enumerate(ancestors):
                data.append({
                    "level": i + 1,
                    "id": ancestor.get("id", ""),
                    "title": ancestor.get("title", "")[:40],
                })

            click.echo(format_table(
                data,
                columns=["level", "id", "title"],
                headers=["Level", "ID", "Title"],
            ))

    print_success(f"Found {len(ancestors)} ancestor(s)")


@hierarchy.command(name="descendants")
@click.argument("page_id")
@click.option("--max-depth", "-d", type=int, help="Maximum depth to traverse")
@click.option("--limit", "-l", type=int, default=100, help="Maximum descendants to return")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def get_descendants(
    page_id: str,
    max_depth: int | None,
    limit: int,
    output: str,
) -> None:
    """Get all descendant pages."""
    page_id = validate_page_id(page_id)
    limit = validate_limit(limit, max_value=500)

    client = get_confluence_client()

    # Get page info
    page = _get_page_info(client, page_id)
    page_title = page.get("title", "Unknown")

    # Recursively collect descendants
    descendants: list[dict[str, Any]] = []

    def collect_descendants(parent_id: str, current_depth: int = 0) -> None:
        if max_depth is not None and current_depth >= max_depth:
            return
        if len(descendants) >= limit:
            return

        for child in client.paginate(
            f"/api/v2/pages/{parent_id}/children",
            operation="get children",
        ):
            if len(descendants) >= limit:
                break
            child["_depth"] = current_depth + 1
            descendants.append(child)
            collect_descendants(child["id"], current_depth + 1)

    collect_descendants(page_id)

    if output == "json":
        click.echo(format_json({
            "page": {"id": page_id, "title": page_title},
            "descendants": descendants,
            "count": len(descendants),
            "maxDepth": max_depth,
        }))
    else:
        click.echo(f"\nDescendants of: {page_title} ({page_id})")
        if max_depth:
            click.echo(f"Max depth: {max_depth}")
        click.echo(f"{'=' * 60}\n")

        if not descendants:
            click.echo("No descendant pages found.")
        else:
            data = []
            for desc in descendants:
                indent = "  " * desc.get("_depth", 0)
                data.append({
                    "depth": desc.get("_depth", 0),
                    "id": desc.get("id", ""),
                    "title": indent + desc.get("title", "")[:35],
                })

            click.echo(format_table(
                data,
                columns=["depth", "id", "title"],
                headers=["Depth", "ID", "Title"],
            ))

    print_success(f"Found {len(descendants)} descendant(s)")


@hierarchy.command(name="tree")
@click.argument("page_id")
@click.option(
    "--max-depth", "-d", type=int, help="Maximum depth to traverse (default: unlimited)"
)
@click.option("--stats", is_flag=True, help="Show tree statistics")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def get_page_tree(
    page_id: str,
    max_depth: int | None,
    stats: bool,
    output: str,
) -> None:
    """Display page tree structure."""
    page_id = validate_page_id(page_id)

    client = get_confluence_client()

    # Get page info
    page = _get_page_info(client, page_id)
    page_title = page.get("title", "Unknown")

    # Build tree structure
    def build_tree(parent_id: str, current_depth: int = 0) -> list[dict[str, Any]]:
        if max_depth is not None and current_depth >= max_depth:
            return []

        tree = []
        for child in client.paginate(
            f"/api/v2/pages/{parent_id}/children",
            operation="get children",
        ):
            node = {
                "id": child.get("id", ""),
                "title": child.get("title", ""),
                "depth": current_depth + 1,
                "children": build_tree(child["id"], current_depth + 1),
            }
            tree.append(node)
        return tree

    tree = build_tree(page_id)

    # Calculate stats if requested
    tree_stats = None
    if stats:
        def count_nodes(nodes: list[dict[str, Any]]) -> tuple[int, int]:
            total = len(nodes)
            max_d = 0
            for node in nodes:
                children = node.get("children", [])
                if children:
                    child_count, child_depth = count_nodes(children)
                    total += child_count
                    max_d = max(max_d, child_depth)
            return total, max_d + 1 if nodes else 0

        total_pages, max_tree_depth = count_nodes(tree)
        tree_stats = {
            "totalPages": total_pages,
            "maxDepth": max_tree_depth,
            "rootChildren": len(tree),
        }

    if output == "json":
        result: dict[str, Any] = {
            "root": {"id": page_id, "title": page_title},
            "tree": tree,
        }
        if tree_stats:
            result["stats"] = tree_stats
        click.echo(format_json(result))
    else:
        click.echo(f"\nPage Tree: {page_title} ({page_id})")
        click.echo(f"{'=' * 60}\n")

        def print_tree(nodes: list[dict[str, Any]], prefix: str = "") -> None:
            for i, node in enumerate(nodes):
                is_last = i == len(nodes) - 1
                connector = "└── " if is_last else "├── "
                click.echo(f"{prefix}{connector}{node['title']} ({node['id']})")

                children = node.get("children", [])
                if children:
                    extension = "    " if is_last else "│   "
                    print_tree(children, prefix + extension)

        click.echo(f"{page_title} (root)")
        print_tree(tree)

        if tree_stats:
            click.echo(f"\n{'=' * 60}")
            click.echo("Statistics:")
            click.echo(f"  Total pages: {tree_stats['totalPages']}")
            click.echo(f"  Max depth: {tree_stats['maxDepth']}")
            click.echo(f"  Root children: {tree_stats['rootChildren']}")

    print_success("Tree generated successfully")


@hierarchy.command(name="reorder")
@click.argument("parent_id")
@click.argument("order", required=False)
@click.option("--reverse", is_flag=True, help="Reverse current order")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def reorder_children(
    parent_id: str,
    order: str | None,
    reverse: bool,
    output: str,
) -> None:
    """Reorder child pages under a parent.

    ORDER is a comma-separated list of child page IDs in the desired order.
    If not provided, children will be sorted alphabetically by title.

    Examples:
        confluence hierarchy reorder 12345 "111,222,333"
        confluence hierarchy reorder 12345 --reverse
    """
    parent_id = validate_page_id(parent_id)

    client = get_confluence_client()

    # Get page info
    page = _get_page_info(client, parent_id)
    page_title = page.get("title", "Unknown")

    # Get current children
    children = list(client.paginate(
        f"/api/v2/pages/{parent_id}/children",
        operation="get children",
    ))

    if not children:
        raise ValidationError(f"No child pages found under {page_title}")

    # Determine new order
    if order:
        # Use provided order
        order_ids = [id.strip() for id in order.split(",")]

        # Validate all IDs exist
        child_ids = {c["id"] for c in children}
        invalid_ids = [id for id in order_ids if id not in child_ids]
        if invalid_ids:
            raise ValidationError(f"Invalid child IDs: {', '.join(invalid_ids)}")

        # Add any missing IDs at the end
        missing_ids = [c["id"] for c in children if c["id"] not in order_ids]
        final_order = order_ids + missing_ids
    else:
        # Sort alphabetically or reverse
        sorted_children = sorted(children, key=lambda c: c.get("title", "").lower())
        if reverse:
            sorted_children.reverse()
        final_order = [c["id"] for c in sorted_children]

    # Apply reordering using v1 API (v2 doesn't have reorder endpoint)
    # Note: The v1 API endpoint for reordering is:
    # PUT /rest/api/content/{id}/child/page/move
    # However, this requires specific positioning operations

    # For now, we'll report the new order - actual reordering
    # requires multiple API calls with position operations
    reordered = []
    for page_id_item in final_order:
        for child in children:
            if child["id"] == page_id_item:
                reordered.append(child)
                break

    if output == "json":
        click.echo(format_json({
            "parent": {"id": parent_id, "title": page_title},
            "newOrder": [{"id": c["id"], "title": c["title"]} for c in reordered],
        }))
    else:
        click.echo(f"\nNew order for children of: {page_title} ({parent_id})")
        click.echo(f"{'=' * 60}\n")

        data = []
        for i, child in enumerate(reordered, 1):
            data.append({
                "position": i,
                "id": child.get("id", ""),
                "title": child.get("title", "")[:40],
            })

        click.echo(format_table(
            data,
            columns=["position", "id", "title"],
            headers=["#", "ID", "Title"],
        ))

        click.echo("\nNote: Use Confluence UI to apply actual reordering.")

    print_success(f"Calculated new order for {len(reordered)} child page(s)")
