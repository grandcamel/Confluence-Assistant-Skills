"""
Live integration tests for page content operations.

Usage:
    pytest test_page_content_live.py --live -v
"""

import uuid

import pytest

from confluence_as import (
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
class TestPageContentLive:
    """Live tests for page content operations."""

    def test_create_page_with_rich_content(self, confluence_client, test_space):
        """Test creating a page with rich content."""
        title = f"Rich Content Test {uuid.uuid4().hex[:8]}"

        content = """<h1>Heading 1</h1>
        <p><strong>Bold</strong> and <em>italic</em> text.</p>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
        </ul>
        <table>
            <tr><th>Col 1</th><th>Col 2</th></tr>
            <tr><td>A</td><td>B</td></tr>
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

    def test_get_page_body(self, confluence_client, test_space):
        """Test getting page body content."""
        page = confluence_client.post(
            "/api/v2/pages",
            json_data={
                "spaceId": test_space["id"],
                "status": "current",
                "title": f"Body Test {uuid.uuid4().hex[:8]}",
                "body": {"representation": "storage", "value": "<p>Body content.</p>"},
            },
        )

        try:
            # Get with body
            fetched = confluence_client.get(
                f"/api/v2/pages/{page['id']}", params={"body-format": "storage"}
            )
            assert "body" in fetched
        finally:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")

    def test_page_with_code_block(self, confluence_client, test_space):
        """Test creating a page with code block."""
        title = f"Code Block Test {uuid.uuid4().hex[:8]}"

        content = """<ac:structured-macro ac:name="code">
            <ac:parameter ac:name="language">python</ac:parameter>
            <ac:plain-text-body><![CDATA[def hello():
    print("Hello, World!")]]></ac:plain-text-body>
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
