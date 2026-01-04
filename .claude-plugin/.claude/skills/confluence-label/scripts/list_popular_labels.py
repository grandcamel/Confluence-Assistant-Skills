#!/usr/bin/env python3
"""
List most popular labels in a space or across all spaces.

Examples:
    python list_popular_labels.py
    python list_popular_labels.py --space DOCS
    python list_popular_labels.py --limit 20
    python list_popular_labels.py --space KB --limit 10 --output json
"""

import sys
import argparse
from collections import Counter
from confluence_assistant_skills_lib import (
    get_confluence_client, handle_errors, validate_space_key, validate_limit,
    print_success, format_table, format_json,
)


def build_cql_query(space: str = None) -> str:
    """Build CQL query for getting content."""
    if space:
        return f'space = "{space}" AND type in (page, blogpost)'
    return 'type in (page, blogpost)'

@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description='List most popular labels in a space or across all spaces',
        epilog='''
Examples:
  python list_popular_labels.py
  python list_popular_labels.py --space DOCS
  python list_popular_labels.py --limit 20
  python list_popular_labels.py --space KB --limit 10 --output json
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--space', '-s', help='Filter by space key')
    parser.add_argument('--limit', '-l', type=int, default=25,
                        help='Number of labels to show (default: 25)')
    parser.add_argument('--max-pages', type=int, default=100,
                        help='Maximum pages to scan (default: 100)')
    parser.add_argument('--profile', '-p', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args(argv)

    # Validate inputs
    limit = validate_limit(args.limit, max_value=250)
    max_pages = validate_limit(args.max_pages, max_value=500)

    space_key = None
    if args.space:
        space_key = validate_space_key(args.space)

    # Build CQL query
    cql = build_cql_query(space=space_key)

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Search for content and collect labels
    label_counter = Counter()
    page_count = 0

    for result in client.paginate(
        '/api/v2/search',
        params={'cql': cql, 'expand': 'metadata.labels'},
        limit=max_pages,
        operation='get content for label analysis'
    ):
        page_count += 1

        # Extract labels from metadata
        metadata = result.get('metadata', {})
        labels_data = metadata.get('labels', {})
        labels = labels_data.get('results', [])

        for label in labels:
            label_name = label.get('name')
            if label_name:
                label_counter[label_name] += 1

    # Get top labels
    top_labels = label_counter.most_common(limit)

    # Output
    if args.output == 'json':
        result = [
            {"label": label, "count": count}
            for label, count in top_labels
        ]
        print(format_json(result))
    else:
        if not top_labels:
            print(f"No labels found")
            if space_key:
                print(f"(searched {page_count} pages in space {space_key})")
            else:
                print(f"(searched {page_count} pages)")
        else:
            scope = f"in space {space_key}" if space_key else "across all spaces"
            print(f"Most popular labels {scope}:")
            print()

            # Format as table
            table_data = [
                {"rank": i+1, "label": label, "count": count}
                for i, (label, count) in enumerate(top_labels)
            ]

            print(format_table(
                table_data,
                columns=['rank', 'label', 'count'],
                headers=['Rank', 'Label', 'Count']
            ))

            print()
            print_success(f"Analyzed {page_count} pages, found {len(label_counter)} unique labels")

if __name__ == '__main__':
    main()
