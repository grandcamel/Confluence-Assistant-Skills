#!/usr/bin/env python3
"""
Create a new Confluence page template.

Examples:
    python create_template.py --name "Meeting Notes" --space DOCS
    python create_template.py --name "Status Report" --space DOCS --description "Weekly status"
    python create_template.py --name "Template" --space DOCS --file template.html
    python create_template.py --name "Template" --space DOCS --file template.md
    python create_template.py --name "Template" --space DOCS --labels "template,meeting"
"""

import sys
import argparse
from pathlib import Path
from confluence_assistant_skills_lib import (
    get_confluence_client, handle_errors, ValidationError, validate_space_key,
    print_success, format_json, markdown_to_xhtml,
)


def validate_template_name(name: str) -> str:
    """
    Validate a template name.

    Args:
        name: Template name to validate

    Returns:
        Validated and normalized name

    Raises:
        ValidationError: If name is invalid
    """
    if not name or not name.strip():
        raise ValidationError("Template name cannot be empty")

    name = name.strip()

    if len(name) > 255:
        raise ValidationError("Template name cannot exceed 255 characters")

    return name

@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description='Create a new Confluence page template',
        epilog='''
Examples:
  python create_template.py --name "Meeting Notes" --space DOCS
  python create_template.py --name "Status Report" --space DOCS --description "Weekly status"
  python create_template.py --name "Template" --space DOCS --file template.html
  python create_template.py --name "Template" --space DOCS --file template.md
  python create_template.py --name "Template" --space DOCS --labels "template,meeting"
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--name', required=True, help='Template name')
    parser.add_argument('--space', required=True, help='Space key for the template')
    parser.add_argument('--description', help='Template description')
    parser.add_argument('--content', help='Template body content (HTML/XHTML)')
    parser.add_argument('--file', help='File with template content (Markdown or HTML)')
    parser.add_argument('--labels', help='Comma-separated labels')
    parser.add_argument('--type', choices=['page', 'blogpost'], default='page',
                        help='Template type (default: page)')
    parser.add_argument('--blueprint-id', help='Base on existing blueprint')
    parser.add_argument('--profile', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args(argv)

    # Validate inputs
    name = validate_template_name(args.name)
    space_key = validate_space_key(args.space)

    # Parse labels
    labels = []
    if args.labels:
        labels = [l.strip() for l in args.labels.split(',') if l.strip()]

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Prepare body content
    body_value = '<p></p>'  # Default empty template

    if args.content:
        body_value = args.content
    elif args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            raise ValidationError(f"File not found: {args.file}")

        content = file_path.read_text(encoding='utf-8')

        # Convert Markdown to XHTML if needed
        if file_path.suffix.lower() in ['.md', '.markdown']:
            body_value = markdown_to_xhtml(content)
        else:
            body_value = content

    # Build template data
    template_data = {
        'name': name,
        'templateType': args.type,
        'body': {
            'storage': {
                'value': body_value,
                'representation': 'storage'
            }
        },
        'space': {
            'key': space_key
        }
    }

    if args.description:
        template_data['description'] = args.description

    if labels:
        template_data['labels'] = [{'name': label} for label in labels]

    if args.blueprint_id:
        template_data['contentBlueprintId'] = args.blueprint_id

    # Create the template
    result = client.post(
        '/rest/api/template',
        json_data=template_data,
        operation='create template'
    )

    # Output
    if args.output == 'json':
        print(format_json(result))
    else:
        print(f"Created template: {result.get('name')}")
        print(f"ID: {result.get('templateId', 'N/A')}")
        print(f"Type: {result.get('templateType', 'page')}")
        print(f"Space: {result.get('space', {}).get('key', 'N/A')}")

        if args.description:
            print(f"Description: {args.description}")

        if labels:
            print(f"Labels: {', '.join(labels)}")

    print_success(f"Created template '{name}'")

if __name__ == '__main__':
    main()
