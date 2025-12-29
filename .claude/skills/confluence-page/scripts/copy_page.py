#!/usr/bin/env python3
"""
Copy a Confluence page to a new location.

Examples:
    python copy_page.py 12345 --title "Page Copy"
    python copy_page.py 12345 --title "Page Copy" --space NEWSPACE
    python copy_page.py 12345 --title "Page Copy" --include-children
"""

import sys
import argparse
from pathlib import Path

# Add shared lib to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'shared' / 'scripts' / 'lib'))

from config_manager import get_confluence_client
from error_handler import handle_errors, ValidationError
from validators import validate_page_id, validate_space_key, validate_title
from formatters import print_success, print_info, format_page, format_json


@handle_errors
def main():
    parser = argparse.ArgumentParser(
        description='Copy a Confluence page to a new location',
        epilog='''
Examples:
  python copy_page.py 12345 --title "Page Copy"
  python copy_page.py 12345 --space NEWSPACE
  python copy_page.py 12345 --include-children
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('page_id', help='Source page ID')
    parser.add_argument('--title', '-t', help='New page title (default: Copy of [original])')
    parser.add_argument('--space', '-s', help='Target space key')
    parser.add_argument('--parent', '-p', help='Target parent page ID')
    parser.add_argument('--include-children', action='store_true',
                        help='Copy child pages recursively')
    parser.add_argument('--profile', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args()

    # Validate
    source_page_id = validate_page_id(args.page_id)

    if args.parent:
        parent_id = validate_page_id(args.parent, field_name='parent')
    else:
        parent_id = None

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Get source page
    source_page = client.get(
        f'/api/v2/pages/{source_page_id}',
        params={'body-format': 'storage'},
        operation='get source page'
    )

    source_title = source_page.get('title', 'Untitled')
    source_space_id = source_page.get('spaceId')

    # Determine new title
    if args.title:
        new_title = validate_title(args.title)
    else:
        new_title = f"Copy of {source_title}"

    # Determine target space
    target_space_id = source_space_id
    if args.space:
        space_key = validate_space_key(args.space)
        spaces = list(client.paginate(
            '/api/v2/spaces',
            params={'keys': space_key},
            operation='get target space'
        ))
        if not spaces:
            raise ValidationError(f"Space not found: {space_key}")
        target_space_id = spaces[0]['id']

    # Build copy data
    copy_data = {
        'spaceId': target_space_id,
        'status': source_page.get('status', 'current'),
        'title': new_title,
        'body': source_page.get('body', {})
    }

    if parent_id:
        copy_data['parentId'] = parent_id

    # Create the copy
    print_info(f"Copying page '{source_title}' to '{new_title}'...")

    result = client.post(
        '/api/v2/pages',
        json_data=copy_data,
        operation='copy page'
    )

    # Handle children if requested
    if args.include_children:
        print_info("Copying child pages...")
        _copy_children(client, source_page_id, result['id'], target_space_id)

    # Output
    if args.output == 'json':
        print(format_json(result))
    else:
        print(format_page(result))

    print_success(f"Copied page to '{new_title}' with ID {result['id']}")


def _copy_children(client, source_parent_id: str, target_parent_id: str, target_space_id: str):
    """Recursively copy child pages."""
    # Get children of source page
    children = list(client.paginate(
        f'/api/v2/pages/{source_parent_id}/children',
        params={'body-format': 'storage'},
        operation='get children'
    ))

    for child in children:
        child_id = child['id']
        child_title = child.get('title', 'Untitled')

        # Get full child page with body
        full_child = client.get(
            f'/api/v2/pages/{child_id}',
            params={'body-format': 'storage'},
            operation='get child page'
        )

        # Create copy of child
        child_copy_data = {
            'spaceId': target_space_id,
            'status': full_child.get('status', 'current'),
            'title': child_title,
            'parentId': target_parent_id,
            'body': full_child.get('body', {})
        }

        new_child = client.post(
            '/api/v2/pages',
            json_data=child_copy_data,
            operation='copy child page'
        )

        print_info(f"  Copied child: {child_title}")

        # Recursively copy grandchildren
        _copy_children(client, child_id, new_child['id'], target_space_id)


if __name__ == '__main__':
    main()
