#!/usr/bin/env python3
"""
Resolve or unresolve a Confluence comment.

Resolution marks a comment as addressed or reopens it for discussion.

Examples:
    python resolve_comment.py 999 --resolve
    python resolve_comment.py 999 --unresolve
    python resolve_comment.py 999 --resolve --profile production
"""

import sys
import argparse
from confluence_assistant_skills_lib import (
    get_confluence_client, handle_errors, ValidationError, validate_page_id,
    print_success, format_comment, format_json,
)


@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description='Resolve or unresolve a Confluence comment',
        epilog='''
Examples:
  python resolve_comment.py 999 --resolve
  python resolve_comment.py 999 --unresolve
  python resolve_comment.py 999 --resolve --profile production

Note: Exactly one of --resolve or --unresolve must be specified.
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('comment_id', help='Comment ID to resolve/unresolve')

    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument('--resolve', '-r', action='store_true',
                              help='Mark comment as resolved')
    action_group.add_argument('--unresolve', '-u', action='store_true',
                              help='Mark comment as unresolved/open')

    parser.add_argument('--profile', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args(argv)

    # Validate inputs
    comment_id = validate_page_id(args.comment_id, "comment_id")

    # Determine resolution status
    if args.resolve:
        resolution_status = 'resolved'
        action = 'resolved'
    else:  # args.unresolve
        resolution_status = 'open'
        action = 'unresolved'

    # Get client
    client = get_confluence_client(profile=args.profile)

    # First, get the current comment to get the version
    current_comment = client.get(
        f'/api/v2/footer-comments/{comment_id}',
        operation='get current comment'
    )

    # Prepare update with resolution status
    comment_data = {
        'version': {
            'number': current_comment['version']['number'] + 1
        },
        'body': current_comment.get('body', {
            'representation': 'storage',
            'value': ''
        }),
        'resolutionStatus': resolution_status
    }

    # Update the comment with resolution status
    result = client.put(
        f'/api/v2/footer-comments/{comment_id}',
        json_data=comment_data,
        operation=f'{action} comment'
    )

    # Output
    if args.output == 'json':
        print(format_json(result))
    else:
        print(format_comment(result))

    print_success(f"Comment {comment_id} marked as {action}")

if __name__ == '__main__':
    main()
