#!/usr/bin/env python3
"""
Start watching a Confluence space for notifications.

Examples:
    python watch_space.py DOCS
    python watch_space.py kb --profile production
    python watch_space.py TEST --output json
"""

import sys
import argparse
from pathlib import Path

# Add shared lib to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'shared' / 'scripts' / 'lib'))

from config_manager import get_confluence_client
from error_handler import handle_errors
from validators import validate_space_key
from formatters import print_success, format_json


@handle_errors
def main():
    parser = argparse.ArgumentParser(
        description='Start watching a Confluence space',
        epilog='''
Examples:
  python watch_space.py DOCS
  python watch_space.py kb --profile production
  python watch_space.py TEST --output json
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('space_key', help='Space key to watch')
    parser.add_argument('--profile', '-p', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args()

    # Validate
    space_key = validate_space_key(args.space_key)

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Watch the space using v1 API
    # Note: Space watching uses the space key endpoint
    result = client.post(
        f'/rest/api/user/watch/space/{space_key}',
        operation='watch space'
    )

    # Output
    if args.output == 'json':
        output = {
            'success': True,
            'space_key': space_key,
            'watching': True
        }
        print(format_json(output))
    else:
        print(f"Now watching space {space_key}")
        print("You will receive notifications for new content in this space.")

    print_success(f"Started watching space {space_key}")


if __name__ == '__main__':
    main()
