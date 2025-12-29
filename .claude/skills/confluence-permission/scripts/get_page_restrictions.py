#!/usr/bin/env python3
"""
Get restrictions for a Confluence page.

Retrieves the list of users and groups that can read and update a page.

Examples:
    python get_page_restrictions.py 123456
    python get_page_restrictions.py 123456 --output json
    python get_page_restrictions.py 123456 --profile production
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


def format_restrictions_text(restrictions):
    """Format restrictions for text output."""
    lines = []

    for operation, data in restrictions.items():
        if operation.startswith('_'):
            continue

        operation_name = data.get('operation', operation)
        lines.append(f"\n{operation_name.upper()} Restrictions:")

        rest_data = data.get('restrictions', {})

        # Users
        users = rest_data.get('user', {}).get('results', [])
        if users:
            lines.append(f"  Users ({len(users)}):")
            for user in users:
                username = user.get('username', user.get('accountId', 'unknown'))
                display = user.get('displayName', username)
                lines.append(f"    - {display} ({username})")
        else:
            lines.append("  Users: (none)")

        # Groups
        groups = rest_data.get('group', {}).get('results', [])
        if groups:
            lines.append(f"  Groups ({len(groups)}):")
            for group in groups:
                name = group.get('name', group.get('id', 'unknown'))
                lines.append(f"    - {name}")
        else:
            lines.append("  Groups: (none)")

    return '\n'.join(lines)


@handle_errors
def main():
    parser = argparse.ArgumentParser(
        description='Get restrictions for a Confluence page',
        epilog='''
Examples:
  python get_page_restrictions.py 123456
  python get_page_restrictions.py 123456 --output json
  python get_page_restrictions.py 123456 --profile production

Note: This uses the v1 API as v2 does not yet support page restrictions.
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('page_id', help='Page ID')
    parser.add_argument('--profile', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args()

    # Validate
    page_id = validate_page_id(args.page_id)

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Get page restrictions (v1 API - v2 doesn't support this yet)
    result = client.get(
        f'/rest/api/content/{page_id}/restriction',
        params={'expand': 'restrictions.user,restrictions.group'},
        operation='get page restrictions'
    )

    # Output
    if args.output == 'json':
        print(format_json(result))
    else:
        print(f"Page Restrictions (ID: {page_id})")

        # Check if page has any restrictions
        has_restrictions = False
        for operation, data in result.items():
            if operation.startswith('_'):
                continue
            rest_data = data.get('restrictions', {})
            user_count = rest_data.get('user', {}).get('size', 0)
            group_count = rest_data.get('group', {}).get('size', 0)
            if user_count > 0 or group_count > 0:
                has_restrictions = True
                break

        if not has_restrictions:
            print("\nNo restrictions on this page.")
            print("(The page is accessible to all space members)")
        else:
            print(format_restrictions_text(result))

    print_success(f"Retrieved restrictions for page {page_id}")


if __name__ == '__main__':
    main()
