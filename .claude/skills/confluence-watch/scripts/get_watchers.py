#!/usr/bin/env python3
"""
Get the list of users watching a Confluence page.

Examples:
    python get_watchers.py 123456
    python get_watchers.py 123456 --profile production
    python get_watchers.py 123456 --output json
"""

import sys
import argparse
from pathlib import Path

# Add shared lib to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'shared' / 'scripts' / 'lib'))

from config_manager import get_confluence_client
from error_handler import handle_errors
from validators import validate_page_id
from formatters import print_success, format_json


@handle_errors
def main():
    parser = argparse.ArgumentParser(
        description='Get the list of users watching a page',
        epilog='''
Examples:
  python get_watchers.py 123456
  python get_watchers.py 123456 --profile production
  python get_watchers.py 123456 --output json
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('page_id', help='Page ID')
    parser.add_argument('--profile', '-p', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args()

    # Validate
    page_id = validate_page_id(args.page_id)

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Get watchers using v1 API
    result = client.get(
        f'/rest/api/content/{page_id}/notification/created',
        operation='get watchers'
    )

    watchers = result.get('results', [])
    count = len(watchers)

    # Output
    if args.output == 'json':
        output = {
            'page_id': page_id,
            'watcher_count': count,
            'watchers': watchers
        }
        print(format_json(output))
    else:
        print(f"Watchers for page {page_id}:")
        print(f"Total: {count}")
        print()

        if count == 0:
            print("No watchers")
        else:
            for watcher in watchers:
                display_name = watcher.get('displayName', watcher.get('publicName', 'Unknown'))
                email = watcher.get('email', '')
                account_id = watcher.get('accountId', '')

                if email:
                    print(f"- {display_name} ({email})")
                else:
                    print(f"- {display_name} [ID: {account_id}]")

    print_success(f"Retrieved {count} watcher(s)")


if __name__ == '__main__':
    main()
