#!/usr/bin/env python3
"""
Get full hierarchical tree structure of a page and its descendants.

Builds a nested tree structure showing the complete hierarchy.
Useful for visualizing page organization or exporting structure.

Examples:
    python get_page_tree.py 12345
    python get_page_tree.py 12345 --max-depth 3
    python get_page_tree.py 12345 --output json
    python get_page_tree.py 12345 --stats
"""

import argparse
import sys
from typing import Any, Optional

from confluence_assistant_skills_lib import (
    format_json,
    get_confluence_client,
    handle_errors,
    print_info,
    print_success,
    validate_page_id,
)


def build_page_tree(
    client,
    page_id: str,
    max_depth: Optional[int] = None,
    current_depth: int = 0,
    visited: Optional[set[str]] = None,
) -> dict[str, Any]:
    """
    Recursively build a tree structure for a page and its descendants.

    Args:
        client: Confluence client
        page_id: Root page ID
        max_depth: Maximum depth to traverse (None = unlimited)
        current_depth: Current recursion depth
        visited: Set of visited page IDs to prevent infinite loops

    Returns:
        Tree structure with nested children
    """
    if visited is None:
        visited = set()

    # Prevent infinite loops
    if page_id in visited:
        return None

    visited.add(page_id)

    # Get page info
    page = client.get(
        f"/api/v2/pages/{page_id}", operation=f"get page at depth {current_depth}"
    )

    tree_node = {
        "id": page.get("id"),
        "title": page.get("title"),
        "status": page.get("status"),
        "children": [],
    }

    # Check depth limit
    if max_depth is not None and current_depth >= max_depth:
        return tree_node

    # Get children
    try:
        children_data = client.get(
            f"/api/v2/pages/{page_id}/children",
            params={"limit": 250},
            operation=f"get children at depth {current_depth}",
        )

        children = children_data.get("results", [])

        for child in children:
            child_id = child.get("id")
            if not child_id:
                continue

            # Recursively build child tree
            child_tree = build_page_tree(
                client, child_id, max_depth, current_depth + 1, visited
            )

            if child_tree:
                tree_node["children"].append(child_tree)

    except Exception as e:
        print(
            f"Warning: Could not get children of page {page_id}: {e}", file=sys.stderr
        )

    return tree_node


def format_tree_text(node: dict[str, Any], depth: int = 0) -> str:
    """
    Format tree as indented text.

    Args:
        node: Tree node
        depth: Current depth for indentation

    Returns:
        Formatted string
    """
    lines = []
    indent = "  " * depth
    title = node.get("title", "Untitled")
    node_id = node.get("id", "Unknown")
    status = node.get("status", "current")

    lines.append(f"{indent}{title} (ID: {node_id}, Status: {status})")

    for child in node.get("children", []):
        lines.append(format_tree_text(child, depth + 1))

    return "\n".join(lines)


def calculate_tree_stats(node: dict[str, Any]) -> dict[str, int]:
    """
    Calculate statistics about the tree.

    Args:
        node: Root tree node

    Returns:
        Dictionary with statistics
    """

    def count_nodes(n):
        count = 1
        for child in n.get("children", []):
            count += count_nodes(child)
        return count

    def max_depth(n, current=0):
        if not n.get("children"):
            return current
        return max(max_depth(child, current + 1) for child in n["children"])

    def count_leaves(n):
        if not n.get("children"):
            return 1
        return sum(count_leaves(child) for child in n["children"])

    return {
        "total_pages": count_nodes(node),
        "max_depth": max_depth(node),
        "leaf_pages": count_leaves(node),
    }


@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Get full page tree structure for a Confluence page",
        epilog="""
Examples:
  python get_page_tree.py 12345
  python get_page_tree.py 12345 --max-depth 3
  python get_page_tree.py 12345 --output json
  python get_page_tree.py 12345 --stats
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("page_id", help="Root page ID")
    parser.add_argument(
        "--max-depth",
        "-d",
        type=int,
        help="Maximum depth to traverse (default: unlimited)",
    )
    parser.add_argument("--stats", action="store_true", help="Show tree statistics")
    parser.add_argument(
        "--output",
        "-o",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    args = parser.parse_args(argv)

    # Validate
    page_id = validate_page_id(args.page_id)

    # Get client
    client = get_confluence_client()

    # Build tree
    print_info("Building page tree...")
    tree = build_page_tree(client, page_id, max_depth=args.max_depth)

    # Output
    if args.output == "json":
        print(format_json(tree))
    else:
        # Text format
        print(f"\nPage Tree for '{tree['title']}' (ID: {page_id}):\n")
        print(format_tree_text(tree))

    # Show statistics if requested
    if args.stats:
        stats = calculate_tree_stats(tree)
        print("\n--- Tree Statistics ---")
        print(f"Total pages: {stats['total_pages']}")
        print(f"Maximum depth: {stats['max_depth']}")
        print(f"Leaf pages: {stats['leaf_pages']}")

    print_success("Page tree retrieved successfully")


if __name__ == "__main__":
    main()
