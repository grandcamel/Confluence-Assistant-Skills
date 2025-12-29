#!/usr/bin/env python3
"""
Add permission to a Confluence space.

Grants a permission to a user or group for a space.

Examples:
    python add_space_permission.py DOCS user:john.doe@example.com read
    python add_space_permission.py DOCS group:confluence-users write
    python add_space_permission.py TEST user:account-id:123456 administer
"""

import sys
import argparse
from pathlib import Path

# Add shared lib to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'shared' / 'scripts' / 'lib'))

from config_manager import get_confluence_client
from error_handler import handle_errors, ValidationError
from validators import validate_space_key
from formatters import print_success, print_warning


VALID_OPERATIONS = [
    'read', 'write', 'create', 'delete', 'export',
    'administer', 'setpermissions', 'createattachment'
]


def parse_principal(principal_str):
    """
    Parse principal string in format 'type:identifier'.

    Examples:
        user:john.doe@example.com
        group:confluence-users
        user:account-id:123456
    """
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
def main():
    parser = argparse.ArgumentParser(
        description='Add permission to a Confluence space',
        epilog='''
Examples:
  python add_space_permission.py DOCS user:john.doe@example.com read
  python add_space_permission.py DOCS group:confluence-users write
  python add_space_permission.py TEST user:account-id:123456 administer

Principal Format:
  user:email@example.com       - User by email
  user:username                - User by username
  user:account-id:123456       - User by account ID
  group:groupname              - Group by name

Valid Operations:
  read, write, create, delete, export, administer, setpermissions, createattachment

Note: This uses the v1 API. Space permission management is not available in v2.
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('space_key', help='Space key')
    parser.add_argument('principal', help='Principal in format type:identifier (e.g., user:email or group:name)')
    parser.add_argument('operation', choices=VALID_OPERATIONS,
                        help='Permission operation to grant')
    parser.add_argument('--profile', help='Confluence profile to use')
    args = parser.parse_args()

    # Validate
    space_key = validate_space_key(args.space_key)
    principal_type, identifier = parse_principal(args.principal)
    operation = args.operation

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Build permission payload for v1 API
    payload = {
        "subject": {
            principal_type: {
                "results": [
                    {"username": identifier} if principal_type == 'user' else {"name": identifier}
                ],
                "size": 1
            }
        },
        "operation": {
            "key": operation,
            "target": "space"
        }
    }

    print_warning("Note: Adding space permissions via API may have limitations.")
    print_warning("Some Confluence instances restrict this operation to administrators.")

    # Add permission (v1 API)
    result = client.post(
        f'/rest/api/space/{space_key}/permission',
        json_data=payload,
        operation='add space permission'
    )

    print(f"\nAdded {operation} permission to {principal_type} '{identifier}' for space {space_key}")
    print_success("Permission added successfully")


if __name__ == '__main__':
    main()
