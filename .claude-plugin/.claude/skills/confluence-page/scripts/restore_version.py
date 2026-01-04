#!/usr/bin/env python3
"""
Restore a Confluence page to a previous version.

Examples:
    python restore_version.py 12345 --version 5
    python restore_version.py 12345 --version 5 --message "Restoring to known good state"
"""

import sys
import argparse
from confluence_assistant_skills_lib import (
    get_confluence_client, handle_errors, ValidationError, validate_page_id,
    print_success, print_warning, format_page, format_json,
)


@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description='Restore a Confluence page to a previous version',
        epilog='''
Examples:
  python restore_version.py 12345 --version 5
  python restore_version.py 12345 --version 5 --message "Restoring"
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('page_id', help='Page ID')
    parser.add_argument('--version', '-v', type=int, required=True,
                        help='Version number to restore')
    parser.add_argument('--message', '-m',
                        help='Version message for the restoration')
    parser.add_argument('--profile', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args(argv)

    # Validate
    page_id = validate_page_id(args.page_id)

    if args.version < 1:
        raise ValidationError("Version number must be at least 1")

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Get current page info
    current_page = client.get(
        f'/api/v2/pages/{page_id}',
        operation='get current page'
    )

    current_version = current_page.get('version', {}).get('number', 1)

    if args.version >= current_version:
        raise ValidationError(
            f"Cannot restore to version {args.version}. "
            f"Current version is {current_version}. "
            f"Specify a version less than {current_version}."
        )

    # Get the historical version content using v1 API
    historical = client.get(
        f'/rest/api/content/{page_id}',
        params={
            'version': args.version,
            'expand': 'body.storage,version'
        },
        operation='get historical version'
    )

    historical_body = historical.get('body', {}).get('storage', {}).get('value', '')

    if not historical_body:
        raise ValidationError(f"Could not retrieve content for version {args.version}")

    # Prepare restore data
    version_message = args.message or f"Restored to version {args.version}"

    restore_data = {
        'id': page_id,
        'status': current_page.get('status', 'current'),
        'title': current_page.get('title'),
        'version': {
            'number': current_version + 1,
            'message': version_message
        },
        'body': {
            'representation': 'storage',
            'value': historical_body
        }
    }

    # Confirm
    print_warning(f"Restoring page '{current_page.get('title')}' from version {current_version} to version {args.version}")

    # Restore by creating a new version with old content
    result = client.put(
        f'/api/v2/pages/{page_id}',
        json_data=restore_data,
        operation='restore version'
    )

    # Output
    if args.output == 'json':
        print(format_json(result))
    else:
        print(format_page(result))

    print_success(
        f"Restored page to version {args.version} content. "
        f"New version number: {current_version + 1}"
    )

if __name__ == '__main__':
    main()
