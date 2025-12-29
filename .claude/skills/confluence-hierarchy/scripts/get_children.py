#!/usr/bin/env python3
"""
Get direct child pages of a given page.

Returns only immediate children (one level down), not all descendants.

Examples:
    python get_children.py 12345
    python get_children.py 12345 --output json
    python get_children.py 12345 --limit 50
    python get_children.py 12345 --sort title
"""

import sys
import argparse
from confluence_assistant_skills_lib import (
    get_confluence_client, handle_errors, validate_page_id, validate_limit,
    print_success, format_json,
)


@handle_errors
def main():
    parser = argparse.ArgumentParser(
        description='Get child pages of a Confluence page',
        epilog='''
Examples:
  python get_children.py 12345
  python get_children.py 12345 --output json
  python get_children.py 12345 --limit 50
  python get_children.py 12345 --sort title
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('page_id', help='Parent page ID')
    parser.add_argument('--limit', '-l', type=int, default=25,
                        help='Maximum number of children to retrieve (default: 25)')
    parser.add_argument('--sort', choices=['title', 'id', 'created'],
                        help='Sort children by field')
    parser.add_argument('--profile', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args()

    # Validate
    page_id = validate_page_id(args.page_id)
    limit = validate_limit(args.limit, max_value=250)

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Get parent page info
    parent = client.get(
        f'/api/v2/pages/{page_id}',
        operation='get parent page'
    )

    # Get children
    params = {'limit': limit}
    children_data = client.get(
        f'/api/v2/pages/{page_id}/children',
        params=params,
        operation='get child pages'
    )

    children = children_data.get('results', [])

    # Sort if requested
    if args.sort:
        if args.sort == 'title':
            children.sort(key=lambda x: x.get('title', '').lower())
        elif args.sort == 'id':
            children.sort(key=lambda x: x.get('id', ''))
        elif args.sort == 'created':
            children.sort(key=lambda x: x.get('createdAt', ''))

    # Output
    if args.output == 'json':
        print(format_json(children))
    else:
        # Text format
        print(f"Children of '{parent['title']}' (ID: {page_id}):\n")

        if not children:
            print("No child pages found.")
        else:
            for i, child in enumerate(children, 1):
                title = child.get('title', 'Untitled')
                child_id = child.get('id', 'Unknown')
                status = child.get('status', 'current')
                print(f"{i}. {title} (ID: {child_id}, Status: {status})")

    print_success(f"Retrieved {len(children)} child page(s)")

if __name__ == '__main__':
    main()
