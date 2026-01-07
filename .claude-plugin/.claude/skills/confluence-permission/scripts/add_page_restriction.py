#!/usr/bin/env python3
"""
Add restriction to a Confluence page.

Restricts page access to specific users or groups.

Examples:
    python add_page_restriction.py 123456 --operation read --user john.doe@example.com
    python add_page_restriction.py 123456 --operation update --group confluence-users
    python add_page_restriction.py 123456 --operation read --user account-id:123456
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
        description="Add restriction to a Confluence page",
        epilog="""
Examples:
  python add_page_restriction.py 123456 --operation read --user john.doe@example.com
  python add_page_restriction.py 123456 --operation update --group confluence-users
  python add_page_restriction.py 123456 --operation read --user account-id:123456

Valid Operations:
  read   - Who can view the page
  update - Who can edit the page

Note: This uses the v1 API as page restrictions are not available in v2.
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("page_id", help="Page ID")
    parser.add_argument(
        "--user", help="User to restrict (email, username, or account-id:xxx)"
    )
    parser.add_argument("--group", help="Group to restrict")
    parser.add_argument(
        "--operation",
        required=True,
        choices=VALID_OPERATIONS,
        help="Restriction type (read or update)",
    )
    parser.add_argument("--profile", help="Confluence profile to use")
    parser.add_argument(
        "--output",
        "-o",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    args = parser.parse_args(argv)

    # Validate inputs
    if not args.user and not args.group:
        raise ValidationError("Either --user or --group must be specified")
    if args.user and args.group:
        raise ValidationError("Cannot specify both --user and --group")

    # Validate
    page_id = validate_page_id(args.page_id)
    operation = args.operation

    # Determine principal type and identifier
    if args.user:
        principal_type = "user"
        identifier = args.user
    else:
        principal_type = "group"
        identifier = args.group

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

    # Add new principal
    if principal_type == "user":
        # Check if already exists
        existing = any(
            u.get("username", u.get("accountId", "")) == identifier for u in users
        )
        if existing:
            print(
                f"User '{identifier}' already has {operation} restriction on page {page_id}"
            )
            return

        users.append({"type": "known", "username": identifier})
    else:  # group
        # Check if already exists
        existing = any(g.get("name", "") == identifier for g in groups)
        if existing:
            print(
                f"Group '{identifier}' already has {operation} restriction on page {page_id}"
            )
            return

        groups.append({"type": "group", "name": identifier})

    # Build payload
    payload = [
        {"operation": operation, "restrictions": {"user": users, "group": groups}}
    ]

    # Update restrictions
    client.put(
        f"/rest/api/content/{page_id}/restriction",
        json_data=payload,
        operation="add page restriction",
    )

    print(
        f"\nAdded {operation} restriction to {principal_type} '{identifier}' for page {page_id}"
    )
    print_success("Restriction added successfully")


if __name__ == "__main__":
    main()
