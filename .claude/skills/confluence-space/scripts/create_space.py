#!/usr/bin/env python3
"""
Create a new Confluence space.

Examples:
    python create_space.py --key DOCS --name "Documentation"
    python create_space.py --key KB --name "Knowledge Base" --description "Company KB"
"""

import sys
import argparse
from confluence_assistant_skills_lib import (
    get_confluence_client, handle_errors, ValidationError, validate_space_key,
    print_success, format_space, format_json,
)


@handle_errors
def main():
    parser = argparse.ArgumentParser(
        description='Create a new Confluence space',
        epilog='''
Examples:
  python create_space.py --key DOCS --name "Documentation"
  python create_space.py --key KB --name "Knowledge Base" --description "KB"
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--key', '-k', required=True, help='Space key')
    parser.add_argument('--name', '-n', required=True, help='Space name')
    parser.add_argument('--description', '-d', help='Space description')
    parser.add_argument('--type', choices=['global', 'personal'], default='global',
                        help='Space type (default: global)')
    parser.add_argument('--profile', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args()

    # Validate
    space_key = validate_space_key(args.key)

    if not args.name or len(args.name.strip()) < 1:
        raise ValidationError("Space name is required")

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Build space data
    space_data = {
        'key': space_key,
        'name': args.name.strip()
    }

    if args.description:
        space_data['description'] = {
            'plain': {
                'value': args.description,
                'representation': 'plain'
            }
        }

    # Create the space
    result = client.post(
        '/api/v2/spaces',
        json_data=space_data,
        operation='create space'
    )

    # Output
    if args.output == 'json':
        print(format_json(result))
    else:
        print(format_space(result))

    print_success(f"Created space '{args.name}' with key {space_key}")

if __name__ == '__main__':
    main()
