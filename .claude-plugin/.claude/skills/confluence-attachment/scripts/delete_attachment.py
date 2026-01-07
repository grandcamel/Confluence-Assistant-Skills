#!/usr/bin/env python3
"""
Delete an attachment from Confluence.

Examples:
    python delete_attachment.py att123456
    python delete_attachment.py att123456 --force
"""

import argparse

from confluence_assistant_skills_lib import (
    get_confluence_client,
    handle_errors,
    print_success,
    print_warning,
    validate_page_id,
)


def confirm_deletion(attachment_title: str, attachment_id: str) -> bool:
    """Prompt user to confirm deletion."""
    response = input(
        f"Delete attachment '{attachment_title}' (ID: {attachment_id})? [y/N]: "
    )
    return response.lower() in ("y", "yes")


@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Delete an attachment from Confluence",
        epilog="""
Examples:
  # Delete with confirmation prompt
  python delete_attachment.py att123456

  # Delete without confirmation
  python delete_attachment.py att123456 --force
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("attachment_id", help="Attachment ID to delete")
    parser.add_argument(
        "--force", "-f", action="store_true", help="Skip confirmation prompt"
    )
    args = parser.parse_args(argv)

    # Validate inputs
    attachment_id = validate_page_id(args.attachment_id)

    # Get client
    client = get_confluence_client()

    # Get attachment info for confirmation
    if not args.force:
        try:
            attachment = client.get(
                f"/api/v2/attachments/{attachment_id}",
                operation=f"get attachment {attachment_id}",
            )
            attachment_title = attachment.get("title", "Unknown")

            if not confirm_deletion(attachment_title, attachment_id):
                print_warning("Deletion cancelled.")
                return

        except Exception as e:
            # If we can't get attachment info, still allow deletion with force
            print_warning(f"Could not retrieve attachment info: {e}")
            if not confirm_deletion("Unknown", attachment_id):
                print_warning("Deletion cancelled.")
                return

    # Delete the attachment
    client.delete(
        f"/api/v2/attachments/{attachment_id}",
        operation=f"delete attachment {attachment_id}",
    )

    print_success(f"Deleted attachment {attachment_id}")


if __name__ == "__main__":
    main()
