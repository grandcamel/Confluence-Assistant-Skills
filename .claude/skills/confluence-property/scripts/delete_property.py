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

import sys
import argparse
from pathlib import Path

# Add shared lib to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'shared' / 'scripts' / 'lib'))

from config_manager import get_confluence_client
from error_handler import handle_errors, ValidationError
from validators import validate_page_id
from formatters import print_success


@handle_errors
def main():
    parser = argparse.ArgumentParser(
        description='Delete a content property from a page or blog post',
        epilog='''
Examples:
  # Delete property (with confirmation)
  python delete_property.py 12345 my-property

  # Force delete without confirmation
  python delete_property.py 12345 my-property --force
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('content_id', help='Content ID (page or blog post)')
    parser.add_argument('key', help='Property key to delete')
    parser.add_argument('--force', action='store_true',
                        help='Delete without confirmation')
    parser.add_argument('--profile', '-p', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args()

    # Validate
    content_id = validate_page_id(args.content_id)

    if not args.key or not args.key.strip():
        raise ValidationError("Property key cannot be empty")

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Confirmation (unless --force)
    if not args.force:
        try:
            # Try to get the property first to show what will be deleted
            property_data = client.get(
                f'/rest/api/content/{content_id}/property/{args.key}',
                operation='get property'
            )

            print(f"Property to delete:")
            print(f"  Content ID: {content_id}")
            print(f"  Key: {args.key}")
            print(f"  Current value: {property_data.get('value', 'N/A')}")
            print()

            response = input("Are you sure you want to delete this property? (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                print("Deletion cancelled")
                return
        except Exception as e:
            # Property might not exist, but let the delete call handle that
            print(f"Warning: Could not fetch property details: {e}")
            print()
            response = input(f"Delete property '{args.key}' anyway? (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                print("Deletion cancelled")
                return

    # Delete the property
    client.delete(
        f'/rest/api/content/{content_id}/property/{args.key}',
        operation='delete property'
    )

    print_success(f"Deleted property '{args.key}' from content {content_id}")


if __name__ == '__main__':
    main()
