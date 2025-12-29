#!/usr/bin/env python3
"""
Retrieve content properties from a Confluence page or blog post.

Content properties allow storing custom metadata as key-value pairs on any content.
This script retrieves either all properties or a specific property by key.

Examples:
    # Get all properties on a page
    python get_properties.py 12345

    # Get a specific property by key
    python get_properties.py 12345 --key my-property

    # Get properties with expanded version info
    python get_properties.py 12345 --expand version

    # Output as JSON
    python get_properties.py 12345 --output json
"""

import sys
import argparse
from confluence_assistant_skills_lib import (
    get_confluence_client, handle_errors, ValidationError, validate_page_id,
    print_success, format_json,
)


@handle_errors
def main():
    parser = argparse.ArgumentParser(
        description='Get content properties from a Confluence page or blog post',
        epilog='''
Examples:
  # Get all properties
  python get_properties.py 12345

  # Get specific property
  python get_properties.py 12345 --key my-property

  # Get with version info
  python get_properties.py 12345 --expand version

  # JSON output
  python get_properties.py 12345 --output json
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('content_id', help='Content ID (page or blog post)')
    parser.add_argument('--key', '-k', help='Specific property key to retrieve')
    parser.add_argument('--expand', help='Comma-separated list of fields to expand (e.g., version)')
    parser.add_argument('--profile', '-p', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args()

    # Validate
    content_id = validate_page_id(args.content_id)

    if args.key and not args.key.strip():
        raise ValidationError("Property key cannot be empty")

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Build request params
    params = {}
    if args.expand:
        params['expand'] = args.expand

    # Get properties
    if args.key:
        # Get specific property
        endpoint = f'/rest/api/content/{content_id}/property/{args.key}'
        result = client.get(endpoint, params=params, operation='get property')

        if args.output == 'json':
            print(format_json(result))
        else:
            print(f"Property: {result.get('key', 'N/A')}")
            print(f"Value: {format_json(result.get('value', {}))}")
            if 'version' in result:
                version = result['version']
                print(f"Version: {version.get('number', 'N/A')}")
                if 'when' in version:
                    print(f"Modified: {version['when']}")
                if 'by' in version:
                    print(f"By: {version['by']}")

        print_success(f"Retrieved property '{args.key}' from content {content_id}")
    else:
        # Get all properties
        endpoint = f'/rest/api/content/{content_id}/property'
        result = client.get(endpoint, params=params, operation='get properties')

        properties = result.get('results', [])

        if args.output == 'json':
            print(format_json(result))
        else:
            if not properties:
                print("No properties found")
            else:
                print(f"Found {len(properties)} properties:\n")
                for prop in properties:
                    print(f"  Key: {prop.get('key', 'N/A')}")
                    value = prop.get('value', {})
                    if isinstance(value, dict):
                        # Pretty print dict values
                        print(f"  Value: {format_json(value)}")
                    else:
                        print(f"  Value: {value}")
                    if 'version' in prop:
                        print(f"  Version: {prop['version'].get('number', 'N/A')}")
                    print()

        print_success(f"Retrieved {len(properties)} properties from content {content_id}")

if __name__ == '__main__':
    main()
