#!/usr/bin/env python3
"""
Update an existing Confluence page.

Examples:
    python update_page.py 12345 --title "New Title"
    python update_page.py 12345 --body "Updated content"
    python update_page.py 12345 --file updated-content.md
    python update_page.py 12345 --body "Fixed" --message "Fixed typos"
"""

import sys
import argparse
from pathlib import Path

# Add shared lib to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'shared' / 'scripts' / 'lib'))

from config_manager import get_confluence_client
from error_handler import handle_errors, ValidationError
from validators import validate_page_id, validate_title
from formatters import print_success, format_page, format_json
from xhtml_helper import markdown_to_xhtml


def read_body_from_file(file_path: Path) -> str:
    """Read body content from a file."""
    if not file_path.exists():
        raise ValidationError(f"File not found: {file_path}")
    return file_path.read_text(encoding='utf-8')


def is_markdown_file(file_path: Path) -> bool:
    """Check if file is a Markdown file."""
    return file_path.suffix.lower() in ('.md', '.markdown')


@handle_errors
def main():
    parser = argparse.ArgumentParser(
        description='Update a Confluence page',
        epilog='''
Examples:
  python update_page.py 12345 --title "New Title"
  python update_page.py 12345 --body "Updated content"
  python update_page.py 12345 --file content.md --message "Updated from file"
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('page_id', help='Page ID to update')
    parser.add_argument('--title', '-t', help='New page title')
    parser.add_argument('--body', '-b', help='New page body content')
    parser.add_argument('--file', '-f', type=Path, help='Read body from file')
    parser.add_argument('--message', '-m', help='Version message')
    parser.add_argument('--status', choices=['current', 'draft'],
                        help='Change page status')
    parser.add_argument('--profile', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args()

    # Validate
    page_id = validate_page_id(args.page_id)

    if args.title:
        title = validate_title(args.title)
    else:
        title = None

    # Check that at least one update is requested
    if not any([args.title, args.body, args.file, args.status]):
        raise ValidationError("At least one of --title, --body, --file, or --status is required")

    # Get body content
    body_content = None
    is_markdown = False

    if args.file:
        body_content = read_body_from_file(args.file)
        is_markdown = is_markdown_file(args.file)
    elif args.body:
        body_content = args.body

    # Get client
    client = get_confluence_client(profile=args.profile)

    # First, get the current page to get version number
    current_page = client.get(
        f'/api/v2/pages/{page_id}',
        operation='get current page'
    )

    current_version = current_page.get('version', {}).get('number', 1)

    # Build update data
    update_data = {
        'id': page_id,
        'status': args.status or current_page.get('status', 'current'),
        'title': title or current_page.get('title'),
        'version': {
            'number': current_version + 1
        }
    }

    # Add version message if provided
    if args.message:
        update_data['version']['message'] = args.message

    # Add body if updating content
    if body_content:
        if is_markdown:
            body_content = markdown_to_xhtml(body_content)

        update_data['body'] = {
            'representation': 'storage',
            'value': body_content
        }

    # Update the page
    result = client.put(
        f'/api/v2/pages/{page_id}',
        json_data=update_data,
        operation='update page'
    )

    # Output
    if args.output == 'json':
        print(format_json(result))
    else:
        print(format_page(result))

    print_success(f"Updated page {page_id} to version {current_version + 1}")


if __name__ == '__main__':
    main()
