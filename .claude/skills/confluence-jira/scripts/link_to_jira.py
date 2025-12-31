#!/usr/bin/env python3
"""
Create a remote link between a Confluence page and a JIRA issue.

Remote links create a bidirectional relationship that appears in both systems.

Examples:
    python link_to_jira.py 12345 PROJ-123
    python link_to_jira.py 12345 PROJ-123 --relationship "documents"
"""

import sys
import argparse
from typing import List, Dict, Any, Optional
from confluence_assistant_skills_lib import (
    get_confluence_client, handle_errors, ValidationError, validate_page_id,
    validate_issue_key, print_success, format_json,
)


def validate_relationship(relationship: str) -> str:
    """
    Validate relationship type.

    Args:
        relationship: Relationship string

    Returns:
        Validated relationship

    Raises:
        ValidationError: If relationship is invalid
    """
    valid_relationships = [
        "relates to",
        "documents",
        "mentions",
        "references",
        "implements"
    ]

    relationship = relationship.lower().strip()

    if relationship not in valid_relationships:
        raise ValidationError(
            f"Relationship must be one of: {', '.join(valid_relationships)}"
        )

    return relationship

def create_remote_link_data(
    page_id: str,
    issue_key: str,
    jira_url: str,
    relationship: str = "relates to"
) -> Dict[str, Any]:
    """
    Create remote link data structure for API.

    Args:
        page_id: Confluence page ID
        issue_key: JIRA issue key
        jira_url: Full URL to JIRA issue
        relationship: Relationship type

    Returns:
        Remote link data
    """
    return {
        "globalId": f"jira={issue_key}",
        "application": {
            "type": "jira",
            "name": "JIRA"
        },
        "relationship": relationship,
        "object": {
            "url": jira_url,
            "title": issue_key,
            "icon": {
                "url16x16": "/images/icons/jira_16.png"
            }
        }
    }

def link_exists(existing_links: List[Dict[str, Any]], issue_key: str) -> bool:
    """
    Check if a link to the issue already exists.

    Args:
        existing_links: List of existing remote links
        issue_key: JIRA issue key to check

    Returns:
        True if link exists
    """
    for link in existing_links:
        obj = link.get('object', {})
        url = obj.get('url', '')
        title = obj.get('title', '')

        if issue_key in url or issue_key == title:
            return True

    return False

def add_jira_link_to_content(
    content: str,
    issue_key: str,
    jira_url: str
) -> str:
    """
    Add a web link to JIRA issue in page content.

    Args:
        content: Current page content
        issue_key: JIRA issue key
        jira_url: URL to JIRA issue

    Returns:
        Updated content
    """
    link_html = f'<p>Related JIRA issue: <a href="{jira_url}">{issue_key}</a></p>'
    return content + "\n" + link_html

@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description='Create a link between Confluence page and JIRA issue',
        epilog='''
Examples:
  python link_to_jira.py 12345 PROJ-123
  python link_to_jira.py 12345 PROJ-123 --relationship "documents"
  python link_to_jira.py 12345 PROJ-123 --jira-url https://jira.example.com
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('page_id', help='Confluence page ID')
    parser.add_argument('issue_key', help='JIRA issue key (e.g., PROJ-123)')
    parser.add_argument('--relationship', default='relates to',
                        help='Relationship type (default: relates to)')
    parser.add_argument('--jira-url', help='Base JIRA URL (e.g., https://jira.example.com)')
    parser.add_argument('--skip-if-exists', action='store_true',
                        help='Skip if link already exists')
    parser.add_argument('--profile', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args(argv)

    # Validate inputs
    page_id = validate_page_id(args.page_id)
    issue_key = validate_issue_key(args.issue_key)
    relationship = validate_relationship(args.relationship)

    # Build JIRA URL
    if args.jira_url:
        jira_base_url = args.jira_url.rstrip('/')
    else:
        # Try to infer from environment or config
        # For now, require explicit URL
        raise ValidationError("--jira-url is required (e.g., https://jira.example.com)")

    issue_url = f"{jira_base_url}/browse/{issue_key}"

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Check existing remote links
    existing_links_response = client.get(
        f'/rest/api/content/{page_id}/remotelink',
        operation='get remote links'
    )

    existing_links = existing_links_response.get('results', [])

    # Check if link already exists
    if link_exists(existing_links, issue_key):
        if args.skip_if_exists:
            if args.output == 'json':
                print(format_json({"status": "skipped", "reason": "Link already exists"}))
            else:
                print(f"Link to {issue_key} already exists on page {page_id}")
            return
        else:
            print(f"Warning: Link to {issue_key} may already exist")

    # Create remote link
    link_data = create_remote_link_data(
        page_id=page_id,
        issue_key=issue_key,
        jira_url=issue_url,
        relationship=relationship
    )

    result = client.post(
        f'/rest/api/content/{page_id}/remotelink',
        json_data=link_data,
        operation='create remote link'
    )

    # Output
    if args.output == 'json':
        print(format_json(result))
    else:
        print(f"Created link:")
        print(f"  Page ID: {page_id}")
        print(f"  JIRA Issue: {issue_key}")
        print(f"  Relationship: {relationship}")
        print(f"  URL: {issue_url}")

    print_success(f"Linked page {page_id} to JIRA issue {issue_key}")

if __name__ == '__main__':
    main()
