"""
Live integration tests for confluence-jira skill.

Tests JIRA integration operations against a real Confluence instance.
Note: These tests require a connected JIRA instance.

Usage:
    pytest test_jira_live.py --profile development -v
"""

import contextlib
import uuid

import pytest

from confluence_assistant_skills_lib import (
    get_confluence_client,
)


def pytest_addoption(parser):
    with contextlib.suppress(ValueError):
        parser.addoption(
            "--profile", action="store", default=None, help="Confluence profile"
        )


@pytest.fixture(scope="session")
def confluence_client(request):
    profile = request.config.getoption("--profile", default=None)
    return get_confluence_client(profile=profile)


@pytest.fixture(scope="session")
def test_space(confluence_client):
    spaces = confluence_client.get("/api/v2/spaces", params={"limit": 1})
    if not spaces.get("results"):
        pytest.skip("No spaces available")
    return spaces["results"][0]


@pytest.fixture
def test_page(confluence_client, test_space):
    page = confluence_client.post(
        "/api/v2/pages",
        json_data={
            "spaceId": test_space["id"],
            "status": "current",
            "title": f"JIRA Test Page {uuid.uuid4().hex[:8]}",
            "body": {"representation": "storage", "value": "<p>Test.</p>"},
        },
    )
    yield page
    with contextlib.suppress(Exception):
        confluence_client.delete(f"/api/v2/pages/{page['id']}")


@pytest.mark.integration
class TestEmbedJiraIssueLive:
    """Live tests for embedding JIRA issues."""

    def test_create_page_with_jira_macro(self, confluence_client, test_space):
        """Test creating a page with a JIRA issue macro."""
        # This creates a page with JIRA macro - the macro may not render
        # if JIRA isn't connected, but the page should still be created
        jira_macro = """
        <ac:structured-macro ac:name="jira">
            <ac:parameter ac:name="server">System JIRA</ac:parameter>
            <ac:parameter ac:name="key">TEST-1</ac:parameter>
        </ac:structured-macro>
        """

        page = confluence_client.post(
            "/api/v2/pages",
            json_data={
                "spaceId": test_space["id"],
                "status": "current",
                "title": f"JIRA Embed Test {uuid.uuid4().hex[:8]}",
                "body": {
                    "representation": "storage",
                    "value": f"<p>Issue below:</p>{jira_macro}",
                },
            },
        )

        try:
            assert page["id"] is not None
        finally:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")

    def test_create_page_with_jira_filter(self, confluence_client, test_space):
        """Test creating a page with a JIRA filter/JQL macro."""
        jql_macro = """
        <ac:structured-macro ac:name="jira">
            <ac:parameter ac:name="server">System JIRA</ac:parameter>
            <ac:parameter ac:name="jqlQuery">project = TEST</ac:parameter>
            <ac:parameter ac:name="maximumIssues">5</ac:parameter>
        </ac:structured-macro>
        """

        page = confluence_client.post(
            "/api/v2/pages",
            json_data={
                "spaceId": test_space["id"],
                "status": "current",
                "title": f"JQL Filter Test {uuid.uuid4().hex[:8]}",
                "body": {
                    "representation": "storage",
                    "value": f"<p>Filter results:</p>{jql_macro}",
                },
            },
        )

        try:
            assert page["id"] is not None
        finally:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")


@pytest.mark.integration
class TestGetLinkedIssuesLive:
    """Live tests for getting linked JIRA issues."""

    def test_get_remote_links(self, confluence_client, test_page):
        """Test getting remote links (including JIRA) from a page."""
        # This endpoint may return empty if no JIRA links exist
        # Using v1 API for remote links
        try:
            links = confluence_client.get(
                f"/rest/api/content/{test_page['id']}",
                params={"expand": "metadata.properties"},
            )

            assert "id" in links
            # metadata may contain link properties

        except Exception:
            # JIRA integration may not be available
            pytest.skip("JIRA integration not available")


@pytest.mark.integration
class TestJiraApplicationLinkLive:
    """Live tests for JIRA application link status."""

    def test_check_application_links(self, confluence_client):
        """Test checking available application links."""
        # This may fail if user doesn't have admin access
        try:
            # Try to get available JIRA servers
            # This is an undocumented/internal endpoint
            response = confluence_client.session.get(
                f"{confluence_client.base_url}/wiki/rest/jiraanywhere/1.0/servers"
            )

            if response.status_code == 200:
                servers = response.json()
                assert isinstance(servers, list)
            else:
                pytest.skip("Cannot access JIRA server info")

        except Exception:
            pytest.skip("JIRA integration endpoint not available")


@pytest.mark.integration
class TestPageWithJiraContentLive:
    """Live tests for pages with JIRA-related content."""

    def test_update_page_with_jira_macro(self, confluence_client, test_page):
        """Test updating a page to add JIRA macro."""
        version = test_page["version"]["number"]

        jira_macro = """
        <ac:structured-macro ac:name="jira">
            <ac:parameter ac:name="server">System JIRA</ac:parameter>
            <ac:parameter ac:name="key">DEMO-1</ac:parameter>
        </ac:structured-macro>
        """

        updated = confluence_client.put(
            f"/api/v2/pages/{test_page['id']}",
            json_data={
                "id": test_page["id"],
                "status": "current",
                "title": test_page["title"],
                "version": {"number": version + 1},
                "body": {
                    "representation": "storage",
                    "value": f"<p>Updated with JIRA:</p>{jira_macro}",
                },
            },
        )

        assert updated["version"]["number"] == version + 1

    def test_create_roadmap_macro(self, confluence_client, test_space):
        """Test creating a page with JIRA roadmap macro."""
        roadmap_macro = """
        <ac:structured-macro ac:name="jiraroadmap">
            <ac:parameter ac:name="server">System JIRA</ac:parameter>
            <ac:parameter ac:name="jqlQuery">project = DEMO</ac:parameter>
        </ac:structured-macro>
        """

        page = confluence_client.post(
            "/api/v2/pages",
            json_data={
                "spaceId": test_space["id"],
                "status": "current",
                "title": f"Roadmap Test {uuid.uuid4().hex[:8]}",
                "body": {
                    "representation": "storage",
                    "value": f"<p>Roadmap:</p>{roadmap_macro}",
                },
            },
        )

        try:
            assert page["id"] is not None
        finally:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")
