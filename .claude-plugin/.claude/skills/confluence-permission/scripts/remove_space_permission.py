#!/usr/bin/env python3
"""
Remove permission from a Confluence space.

Revokes a permission from a user or group for a space.

Examples:
    python remove_space_permission.py DOCS user:john.doe@example.com read
    python remove_space_permission.py DOCS group:confluence-users write
    python remove_space_permission.py TEST --permission-id 123456
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

def parse_principal(principal_str):
    """Parse principal string in format 'type:identifier'."""
    if ':' not in principal_str:
        raise ValidationError(
            "Principal must be in format 'type:identifier' (e.g., 'user:email@example.com' or 'group:groupname')"
        )

    parts = principal_str.split(':', 1)
    principal_type = parts[0].lower()

    if principal_type not in ['user', 'group']:
        raise ValidationError(f"Principal type must be 'user' or 'group', got '{principal_type}'")

    identifier = parts[1]

    if not identifier:
        raise ValidationError("Principal identifier cannot be empty")

    return principal_type, identifier

@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description='Remove permission from a Confluence space',
        epilog='''
Examples:
  python remove_space_permission.py DOCS user:john.doe@example.com read
  python remove_space_permission.py DOCS group:confluence-users write

Principal Format:
  user:email@example.com       - User by email
  user:username                - User by username
  group:groupname              - Group by name

Valid Operations:
  read, write, create, delete, export, administer, setpermissions, createattachment

Note: This uses the v1 API. The v2 API does not support removing space permissions.
      You may need to use the Confluence UI for some permission management operations.
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('space_key', help='Space key')
    parser.add_argument('principal', help='Principal in format type:identifier (e.g., user:email or group:name)')
    parser.add_argument('operation', choices=VALID_OPERATIONS,
                        help='Permission operation to revoke')
    parser.add_argument('--profile', help='Confluence profile to use')
    args = parser.parse_args(argv)

    # Validate
    space_key = validate_space_key(args.space_key)
    principal_type, identifier = parse_principal(args.principal)
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
