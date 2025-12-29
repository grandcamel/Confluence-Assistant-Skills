#!/usr/bin/env python3
"""
Get analytics and view information for a Confluence page.

This script retrieves version history, contributor information, and other
analytics data for a page using the v1 REST API.

Examples:
    python get_page_views.py 12345
    python get_page_views.py 12345 --output json
    python get_page_views.py 12345 --profile production
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
        description='Get analytics and view information for a Confluence page',
        epilog='''
Examples:
  python get_page_views.py 12345
  python get_page_views.py 12345 --output json
  python get_page_views.py 12345 --profile production
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

    # Get page with history and contributors
    # Using v1 API for history/analytics data
    result = client.get(
        f'/rest/api/content/{page_id}',
        params={
            'expand': 'version,history,history.contributors.publishers,space'
        },
        operation='get page analytics'
    )

    # Output
    if args.output == 'json':
        print(format_json(result))
    else:
        # Text output
        print(f"Page: {result['title']}")
        print(f"ID: {result['id']}")
        print(f"Type: {result['type']}")
        print(f"Space: {result['space']['key']}")

        # Version info
        version = result.get('version', {})
        print(f"\nVersion: {version.get('number', 'N/A')}")
        print(f"Last Modified: {version.get('when', 'N/A')}")
        if 'by' in version:
            print(f"Modified By: {version['by'].get('displayName', 'Unknown')}")

        # History info
        history = result.get('history', {})
        print(f"\nCreated: {history.get('createdDate', 'N/A')}")
        created_by = history.get('createdBy', {})
        print(f"Created By: {created_by.get('displayName', 'Unknown')}")

        # Contributors
        contributors = history.get('contributors', {})
        publishers = contributors.get('publishers', {})
        users = publishers.get('users', [])

        if users:
            print(f"\nContributors ({len(users)}):")
            for user in users:
                print(f"  - {user.get('displayName', 'Unknown')}")
        else:
            print("\nContributors: None listed")

        # Web link
        web_link = result.get('_links', {}).get('webui', '')
        if web_link:
            print(f"\nWeb UI: {client.base_url}/wiki{web_link}")

    print_success(f"Retrieved analytics for page {page_id}")


if __name__ == '__main__':
    main()
