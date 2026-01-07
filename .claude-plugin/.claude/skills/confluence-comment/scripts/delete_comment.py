#!/usr/bin/env python3
"""
Delete a Confluence comment.

Examples:
    python delete_comment.py 999
    python delete_comment.py 999 --force
"""

import argparse
import sys

from confluence_assistant_skills_lib import (
    get_confluence_client,
    handle_errors,
    print_success,
    print_warning,
    validate_page_id,
)


@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Delete a Confluence comment",
        epilog="""
Examples:
  python delete_comment.py 999
  python delete_comment.py 999 --force
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("comment_id", help="Comment ID to delete")
    parser.add_argument(
        "--force", "-f", action="store_true", help="Skip confirmation prompt"
    )
    args = parser.parse_args(argv)

    # Validate inputs
    comment_id = validate_page_id(args.comment_id, "comment_id")

    # Get client
    client = get_confluence_client()

    # Confirmation prompt (unless --force)
    if not args.force:
        print_warning(f"You are about to delete comment {comment_id}")
        response = input("Are you sure? (yes/no): ").strip().lower()
        if response not in ["yes", "y"]:
            print("Delete cancelled.")
            sys.exit(0)

    # Delete the comment using v1 API
    client.delete(f"/rest/api/content/{comment_id}", operation="delete comment")

    print_success(f"Deleted comment {comment_id}")


if __name__ == "__main__":
    main()
