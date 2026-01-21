"""
Confluence JIRA Skill - Test Configuration
"""

import json
from typing import Optional
from unittest.mock import MagicMock, Mock, patch

import pytest


@pytest.fixture
def mock_response():
    """Factory for creating mock HTTP responses."""

    def _create_response(
        status_code: int = 200,
        json_data: Optional[dict] = None,
        text: str = "",
        headers: Optional[dict] = None,
    ):
        response = Mock()
        response.status_code = status_code
        response.ok = 200 <= status_code < 300
        response.text = text or json.dumps(json_data or {})
        response.headers = headers or {}

        if json_data is not None:
            response.json.return_value = json_data
        else:
            response.json.side_effect = ValueError("No JSON")

        return response

    return _create_response


@pytest.fixture
def mock_client(mock_response):
    """Create a mock Confluence client."""
    from confluence_as import ConfluenceClient

    with patch.object(ConfluenceClient, "_create_session"):
        client = ConfluenceClient(
            base_url="https://test.atlassian.net",
            email="test@example.com",
            api_token="test-token",
        )

        client.session = MagicMock()

        def setup_response(method: str, response_data: dict, status_code: int = 200):
            response = mock_response(status_code=status_code, json_data=response_data)
            method_upper = method.upper()
            # POST/PUT/PATCH use session.request(), GET/DELETE use direct methods
            if method_upper in ("POST", "PUT", "PATCH"):
                client.session.request.return_value = response
            else:
                getattr(client.session, method.lower()).return_value = response

        client.setup_response = setup_response
        yield client


@pytest.fixture
def sample_page():
    """Sample page data from API."""
    return {
        "id": "123456",
        "status": "current",
        "title": "Test Page",
        "spaceId": "789",
        "parentId": "111",
        "version": {"number": 1},
        "body": {
            "storage": {"value": "<p>Test content</p>", "representation": "storage"}
        },
        "_links": {"webui": "/wiki/spaces/TEST/pages/123456"},
    }


@pytest.fixture
def sample_space():
    """Sample space data from API."""
    return {
        "id": "789",
        "key": "TEST",
        "name": "Test Space",
        "type": "global",
        "status": "current",
    }


@pytest.fixture
def sample_jira_issue():
    """Sample JIRA issue data."""
    return {
        "id": "10001",
        "key": "PROJ-123",
        "fields": {
            "summary": "Test Issue",
            "description": "Test description",
            "status": {"name": "Open"},
            "issuetype": {"name": "Task"},
            "priority": {"name": "Medium"},
            "assignee": {"displayName": "Test User"},
        },
    }


@pytest.fixture
def jira_macro_xhtml():
    """Sample JIRA macro in XHTML storage format."""
    return """<ac:structured-macro ac:name="jira" ac:schema-version="1">
    <ac:parameter ac:name="server">System JIRA</ac:parameter>
    <ac:parameter ac:name="serverId">12345-abcd-6789-efgh</ac:parameter>
    <ac:parameter ac:name="key">PROJ-123</ac:parameter>
</ac:structured-macro>"""


@pytest.fixture
def jira_issues_macro_xhtml():
    """Sample JIRA issues macro in XHTML storage format."""
    return """<ac:structured-macro ac:name="jiraissues" ac:schema-version="1">
    <ac:parameter ac:name="url">https://jira.example.com/issues/?jql=project=PROJ AND status=Open</ac:parameter>
    <ac:parameter ac:name="serverId">12345-abcd-6789-efgh</ac:parameter>
</ac:structured-macro>"""
