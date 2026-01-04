#!/usr/bin/env python3
"""
Reorder child pages of a parent page.

Changes the display order of child pages in Confluence.
Note: The v2 API may have limitations on reordering. This script provides
the structure and validation needed when the API supports it.

Examples:
    python reorder_children.py 12345 200,201,202
    python reorder_children.py 12345 --order 200,201,202
    python reorder_children.py 12345 --reverse
"""

import sys
import argparse
from typing import List
from confluence_assistant_skills_lib import (
    get_confluence_client, handle_errors, ValidationError, validate_page_id,
    print_success, print_warning, print_info,
)


def parse_order(order_str: str) -> List[str]:
    """
    Parse comma-separated page IDs.

    Args:
        order_str: Comma-separated page IDs

    Returns:
        List of page IDs

    Raises:
        ValidationError: If format is invalid
    """
    if not order_str:
        raise ValidationError("Order string cannot be empty")

    page_ids = [id.strip() for id in order_str.split(',')]

    # Validate each ID
    validated_ids = []
    for page_id in page_ids:
        validated = validate_page_id(page_id)
        validated_ids.append(validated)

    return validated_ids

def validate_order(
    proposed_order: List[str],
    current_children: List[dict]
) -> None:
    """
    Validate that proposed order matches current children.

    Args:
        proposed_order: List of proposed page IDs
        current_children: Current children from API

    Raises:
        ValidationError: If order is invalid
    """
    current_ids = set(c['id'] for c in current_children)
    proposed_ids = set(proposed_order)

    # Check for duplicates
    if len(proposed_ids) != len(proposed_order):
        duplicates = [id for id in proposed_order if proposed_order.count(id) > 1]
        raise ValidationError(
            f"Duplicate page IDs in order: {', '.join(set(duplicates))}"
        )

    # Check for missing children
    missing = current_ids - proposed_ids
    if missing:
        raise ValidationError(
            f"Order is missing {len(missing)} child page(s): {', '.join(missing)}"
        )

    # Check for extra IDs
    extra = proposed_ids - current_ids
    if extra:
        raise ValidationError(
            f"Order contains {len(extra)} invalid page ID(s): {', '.join(extra)}"
        )

@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description='Reorder child pages of a Confluence page',
        epilog='''
Examples:
  python reorder_children.py 12345 200,201,202
  python reorder_children.py 12345 --order 200,201,202
  python reorder_children.py 12345 --reverse

Note: As of this implementation, the Confluence v2 API may not fully support
page reordering. This script provides validation and structure for when the
API supports it. Check the Confluence API documentation for current capabilities.
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('parent_id', help='Parent page ID')
    parser.add_argument('order', nargs='?', help='Comma-separated child page IDs in desired order')
    parser.add_argument('--order', '-o', dest='order_flag',
                        help='Comma-separated child page IDs (alternative to positional arg)')
    parser.add_argument('--reverse', action='store_true',
                        help='Reverse current order')
    parser.add_argument('--profile', help='Confluence profile to use')
    args = parser.parse_args(argv)

    # Validate parent ID
    parent_id = validate_page_id(args.parent_id)

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Get parent page info
    parent = client.get(
        f'/api/v2/pages/{parent_id}',
        operation='get parent page'
    )

    # Get current children
    children_data = client.get(
        f'/api/v2/pages/{parent_id}/children',
        params={'limit': 250},
        operation='get current children'
    )

    current_children = children_data.get('results', [])

    if not current_children:
        print_warning(f"Page '{parent['title']}' has no children to reorder")
        return

    # Determine new order
    if args.reverse:
        # Reverse current order
        new_order = [c['id'] for c in reversed(current_children)]
        print_info("Reversing current order")
    else:
        # Parse order from arguments
        order_str = args.order or args.order_flag
        if not order_str:
            # Show current order and exit
            print(f"Current children of '{parent['title']}':\n")
            for i, child in enumerate(current_children, 1):
                print(f"{i}. {child['title']} (ID: {child['id']})")
            print("\nTo reorder, provide comma-separated IDs:")
            print(f"  python reorder_children.py {parent_id} <id1,id2,id3>")
            return

        new_order = parse_order(order_str)

    # Validate order
    validate_order(new_order, current_children)

    # Display proposed order
    print(f"Proposed order for children of '{parent['title']}':\n")
    child_lookup = {c['id']: c for c in current_children}
    for i, page_id in enumerate(new_order, 1):
        child = child_lookup.get(page_id, {})
        title = child.get('title', 'Unknown')
        print(f"{i}. {title} (ID: {page_id})")

    # Note about API limitations
    print_warning(
        "\nNote: The Confluence v2 API may not fully support page reordering.\n"
        "This operation validates the order but may require API updates to execute."
    )

    # TODO: Implement actual reordering when API supports it
    # The endpoint might be something like:
    # PUT /api/v2/pages/{parent_id}/children/order
    # with body: {"order": new_order}

    print_success(f"Validated order for {len(new_order)} children")

if __name__ == '__main__':
    main()
