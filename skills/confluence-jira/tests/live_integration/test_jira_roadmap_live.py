"""
Live integration tests for JIRA roadmap macro operations.

Usage:
    pytest test_jira_roadmap_live.py --live -v
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
class TestJiraRoadmapLive:
    """Live tests for JIRA roadmap-like content in Confluence."""

    def test_create_roadmap_table(self, confluence_client, test_space):
        """Test creating a roadmap-style table."""
        title = f"Roadmap Test {uuid.uuid4().hex[:8]}"

        content = """<table>
            <tr>
                <th>Quarter</th>
                <th>Feature</th>
                <th>Status</th>
            </tr>
            <tr>
                <td>Q1</td>
                <td>Feature A</td>
                <td><ac:structured-macro ac:name="status">
                    <ac:parameter ac:name="colour">Green</ac:parameter>
                    <ac:parameter ac:name="title">Done</ac:parameter>
                </ac:structured-macro></td>
            </tr>
            <tr>
                <td>Q2</td>
                <td>Feature B</td>
                <td><ac:structured-macro ac:name="status">
                    <ac:parameter ac:name="colour">Yellow</ac:parameter>
                    <ac:parameter ac:name="title">In Progress</ac:parameter>
                </ac:structured-macro></td>
            </tr>
        </table>"""

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

    def test_page_with_panel_macro(self, confluence_client, test_space):
        """Test creating a page with panel macro for highlights."""
        title = f"Panel Test {uuid.uuid4().hex[:8]}"

        content = """<ac:structured-macro ac:name="panel">
            <ac:parameter ac:name="title">Key Milestone</ac:parameter>
            <ac:rich-text-body>
                <p>Important roadmap milestone description.</p>
            </ac:rich-text-body>
        </ac:structured-macro>"""

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

    def test_page_with_expand_macro(self, confluence_client, test_space):
        """Test creating a page with expand macro for details."""
        title = f"Expand Test {uuid.uuid4().hex[:8]}"

        content = """<ac:structured-macro ac:name="expand">
            <ac:parameter ac:name="title">Click to expand details</ac:parameter>
            <ac:rich-text-body>
                <p>Detailed information here.</p>
            </ac:rich-text-body>
        </ac:structured-macro>"""

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
