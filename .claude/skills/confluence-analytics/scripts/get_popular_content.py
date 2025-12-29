#!/usr/bin/env python3
"""
Get the most popular/most viewed content in Confluence.

This script uses CQL queries with ordering to find recently created,
recently modified, or labeled content as a proxy for popularity.

Examples:
    python get_popular_content.py --space DOCS
    python get_popular_content.py --space DOCS --limit 10
    python get_popular_content.py --space DOCS --sort created
    python get_popular_content.py --label featured --limit 5
"""

import sys
import argparse
from pathlib import Path

# Add shared lib to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'shared' / 'scripts' / 'lib'))

from config_manager import get_confluence_client
from error_handler import handle_errors, ValidationError
from validators import validate_space_key
from formatters import print_success, format_json


@handle_errors
def main():
    parser = argparse.ArgumentParser(
        description='Get the most popular/most viewed content in Confluence',
        epilog='''
Examples:
  python get_popular_content.py --space DOCS
  python get_popular_content.py --space DOCS --limit 10
  python get_popular_content.py --space DOCS --sort created
  python get_popular_content.py --label featured --limit 5
  python get_popular_content.py --type blogpost --limit 5
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--space', help='Space key to search within')
    parser.add_argument('--label', help='Filter by label')
    parser.add_argument('--type', choices=['page', 'blogpost', 'all'], default='all',
                        help='Content type (default: all)')
    parser.add_argument('--sort', choices=['created', 'modified'], default='modified',
                        help='Sort by created or modified date (default: modified)')
    parser.add_argument('--limit', type=int, default=10,
                        help='Number of results to return (default: 10)')
    parser.add_argument('--profile', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args()

    # Validate
    if args.space:
        space_key = validate_space_key(args.space)
    else:
        space_key = None

    if not args.space and not args.label:
        raise ValidationError("Must specify either --space or --label")

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Build CQL query
    cql_parts = []

    if space_key:
        cql_parts.append(f'space={space_key}')

    if args.label:
        cql_parts.append(f'label={args.label}')

    if args.type == 'page':
        cql_parts.append('type=page')
    elif args.type == 'blogpost':
        cql_parts.append('type=blogpost')
    else:
        cql_parts.append('type in (page, blogpost)')

    cql = ' AND '.join(cql_parts)

    # Add ordering
    if args.sort == 'created':
        cql += ' ORDER BY created DESC'
    else:
        cql += ' ORDER BY lastModified DESC'

    # Search
    results = []
    for item in client.paginate(
        '/rest/api/search',
        params={'cql': cql, 'limit': args.limit, 'expand': 'content.version,content.space'},
        limit=args.limit,
        operation='search popular content'
    ):
        results.append(item)

    # Output
    if args.output == 'json':
        output = {
            'query': cql,
            'total': len(results),
            'results': [
                {
                    'id': item.get('content', {}).get('id'),
                    'title': item.get('content', {}).get('title'),
                    'type': item.get('content', {}).get('type'),
                    'space': item.get('content', {}).get('space', {}).get('key'),
                    'modified': item.get('content', {}).get('version', {}).get('when'),
                    'url': item.get('content', {}).get('_links', {}).get('webui')
                }
                for item in results
            ]
        }
        print(format_json(output))
    else:
        # Text output
        print(f"Popular Content (sorted by {args.sort})")
        if space_key:
            print(f"Space: {space_key}")
        if args.label:
            print(f"Label: {args.label}")
        print(f"Type: {args.type}")
        print(f"\nFound {len(results)} items:\n")

        for i, item in enumerate(results, 1):
            content = item.get('content', {})
            title = content.get('title', 'Untitled')
            content_type = content.get('type', 'unknown')
            space = content.get('space', {}).get('key', 'N/A')
            version = content.get('version', {})
            modified = version.get('when', 'N/A')

            print(f"{i}. {title}")
            print(f"   Type: {content_type} | Space: {space}")
            print(f"   Last Modified: {modified}")

            web_link = content.get('_links', {}).get('webui', '')
            if web_link:
                print(f"   URL: {client.base_url}/wiki{web_link}")
            print()

    print_success(f"Retrieved {len(results)} popular content items")


if __name__ == '__main__':
    main()
