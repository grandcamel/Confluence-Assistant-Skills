#!/usr/bin/env python3
"""
Delete a content property from a Confluence page or blog post.

Content properties are custom metadata key-value pairs.
This script deletes a specific property by key.

Examples:
    # Delete a property
    python delete_property.py 12345 my-property

    # Delete with confirmation
    python delete_property.py 12345 my-property --confirm

    # Force delete without confirmation
    python delete_property.py 12345 my-property --force
"""

import argparse

from confluence_assistant_skills_lib import (
    ValidationError,
    get_confluence_client,
    handle_errors,
    print_success,
    validate_page_id,
)


@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Delete a content property from a page or blog post",
        epilog="""
Examples:
  # Delete property (with confirmation)
  python delete_property.py 12345 my-property

  # Force delete without confirmation
  python delete_property.py 12345 my-property --force
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("content_id", help="Content ID (page or blog post)")
    parser.add_argument("key", help="Property key to delete")
    parser.add_argument(
        "--force", action="store_true", help="Delete without confirmation"
    )
    parser.add_argument(
        "--output",
        "-o",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    args = parser.parse_args(argv)

    # Validate
    content_id = validate_page_id(args.content_id)

    if not args.key or not args.key.strip():
        raise ValidationError("Property key cannot be empty")

    # Get client
    client = get_confluence_client()

    # Confirmation (unless --force)
    if not args.force:
        try:
            # Try to get the property first to show what will be deleted
            property_data = client.get(
                f"/rest/api/content/{content_id}/property/{args.key}",
                operation="get property",
            )

            print("Property to delete:")
            print(f"  Content ID: {content_id}")
            print(f"  Key: {args.key}")
            print(f"  Current value: {property_data.get('value', 'N/A')}")
            print()

            response = input(
                "Are you sure you want to delete this property? (yes/no): "
            )
            if response.lower() not in ["yes", "y"]:
                print("Deletion cancelled")
                return
        except Exception as e:
            # Property might not exist, but let the delete call handle that
            print(f"Warning: Could not fetch property details: {e}")
            print()
            response = input(f"Delete property '{args.key}' anyway? (yes/no): ")
            if response.lower() not in ["yes", "y"]:
                print("Deletion cancelled")
                return

    # Delete the property
    client.delete(
        f"/rest/api/content/{content_id}/property/{args.key}",
        operation="delete property",
    )

    print_success(f"Deleted property '{args.key}' from content {content_id}")


if __name__ == "__main__":
    main()
