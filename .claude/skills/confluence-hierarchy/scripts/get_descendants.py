#!/usr/bin/env python3
"""
Get all descendant pages of a given page (recursive).

Retrieves all pages below the specified page in the hierarchy,
including children, grandchildren, etc.

Examples:
    python get_descendants.py 12345
    python get_descendants.py 12345 --max-depth 2
    python get_descendants.py 12345 --output json
"""

import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any, Set

# Add shared lib to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'shared' / 'scripts' / 'lib'))

from config_manager import get_confluence_client
from error_handler import handle_errors
from validators import validate_page_id
from formatters import print_success, format_json


def get_descendants_recursive(
    client,
    page_id: str,
    max_depth: int = None,
    current_depth: int = 1,
    visited: Set[str] = None
) -> List[Dict[str, Any]]:
    """
    Recursively get all descendants of a page.

    Args:
        client: Confluence client
        page_id: Parent page ID
        max_depth: Maximum depth to traverse (None = unlimited)
        current_depth: Current recursion depth
        visited: Set of visited page IDs to prevent infinite loops

    Returns:
        List of descendant pages with depth information
    """
    if visited is None:
        visited = set()

    # Prevent infinite loops
    if page_id in visited:
        return []

    visited.add(page_id)

    # Check depth limit
    if max_depth is not None and current_depth > max_depth:
        return []

    descendants = []

    # Get direct children
    try:
        children_data = client.get(
            f'/api/v2/pages/{page_id}/children',
            params={'limit': 250},
            operation=f'get children at depth {current_depth}'
        )

        children = children_data.get('results', [])

        for child in children:
            child_id = child.get('id')
            if not child_id:
                continue

            # Add child with depth info
            child_with_depth = child.copy()
            child_with_depth['depth'] = current_depth
            descendants.append(child_with_depth)

            # Recursively get grandchildren
            grandchildren = get_descendants_recursive(
                client,
                child_id,
                max_depth,
                current_depth + 1,
                visited
            )
            descendants.extend(grandchildren)

    except Exception as e:
        # Log error but continue with other branches
        print(f"Warning: Could not get children of page {page_id}: {e}", file=sys.stderr)

    return descendants


@handle_errors
def main():
    parser = argparse.ArgumentParser(
        description='Get all descendant pages of a Confluence page (recursive)',
        epilog='''
Examples:
  python get_descendants.py 12345
  python get_descendants.py 12345 --max-depth 2
  python get_descendants.py 12345 --output json
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('page_id', help='Parent page ID')
    parser.add_argument('--max-depth', '-d', type=int,
                        help='Maximum depth to traverse (default: unlimited)')
    parser.add_argument('--profile', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args()

    # Validate
    page_id = validate_page_id(args.page_id)

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Get parent page info
    parent = client.get(
        f'/api/v2/pages/{page_id}',
        operation='get parent page'
    )

    # Get all descendants
    descendants = get_descendants_recursive(
        client,
        page_id,
        max_depth=args.max_depth
    )

    # Output
    if args.output == 'json':
        print(format_json(descendants))
    else:
        # Text format with indentation
        print(f"Descendants of '{parent['title']}' (ID: {page_id}):\n")

        if not descendants:
            print("No descendant pages found.")
        else:
            for descendant in descendants:
                title = descendant.get('title', 'Untitled')
                desc_id = descendant.get('id', 'Unknown')
                depth = descendant.get('depth', 1)
                indent = '  ' * (depth - 1)
                print(f"{indent}- {title} (ID: {desc_id})")

    print_success(f"Retrieved {len(descendants)} descendant(s)")


if __name__ == '__main__':
    main()
