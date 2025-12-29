#!/usr/bin/env python3
"""
Get JIRA issues linked to a Confluence page.

Extracts JIRA issue keys from:
- JIRA macros in the page
- Plain text mentions in the content
- Remote links to JIRA

Examples:
    python get_linked_issues.py 12345
    python get_linked_issues.py 12345 --output json
"""

import sys
import argparse
import re
import json
from typing import List, Set
from confluence_assistant_skills_lib import (
    get_confluence_client, handle_errors, validate_page_id, print_success,
    format_json,
)


# JIRA issue key pattern: PROJECT-123
JIRA_KEY_PATTERN = r'\b([A-Z][A-Z0-9_]{0,9}-\d+)\b'

def extract_jira_keys(content: str) -> List[str]:
    """
    Extract all JIRA issue keys from content.

    Args:
        content: Page content in any format

    Returns:
        List of unique issue keys
    """
    matches = re.findall(JIRA_KEY_PATTERN, content)
    # Deduplicate while preserving order
    seen = set()
    keys = []
    for key in matches:
        if key not in seen:
            seen.add(key)
            keys.append(key)
    return keys

def extract_jira_keys_from_macros(content: str) -> List[str]:
    """
    Extract JIRA issue keys specifically from JIRA macros.

    Args:
        content: Page content with JIRA macros

    Returns:
        List of issue keys from macros
    """
    keys = []

    # Single issue macro: <ac:parameter ac:name="key">PROJ-123</ac:parameter>
    single_issue_pattern = r'<ac:parameter ac:name="key">([A-Z][A-Z0-9_]{0,9}-\d+)</ac:parameter>'
    keys.extend(re.findall(single_issue_pattern, content))

    return keys

def extract_jql_from_macros(content: str) -> List[str]:
    """
    Extract JQL queries from JIRA issues macros.

    Args:
        content: Page content with JIRA macros

    Returns:
        List of JQL queries
    """
    queries = []

    # Issues macro: <ac:parameter ac:name="jqlQuery">...</ac:parameter>
    jql_pattern = r'<ac:parameter ac:name="jqlQuery">([^<]+)</ac:parameter>'
    queries.extend(re.findall(jql_pattern, content))

    # Also check for URL-based queries
    url_pattern = r'<ac:parameter ac:name="url">([^<]+jql=([^<&]+))[^<]*</ac:parameter>'
    url_matches = re.findall(url_pattern, content)
    for full_url, jql_part in url_matches:
        # Unescape JQL from URL
        import urllib.parse
        jql = urllib.parse.unquote(jql_part)
        queries.append(jql)

    return queries

def format_linked_issues_json(issues: List[str]) -> str:
    """
    Format issue keys as JSON.

    Args:
        issues: List of issue keys

    Returns:
        JSON string
    """
    return json.dumps({
        "count": len(issues),
        "issues": issues
    }, indent=2)

def format_linked_issues_text(issues: List[str]) -> str:
    """
    Format issue keys as text.

    Args:
        issues: List of issue keys

    Returns:
        Formatted text string
    """
    if not issues:
        return "No JIRA issues found."

    lines = [f"Found {len(issues)} JIRA issue(s):"]
    lines.append("")
    for issue in issues:
        lines.append(f"  - {issue}")

    return "\n".join(lines)

@handle_errors
def main():
    parser = argparse.ArgumentParser(
        description='Get JIRA issues linked to a Confluence page',
        epilog='''
Examples:
  python get_linked_issues.py 12345
  python get_linked_issues.py 12345 --output json
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('page_id', help='Page ID to analyze')
    parser.add_argument('--profile', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args()

    # Validate inputs
    page_id = validate_page_id(args.page_id)

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Get page content (v1 API for full XHTML)
    page = client.get(
        f'/rest/api/content/{page_id}',
        params={'expand': 'body.storage'},
        operation='get page'
    )

    content = page['body']['storage']['value']

    # Extract all JIRA keys
    all_keys = extract_jira_keys(content)

    # Extract keys from macros specifically
    macro_keys = extract_jira_keys_from_macros(content)

    # Extract JQL queries (informational)
    jql_queries = extract_jql_from_macros(content)

    # Output
    if args.output == 'json':
        output_data = {
            "page_id": page_id,
            "page_title": page['title'],
            "all_issues": all_keys,
            "macro_issues": macro_keys,
            "jql_queries": jql_queries
        }
        print(format_json(output_data))
    else:
        print(f"Page: {page['title']} (ID: {page_id})")
        print()
        print(format_linked_issues_text(all_keys))

        if macro_keys:
            print()
            print(f"Issues from JIRA macros: {', '.join(macro_keys)}")

        if jql_queries:
            print()
            print("JQL queries found:")
            for jql in jql_queries:
                print(f"  - {jql}")

    print_success(f"Analyzed page {page_id}")

if __name__ == '__main__':
    main()
