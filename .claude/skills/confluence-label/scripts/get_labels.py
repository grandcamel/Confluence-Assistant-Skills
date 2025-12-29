#!/usr/bin/env python3
"""
Get all labels on a Confluence page or blog post.

Examples:
    python get_labels.py 12345
    python get_labels.py 12345 --output json
    python get_labels.py 12345 --profile production
"""

import sys
import argparse
from pathlib import Path

# Add shared lib to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'shared' / 'scripts' / 'lib'))

from config_manager import get_confluence_client
from error_handler import handle_errors
from validators import validate_page_id
from formatters import print_success, format_label, format_json, print_info


@handle_errors
def main():
    parser = argparse.ArgumentParser(
        description='Get all labels on a Confluence page',
        epilog='''
Examples:
  python get_labels.py 12345
  python get_labels.py 12345 --output json
  python get_labels.py 12345 --profile production
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('page_id', help='Page or blog post ID')
    parser.add_argument('--profile', '-p', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args()

    # Validate page ID
    page_id = validate_page_id(args.page_id)

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Get labels
    response = client.get(
        f'/api/v2/pages/{page_id}/labels',
        operation='get labels'
    )

    labels = response.get('results', [])

    # Output
    if args.output == 'json':
        print(format_json(labels))
    else:
        if not labels:
            print_info(f"No labels found on page {page_id}")
        else:
            print(f"Labels on page {page_id}:")
            for i, label in enumerate(labels, 1):
                print(f"{i}. {format_label(label)}")
            print_success(f"Found {len(labels)} label(s)")


if __name__ == '__main__':
    main()
