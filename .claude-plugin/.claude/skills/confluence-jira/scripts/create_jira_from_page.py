#!/usr/bin/env python3
"""
Create a JIRA issue from Confluence page content.

Extracts title and content from a Confluence page and creates a JIRA issue.
Requires JIRA API access (separate from Confluence API).

Examples:
    python create_jira_from_page.py 12345 --project PROJ --type Task
    python create_jira_from_page.py 12345 --project PROJ --type Bug --priority High
"""

import argparse
from typing import Any, Optional

from confluence_assistant_skills_lib import (
    ValidationError,
    format_json,
    get_confluence_client,
    handle_errors,
    print_success,
    validate_page_id,
)


def validate_jira_project_key(project_key: str) -> str:
    """
    Validate JIRA project key.

    Args:
        project_key: Project key to validate

    Returns:
        Validated project key (uppercase)

    Raises:
        ValidationError: If invalid
    """
    if not project_key:
        raise ValidationError("Project key is required")

    project_key = project_key.strip().upper()

    if len(project_key) < 2 or len(project_key) > 10:
        raise ValidationError("Project key must be 2-10 characters")

    return project_key


def validate_issue_type(issue_type: str) -> str:
    """
    Validate JIRA issue type.

    Args:
        issue_type: Issue type to validate

    Returns:
        Validated issue type

    Raises:
        ValidationError: If invalid
    """
    valid_types = [
        "Task",
        "Story",
        "Bug",
        "Epic",
        "Subtask",
        "Improvement",
        "New Feature",
    ]

    issue_type = issue_type.strip()

    # Case-insensitive check
    for vtype in valid_types:
        if issue_type.lower() == vtype.lower():
            return vtype

    raise ValidationError(f"Issue type must be one of: {', '.join(valid_types)}")


def create_jira_issue_data(
    project_key: str,
    summary: str,
    description: str,
    issue_type: str = "Task",
    priority: Optional[str] = None,
    assignee: Optional[str] = None,
) -> dict[str, Any]:
    """
    Create JIRA issue data structure.

    Args:
        project_key: JIRA project key
        summary: Issue summary
        description: Issue description
        issue_type: Issue type
        priority: Priority level
        assignee: Assignee username

    Returns:
        JIRA issue data
    """
    fields = {
        "project": {"key": project_key},
        "summary": summary,
        "description": description,
        "issuetype": {"name": issue_type},
    }

    if priority:
        fields["priority"] = {"name": priority}

    if assignee:
        fields["assignee"] = {"name": assignee}

    return {"fields": fields}


def extract_plain_text_from_xhtml(xhtml: str) -> str:
    """
    Extract plain text from XHTML storage format.

    Args:
        xhtml: XHTML content

    Returns:
        Plain text
    """
    from confluence_assistant_skills_lib import extract_text_from_xhtml

    return extract_text_from_xhtml(xhtml)


@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Create a JIRA issue from Confluence page content",
        epilog="""
Examples:
  python create_jira_from_page.py 12345 --project PROJ --type Task
  python create_jira_from_page.py 12345 --project PROJ --type Bug --priority High

Note: This script requires JIRA API access. Set JIRA credentials:
  export JIRA_URL="https://jira.example.com"
  export JIRA_EMAIL="your-email@example.com"
  export JIRA_API_TOKEN="your-jira-token"
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("page_id", help="Confluence page ID to convert")
    parser.add_argument("--project", "-p", required=True, help="JIRA project key")
    parser.add_argument(
        "--type", "-t", default="Task", help="Issue type (default: Task)"
    )
    parser.add_argument("--priority", help="Priority (e.g., High, Medium, Low)")
    parser.add_argument("--assignee", help="Assignee username")
    parser.add_argument("--jira-url", help="JIRA base URL (or set JIRA_URL env var)")
    parser.add_argument("--jira-email", help="JIRA email (or set JIRA_EMAIL env var)")
    parser.add_argument(
        "--jira-token", help="JIRA API token (or set JIRA_API_TOKEN env var)"
    )
    parser.add_argument(
        "--output",
        "-o",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    args = parser.parse_args(argv)

    # Validate inputs
    page_id = validate_page_id(args.page_id)
    project_key = validate_jira_project_key(args.project)
    issue_type = validate_issue_type(args.type)

    # Get JIRA credentials
    import os

    jira_url = args.jira_url or os.getenv("JIRA_URL")
    jira_email = args.jira_email or os.getenv("JIRA_EMAIL")
    jira_token = args.jira_token or os.getenv("JIRA_API_TOKEN")

    if not all([jira_url, jira_email, jira_token]):
        raise ValidationError(
            "JIRA credentials required. Set --jira-url, --jira-email, --jira-token "
            "or environment variables JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN"
        )

    # Get Confluence client
    confluence_client = get_confluence_client()

    # Get page content
    page = confluence_client.get(
        f"/rest/api/content/{page_id}",
        params={"expand": "body.storage"},
        operation="get page",
    )

    page_title = page["title"]
    page_content = page["body"]["storage"]["value"]

    # Extract plain text for JIRA description
    description = extract_plain_text_from_xhtml(page_content)

    # Add reference to Confluence page
    page_url = page.get("_links", {}).get("webui", "")
    if page_url:
        full_url = jira_url.rstrip("/") + page_url
        description += f"\n\nSource: {full_url}"

    # Create JIRA issue data
    issue_data = create_jira_issue_data(
        project_key=project_key,
        summary=page_title,
        description=description,
        issue_type=issue_type,
        priority=args.priority,
        assignee=args.assignee,
    )

    # Create JIRA client
    import requests
    from requests.auth import HTTPBasicAuth

    jira_api_url = jira_url.rstrip("/") + "/rest/api/2/issue"

    response = requests.post(
        jira_api_url,
        json=issue_data,
        auth=HTTPBasicAuth(jira_email, jira_token),
        headers={"Content-Type": "application/json"},
        timeout=30,
    )

    if not response.ok:
        error_msg = response.text
        try:
            error_json = response.json()
            error_msg = error_json.get("errorMessages", [error_msg])[0]
        except Exception:
            pass
        raise ValidationError(f"Failed to create JIRA issue: {error_msg}")

    result = response.json()
    issue_key = result["key"]

    # Output
    if args.output == "json":
        print(format_json(result))
    else:
        print("Created JIRA issue:")
        print(f"  Issue Key: {issue_key}")
        print(f"  Project: {project_key}")
        print(f"  Type: {issue_type}")
        print(f"  Summary: {page_title}")
        if args.priority:
            print(f"  Priority: {args.priority}")
        print(f"\nView issue: {jira_url}/browse/{issue_key}")

    print_success(f"Created JIRA issue {issue_key} from page {page_id}")


if __name__ == "__main__":
    main()
