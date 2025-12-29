#!/usr/bin/env python3
"""
Create a Confluence page from a template or blueprint.

Examples:
    python create_from_template.py --template tmpl-123 --space DOCS --title "New Page"
    python create_from_template.py --template tmpl-123 --space DOCS --title "Page" --parent-id 12345
    python create_from_template.py --blueprint bp-456 --space DOCS --title "Project Plan"
    python create_from_template.py --template tmpl-123 --space DOCS --title "Page" --labels "tag1,tag2"
"""

import sys
import argparse
from pathlib import Path

# Add shared lib to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'shared' / 'scripts' / 'lib'))

from config_manager import get_confluence_client
from error_handler import handle_errors, ValidationError
from validators import validate_space_key, validate_title, validate_page_id
from formatters import print_success, format_json
from xhtml_helper import markdown_to_xhtml


@handle_errors
def main():
    parser = argparse.ArgumentParser(
        description='Create a page from a Confluence template or blueprint',
        epilog='''
Examples:
  python create_from_template.py --template tmpl-123 --space DOCS --title "New Page"
  python create_from_template.py --template tmpl-123 --space DOCS --title "Page" --parent-id 12345
  python create_from_template.py --blueprint bp-456 --space DOCS --title "Project"
  python create_from_template.py --template tmpl-123 --space DOCS --title "Page" --labels "tag1,tag2"
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--template', help='Template ID to use')
    parser.add_argument('--blueprint', help='Blueprint ID to use (alternative to --template)')
    parser.add_argument('--space', required=True, help='Space key for the new page')
    parser.add_argument('--title', required=True, help='Title for the new page')
    parser.add_argument('--parent-id', help='Parent page ID')
    parser.add_argument('--labels', help='Comma-separated labels to add')
    parser.add_argument('--content', help='Custom content (overrides template)')
    parser.add_argument('--file', help='File with custom content (Markdown or HTML)')
    parser.add_argument('--profile', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args()

    # Validate that either template or blueprint is provided
    if not args.template and not args.blueprint:
        raise ValidationError("Either --template or --blueprint is required")

    if args.template and args.blueprint:
        raise ValidationError("Cannot specify both --template and --blueprint")

    # Validate inputs
    space_key = validate_space_key(args.space)
    title = validate_title(args.title)

    parent_id = None
    if args.parent_id:
        parent_id = validate_page_id(args.parent_id)

    # Parse labels
    labels = []
    if args.labels:
        labels = [l.strip() for l in args.labels.split(',') if l.strip()]

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Get template/blueprint to use as base
    if args.template:
        template = client.get(f'/rest/api/template/{args.template}',
                            operation='get template')
        template_id = template.get('templateId')
    else:
        template = client.get(f'/rest/api/template/blueprint/{args.blueprint}',
                            operation='get blueprint')
        template_id = None

    # Prepare body content
    body_value = None
    if args.content:
        # Use custom content
        body_value = args.content
    elif args.file:
        # Read from file
        file_path = Path(args.file)
        if not file_path.exists():
            raise ValidationError(f"File not found: {args.file}")

        content = file_path.read_text(encoding='utf-8')

        # Convert Markdown to XHTML if needed
        if file_path.suffix.lower() in ['.md', '.markdown']:
            body_value = markdown_to_xhtml(content)
        else:
            body_value = content
    elif args.template:
        # Use template body
        body = template.get('body', {})
        storage = body.get('storage', {})
        body_value = storage.get('value', '')

    # Build page data
    page_data = {
        'type': 'page',
        'title': title,
        'space': {'key': space_key}
    }

    # Add body
    if body_value:
        page_data['body'] = {
            'storage': {
                'value': body_value,
                'representation': 'storage'
            }
        }

    # Add template ID
    if template_id:
        page_data['metadata'] = {
            'properties': {
                'editor': {'value': 'v2'},
                'content-appearance-draft': {'value': 'full-width'},
                'content-appearance-published': {'value': 'full-width'}
            }
        }

    # Add parent (ancestors)
    if parent_id:
        page_data['ancestors'] = [{'id': parent_id}]

    # Create the page
    result = client.post(
        '/rest/api/content',
        json_data=page_data,
        operation='create page from template'
    )

    # Add labels if specified
    if labels:
        page_id = result['id']
        label_data = [{'name': label} for label in labels]
        client.post(
            f'/rest/api/content/{page_id}/label',
            json_data=label_data,
            operation='add labels'
        )
        result['labels'] = label_data

    # Output
    if args.output == 'json':
        print(format_json(result))
    else:
        print(f"Created page: {result.get('title')}")
        print(f"ID: {result.get('id')}")
        print(f"Space: {result.get('space', {}).get('key', 'N/A')}")

        # Web link
        links = result.get('_links', {})
        if 'webui' in links:
            base_url = client.base_url.rstrip('/')
            print(f"URL: {base_url}{links['webui']}")

    print_success(f"Created page from {'template' if args.template else 'blueprint'}")


if __name__ == '__main__':
    main()
