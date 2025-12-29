#!/usr/bin/env python3
"""
Create a new Confluence page.

Examples:
    python create_page.py --space DOCS --title "My Page" --body "Content here"
    python create_page.py --space DOCS --title "From File" --file content.md
    python create_page.py --space DOCS --title "Child Page" --parent 12345 --body "Content"
"""

import sys
import argparse
from pathlib import Path

# Add shared lib to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'shared' / 'scripts' / 'lib'))

from config_manager import get_confluence_client
from error_handler import handle_errors, ValidationError
from validators import validate_space_key, validate_page_id, validate_title
from formatters import print_success, format_page, format_json
from adf_helper import markdown_to_adf, text_to_adf


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
        description='Create a new Confluence page',
        epilog='''
Examples:
  python create_page.py --space DOCS --title "My Page" --body "Hello World"
  python create_page.py --space DOCS --title "From File" --file content.md
  python create_page.py --space DOCS --title "Child" --parent 12345 --body "Content"
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--space', '-s', required=True, help='Space key')
    parser.add_argument('--title', '-t', required=True, help='Page title')
    parser.add_argument('--body', '-b', help='Page body content')
    parser.add_argument('--file', '-f', type=Path, help='Read body from file')
    parser.add_argument('--parent', '-p', help='Parent page ID')
    parser.add_argument('--status', choices=['current', 'draft'], default='current',
                        help='Page status (default: current)')
    parser.add_argument('--profile', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args()

    # Validate inputs
    space_key = validate_space_key(args.space)
    title = validate_title(args.title)

    if args.parent:
        parent_id = validate_page_id(args.parent)
    else:
        parent_id = None

    # Get body content
    if args.file:
        body_content = read_body_from_file(args.file)
        is_markdown = is_markdown_file(args.file)
    elif args.body:
        body_content = args.body
        is_markdown = False
    else:
        raise ValidationError("Either --body or --file is required")

    # Get client
    client = get_confluence_client(profile=args.profile)

    # First, get the space ID from the space key
    spaces = list(client.paginate(
        '/api/v2/spaces',
        params={'keys': space_key},
        operation='get space'
    ))

    if not spaces:
        raise ValidationError(f"Space not found: {space_key}")

    space_id = spaces[0]['id']

    # Prepare page data
    page_data = {
        'spaceId': space_id,
        'status': args.status,
        'title': title,
        'body': {
            'representation': 'storage',
            'value': body_content if not is_markdown else ''
        }
    }

    # Convert Markdown to storage format if needed
    if is_markdown:
        from xhtml_helper import markdown_to_xhtml
        page_data['body']['value'] = markdown_to_xhtml(body_content)

    # Add parent if specified
    if parent_id:
        page_data['parentId'] = parent_id

    # Create the page
    result = client.post(
        '/api/v2/pages',
        json_data=page_data,
        operation='create page'
    )

    # Output
    if args.output == 'json':
        print(format_json(result))
    else:
        print(format_page(result))

    print_success(f"Created page '{title}' with ID {result['id']}")


if __name__ == '__main__':
    main()
