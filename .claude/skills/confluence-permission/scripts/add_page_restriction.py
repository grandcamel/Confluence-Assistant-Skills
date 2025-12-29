#!/usr/bin/env python3
"""
Add restriction to a Confluence page.

Restricts page access to specific users or groups.

Examples:
    python add_page_restriction.py 123456 read user:john.doe@example.com
    python add_page_restriction.py 123456 update group:confluence-users
    python add_page_restriction.py 123456 read user:account-id:123456
"""

import sys
import argparse
from pathlib import Path

# Add shared lib to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'shared' / 'scripts' / 'lib'))

from config_manager import get_confluence_client
from error_handler import handle_errors, ValidationError
from validators import validate_page_id
from formatters import print_success


VALID_OPERATIONS = ['read', 'update']


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
def main():
    parser = argparse.ArgumentParser(
        description='Add restriction to a Confluence page',
        epilog='''
Examples:
  python add_page_restriction.py 123456 read user:john.doe@example.com
  python add_page_restriction.py 123456 update group:confluence-users
  python add_page_restriction.py 123456 read user:account-id:123456

Principal Format:
  user:email@example.com       - User by email
  user:username                - User by username
  user:account-id:123456       - User by account ID
  group:groupname              - Group by name

Valid Operations:
  read   - Who can view the page
  update - Who can edit the page

Note: This uses the v1 API as page restrictions are not available in v2.
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('page_id', help='Page ID')
    parser.add_argument('operation', choices=VALID_OPERATIONS,
                        help='Restriction type (read or update)')
    parser.add_argument('principal', help='Principal in format type:identifier (e.g., user:email or group:name)')
    parser.add_argument('--profile', help='Confluence profile to use')
    args = parser.parse_args()

    # Validate
    page_id = validate_page_id(args.page_id)
    operation = args.operation
    principal_type, identifier = parse_principal(args.principal)

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Get current restrictions
    current = client.get(
        f'/rest/api/content/{page_id}/restriction',
        params={'expand': 'restrictions.user,restrictions.group'},
        operation='get current restrictions'
    )

    # Build updated restrictions
    operation_data = current.get(operation, {})
    restrictions = operation_data.get('restrictions', {})

    # Get existing lists
    users = restrictions.get('user', {}).get('results', [])
    groups = restrictions.get('group', {}).get('results', [])

    # Add new principal
    if principal_type == 'user':
        # Check if already exists
        existing = any(u.get('username', u.get('accountId', '')) == identifier for u in users)
        if existing:
            print(f"User '{identifier}' already has {operation} restriction on page {page_id}")
            return

        users.append({"type": "known", "username": identifier})
    else:  # group
        # Check if already exists
        existing = any(g.get('name', '') == identifier for g in groups)
        if existing:
            print(f"Group '{identifier}' already has {operation} restriction on page {page_id}")
            return

        groups.append({"type": "group", "name": identifier})

    # Build payload
    payload = [{
        "operation": operation,
        "restrictions": {
            "user": users,
            "group": groups
        }
    }]

    # Update restrictions
    client.put(
        f'/rest/api/content/{page_id}/restriction',
        json_data=payload,
        operation='add page restriction'
    )

    print(f"\nAdded {operation} restriction to {principal_type} '{identifier}' for page {page_id}")
    print_success("Restriction added successfully")


if __name__ == '__main__':
    main()
