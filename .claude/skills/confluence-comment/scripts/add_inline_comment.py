#!/usr/bin/env python3
"""
Add an inline comment to specific content in a Confluence page.

Note: Inline comments are attached to specific text selections in the page content.
This script uses the v2 API inline-comments endpoint.

Examples:
    python add_inline_comment.py 12345 "selected text" "This is my inline comment"
    python add_inline_comment.py 12345 "text" "Comment" --profile production
"""

import sys
import argparse
from pathlib import Path

# Add shared lib to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'shared' / 'scripts' / 'lib'))

from config_manager import get_confluence_client
from error_handler import handle_errors, ValidationError
from validators import validate_page_id
from formatters import print_success, format_comment, format_json


def validate_text_selection(selection: str, field_name: str = "selection") -> str:
    """
    Validate text selection for inline comment.

    Args:
        selection: The text selection
        field_name: Name of the field for error messages

    Returns:
        Validated selection (stripped)

    Raises:
        ValidationError: If the selection is invalid
    """
    if selection is None:
        raise ValidationError(f"{field_name} is required", field=field_name)

    selection = str(selection).strip()

    if not selection:
        raise ValidationError(
            f"{field_name} cannot be empty - inline comments require text selection",
            field=field_name,
            value=selection
        )

    return selection


def validate_comment_body(body: str, field_name: str = "body") -> str:
    """
    Validate comment body.

    Args:
        body: The comment body to validate
        field_name: Name of the field for error messages

    Returns:
        Validated body (stripped)

    Raises:
        ValidationError: If the body is invalid
    """
    if body is None:
        raise ValidationError(f"{field_name} is required", field=field_name)

    body = str(body).strip()

    if not body:
        raise ValidationError(f"{field_name} cannot be empty", field=field_name, value=body)

    return body


@handle_errors
def main():
    parser = argparse.ArgumentParser(
        description='Add an inline comment to specific content in a Confluence page',
        epilog='''
Examples:
  python add_inline_comment.py 12345 "selected text" "This is my inline comment"
  python add_inline_comment.py 12345 "text" "Comment" --profile production

Note: Inline comments are attached to specific text in the page. The text selection
      must match existing text in the page content.
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('page_id', help='Page ID to add inline comment to')
    parser.add_argument('selection', help='Text selection to attach comment to')
    parser.add_argument('body', help='Comment body text')
    parser.add_argument('--profile', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args()

    # Validate inputs
    page_id = validate_page_id(args.page_id)
    selection = validate_text_selection(args.selection)
    body_content = validate_comment_body(args.body)

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Prepare inline comment data
    comment_data = {
        'body': {
            'representation': 'storage',
            'value': f'<p>{body_content}</p>'
        },
        'inlineProperties': {
            'originalSelection': selection,
            'textSelection': selection
        }
    }

    # Create the inline comment
    result = client.post(
        f'/api/v2/pages/{page_id}/inline-comments',
        json_data=comment_data,
        operation='add inline comment'
    )

    # Output
    if args.output == 'json':
        print(format_json(result))
    else:
        print(format_comment(result))

    print_success(f"Added inline comment {result['id']} to page {page_id}")


if __name__ == '__main__':
    main()
