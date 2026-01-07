#!/usr/bin/env python3
"""
Add permission to a Confluence space.

Grants a permission to a user or group for a space.

Examples:
    python add_space_permission.py DOCS --user john.doe@example.com --operation read
    python add_space_permission.py DOCS --group confluence-users --operation write
    python add_space_permission.py TEST --user account-id:123456 --operation administer
"""

import argparse

from confluence_assistant_skills_lib import (
    ValidationError,
    get_confluence_client,
    handle_errors,
    print_success,
    print_warning,
    validate_space_key,
)

VALID_OPERATIONS = [
    "read",
    "write",
    "create",
    "delete",
    "export",
    "administer",
    "setpermissions",
    "createattachment",
]


@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Add permission to a Confluence space",
        epilog="""
Examples:
  python add_space_permission.py DOCS --user john.doe@example.com --operation read
  python add_space_permission.py DOCS --group confluence-users --operation write
  python add_space_permission.py TEST --user account-id:123456 --operation administer

Valid Operations:
  read, write, create, delete, export, administer, setpermissions, createattachment

Note: This uses the v1 API. Space permission management is not available in v2.
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("space_key", help="Space key")
    parser.add_argument(
        "--user", help="User to grant permission (email, username, or account-id:xxx)"
    )
    parser.add_argument("--group", help="Group to grant permission")
    parser.add_argument(
        "--operation",
        required=True,
        choices=VALID_OPERATIONS,
        help="Permission operation to grant",
    )
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
    space_key = validate_space_key(args.space_key)

    # Determine principal type and identifier
    if args.user:
        principal_type = "user"
        identifier = args.user
    else:
        principal_type = "group"
        identifier = args.group

    operation = args.operation

    # Get client
    client = get_confluence_client()

    # Build permission payload for v1 API
    payload = {
        "subject": {
            principal_type: {
                "results": [
                    {"username": identifier}
                    if principal_type == "user"
                    else {"name": identifier}
                ],
                "size": 1,
            }
        },
        "operation": {"key": operation, "target": "space"},
    }

    print_warning("Note: Adding space permissions via API may have limitations.")
    print_warning(
        "Some Confluence instances restrict this operation to administrators."
    )

    # Add permission (v1 API)
    client.post(
        f"/rest/api/space/{space_key}/permission",
        json_data=payload,
        operation="add space permission",
    )

    print(
        f"\nAdded {operation} permission to {principal_type} '{identifier}' for space {space_key}"
    )
    print_success("Permission added successfully")


if __name__ == "__main__":
    main()
