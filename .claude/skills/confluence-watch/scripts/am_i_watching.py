#!/usr/bin/env python3
"""
Check if the current user is watching a Confluence page.

Examples:
    python am_i_watching.py 123456
    python am_i_watching.py 123456 --profile production
    python am_i_watching.py 123456 --output json
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
        description='Check if current user is watching a page',
        epilog='''
Examples:
  python am_i_watching.py 123456
  python am_i_watching.py 123456 --profile production
  python am_i_watching.py 123456 --output json
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('page_id', help='Page ID to check')
    parser.add_argument('--profile', '-p', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args()

    # Validate
    page_id = validate_page_id(args.page_id)

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Get current user
    current_user = client.get(
        '/rest/api/user/current',
        operation='get current user'
    )

    current_account_id = current_user.get('accountId')

    # Get watchers for the page
    watchers_result = client.get(
        f'/rest/api/content/{page_id}/notification/created',
        operation='get watchers'
    )

    watchers = watchers_result.get('results', [])

    # Check if current user is in watchers list
    is_watching = any(
        watcher.get('accountId') == current_account_id
        for watcher in watchers
    )

    # Output
    if args.output == 'json':
        output = {
            'page_id': page_id,
            'watching': is_watching,
            'user': {
                'accountId': current_account_id,
                'displayName': current_user.get('displayName', ''),
                'email': current_user.get('email', '')
            }
        }
        print(format_json(output))
    else:
        user_name = current_user.get('displayName', current_user.get('username', 'You'))

        if is_watching:
            print(f"Yes - {user_name} is watching page {page_id}")
            print("You will receive notifications for updates to this page.")
        else:
            print(f"No - {user_name} is not watching page {page_id}")
            print("Use watch_page.py to start watching this page.")

    if is_watching:
        print_success("Watching confirmed")
    else:
        print_success("Not watching")


if __name__ == '__main__':
    main()
