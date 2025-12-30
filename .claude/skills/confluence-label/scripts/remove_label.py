#!/usr/bin/env python3
"""
Remove a label from a Confluence page or blog post.

Examples:
    python remove_label.py 12345 --label draft
    python remove_label.py 12345 -l old-version --profile production
"""

import sys
import argparse
from confluence_assistant_skills_lib import (
    get_confluence_client, handle_errors, ValidationError, NotFoundError,
    validate_page_id, validate_label, print_success, format_json,
)


@handle_errors
def main():
    parser = argparse.ArgumentParser(
        description='Remove a label from a Confluence page',
        epilog='''
Examples:
  python remove_label.py 12345 --label draft
  python remove_label.py 12345 -l old-version --profile production
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('page_id', help='Page or blog post ID')
    parser.add_argument('--label', '-l', required=True, help='Label to remove')
    parser.add_argument('--profile', '-p', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args()

    # Validate inputs
    page_id = validate_page_id(args.page_id)
    label_name = validate_label(args.label)

    # Get client
    client = get_confluence_client(profile=args.profile)

    # First, verify the label exists on the page
    labels_response = client.get(
        f'/api/v2/pages/{page_id}/labels',
        operation='get labels'
    )

    # Check if label exists
    label_names = [l.get('name') for l in labels_response.get('results', [])]
    if label_name not in label_names:
        raise NotFoundError(f"Label '{label_name}' not found on page {page_id}")

    # Remove the label using v1 API (v2 API delete doesn't work reliably)
    client.delete(
        f'/rest/api/content/{page_id}/label/{label_name}',
        operation=f'remove label {label_name}'
    )

    # Output
    if args.output == 'json':
        print(format_json({"status": "deleted", "label": label_name, "page_id": page_id}))
    else:
        print_success(f"Removed label '{label_name}' from page {page_id}")

if __name__ == '__main__':
    main()
