#!/usr/bin/env python3
"""
Remove permission from a Confluence space.

Revokes a permission from a user or group for a space.

Examples:
    python remove_space_permission.py DOCS --user john.doe@example.com --operation read
    python remove_space_permission.py DOCS --group confluence-users --operation write
"""

import sys
import argparse
from confluence_assistant_skills_lib import (
    get_confluence_client, handle_errors, ValidationError, validate_space_key,
    print_success, print_warning,
)


VALID_OPERATIONS = [
    'read', 'write', 'create', 'delete', 'export',
    'administer', 'setpermissions', 'createattachment'
]


@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description='Remove permission from a Confluence space',
        epilog='''
Examples:
  python remove_space_permission.py DOCS --user john.doe@example.com --operation read
  python remove_space_permission.py DOCS --group confluence-users --operation write

Valid Operations:
  read, write, create, delete, export, administer, setpermissions, createattachment

Note: This uses the v1 API. The v2 API does not support removing space permissions.
      You may need to use the Confluence UI for some permission management operations.
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('space_key', help='Space key')
    parser.add_argument('--user', help='User permission to remove (email, username, or account-id:xxx)')
    parser.add_argument('--group', help='Group permission to remove')
    parser.add_argument('--operation', required=True, choices=VALID_OPERATIONS,
                        help='Permission operation to revoke')
    parser.add_argument('--profile', help='Confluence profile to use')
    args = parser.parse_args(argv)

    # Validate inputs
    if not args.user and not args.group:
        raise ValidationError("Either --user or --group must be specified")
    if args.user and args.group:
        raise ValidationError("Cannot specify both --user and --group")

    # Validate
    space_key = validate_space_key(args.space_key)

    # Determine principal type and identifier
    if args.user:
        principal_type = 'user'
        identifier = args.user
    else:
        principal_type = 'group'
        identifier = args.group

    operation = args.operation

    # Get client
    client = get_confluence_client(profile=args.profile)

    print_warning("Note: Removing space permissions via API may have limitations.")
    print_warning("You may need to first list permissions to find the permission ID.")

    # First, get current permissions to find the ID
    permissions_result = client.get(
        f'/rest/api/space/{space_key}/permission',
        operation='get space permissions for deletion'
    )

    # Find matching permission
    permission_id = None
    if 'results' in permissions_result:
        for perm in permissions_result['results']:
            perm_op = perm.get('operation', {}).get('key', '')
            principal_data = perm.get('subjects', {}).get(principal_type, {}).get('results', [])

            for principal in principal_data:
                principal_name = principal.get('username' if principal_type == 'user' else 'name', '')
                if principal_name == identifier and perm_op == operation:
                    permission_id = perm.get('id')
                    break

            if permission_id:
                break

    if not permission_id:
        raise ValidationError(
            f"Could not find {operation} permission for {principal_type} '{identifier}' in space {space_key}"
        )

    # Delete the permission
    client.delete(
        f'/rest/api/space/{space_key}/permission/{permission_id}',
        operation='remove space permission'
    )

    print(f"\nRemoved {operation} permission from {principal_type} '{identifier}' for space {space_key}")
    print_success("Permission removed successfully")

if __name__ == '__main__':
    main()
