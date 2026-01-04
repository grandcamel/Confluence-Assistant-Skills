#!/usr/bin/env python3
"""
Get all footer comments on a Confluence page.

Examples:
    python get_comments.py 12345
    python get_comments.py 12345 --limit 10
    python get_comments.py 12345 --output json
"""

import sys
import argparse
from confluence_assistant_skills_lib import (
    get_confluence_client, handle_errors, validate_page_id, validate_limit,
    print_success, format_comments, format_json,
)


@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description='Get all footer comments on a Confluence page',
        epilog='''
Examples:
  python get_comments.py 12345
  python get_comments.py 12345 --limit 10
  python get_comments.py 12345 --output json
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('page_id', help='Page ID to get comments from')
    parser.add_argument('--limit', '-l', type=int, help='Maximum number of comments to retrieve')
    parser.add_argument('--sort', '-s', choices=['created', '-created'], default='-created',
                        help='Sort order (default: -created for newest first)')
    parser.add_argument('--profile', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args(argv)

    # Validate inputs
    page_id = validate_page_id(args.page_id)

    if args.limit:
        limit = validate_limit(args.limit, max_value=250)
    else:
        limit = None

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Prepare query parameters
    params = {
        'sort': args.sort
    }

    # Get comments
    comments = []
    for comment in client.paginate(
        f'/api/v2/pages/{page_id}/footer-comments',
        params=params,
        limit=limit,
        operation='get comments'
    ):
        comments.append(comment)

    # Output
    if args.output == 'json':
        print(format_json(comments))
    else:
        print(format_comments(comments))
        print_success(f"Retrieved {len(comments)} comment(s) from page {page_id}")

if __name__ == '__main__':
    main()
