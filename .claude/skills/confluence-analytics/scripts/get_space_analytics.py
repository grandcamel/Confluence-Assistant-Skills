#!/usr/bin/env python3
"""
Get analytics for an entire Confluence space.

This script retrieves aggregate statistics and information about all content
in a space, including page counts, recent activity, and contributors.

Examples:
    python get_space_analytics.py DOCS
    python get_space_analytics.py DOCS --days 30
    python get_space_analytics.py DOCS --output json
"""

import sys
import argparse
from datetime import datetime, timedelta
from collections import defaultdict
from confluence_assistant_skills_lib import (
    get_confluence_client, handle_errors, validate_space_key, print_success,
    format_json,
)


@handle_errors
def main():
    parser = argparse.ArgumentParser(
        description='Get analytics for an entire Confluence space',
        epilog='''
Examples:
  python get_space_analytics.py DOCS
  python get_space_analytics.py DOCS --days 30
  python get_space_analytics.py DOCS --output json
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('space_key', help='Space key')
    parser.add_argument('--days', type=int, help='Limit to content from last N days')
    parser.add_argument('--profile', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args()

    # Validate
    space_key = validate_space_key(args.space_key)

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Build CQL query
    cql = f'space={space_key}'
    if args.days:
        cutoff_date = (datetime.now() - timedelta(days=args.days)).strftime('%Y-%m-%d')
        cql += f' AND created >= "{cutoff_date}"'

    # Search for all content in space
    all_results = []
    for item in client.paginate(
        '/rest/api/search',
        params={'cql': cql, 'expand': 'content.version,content.history'},
        operation='search space content'
    ):
        all_results.append(item)

    # Aggregate statistics
    stats = {
        'space_key': space_key,
        'total_items': len(all_results),
        'by_type': defaultdict(int),
        'by_author': defaultdict(int),
        'recent_updates': []
    }

    for item in all_results:
        content = item.get('content', {})
        content_type = content.get('type', 'unknown')
        stats['by_type'][content_type] += 1

        # Track authors
        history = content.get('history', {})
        created_by = history.get('createdBy', {})
        author = created_by.get('displayName', 'Unknown')
        stats['by_author'][author] += 1

    # Get most recent updates
    sorted_results = sorted(
        all_results,
        key=lambda x: x.get('content', {}).get('version', {}).get('when', ''),
        reverse=True
    )
    stats['recent_updates'] = [
        {
            'title': item.get('content', {}).get('title', 'Untitled'),
            'type': item.get('content', {}).get('type', 'unknown'),
            'modified': item.get('content', {}).get('version', {}).get('when', 'N/A')
        }
        for item in sorted_results[:10]
    ]

    # Output
    if args.output == 'json':
        # Convert defaultdicts to regular dicts for JSON serialization
        output = {
            'space_key': stats['space_key'],
            'total_items': stats['total_items'],
            'by_type': dict(stats['by_type']),
            'by_author': dict(stats['by_author']),
            'recent_updates': stats['recent_updates']
        }
        print(format_json(output))
    else:
        # Text output
        print(f"Space: {space_key}")
        if args.days:
            print(f"Period: Last {args.days} days")
        print(f"\nTotal Items: {stats['total_items']}")

        # By type
        print("\nBy Type:")
        for content_type, count in sorted(stats['by_type'].items()):
            print(f"  {content_type}: {count}")

        # Top contributors
        print("\nTop Contributors:")
        top_authors = sorted(stats['by_author'].items(), key=lambda x: x[1], reverse=True)[:10]
        for author, count in top_authors:
            print(f"  {author}: {count} items")

        # Recent updates
        print("\nRecent Updates:")
        for update in stats['recent_updates']:
            print(f"  - {update['title']} ({update['type']}) - {update['modified']}")

    print_success(f"Retrieved analytics for space {space_key}")

if __name__ == '__main__':
    main()
