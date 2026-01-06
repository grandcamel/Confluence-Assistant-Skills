#!/usr/bin/env python3
"""
Get permissions for a Confluence space.

Retrieves the list of permissions assigned to users and groups for a space.

Examples:
    python get_space_permissions.py DOCS
    python get_space_permissions.py DOCS --output json
    python get_space_permissions.py DOCS --profile production
"""

import sys
import argparse
from confluence_assistant_skills_lib import (
    get_confluence_client, handle_errors, validate_space_key, print_success,
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
  python get_space_permissions.py DOCS
  python get_space_permissions.py DOCS --output json
  python get_space_permissions.py DOCS --profile production
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('space_key', help='Space key (e.g., DOCS, TEST)')
    parser.add_argument('--profile', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args(argv)

    # Validate
    space_key = validate_space_key(args.space_key)

    # Get client
    client = get_confluence_client(profile=args.profile)

    # First get space ID from space key (v2 API requires numeric ID)
    space_result = client.get(
        '/rest/api/space',
        params={'spaceKey': space_key},
        operation='get space by key'
    )
    spaces = space_result.get('results', [])
    if not spaces:
        raise ValueError(f"Space with key '{space_key}' not found")
    space_id = spaces[0].get('id')

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
            print(f"Space Permissions (Key: {space_key})")
            print(f"Total permissions: {len(permissions)}\n")

            # Format as table
            formatted = [format_permission(p) for p in permissions]
            print(format_table(
                formatted,
                columns=['Principal Type', 'Principal ID', 'Operation', 'Target'],
                max_width=50
            ))

    print_success(f"Retrieved {len(permissions)} permission(s) for space {space_key}")

if __name__ == '__main__':
    main()
