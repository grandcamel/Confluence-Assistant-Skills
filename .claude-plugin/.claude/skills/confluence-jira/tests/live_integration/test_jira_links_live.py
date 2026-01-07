"""
Live integration tests for JIRA link operations.

Usage:
    pytest test_jira_links_live.py --profile development -v
"""

import contextlib
import uuid

import pytest

from confluence_assistant_skills_lib import (
    get_confluence_client,
)


def pytest_addoption(parser):
    with contextlib.suppress(ValueError):
        parser.addoption("--profile", action="store", default=None)


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


@pytest.mark.integration
class TestJiraLinksLive:
    """Live tests for JIRA link operations in Confluence."""

    def test_create_page_with_jira_link(self, confluence_client, test_space):
        """Test creating a page with a JIRA-style link."""
        title = f"JIRA Link Test {uuid.uuid4().hex[:8]}"

        # Page with external link styled like JIRA
        content = """<p>Related issue:
            <a href="https://jira.atlassian.com/browse/DEMO-123">DEMO-123</a>
        </p>"""

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

    def test_page_with_jira_status_macro(self, confluence_client, test_space):
        """Test creating a page with a status macro (like JIRA status)."""
        title = f"Status Macro Test {uuid.uuid4().hex[:8]}"

        status_macro = """<ac:structured-macro ac:name="status">
            <ac:parameter ac:name="title">In Progress</ac:parameter>
            <ac:parameter ac:name="colour">Yellow</ac:parameter>
        </ac:structured-macro>"""

        page = confluence_client.post(
            "/api/v2/pages",
            json_data={
                "spaceId": test_space["id"],
                "status": "current",
                "title": title,
                "body": {
                    "representation": "storage",
                    "value": f"<p>Status: {status_macro}</p>",
                },
            },
        )

        try:
            assert page["id"] is not None
        finally:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")

    def test_page_with_task_list(self, confluence_client, test_space):
        """Test creating a page with task list (like JIRA tasks)."""
        title = f"Task List Test {uuid.uuid4().hex[:8]}"

        task_list = """<ac:task-list>
            <ac:task>
                <ac:task-status>incomplete</ac:task-status>
                <ac:task-body>Task 1 - similar to JIRA subtask</ac:task-body>
            </ac:task>
            <ac:task>
                <ac:task-status>complete</ac:task-status>
                <ac:task-body>Task 2 - completed</ac:task-body>
            </ac:task>
        </ac:task-list>"""

        page = confluence_client.post(
            "/api/v2/pages",
            json_data={
                "spaceId": test_space["id"],
                "status": "current",
                "title": title,
                "body": {"representation": "storage", "value": task_list},
            },
        )

        try:
            assert page["id"] is not None
        finally:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")
