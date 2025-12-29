#!/usr/bin/env python3
"""
Add a footer comment to a Confluence page.

Examples:
    python add_comment.py 12345 "This is my comment"
    python add_comment.py 12345 --file comment.txt
    python add_comment.py 12345 "Great page!" --profile production
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


def read_body_from_file(file_path: Path) -> str:
    """Read comment body from a file."""
    if not file_path.exists():
        raise ValidationError(f"File not found: {file_path}")

    return file_path.read_text(encoding='utf-8')


@handle_errors
def main():
    parser = argparse.ArgumentParser(
        description='Add a footer comment to a Confluence page',
        epilog='''
Examples:
  python add_comment.py 12345 "This is my comment"
  python add_comment.py 12345 --file comment.txt
  python add_comment.py 12345 "Great page!" --profile production
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('page_id', help='Page ID to add comment to')
    parser.add_argument('body', nargs='?', help='Comment body text')
    parser.add_argument('--file', '-f', type=Path, help='Read body from file')
    parser.add_argument('--profile', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args()

    # Validate inputs
    page_id = validate_page_id(args.page_id)

    # Get body content
    if args.file:
        body_content = read_body_from_file(args.file)
    elif args.body:
        body_content = args.body
    else:
        raise ValidationError("Either body argument or --file is required")

    # Validate body
    body_content = validate_comment_body(body_content)

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Prepare comment data
    comment_data = {
        'body': {
            'representation': 'storage',
            'value': f'<p>{body_content}</p>'  # Simple HTML wrapper
        }
    }

    # Create the comment
    result = client.post(
        f'/api/v2/pages/{page_id}/footer-comments',
        json_data=comment_data,
        operation='add comment'
    )

    # Output
    if args.output == 'json':
        print(format_json(result))
    else:
        print(format_comment(result))

    print_success(f"Added comment {result['id']} to page {page_id}")


if __name__ == '__main__':
    main()
