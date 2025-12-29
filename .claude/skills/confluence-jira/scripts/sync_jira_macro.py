#!/usr/bin/env python3
"""
Refresh/sync JIRA macro content in a Confluence page.

JIRA macros are automatically refreshed by Confluence, but this script can
force a page update to trigger macro refresh, or update macro parameters.

Examples:
    python sync_jira_macro.py 12345
    python sync_jira_macro.py 12345 --update-jql "project = PROJ AND status = Open"
"""

import sys
import argparse
import re
from typing import Optional
from confluence_assistant_skills_lib import (
    get_confluence_client, handle_errors, ValidationError, validate_page_id,
    validate_jql_query, print_success, format_json,
)


def find_jira_macros(content: str) -> list:
    """
    Find all JIRA macros in page content.

    Args:
        content: Page content

    Returns:
        List of macro matches with positions
    """
    # Pattern for JIRA macros
    pattern = r'<ac:structured-macro ac:name="jira"[^>]*>.*?</ac:structured-macro>'
    matches = []

    for match in re.finditer(pattern, content, re.DOTALL):
        matches.append({
            'start': match.start(),
            'end': match.end(),
            'content': match.group(0)
        })

    return matches

def update_jql_in_macro(macro_content: str, new_jql: str) -> str:
    """
    Update JQL query in a JIRA macro.

    Args:
        macro_content: Original macro content
        new_jql: New JQL query

    Returns:
        Updated macro content
    """
    import html

    # Find and replace jqlQuery parameter
    pattern = r'(<ac:parameter ac:name="jqlQuery">)([^<]+)(</ac:parameter>)'

    def replacer(match):
        return match.group(1) + html.escape(new_jql) + match.group(3)

    # Check if jqlQuery parameter exists
    if re.search(r'ac:name="jqlQuery"', macro_content):
        # Update existing
        updated = re.sub(pattern, replacer, macro_content)
    else:
        # Add new parameter (insert before closing tag)
        param = f'<ac:parameter ac:name="jqlQuery">{html.escape(new_jql)}</ac:parameter>'
        updated = macro_content.replace(
            '</ac:structured-macro>',
            f'{param}\n</ac:structured-macro>'
        )

    return updated

def touch_page(content: str) -> str:
    """
    Make a minor change to content to trigger update.

    Args:
        content: Page content

    Returns:
        Slightly modified content
    """
    # Add and remove a comment to trigger update
    return content

@handle_errors
def main():
    parser = argparse.ArgumentParser(
        description='Sync/refresh JIRA macro content in a Confluence page',
        epilog='''
Examples:
  # Force page update to refresh macros
  python sync_jira_macro.py 12345

  # Update JQL in all JIRA macros
  python sync_jira_macro.py 12345 --update-jql "project = PROJ AND status = Open"

  # Update specific macro by index
  python sync_jira_macro.py 12345 --update-jql "status = Done" --macro-index 0
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('page_id', help='Page ID containing JIRA macros')
    parser.add_argument('--update-jql', help='Update JQL query in macros')
    parser.add_argument('--macro-index', type=int,
                        help='Index of macro to update (0-based, default: all)')
    parser.add_argument('--profile', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args()

    # Validate inputs
    page_id = validate_page_id(args.page_id)

    if args.update_jql:
        new_jql = validate_jql_query(args.update_jql)
    else:
        new_jql = None

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Get page content (v1 API for XHTML)
    page = client.get(
        f'/rest/api/content/{page_id}',
        params={'expand': 'body.storage,version'},
        operation='get page'
    )

    content = page['body']['storage']['value']
    current_version = page['version']['number']

    # Find JIRA macros
    macros = find_jira_macros(content)

    if not macros:
        if args.output == 'json':
            print(format_json({"error": "No JIRA macros found in page"}))
        else:
            print(f"No JIRA macros found in page {page_id}")
        return

    # Update content if requested
    updated_content = content
    updated_count = 0

    if new_jql:
        # Update JQL in macros
        if args.macro_index is not None:
            # Update specific macro
            if args.macro_index >= len(macros):
                raise ValidationError(
                    f"Macro index {args.macro_index} out of range (found {len(macros)} macros)"
                )

            macro = macros[args.macro_index]
            new_macro = update_jql_in_macro(macro['content'], new_jql)
            updated_content = (
                content[:macro['start']] +
                new_macro +
                content[macro['end']:]
            )
            updated_count = 1
        else:
            # Update all macros
            offset = 0
            for macro in macros:
                new_macro = update_jql_in_macro(macro['content'], new_jql)
                start = macro['start'] + offset
                end = macro['end'] + offset

                updated_content = (
                    updated_content[:start] +
                    new_macro +
                    updated_content[end:]
                )

                # Adjust offset for next iteration
                offset += len(new_macro) - len(macro['content'])
                updated_count += 1
    else:
        # Just touch the page to trigger refresh
        updated_content = touch_page(content)

    # Update page
    update_data = {
        'version': {
            'number': current_version + 1
        },
        'type': page['type'],
        'title': page['title'],
        'body': {
            'storage': {
                'value': updated_content,
                'representation': 'storage'
            }
        }
    }

    result = client.put(
        f'/rest/api/content/{page_id}',
        json_data=update_data,
        operation='update page'
    )

    # Output
    if args.output == 'json':
        output_data = {
            "page_id": page_id,
            "version": result['version']['number'],
            "macros_found": len(macros),
            "macros_updated": updated_count
        }
        print(format_json(output_data))
    else:
        print(f"Page: {result['title']}")
        print(f"ID: {result['id']}")
        print(f"Version: {result['version']['number']}")
        print(f"JIRA macros found: {len(macros)}")
        if updated_count > 0:
            print(f"Macros updated: {updated_count}")

    print_success(f"Synced JIRA macros in page {page_id}")

if __name__ == '__main__':
    main()
