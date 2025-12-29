#!/usr/bin/env python3
"""
Retrieve Confluence space details.

Examples:
    python get_space.py DOCS
    python get_space.py DOCS --output json
"""

import sys
import argparse
from pathlib import Path

# Add shared lib to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'shared' / 'scripts' / 'lib'))

from config_manager import get_confluence_client
from error_handler import handle_errors, NotFoundError
from validators import validate_space_key
from formatters import print_success, format_space, format_json


@handle_errors
def main():
    parser = argparse.ArgumentParser(
        description='Get Confluence space details',
        epilog='''
Examples:
  python get_space.py DOCS
  python get_space.py DOCS --output json
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

    # Get spaces by key
    spaces = list(client.paginate(
        '/api/v2/spaces',
        params={'keys': space_key},
        operation='get space'
    ))

    if not spaces:
        raise NotFoundError(f"Space not found: {space_key}")

    result = spaces[0]

    # Output
    if args.output == 'json':
        print(format_json(result))
    else:
        print(format_space(result, detailed=True))

    print_success(f"Retrieved space {space_key}")


if __name__ == '__main__':
    main()
