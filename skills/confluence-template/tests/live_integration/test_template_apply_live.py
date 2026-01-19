"""
Live integration tests for template application operations.

Usage:
    pytest test_template_apply_live.py --live -v
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
class TestTemplateApplyLive:
    """Live tests for template application operations."""

    def test_create_page_with_template_content(self, confluence_client, test_space):
        """Test creating a page using template-like content structure."""
        title = f"Template Applied {uuid.uuid4().hex[:8]}"

        # Simulate a meeting notes template structure
        template_content = """
        <h1>Meeting Notes</h1>
        <h2>Date</h2>
        <p><ac:placeholder>Enter date here</ac:placeholder></p>
        <h2>Attendees</h2>
        <ul>
            <li>Attendee 1</li>
            <li>Attendee 2</li>
        </ul>
        <h2>Agenda</h2>
        <ol>
            <li>Topic 1</li>
            <li>Topic 2</li>
        </ol>
        <h2>Action Items</h2>
        <ac:task-list>
            <ac:task>
                <ac:task-status>incomplete</ac:task-status>
                <ac:task-body>Action item 1</ac:task-body>
            </ac:task>
        </ac:task-list>
        """

        page = confluence_client.post(
            "/api/v2/pages",
            json_data={
                "spaceId": test_space["id"],
                "status": "current",
                "title": title,
                "body": {"representation": "storage", "value": template_content},
            },
        )

        try:
            assert page["id"] is not None
            assert page["title"] == title
        finally:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")

    def test_create_page_with_table_template(self, confluence_client, test_space):
        """Test creating a page with a table template structure."""
        title = f"Table Template {uuid.uuid4().hex[:8]}"

        table_content = """
        <table>
            <tbody>
                <tr>
                    <th>Column 1</th>
                    <th>Column 2</th>
                    <th>Column 3</th>
                </tr>
                <tr>
                    <td>Data 1</td>
                    <td>Data 2</td>
                    <td>Data 3</td>
                </tr>
            </tbody>
        </table>
        """

        page = confluence_client.post(
            "/api/v2/pages",
            json_data={
                "spaceId": test_space["id"],
                "status": "current",
                "title": title,
                "body": {"representation": "storage", "value": table_content},
            },
        )

        try:
            assert page["id"] is not None
        finally:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")

    def test_list_content_templates(self, confluence_client, test_space):
        """Test listing available content templates in space."""
        templates = confluence_client.get(
            "/rest/api/template/page",
            params={"spaceKey": test_space["key"], "limit": 25},
        )

        # May be empty but should have results key
        assert "results" in templates

    def test_get_global_templates(self, confluence_client):
        """Test getting globally available templates."""
        templates = confluence_client.get(
            "/rest/api/template/page", params={"limit": 25}
        )

        assert "results" in templates
