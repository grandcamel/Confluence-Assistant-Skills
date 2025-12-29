#!/usr/bin/env python3
"""
List pages in a Confluence space.

Examples:
    python get_space_content.py DOCS
    python get_space_content.py DOCS --depth root
    python get_space_content.py DOCS --limit 100
"""

import sys
import argparse
from pathlib import Path

# Add shared lib to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'shared' / 'scripts' / 'lib'))

from config_manager import get_confluence_client
from error_handler import handle_errors, NotFoundError
from validators import validate_space_key, validate_limit
from formatters import print_success, format_page, format_json, format_table


@handle_errors
def main():
    parser = argparse.ArgumentParser(
        description='List pages in a Confluence space',
        epilog='''
Examples:
  python get_space_content.py DOCS
  python get_space_content.py DOCS --depth root
  python get_space_content.py DOCS --limit 100
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('space_key', help='Space key')
    parser.add_argument('--depth', choices=['root', 'children', 'all'], default='all',
                        help='Content depth (default: all)')
    parser.add_argument('--status', choices=['current', 'archived', 'draft'],
                        help='Filter by status')
    parser.add_argument('--include-archived', action='store_true',
                        help='Include archived content')
    parser.add_argument('--limit', '-l', type=int, default=50,
                        help='Maximum results (default: 50)')
    parser.add_argument('--profile', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args()

    # Validate
    space_key = validate_space_key(args.space_key)
    limit = validate_limit(args.limit, max_value=250)

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Get space ID first
    spaces = list(client.paginate(
        '/api/v2/spaces',
        params={'keys': space_key},
        operation='get space'
    ))

    if not spaces:
        raise NotFoundError(f"Space not found: {space_key}")

    space_id = spaces[0]['id']

    # Build params
    params = {
        'space-id': space_id,
        'limit': min(limit, 25)
    }

    if args.status:
        params['status'] = args.status

    if args.depth == 'root':
        params['depth'] = 'root'

    # Get pages
    pages = list(client.paginate(
        '/api/v2/pages',
        params=params,
        limit=limit,
        operation='get space content'
    ))

    # Output
    if args.output == 'json':
        print(format_json({'space_key': space_key, 'pages': pages, 'count': len(pages)}))
    else:
        if not pages:
            print(f"No pages found in space {space_key}.")
        else:
            print(f"\nSpace: {space_key}")
            print(f"Found {len(pages)} page(s):\n")

            # Table format
            data = []
            for page in pages:
                data.append({
                    'id': page.get('id', ''),
                    'title': page.get('title', '')[:40],
                    'status': page.get('status', 'current'),
                    'parent': page.get('parentId', '-') or '-'
                })

            print(format_table(
                data,
                columns=['id', 'title', 'status', 'parent'],
                headers=['ID', 'Title', 'Status', 'Parent ID']
            ))

    print_success(f"Listed {len(pages)} page(s) in space {space_key}")


if __name__ == '__main__':
    main()
