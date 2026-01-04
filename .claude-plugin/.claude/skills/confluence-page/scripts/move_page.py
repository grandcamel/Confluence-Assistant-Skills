#!/usr/bin/env python3
"""
Move a Confluence page to a new location.

Examples:
    python move_page.py 12345 --parent 67890
    python move_page.py 12345 --space NEWSPACE
    python move_page.py 12345 --space NEWSPACE --root
"""

import sys
import argparse
from confluence_assistant_skills_lib import (
    get_confluence_client, handle_errors, ValidationError, validate_page_id,
    validate_space_key, print_success, format_page, format_json,
)


@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description='Move a Confluence page to a new location',
        epilog='''
Examples:
  python move_page.py 12345 --parent 67890
  python move_page.py 12345 --space NEWSPACE
  python move_page.py 12345 --space NEWSPACE --root
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('page_id', help='Page ID to move')
    parser.add_argument('--space', '-s', help='Target space key')
    parser.add_argument('--parent', '-p', help='Target parent page ID')
    parser.add_argument('--root', action='store_true',
                        help='Move to space root (no parent)')
    parser.add_argument('--profile', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args(argv)

    # Validate
    page_id = validate_page_id(args.page_id)

    if args.parent:
        parent_id = validate_page_id(args.parent, field_name='parent')
    else:
        parent_id = None

    # Check that at least one move option is provided
    if not args.space and not args.parent and not args.root:
        raise ValidationError("At least one of --space, --parent, or --root is required")

    if args.parent and args.root:
        raise ValidationError("Cannot specify both --parent and --root")

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Get current page
    current_page = client.get(
        f'/api/v2/pages/{page_id}',
        operation='get current page'
    )

    current_version = current_page.get('version', {}).get('number', 1)

    # Determine target space ID
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
    else:
        target_space_id = current_page.get('spaceId')

    # Build update data
    update_data = {
        'id': page_id,
        'status': current_page.get('status', 'current'),
        'title': current_page.get('title'),
        'spaceId': target_space_id,
        'version': {
            'number': current_version + 1,
            'message': 'Page moved'
        }
    }

    # Set parent
    if args.root:
        # Remove parent to move to root
        # In API v2, we don't include parentId to make it a root page
        pass
    elif parent_id:
        update_data['parentId'] = parent_id
    else:
        # Keep current parent if moving within space
        if current_page.get('parentId'):
            update_data['parentId'] = current_page['parentId']

    # Move the page
    result = client.put(
        f'/api/v2/pages/{page_id}',
        json_data=update_data,
        operation='move page'
    )

    # Output
    if args.output == 'json':
        print(format_json(result))
    else:
        print(format_page(result))

    destination = []
    if args.space:
        destination.append(f"space {args.space}")
    if args.parent:
        destination.append(f"under parent {args.parent}")
    elif args.root:
        destination.append("to space root")

    print_success(f"Moved page '{result['title']}' {' '.join(destination)}")

if __name__ == '__main__':
    main()
