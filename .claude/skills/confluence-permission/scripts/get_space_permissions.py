#!/usr/bin/env python3
"""
Get permissions for a Confluence space.

Retrieves the list of permissions assigned to users and groups for a space.

Examples:
    python get_space_permissions.py 123456
    python get_space_permissions.py 123456 --output json
    python get_space_permissions.py 123456 --profile production
"""

import sys
import argparse
from confluence_assistant_skills_lib import (
    get_confluence_client, handle_errors, validate_page_id  # Space IDs use same numeric format, print_success,
    format_json, format_table,
)


def format_permission(permission):
    """Format a single permission for display."""
    principal = permission.get('principal', {})
    operation = permission.get('operation', {})

    principal_type = principal.get('type', 'unknown')
    principal_id = principal.get('id', 'unknown')
    operation_key = operation.get('key', 'unknown')
    target = operation.get('target', 'unknown')

    return {
        'Principal Type': principal_type,
        'Principal ID': principal_id,
        'Operation': operation_key,
        'Target': target
    }

@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description='Get permissions for a Confluence space',
        epilog='''
Examples:
  python get_space_permissions.py 123456
  python get_space_permissions.py 123456 --output json
  python get_space_permissions.py 123456 --profile production
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('space_id', help='Space ID (numeric)')
    parser.add_argument('--profile', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args(argv)

    # Validate
    space_id = validate_page_id(args.space_id, 'space_id')

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Get space permissions (v2 API)
    result = client.get(
        f'/api/v2/spaces/{space_id}/permissions',
        operation='get space permissions'
    )

    permissions = result.get('results', [])

    # Output
    if args.output == 'json':
        print(format_json(result))
    else:
        if not permissions:
            print("No explicit permissions found for this space.")
            print("(The space may inherit permissions from global settings)")
        else:
            print(f"Space Permissions (ID: {space_id})")
            print(f"Total permissions: {len(permissions)}\n")

            # Format as table
            formatted = [format_permission(p) for p in permissions]
            print(format_table(
                formatted,
                columns=['Principal Type', 'Principal ID', 'Operation', 'Target'],
                max_width=50
            ))

    print_success(f"Retrieved {len(permissions)} permission(s) for space {space_id}")

if __name__ == '__main__':
    main()
