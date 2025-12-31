#!/usr/bin/env python3
"""
Simple text search (no CQL knowledge required).

Examples:
    python search_content.py "meeting notes"
    python search_content.py "meeting notes" --space DOCS
    python search_content.py "API documentation" --type page
"""

import sys
import argparse
from confluence_assistant_skills_lib import (
    get_confluence_client, handle_errors, ValidationError, validate_space_key,
    validate_limit, print_success, format_search_results, format_json,
)


@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description='Simple text search for Confluence content',
        epilog='''
Examples:
  python search_content.py "meeting notes"
  python search_content.py "API documentation" --space DOCS
  python search_content.py "config" --type page --limit 50
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('query', help='Search text')
    parser.add_argument('--space', '-s', help='Limit to space')
    parser.add_argument('--type', '-t', choices=['page', 'blogpost', 'all'],
                        default='all', help='Content type (default: all)')
    parser.add_argument('--limit', '-l', type=int, default=25,
                        help='Maximum results (default: 25)')
    parser.add_argument('--profile', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args(argv)

    # Validate
    if not args.query.strip():
        raise ValidationError("Search query cannot be empty")

    limit = validate_limit(args.limit, max_value=200)

    # Build CQL
    cql_parts = [f'text ~ "{args.query}"']

    if args.space:
        space_key = validate_space_key(args.space)
        cql_parts.append(f'space = "{space_key}"')

    if args.type != 'all':
        cql_parts.append(f'type = {args.type}')

    cql = ' AND '.join(cql_parts)

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Execute search
    params = {
        'cql': cql,
        'limit': min(limit, 50)
    }

    results = []
    start = 0

    while len(results) < limit:
        params['start'] = start
        response = client.get(
            '/rest/api/search',
            params=params,
            operation='text search'
        )

        batch = response.get('results', [])
        if not batch:
            break

        results.extend(batch)
        start += len(batch)

        if len(batch) < params['limit']:
            break

    results = results[:limit]

    # Output
    if args.output == 'json':
        print(format_json({
            'query': args.query,
            'cql': cql,
            'results': results,
            'count': len(results)
        }))
    else:
        print(f"\nSearch: \"{args.query}\"\n")
        print(format_search_results(results, show_excerpt=True))

    print_success(f"Found {len(results)} result(s)")

if __name__ == '__main__':
    main()
