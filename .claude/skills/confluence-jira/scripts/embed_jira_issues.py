#!/usr/bin/env python3
"""
Embed JIRA issues in a Confluence page using JIRA macros.

Supports two modes:
1. JQL query - Embed multiple issues matching a JQL query
2. Issue keys - Embed specific issues by their keys

Examples:
    python embed_jira_issues.py 12345 --jql "project = PROJ AND status = Open"
    python embed_jira_issues.py 12345 --issues PROJ-123,PROJ-456,PROJ-789
    python embed_jira_issues.py 12345 --issues PROJ-123 --mode replace
"""

import sys
import argparse
import html
from typing import List, Optional
from confluence_assistant_skills_lib import (
    get_confluence_client, handle_errors, ValidationError, validate_page_id,
    validate_issue_key, validate_jql_query, print_success, format_json,
)


def create_jira_macro(issue_key: str, server_id: Optional[str] = None) -> str:
    """
    Create JIRA single issue macro in XHTML storage format.

    Args:
        issue_key: JIRA issue key (e.g., PROJ-123)
        server_id: Optional JIRA server ID

    Returns:
        XHTML macro string
    """
    server_param = ""
    if server_id:
        server_param = f'<ac:parameter ac:name="serverId">{html.escape(server_id)}</ac:parameter>'

    return f'''<ac:structured-macro ac:name="jira" ac:schema-version="1">
    {server_param}
    <ac:parameter ac:name="key">{html.escape(issue_key)}</ac:parameter>
</ac:structured-macro>'''

def create_jira_issues_macro(
    jql: Optional[str] = None,
    issue_keys: Optional[List[str]] = None,
    server_id: Optional[str] = None,
    columns: Optional[List[str]] = None,
    max_results: int = 20,
) -> str:
    """
    Create JIRA issues table macro in XHTML storage format.

    Args:
        jql: JQL query string
        issue_keys: List of issue keys (converted to JQL)
        server_id: Optional JIRA server ID
        columns: Columns to display
        max_results: Maximum number of results

    Returns:
        XHTML macro string
    """
    # Build JQL from issue keys if provided
    if issue_keys and not jql:
        jql = build_jql_from_keys(issue_keys)

    if not jql:
        raise ValidationError("Either jql or issue_keys must be provided")

    server_param = ""
    if server_id:
        server_param = f'<ac:parameter ac:name="serverId">{html.escape(server_id)}</ac:parameter>'

    columns_param = ""
    if columns:
        columns_str = ";".join(columns)
        columns_param = f'<ac:parameter ac:name="columns">{html.escape(columns_str)}</ac:parameter>'

    count_param = f'<ac:parameter ac:name="maximumIssues">{max_results}</ac:parameter>'

    # Escape JQL for URL parameter
    jql_escaped = html.escape(jql)

    return f'''<ac:structured-macro ac:name="jira" ac:schema-version="1">
    {server_param}
    <ac:parameter ac:name="jqlQuery">{jql_escaped}</ac:parameter>
    {columns_param}
    {count_param}
</ac:structured-macro>'''

def build_jql_from_keys(keys: List[str]) -> str:
    """
    Build a JQL query from a list of issue keys.

    Args:
        keys: List of issue keys

    Returns:
        JQL query string
    """
    if len(keys) == 1:
        return f"key = {keys[0]}"
    else:
        # Create OR query: key in (PROJ-123, PROJ-456, ...)
        keys_str = ", ".join(keys)
        return f"key in ({keys_str})"

def append_jira_macro(content: str, macro: str) -> str:
    """
    Append JIRA macro to existing page content.

    Args:
        content: Existing page content
        macro: JIRA macro to append

    Returns:
        Updated content
    """
    return content + "\n" + macro

def replace_with_jira_macro(content: str, macro: str) -> str:
    """
    Replace page content with JIRA macro.

    Args:
        content: Existing page content (ignored)
        macro: JIRA macro to use

    Returns:
        New content (just the macro)
    """
    return macro

@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description='Embed JIRA issues in a Confluence page',
        epilog='''
Examples:
  # Embed issues matching a JQL query
  python embed_jira_issues.py 12345 --jql "project = PROJ AND status = Open"

  # Embed specific issues by key
  python embed_jira_issues.py 12345 --issues PROJ-123,PROJ-456

  # Replace page content with JIRA macro
  python embed_jira_issues.py 12345 --jql "project = PROJ" --mode replace
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('page_id', help='Page ID to update')
    parser.add_argument('--jql', help='JQL query to filter issues')
    parser.add_argument('--issues', help='Comma-separated list of issue keys (e.g., PROJ-123,PROJ-456)')
    parser.add_argument('--mode', choices=['append', 'replace'], default='append',
                        help='How to add the macro (default: append)')
    parser.add_argument('--server-id', help='JIRA server ID (optional)')
    parser.add_argument('--columns', help='Comma-separated list of columns to display')
    parser.add_argument('--max-results', type=int, default=20,
                        help='Maximum number of issues to display (default: 20)')
    parser.add_argument('--profile', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args(argv)

    # Validate inputs
    page_id = validate_page_id(args.page_id)

    # Must provide either JQL or issues
    if not args.jql and not args.issues:
        raise ValidationError("Either --jql or --issues must be provided")

    # Process issue keys if provided
    issue_keys = None
    if args.issues:
        issue_keys = [validate_issue_key(k.strip()) for k in args.issues.split(',')]

    # Validate JQL if provided
    jql = None
    if args.jql:
        jql = validate_jql_query(args.jql)

    # Parse columns if provided
    columns = None
    if args.columns:
        columns = [c.strip() for c in args.columns.split(',')]

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Get current page content (v1 API for XHTML storage format)
    page = client.get(
        f'/rest/api/content/{page_id}',
        params={'expand': 'body.storage,version'},
        operation='get page'
    )

    current_content = page['body']['storage']['value']
    current_version = page['version']['number']

    # Create appropriate macro
    if issue_keys and len(issue_keys) == 1 and not jql:
        # Single issue macro
        macro = create_jira_macro(
            issue_key=issue_keys[0],
            server_id=args.server_id
        )
    else:
        # Multiple issues macro
        macro = create_jira_issues_macro(
            jql=jql,
            issue_keys=issue_keys,
            server_id=args.server_id,
            columns=columns,
            max_results=args.max_results
        )

    # Update content based on mode
    if args.mode == 'append':
        new_content = append_jira_macro(current_content, macro)
    else:
        new_content = replace_with_jira_macro(current_content, macro)

    # Update page (v1 API)
    update_data = {
        'version': {
            'number': current_version + 1
        },
        'type': page['type'],
        'title': page['title'],
        'body': {
            'storage': {
                'value': new_content,
                'representation': 'storage'
            }
        }
    }

    result = client.put(
        f'/rest/api/content/{page_id}',
        json_data=update_data,
        operation='update page with JIRA macro'
    )

    # Output
    if args.output == 'json':
        print(format_json(result))
    else:
        print(f"Page: {result['title']}")
        print(f"ID: {result['id']}")
        print(f"Version: {result['version']['number']}")
        if issue_keys:
            print(f"Issues embedded: {', '.join(issue_keys)}")
        if jql:
            print(f"JQL query: {jql}")

    print_success(f"Embedded JIRA issues in page {page_id}")

if __name__ == '__main__':
    main()
