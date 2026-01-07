#!/usr/bin/env python3
"""
Delete a Confluence space.

Examples:
    python delete_space.py TEST
    python delete_space.py TEST --force
"""

import argparse

from confluence_assistant_skills_lib import (
    NotFoundError,
    get_confluence_client,
    handle_errors,
    print_success,
    print_warning,
    validate_space_key,
)


def confirm_delete(space_name: str, space_key: str) -> bool:
    """Ask for confirmation before deleting."""
    print(f"\nYou are about to delete the space: {space_name} ({space_key})")
    print_warning("This will delete all pages, blog posts, and content in this space!")
    print_warning("This action cannot be undone!")

    response = input("\nAre you sure? Type the space key to confirm: ").strip().upper()
    return response == space_key.upper()


@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Delete a Confluence space",
        epilog="""
Examples:
  python delete_space.py TEST
  python delete_space.py TEST --force
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("space_key", help="Space key to delete")
    parser.add_argument(
        "--force", "-f", action="store_true", help="Skip confirmation prompt"
    )
    args = parser.parse_args(argv)

    # Validate
    space_key = validate_space_key(args.space_key)

    # Get client
    client = get_confluence_client()

    # Get space info for confirmation
    spaces = list(
        client.paginate(
            "/api/v2/spaces", params={"keys": space_key}, operation="get space"
        )
    )

    if not spaces:
        raise NotFoundError(f"Space not found: {space_key}")

    space = spaces[0]
    space_name = space.get("name", "Unknown")
    space_id = space["id"]

    # Confirm if not forced
    if not args.force and not confirm_delete(space_name, space_key):
        print("Delete cancelled.")
        return

    # Delete the space
    client.delete(f"/api/v2/spaces/{space_id}", operation="delete space")

    print_success(f"Deleted space '{space_name}' ({space_key})")


if __name__ == "__main__":
    main()
