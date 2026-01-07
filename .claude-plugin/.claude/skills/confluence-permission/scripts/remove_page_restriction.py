#!/usr/bin/env python3
"""
Remove restriction from a Confluence page.

Removes a user or group restriction from a page.

Examples:
    python remove_page_restriction.py 123456 --operation read --user john.doe@example.com
    python remove_page_restriction.py 123456 --operation update --group confluence-users
    python remove_page_restriction.py 123456 --operation read --all
"""

import argparse

from confluence_assistant_skills_lib import (
    ValidationError,
    get_confluence_client,
    handle_errors,
    print_success,
    validate_page_id,
)

VALID_OPERATIONS = ["read", "update"]


@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Remove restriction from a Confluence page",
        epilog="""
Examples:
  python remove_page_restriction.py 123456 --operation read --user john.doe@example.com
  python remove_page_restriction.py 123456 --operation update --group confluence-users
  python remove_page_restriction.py 123456 --operation read --all

Valid Operations:
  read   - Who can view the page
  update - Who can edit the page

Note: This uses the v1 API as page restrictions are not available in v2.
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("page_id", help="Page ID")
    parser.add_argument(
        "--user", help="User restriction to remove (email, username, or account-id:xxx)"
    )
    parser.add_argument("--group", help="Group restriction to remove")
    parser.add_argument(
        "--operation",
        required=True,
        choices=VALID_OPERATIONS,
        help="Restriction type (read or update)",
    )
    parser.add_argument(
        "--all", action="store_true", help="Remove all restrictions of this type"
    )
    parser.add_argument("--profile", help="Confluence profile to use")
    args = parser.parse_args(argv)

    # Validate
    page_id = validate_page_id(args.page_id)
    operation = args.operation

    # Validate inputs - need either --user, --group, or --all
    if not args.all and not args.user and not args.group:
        raise ValidationError("Either --user, --group, or --all must be specified")

    if args.all and (args.user or args.group):
        raise ValidationError(
            "Cannot specify both a principal (--user/--group) and --all"
        )

    if args.user and args.group:
        raise ValidationError("Cannot specify both --user and --group")

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Get current restrictions
    current = client.get(
        f"/rest/api/content/{page_id}/restriction",
        params={"expand": "restrictions.user,restrictions.group"},
        operation="get current restrictions",
    )

    # Build updated restrictions
    operation_data = current.get(operation, {})
    restrictions = operation_data.get("restrictions", {})

    # Get existing lists
    users = restrictions.get("user", {}).get("results", [])
    groups = restrictions.get("group", {}).get("results", [])

    if args.all:
        # Remove all restrictions
        users = []
        groups = []
        message = f"all {operation} restrictions"
    else:
        # Remove specific principal
        if args.user:
            principal_type = "user"
            identifier = args.user
            original_count = len(users)
            users = [
                u
                for u in users
                if u.get("username", u.get("accountId", "")) != identifier
            ]
            if len(users) == original_count:
                raise ValidationError(
                    f"User '{identifier}' does not have {operation} restriction on page {page_id}"
                )
        else:  # group
            principal_type = "group"
            identifier = args.group
            original_count = len(groups)
            groups = [g for g in groups if g.get("name", "") != identifier]
            if len(groups) == original_count:
                raise ValidationError(
                    f"Group '{identifier}' does not have {operation} restriction on page {page_id}"
                )

        message = f"{operation} restriction from {principal_type} '{identifier}'"

    # Build payload
    payload = [
        {"operation": operation, "restrictions": {"user": users, "group": groups}}
    ]

    # Update restrictions
    client.put(
        f"/rest/api/content/{page_id}/restriction",
        json_data=payload,
        operation="remove page restriction",
    )

    print(f"\nRemoved {message} for page {page_id}")
    print_success("Restriction removed successfully")


if __name__ == "__main__":
    main()
