#!/usr/bin/env python3
"""
List Confluence page templates and blueprints.

Examples:
    python list_templates.py
    python list_templates.py --space DOCS
    python list_templates.py --type page
    python list_templates.py --blueprints
    python list_templates.py --output json
"""

import sys
import argparse
from confluence_assistant_skills_lib import (
    get_confluence_client, handle_errors, validate_space_key, print_success,
    format_json,
)


@handle_errors
def main():
    parser = argparse.ArgumentParser(
        description='List Confluence templates and blueprints',
        epilog='''
Examples:
  python list_templates.py
  python list_templates.py --space DOCS
  python list_templates.py --type page
  python list_templates.py --blueprints
  python list_templates.py --output json
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--space', help='Filter by space key')
    parser.add_argument('--type', choices=['page', 'blogpost'],
                        help='Filter by template type')
    parser.add_argument('--blueprints', action='store_true',
                        help='List blueprints instead of templates')
    parser.add_argument('--profile', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    parser.add_argument('--limit', type=int, default=100,
                        help='Maximum number of results (default: 100)')
    args = parser.parse_args()

    # Validate space if provided
    space_key = None
    if args.space:
        space_key = validate_space_key(args.space)

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Build request params
    params = {'limit': args.limit}
    if space_key:
        params['spaceKey'] = space_key

    # Determine endpoint
    if args.blueprints:
        endpoint = '/rest/api/template/blueprint'
    else:
        endpoint = '/rest/api/template/page'

    # Get templates/blueprints
    results = []
    for item in client.paginate(endpoint, params=params, limit=args.limit):
        # Filter by type if specified (for templates only)
        if not args.blueprints and args.type:
            item_type = item.get('templateType', 'page')
            if item_type != args.type:
                continue

        results.append(item)

    # Output
    if args.output == 'json':
        print(format_json({'results': results, 'size': len(results)}))
    else:
        if not results:
            print("No templates found.")
        else:
            item_type = "blueprints" if args.blueprints else "templates"
            print(f"Found {len(results)} {item_type}:")
            print()

            for item in results:
                if args.blueprints:
                    # Blueprint format
                    bp_id = item.get('blueprintId', item.get('contentBlueprintId', 'N/A'))
                    name = item.get('name', 'Unnamed')
                    desc = item.get('description', '')

                    print(f"Blueprint: {name}")
                    print(f"  ID: {bp_id}")
                    if desc:
                        print(f"  Description: {desc}")
                    print()
                else:
                    # Template format
                    tmpl_id = item.get('templateId', 'N/A')
                    name = item.get('name', 'Unnamed')
                    tmpl_type = item.get('templateType', 'page')
                    desc = item.get('description', '')
                    space = item.get('space', {})
                    space_key = space.get('key', 'N/A') if space else 'N/A'

                    print(f"Template: {name}")
                    print(f"  ID: {tmpl_id}")
                    print(f"  Type: {tmpl_type}")
                    print(f"  Space: {space_key}")
                    if desc:
                        print(f"  Description: {desc}")
                    print()

    print_success(f"Listed {len(results)} {'blueprints' if args.blueprints else 'templates'}")

if __name__ == '__main__':
    main()
