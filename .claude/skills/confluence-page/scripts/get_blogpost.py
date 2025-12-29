#!/usr/bin/env python3
"""
Retrieve a Confluence blog post.

Examples:
    python get_blogpost.py 67890
    python get_blogpost.py 67890 --body
    python get_blogpost.py 67890 --output json
"""

import sys
import argparse
from confluence_assistant_skills_lib import (
    get_confluence_client, handle_errors, validate_page_id, print_success,
    format_blogpost, format_json, xhtml_to_markdown,
)


@handle_errors
def main():
    parser = argparse.ArgumentParser(
        description='Get a Confluence blog post by ID',
        epilog='''
Examples:
  python get_blogpost.py 67890
  python get_blogpost.py 67890 --body
  python get_blogpost.py 67890 --output json
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('blogpost_id', help='Blog post ID')
    parser.add_argument('--body', action='store_true',
                        help='Include body content in output')
    parser.add_argument('--format', choices=['storage', 'view', 'markdown'],
                        default='storage', help='Body format (default: storage)')
    parser.add_argument('--profile', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args()

    # Validate
    blogpost_id = validate_page_id(args.blogpost_id, field_name='blogpost_id')

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Build request params
    params = {}
    if args.body:
        params['body-format'] = 'storage'

    # Get the blog post
    result = client.get(
        f'/api/v2/blogposts/{blogpost_id}',
        params=params,
        operation='get blog post'
    )

    # Convert body format if needed
    if args.body and args.format == 'markdown':
        body = result.get('body', {})
        storage = body.get('storage', {}).get('value', '')
        if storage:
            result['body']['markdown'] = xhtml_to_markdown(storage)

    # Output
    if args.output == 'json':
        print(format_json(result))
    else:
        print(format_blogpost(result, detailed=args.body))

        if args.body:
            print("\n--- Content ---")
            body = result.get('body', {})

            if args.format == 'markdown' and 'markdown' in body:
                print(body['markdown'])
            elif 'storage' in body:
                print(body['storage'].get('value', ''))

    print_success(f"Retrieved blog post {blogpost_id}")

if __name__ == '__main__':
    main()
