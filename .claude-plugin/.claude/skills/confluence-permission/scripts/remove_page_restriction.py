#!/usr/bin/env python3
"""
Remove restriction from a Confluence page.

Removes a user or group restriction from a page.

Examples:
    python remove_page_restriction.py 123456 read user:john.doe@example.com
    python remove_page_restriction.py 123456 update group:confluence-users
    python remove_page_restriction.py 123456 read --all
"""

import sys
import argparse
from confluence_assistant_skills_lib import (
    get_confluence_client, handle_errors, ValidationError, validate_page_id,
    print_success,
)


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
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description='Remove restriction from a Confluence page',
        epilog='''
Examples:
  python remove_page_restriction.py 123456 read user:john.doe@example.com
  python remove_page_restriction.py 123456 update group:confluence-users
  python remove_page_restriction.py 123456 read --all

Principal Format:
  user:email@example.com       - User by email
  user:username                - User by username
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
    parser.add_argument('principal', nargs='?', help='Principal in format type:identifier (e.g., user:email or group:name)')
    parser.add_argument('--all', action='store_true',
                        help='Remove all restrictions of this type')
    parser.add_argument('--profile', help='Confluence profile to use')
    args = parser.parse_args(argv)

    # Validate
    page_id = validate_page_id(args.page_id)
    operation = args.operation

    if not args.all and not args.principal:
        raise ValidationError("Either specify a principal or use --all to remove all restrictions")

    if args.all and args.principal:
        raise ValidationError("Cannot specify both a principal and --all")

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

    if args.all:
        # Remove all restrictions
        users = []
        groups = []
        message = f"all {operation} restrictions"
    else:
        # Remove specific principal
        principal_type, identifier = parse_principal(args.principal)

        if principal_type == 'user':
            original_count = len(users)
            users = [u for u in users if u.get('username', u.get('accountId', '')) != identifier]
            if len(users) == original_count:
                raise ValidationError(
                    f"User '{identifier}' does not have {operation} restriction on page {page_id}"
                )
        else:  # group
            original_count = len(groups)
            groups = [g for g in groups if g.get('name', '') != identifier]
            if len(groups) == original_count:
                raise ValidationError(
                    f"Group '{identifier}' does not have {operation} restriction on page {page_id}"
                )

        message = f"{operation} restriction from {principal_type} '{identifier}'"

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
        operation='remove page restriction'
    )

    print(f"\nRemoved {message} for page {page_id}")
    print_success("Restriction removed successfully")

if __name__ == '__main__':
    main()
