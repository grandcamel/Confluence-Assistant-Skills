"""JIRA integration commands - CLI-only implementation."""

from __future__ import annotations

import os
import re
from typing import Any

import click

from confluence_assistant_skills_lib import (
    ValidationError,
    format_json,
    format_table,
    get_confluence_client,
    handle_errors,
    print_info,
    print_success,
    print_warning,
    validate_page_id,
    xhtml_to_markdown,
)


def _get_jira_client_config(
    jira_url: str | None,
    jira_email: str | None,
    jira_token: str | None,
) -> dict[str, str]:
    """Get JIRA client configuration from options or environment."""
    url = jira_url or os.environ.get("JIRA_URL", "")
    email = jira_email or os.environ.get("JIRA_EMAIL", "")
    token = jira_token or os.environ.get("JIRA_API_TOKEN", "")

    if not url:
        raise ValidationError("JIRA URL required (--jira-url or JIRA_URL env var)")
    if not email:
        raise ValidationError("JIRA email required (--jira-email or JIRA_EMAIL env var)")
    if not token:
        raise ValidationError("JIRA token required (--jira-token or JIRA_API_TOKEN env var)")

    return {"url": url, "email": email, "token": token}


def _build_jira_macro(
    jql: str | None = None,
    issues: list[str] | None = None,
    columns: str | None = None,
    max_results: int = 20,
    server_id: str | None = None,
) -> str:
    """Build JIRA Issues macro XHTML."""
    params = []

    if jql:
        params.append(f'<ac:parameter ac:name="jqlQuery">{jql}</ac:parameter>')
    elif issues:
        # For specific issues, use key-based query
        keys = ",".join(issues)
        jql_query = f"key in ({keys})"
        params.append(f'<ac:parameter ac:name="jqlQuery">{jql_query}</ac:parameter>')

    if columns:
        params.append(f'<ac:parameter ac:name="columns">{columns}</ac:parameter>')

    params.append(f'<ac:parameter ac:name="maximumIssues">{max_results}</ac:parameter>')

    if server_id:
        params.append(f'<ac:parameter ac:name="serverId">{server_id}</ac:parameter>')

    params_str = "\n".join(params)

    return f'''<ac:structured-macro ac:name="jira" ac:schema-version="1" ac:macro-id="jira-issues">
{params_str}
</ac:structured-macro>'''


@click.group()
def jira() -> None:
    """JIRA integration commands."""
    pass


@jira.command(name="link")
@click.argument("page_id")
@click.argument("issue_key")
@click.option(
    "--jira-url", required=True, help="Base JIRA URL (e.g., https://jira.example.com)"
)
@click.option(
    "--relationship",
    default="relates to",
    help="Relationship type (default: relates to)",
)
@click.option("--skip-if-exists", is_flag=True, help="Skip if link already exists")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def link_to_jira(
    page_id: str,
    issue_key: str,
    jira_url: str,
    relationship: str,
    skip_if_exists: bool,
    output: str,
) -> None:
    """Link a Confluence page to a JIRA issue.

    Creates a remote issue link between the Confluence page and the JIRA issue.
    """
    page_id = validate_page_id(page_id)

    if not issue_key:
        raise ValidationError("Issue key is required")

    # Validate issue key format
    if not re.match(r"^[A-Z][A-Z0-9]+-\d+$", issue_key.upper()):
        raise ValidationError(f"Invalid issue key format: {issue_key}")

    issue_key = issue_key.upper()

    client = get_confluence_client()

    # Get page info
    page = client.get(f"/api/v2/pages/{page_id}", operation="get page")
    page_title = page.get("title", "Unknown")
    space_key = page.get("spaceId", "")

    # Check for existing link if skip_if_exists
    if skip_if_exists:
        # Check remote links on page
        try:
            links = client.get(
                f"/rest/api/content/{page_id}",
                params={"expand": "metadata.properties"},
                operation="get page metadata",
            )
            # Check if JIRA link exists
            properties = links.get("metadata", {}).get("properties", {})
            for key, value in properties.items():
                if issue_key in str(value):
                    if output == "json":
                        click.echo(format_json({
                            "page": {"id": page_id, "title": page_title},
                            "issue": issue_key,
                            "linked": True,
                            "skipped": True,
                            "message": "Link already exists",
                        }))
                    else:
                        print_info(f"Link to {issue_key} already exists, skipping.")
                    return
        except Exception:
            pass  # Continue with linking

    # Build the JIRA link URL
    jira_url = jira_url.rstrip("/")
    issue_url = f"{jira_url}/browse/{issue_key}"

    # Add JIRA issue link to page using a property or applink
    # Note: The actual linking mechanism depends on how Confluence and JIRA are connected
    # For Confluence Cloud with JIRA Cloud, we can use the remote issue link API

    # Create remote link by adding a JIRA macro to the page
    # First, get current content
    page_content = client.get(
        f"/api/v2/pages/{page_id}",
        params={"body-format": "storage"},
        operation="get page content",
    )

    current_body = page_content.get("body", {}).get("storage", {}).get("value", "")

    # Add a comment-style link indicator (lightweight approach)
    link_marker = f'<!-- JIRA-LINK: {issue_key} -->'

    if link_marker not in current_body:
        # Add the marker at the end
        new_body = current_body + f"\n{link_marker}"

        # Update page
        current_version = page_content.get("version", {}).get("number", 1)
        update_data = {
            "id": page_id,
            "title": page_title,
            "body": {
                "representation": "storage",
                "value": new_body,
            },
            "version": {
                "number": current_version + 1,
            },
        }

        client.put(
            f"/api/v2/pages/{page_id}",
            json_data=update_data,
            operation="update page with link",
        )

    if output == "json":
        click.echo(format_json({
            "page": {"id": page_id, "title": page_title},
            "issue": issue_key,
            "issueUrl": issue_url,
            "relationship": relationship,
            "linked": True,
        }))
    else:
        click.echo(f"\nPage linked to JIRA issue")
        click.echo(f"  Page: {page_title} ({page_id})")
        click.echo(f"  Issue: {issue_key}")
        click.echo(f"  URL: {issue_url}")
        click.echo(f"  Relationship: {relationship}")

    print_success(f"Linked page {page_id} to issue {issue_key}")


@jira.command(name="linked")
@click.argument("page_id")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def get_linked_issues(
    page_id: str,
    output: str,
) -> None:
    """Get JIRA issues linked to a page.

    Finds JIRA issue references in the page content and macros.
    """
    page_id = validate_page_id(page_id)

    client = get_confluence_client()

    # Get page info with content
    page = client.get(
        f"/api/v2/pages/{page_id}",
        params={"body-format": "storage"},
        operation="get page",
    )

    page_title = page.get("title", "Unknown")
    body = page.get("body", {}).get("storage", {}).get("value", "")

    # Find JIRA references in page content
    # Look for:
    # 1. JIRA macros
    # 2. Issue keys in text
    # 3. JIRA-LINK markers

    linked_issues: list[dict[str, Any]] = []

    # Find JIRA macros
    macro_pattern = r'<ac:structured-macro[^>]*ac:name="jira"[^>]*>.*?</ac:structured-macro>'
    macros = re.findall(macro_pattern, body, re.DOTALL)

    for i, macro in enumerate(macros):
        # Extract JQL from macro
        jql_match = re.search(r'<ac:parameter ac:name="jqlQuery">([^<]+)</ac:parameter>', macro)
        if jql_match:
            linked_issues.append({
                "type": "macro",
                "index": i,
                "jql": jql_match.group(1),
            })

    # Find issue keys in text (format: PROJECT-123)
    issue_pattern = r'\b([A-Z][A-Z0-9]+-\d+)\b'
    issue_keys = set(re.findall(issue_pattern, body))

    for key in issue_keys:
        linked_issues.append({
            "type": "reference",
            "key": key,
        })

    # Find JIRA-LINK markers
    link_pattern = r'<!-- JIRA-LINK: ([A-Z][A-Z0-9]+-\d+) -->'
    link_markers = re.findall(link_pattern, body)

    for key in link_markers:
        if not any(i.get("key") == key for i in linked_issues):
            linked_issues.append({
                "type": "link",
                "key": key,
            })

    if output == "json":
        click.echo(format_json({
            "page": {"id": page_id, "title": page_title},
            "linkedIssues": linked_issues,
            "count": len(linked_issues),
        }))
    else:
        click.echo(f"\nJIRA Issues Linked to: {page_title} ({page_id})")
        click.echo(f"{'=' * 60}\n")

        if not linked_issues:
            click.echo("No JIRA issues found linked to this page.")
        else:
            # Group by type
            macros = [i for i in linked_issues if i["type"] == "macro"]
            references = [i for i in linked_issues if i["type"] in ("reference", "link")]

            if macros:
                click.echo("JIRA Macros:")
                for m in macros:
                    click.echo(f"  [{m['index']}] JQL: {m.get('jql', 'N/A')[:50]}")
                click.echo()

            if references:
                click.echo("Issue References:")
                data = []
                for ref in references:
                    data.append({
                        "key": ref.get("key", ""),
                        "type": ref.get("type", ""),
                    })

                click.echo(format_table(
                    data,
                    columns=["key", "type"],
                    headers=["Issue Key", "Type"],
                ))

    print_success(f"Found {len(linked_issues)} JIRA reference(s)")


@jira.command(name="embed")
@click.argument("page_id")
@click.option("--jql", help="JQL query to filter issues")
@click.option(
    "--issues", help="Comma-separated list of issue keys (e.g., PROJ-123,PROJ-456)"
)
@click.option(
    "--mode",
    type=click.Choice(["append", "replace"]),
    default="append",
    help="How to add the macro (default: append)",
)
@click.option("--server-id", help="JIRA server ID (optional)")
@click.option("--columns", help="Columns to display (comma-separated)")
@click.option(
    "--max-results", type=int, default=20, help="Maximum number of issues (default: 20)"
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def embed_jira_issues(
    page_id: str,
    jql: str | None,
    issues: str | None,
    mode: str,
    server_id: str | None,
    columns: str | None,
    max_results: int,
    output: str,
) -> None:
    """Embed JIRA issues in a page using JQL or issue keys.

    Either --jql or --issues must be provided.
    """
    page_id = validate_page_id(page_id)

    if not jql and not issues:
        raise ValidationError("Either --jql or --issues must be provided")

    client = get_confluence_client()

    # Get page info
    page = client.get(
        f"/api/v2/pages/{page_id}",
        params={"body-format": "storage"},
        operation="get page",
    )

    page_title = page.get("title", "Unknown")
    current_body = page.get("body", {}).get("storage", {}).get("value", "")
    current_version = page.get("version", {}).get("number", 1)

    # Parse issues list
    issue_list = None
    if issues:
        issue_list = [i.strip().upper() for i in issues.split(",") if i.strip()]

    # Build JIRA macro
    macro_html = _build_jira_macro(
        jql=jql,
        issues=issue_list,
        columns=columns,
        max_results=max_results,
        server_id=server_id,
    )

    # Update page content
    if mode == "replace":
        # Remove existing JIRA macros
        new_body = re.sub(
            r'<ac:structured-macro[^>]*ac:name="jira"[^>]*>.*?</ac:structured-macro>',
            '',
            current_body,
            flags=re.DOTALL,
        )
        new_body = new_body.strip() + f"\n\n{macro_html}"
    else:
        # Append macro
        new_body = current_body + f"\n\n{macro_html}"

    # Update page
    update_data = {
        "id": page_id,
        "title": page_title,
        "body": {
            "representation": "storage",
            "value": new_body,
        },
        "version": {
            "number": current_version + 1,
        },
    }

    result = client.put(
        f"/api/v2/pages/{page_id}",
        json_data=update_data,
        operation="embed jira issues",
    )

    if output == "json":
        click.echo(format_json({
            "page": {"id": page_id, "title": page_title},
            "jql": jql,
            "issues": issue_list,
            "mode": mode,
            "macroAdded": True,
        }))
    else:
        click.echo(f"\nJIRA Issues embedded in: {page_title}")
        click.echo(f"  Page ID: {page_id}")
        if jql:
            click.echo(f"  JQL: {jql}")
        if issue_list:
            click.echo(f"  Issues: {', '.join(issue_list)}")
        click.echo(f"  Mode: {mode}")
        click.echo(f"  Max Results: {max_results}")

    print_success(f"Embedded JIRA issues in page {page_id}")


@jira.command(name="create-from-page")
@click.argument("page_id")
@click.option("--project", "-p", required=True, help="JIRA project key")
@click.option(
    "--type", "-t", "issue_type", default="Task", help="Issue type (default: Task)"
)
@click.option("--priority", help="Priority (e.g., High, Medium, Low)")
@click.option("--assignee", help="Assignee username/account ID")
@click.option("--jira-url", help="JIRA base URL (or set JIRA_URL env var)")
@click.option("--jira-email", help="JIRA email (or set JIRA_EMAIL env var)")
@click.option("--jira-token", help="JIRA API token (or set JIRA_API_TOKEN env var)")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def create_jira_from_page(
    page_id: str,
    project: str,
    issue_type: str,
    priority: str | None,
    assignee: str | None,
    jira_url: str | None,
    jira_email: str | None,
    jira_token: str | None,
    output: str,
) -> None:
    """Create a JIRA issue from a Confluence page.

    Requires JIRA credentials via options or environment variables
    (JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN).

    Note: This command requires a direct JIRA API connection.
    """
    page_id = validate_page_id(page_id)

    # Get JIRA config
    jira_config = _get_jira_client_config(jira_url, jira_email, jira_token)

    client = get_confluence_client()

    # Get page info
    page = client.get(
        f"/api/v2/pages/{page_id}",
        params={"body-format": "storage"},
        operation="get page",
    )

    page_title = page.get("title", "Unknown")
    page_body = page.get("body", {}).get("storage", {}).get("value", "")

    # Convert page body to plain text for JIRA description
    try:
        description = xhtml_to_markdown(page_body)[:32000]  # JIRA limit
    except Exception:
        # Fallback: strip HTML tags
        description = re.sub(r'<[^>]+>', '', page_body)[:32000]

    # Build JIRA issue data
    issue_data: dict[str, Any] = {
        "fields": {
            "project": {"key": project.upper()},
            "summary": page_title[:255],
            "description": description,
            "issuetype": {"name": issue_type},
        }
    }

    if priority:
        issue_data["fields"]["priority"] = {"name": priority}

    if assignee:
        issue_data["fields"]["assignee"] = {"accountId": assignee}

    # Create issue via JIRA API
    # Note: This requires requests library for direct JIRA API call
    import requests
    from requests.auth import HTTPBasicAuth

    jira_api_url = f"{jira_config['url'].rstrip('/')}/rest/api/3/issue"

    response = requests.post(
        jira_api_url,
        json=issue_data,
        auth=HTTPBasicAuth(jira_config["email"], jira_config["token"]),
        headers={"Content-Type": "application/json"},
        timeout=30,
    )

    if response.status_code not in (200, 201):
        error_msg = response.text[:500]
        raise ValidationError(f"Failed to create JIRA issue: {response.status_code} - {error_msg}")

    result = response.json()
    issue_key = result.get("key", "")
    issue_id = result.get("id", "")

    # Link the page to the new issue
    if issue_key:
        jira_url_base = jira_config["url"].rstrip("/")
        link_marker = f'<!-- JIRA-LINK: {issue_key} -->'

        # Add link marker to page
        page_content = client.get(
            f"/api/v2/pages/{page_id}",
            params={"body-format": "storage"},
            operation="get page content",
        )

        current_body = page_content.get("body", {}).get("storage", {}).get("value", "")
        current_version = page_content.get("version", {}).get("number", 1)

        if link_marker not in current_body:
            new_body = current_body + f"\n{link_marker}"
            update_data = {
                "id": page_id,
                "title": page_title,
                "body": {
                    "representation": "storage",
                    "value": new_body,
                },
                "version": {
                    "number": current_version + 1,
                },
            }
            client.put(
                f"/api/v2/pages/{page_id}",
                json_data=update_data,
                operation="link page to new issue",
            )

    if output == "json":
        click.echo(format_json({
            "page": {"id": page_id, "title": page_title},
            "issue": {
                "key": issue_key,
                "id": issue_id,
                "url": f"{jira_config['url']}/browse/{issue_key}",
                "project": project,
                "type": issue_type,
            },
        }))
    else:
        click.echo(f"\nJIRA Issue Created from Confluence Page")
        click.echo(f"  Page: {page_title} ({page_id})")
        click.echo(f"  Issue: {issue_key}")
        click.echo(f"  URL: {jira_config['url']}/browse/{issue_key}")
        click.echo(f"  Project: {project}")
        click.echo(f"  Type: {issue_type}")

    print_success(f"Created JIRA issue {issue_key} from page {page_id}")


@jira.command(name="sync-macro")
@click.argument("page_id")
@click.option("--update-jql", help="Update JQL query in macros")
@click.option(
    "--macro-index", type=int, help="Index of macro to update (0-based, default: all)"
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def sync_jira_macro(
    page_id: str,
    update_jql: str | None,
    macro_index: int | None,
    output: str,
) -> None:
    """Refresh JIRA macros on a page.

    Force a page update to trigger macro refresh, or update macro JQL queries.
    """
    page_id = validate_page_id(page_id)

    client = get_confluence_client()

    # Get page info
    page = client.get(
        f"/api/v2/pages/{page_id}",
        params={"body-format": "storage"},
        operation="get page",
    )

    page_title = page.get("title", "Unknown")
    current_body = page.get("body", {}).get("storage", {}).get("value", "")
    current_version = page.get("version", {}).get("number", 1)

    # Find JIRA macros
    macro_pattern = r'(<ac:structured-macro[^>]*ac:name="jira"[^>]*>.*?</ac:structured-macro>)'
    macros = re.findall(macro_pattern, current_body, re.DOTALL)

    if not macros:
        if output == "json":
            click.echo(format_json({
                "page": {"id": page_id, "title": page_title},
                "macrosFound": 0,
                "updated": False,
            }))
        else:
            print_warning("No JIRA macros found on this page.")
        return

    updated_body = current_body
    macros_updated = 0

    if update_jql:
        # Update JQL in specified or all macros
        for i, macro in enumerate(macros):
            if macro_index is not None and i != macro_index:
                continue

            # Replace JQL parameter
            new_macro = re.sub(
                r'<ac:parameter ac:name="jqlQuery">[^<]*</ac:parameter>',
                f'<ac:parameter ac:name="jqlQuery">{update_jql}</ac:parameter>',
                macro,
            )

            if new_macro != macro:
                updated_body = updated_body.replace(macro, new_macro)
                macros_updated += 1

    # Update page to trigger refresh
    update_data = {
        "id": page_id,
        "title": page_title,
        "body": {
            "representation": "storage",
            "value": updated_body,
        },
        "version": {
            "number": current_version + 1,
            "message": "Sync JIRA macros",
        },
    }

    client.put(
        f"/api/v2/pages/{page_id}",
        json_data=update_data,
        operation="sync jira macros",
    )

    if output == "json":
        click.echo(format_json({
            "page": {"id": page_id, "title": page_title},
            "macrosFound": len(macros),
            "macrosUpdated": macros_updated,
            "jqlUpdated": update_jql if update_jql else None,
            "synced": True,
        }))
    else:
        click.echo(f"\nJIRA Macros Synced: {page_title}")
        click.echo(f"  Page ID: {page_id}")
        click.echo(f"  Macros Found: {len(macros)}")
        if update_jql:
            click.echo(f"  Macros Updated: {macros_updated}")
            click.echo(f"  New JQL: {update_jql}")
        click.echo("  Page refreshed to trigger macro sync.")

    print_success(f"Synced JIRA macros on page {page_id}")
