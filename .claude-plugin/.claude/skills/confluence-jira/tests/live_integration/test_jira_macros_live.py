"""
Live integration tests for JIRA macro operations.

Usage:
    pytest test_jira_macros_live.py --live -v
"""

import uuid

import pytest

from confluence_assistant_skills_lib import (
    get_confluence_client,
)


@pytest.fixture(scope="session")
def confluence_client():
    return get_confluence_client()


@pytest.fixture(scope="session")
def test_space(confluence_client):
    spaces = confluence_client.get("/api/v2/spaces", params={"limit": 1})
    if not spaces.get("results"):
        pytest.skip("No spaces available")
    return spaces["results"][0]


@pytest.mark.integration
class TestJiraMacrosLive:
    """Live tests for JIRA macro rendering in Confluence."""

    def test_create_page_with_jira_macro(self, confluence_client, test_space):
        """Test creating a page with a JIRA issue macro."""
        title = f"JIRA Macro Test {uuid.uuid4().hex[:8]}"

        # JIRA macro in storage format
        jira_macro = """<ac:structured-macro ac:name="jira">
            <ac:parameter ac:name="server">System JIRA</ac:parameter>
            <ac:parameter ac:name="serverId">your-server-id</ac:parameter>
            <ac:parameter ac:name="key">DEMO-1</ac:parameter>
        </ac:structured-macro>"""

        page = confluence_client.post(
            "/api/v2/pages",
            json_data={
                "spaceId": test_space["id"],
                "status": "current",
                "title": title,
                "body": {
                    "representation": "storage",
                    "value": f"<p>JIRA issue: {jira_macro}</p>",
                },
            },
        )

        try:
            assert page["id"] is not None
            assert page["title"] == title
        finally:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")

    def test_create_page_with_jira_filter_macro(self, confluence_client, test_space):
        """Test creating a page with a JIRA issues filter macro."""
        title = f"JIRA Filter Test {uuid.uuid4().hex[:8]}"

        # JIRA issues macro in storage format
        jira_issues_macro = """<ac:structured-macro ac:name="jira">
            <ac:parameter ac:name="server">System JIRA</ac:parameter>
            <ac:parameter ac:name="jqlQuery">project = DEMO</ac:parameter>
            <ac:parameter ac:name="maximumIssues">5</ac:parameter>
        </ac:structured-macro>"""

        page = confluence_client.post(
            "/api/v2/pages",
            json_data={
                "spaceId": test_space["id"],
                "status": "current",
                "title": title,
                "body": {
                    "representation": "storage",
                    "value": f"<p>JIRA issues: {jira_issues_macro}</p>",
                },
            },
        )

        try:
            assert page["id"] is not None
        finally:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")

    def test_page_with_multiple_jira_references(self, confluence_client, test_space):
        """Test creating a page with multiple JIRA references."""
        title = f"Multi JIRA Test {uuid.uuid4().hex[:8]}"

        content = """<p>Issue 1: <ac:structured-macro ac:name="jira">
            <ac:parameter ac:name="key">DEMO-1</ac:parameter>
        </ac:structured-macro></p>
        <p>Issue 2: <ac:structured-macro ac:name="jira">
            <ac:parameter ac:name="key">DEMO-2</ac:parameter>
        </ac:structured-macro></p>"""

        page = confluence_client.post(
            "/api/v2/pages",
            json_data={
                "spaceId": test_space["id"],
                "status": "current",
                "title": title,
                "body": {"representation": "storage", "value": content},
            },
        )

        try:
            assert page["id"] is not None
        finally:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")
