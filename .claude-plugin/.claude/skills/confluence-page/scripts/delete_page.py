#!/usr/bin/env python3
"""
Delete a Confluence page.

By default, moves the page to trash. Use --permanent for permanent deletion.

Examples:
    python delete_page.py 12345
    python delete_page.py 12345 --permanent
    python delete_page.py 12345 --force
"""

import argparse

from confluence_assistant_skills_lib import (
    get_confluence_client,
    handle_errors,
    print_success,
    print_warning,
    validate_page_id,
)


def confirm_delete(page_title: str, permanent: bool) -> bool:
    """Ask for confirmation before deleting."""
    action = "permanently delete" if permanent else "move to trash"
    print(f"\nYou are about to {action} the page: {page_title}")

    if permanent:
        print_warning("This action cannot be undone!")

    response = input("\nAre you sure? [y/N]: ").strip().lower()
    return response in ("y", "yes")


@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Delete a Confluence page",
        epilog="""
Examples:
  python delete_page.py 12345
  python delete_page.py 12345 --permanent
  python delete_page.py 12345 --force
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("page_id", help="Page ID to delete")
    parser.add_argument(
        "--permanent",
        action="store_true",
        help="Permanently delete (cannot be recovered)",
    )
    parser.add_argument(
        "--force", "-f", action="store_true", help="Skip confirmation prompt"
    )
    parser.add_argument("--profile", help="Confluence profile to use")
    args = parser.parse_args(argv)

    # Validate
    page_id = validate_page_id(args.page_id)

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Get page info for confirmation
    page = client.get(f"/api/v2/pages/{page_id}", operation="get page")
    page_title = page.get("title", "Unknown")

    # Confirm if not forced
    if not args.force and not confirm_delete(page_title, args.permanent):
        print("Delete cancelled.")
        return

    # Delete the page
    params = {}
    if args.permanent:
        params["purge"] = "true"

    client.delete(f"/api/v2/pages/{page_id}", params=params, operation="delete page")

    if args.permanent:
        print_success(f"Permanently deleted page '{page_title}' (ID: {page_id})")
    else:
        print_success(f"Moved page '{page_title}' to trash (ID: {page_id})")


if __name__ == "__main__":
    main()
