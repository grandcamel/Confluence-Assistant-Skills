#!/usr/bin/env python3
"""
Get Confluence space settings and theme.

Examples:
    python get_space_settings.py DOCS
    python get_space_settings.py DOCS --output json
"""

import sys
import argparse
from pathlib import Path

# Add shared lib to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'shared' / 'scripts' / 'lib'))

from config_manager import get_confluence_client
from error_handler import handle_errors, NotFoundError
from validators import validate_space_key
from formatters import print_success, format_json


@handle_errors
def main():
    parser = argparse.ArgumentParser(
        description='Get Confluence space settings and theme',
        epilog='''
Examples:
  python get_space_settings.py DOCS
  python get_space_settings.py DOCS --output json
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('space_key', help='Space key')
    parser.add_argument('--profile', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args()

    # Validate
    space_key = validate_space_key(args.space_key)

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Get space basic info using v2 API
    spaces = list(client.paginate(
        '/api/v2/spaces',
        params={'keys': space_key},
        operation='get space'
    ))

    if not spaces:
        raise NotFoundError(f"Space not found: {space_key}")

    space = spaces[0]

    # Get additional settings using v1 API
    try:
        space_settings = client.get(
            f'/rest/api/space/{space_key}',
            params={'expand': 'settings,theme,homepage,description,icon,permissions'},
            operation='get space settings'
        )
    except Exception:
        # v1 API may not have all these expansions, use what we have
        space_settings = space

    # Build result
    result = {
        'key': space.get('key'),
        'name': space.get('name'),
        'id': space.get('id'),
        'type': space.get('type'),
        'status': space.get('status'),
        'homepageId': space.get('homepageId'),
        'description': space.get('description', {}),
        'settings': space_settings.get('settings', {}),
        'theme': space_settings.get('theme', {}),
        'icon': space_settings.get('icon', {}),
        '_links': space.get('_links', {})
    }

    # Output
    if args.output == 'json':
        print(format_json(result))
    else:
        print(f"\nSpace Settings: {space.get('name')} ({space_key})")
        print("=" * 50)

        print(f"\nBasic Information:")
        print(f"  ID: {result.get('id')}")
        print(f"  Type: {result.get('type')}")
        print(f"  Status: {result.get('status')}")

        homepage_id = result.get('homepageId')
        if homepage_id:
            print(f"  Homepage ID: {homepage_id}")

        desc = result.get('description', {})
        if isinstance(desc, dict):
            desc_text = desc.get('plain', {}).get('value', '')
        else:
            desc_text = str(desc) if desc else ''
        if desc_text:
            print(f"  Description: {desc_text[:100]}")

        settings = result.get('settings', {})
        if settings:
            print(f"\nSettings:")
            for key, value in settings.items():
                print(f"  {key}: {value}")

        theme = result.get('theme', {})
        if theme:
            print(f"\nTheme:")
            theme_key = theme.get('themeKey', 'default')
            print(f"  Theme Key: {theme_key}")

        links = result.get('_links', {})
        if links.get('webui'):
            print(f"\nURL: {links['webui']}")

    print_success(f"Retrieved settings for space {space_key}")


if __name__ == '__main__':
    main()
