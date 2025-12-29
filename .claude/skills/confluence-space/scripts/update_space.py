#!/usr/bin/env python3
"""
Update Confluence space properties.

Examples:
    python update_space.py DOCS --name "New Name"
    python update_space.py DOCS --description "Updated description"
    python update_space.py DOCS --homepage 12345
"""

import sys
import argparse
from pathlib import Path

# Add shared lib to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'shared' / 'scripts' / 'lib'))

from config_manager import get_confluence_client
from error_handler import handle_errors, ValidationError, NotFoundError
from validators import validate_space_key, validate_page_id
from formatters import print_success, format_space, format_json


@handle_errors
def main():
    parser = argparse.ArgumentParser(
        description='Update Confluence space properties',
        epilog='''
Examples:
  python update_space.py DOCS --name "New Name"
  python update_space.py DOCS --description "Updated description"
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('space_key', help='Space key')
    parser.add_argument('--name', '-n', help='New space name')
    parser.add_argument('--description', '-d', help='New description')
    parser.add_argument('--homepage', help='Homepage page ID')
    parser.add_argument('--profile', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args()

    # Validate
    space_key = validate_space_key(args.space_key)

    if args.homepage:
        homepage_id = validate_page_id(args.homepage, field_name='homepage')
    else:
        homepage_id = None

    # Check that at least one update is requested
    if not any([args.name, args.description, args.homepage]):
        raise ValidationError("At least one of --name, --description, or --homepage is required")

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Get current space
    spaces = list(client.paginate(
        '/api/v2/spaces',
        params={'keys': space_key},
        operation='get space'
    ))

    if not spaces:
        raise NotFoundError(f"Space not found: {space_key}")

    current_space = spaces[0]
    space_id = current_space['id']

    # Build update data
    update_data = {}

    if args.name:
        update_data['name'] = args.name.strip()

    if args.description:
        update_data['description'] = {
            'plain': {
                'value': args.description,
                'representation': 'plain'
            }
        }

    if homepage_id:
        update_data['homepageId'] = homepage_id

    # Update the space
    result = client.put(
        f'/api/v2/spaces/{space_id}',
        json_data=update_data,
        operation='update space'
    )

    # Output
    if args.output == 'json':
        print(format_json(result))
    else:
        print(format_space(result))

    print_success(f"Updated space {space_key}")


if __name__ == '__main__':
    main()
