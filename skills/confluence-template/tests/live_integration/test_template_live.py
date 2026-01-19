"""
Live integration tests for confluence-template skill.

Tests template operations against a real Confluence instance.

Usage:
    pytest test_template_live.py --live -v
"""

import contextlib
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
class TestListTemplatesLive:
    """Live tests for listing templates."""

    def test_list_global_templates(self, confluence_client):
        """Test listing global templates."""
        templates = confluence_client.get(
            "/rest/api/template/page", params={"limit": 25}
        )

        assert "results" in templates
        # Should have at least some built-in templates
        assert isinstance(templates["results"], list)

    def test_list_space_templates(self, confluence_client, test_space):
        """Test listing space templates."""
        templates = confluence_client.get(
            "/rest/api/template/page",
            params={"spaceKey": test_space["key"], "limit": 25},
        )

        assert "results" in templates

    def test_list_blueprint_templates(self, confluence_client):
        """Test listing blueprint templates."""
        blueprints = confluence_client.get(
            "/rest/api/template/blueprint", params={"limit": 25}
        )

        assert "results" in blueprints


@pytest.mark.integration
class TestGetTemplateLive:
    """Live tests for getting template details."""

    def test_get_template_by_id(self, confluence_client):
        """Test getting a template by ID."""
        # First get a template ID
        templates = confluence_client.get(
            "/rest/api/template/page", params={"limit": 1}
        )

        if not templates.get("results"):
            pytest.skip("No templates available")

        template_id = templates["results"][0]["templateId"]

        # Get template by ID
        template = confluence_client.get(f"/rest/api/template/{template_id}")

        assert template["templateId"] == template_id
        assert "name" in template


@pytest.mark.integration
class TestCreateFromTemplateLive:
    """Live tests for creating pages from templates."""

    def test_create_page_from_blank(self, confluence_client, test_space):
        """Test creating a page (blank template equivalent)."""
        title = f"Template Test Page {uuid.uuid4().hex[:8]}"

        page = confluence_client.post(
            "/api/v2/pages",
            json_data={
                "spaceId": test_space["id"],
                "status": "current",
                "title": title,
                "body": {
                    "representation": "storage",
                    "value": "<p>Created from test.</p>",
                },
            },
        )

        try:
            assert page["id"] is not None
            assert page["title"] == title
        finally:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")


@pytest.mark.integration
class TestCreateTemplateLive:
    """Live tests for creating templates."""

    def test_create_space_template(self, confluence_client, test_space):
        """Test creating a space-level template."""
        template_name = f"Test Template {uuid.uuid4().hex[:8]}"

        template = confluence_client.post(
            "/rest/api/template",
            json_data={
                "name": template_name,
                "templateType": "page",
                "space": {"key": test_space["key"]},
                "body": {
                    "storage": {
                        "value": "<p>Template content.</p>",
                        "representation": "storage",
                    }
                },
            },
        )

        try:
            assert template["name"] == template_name
            assert "templateId" in template
        finally:
            # Clean up template
            with contextlib.suppress(Exception):
                confluence_client.delete(f"/rest/api/template/{template['templateId']}")

    def test_create_template_with_variables(self, confluence_client, test_space):
        """Test creating a template with placeholder variables."""
        template_name = f"Variable Template {uuid.uuid4().hex[:8]}"

        # Templates can use @mention and variable macros
        content = """
        <p>Project: <at:var at:name="project" /></p>
        <p>Author: <at:var at:name="author" /></p>
        <p>Date: <at:var at:name="date" /></p>
        """

        template = confluence_client.post(
            "/rest/api/template",
            json_data={
                "name": template_name,
                "templateType": "page",
                "space": {"key": test_space["key"]},
                "body": {"storage": {"value": content, "representation": "storage"}},
            },
        )

        try:
            assert template["name"] == template_name
        finally:
            with contextlib.suppress(Exception):
                confluence_client.delete(f"/rest/api/template/{template['templateId']}")


@pytest.mark.integration
class TestUpdateTemplateLive:
    """Live tests for updating templates."""

    def test_update_template_content(self, confluence_client, test_space):
        """Test updating template content."""
        # Create template
        template_name = f"Update Test {uuid.uuid4().hex[:8]}"
        template = confluence_client.post(
            "/rest/api/template",
            json_data={
                "name": template_name,
                "templateType": "page",
                "space": {"key": test_space["key"]},
                "body": {
                    "storage": {
                        "value": "<p>Original.</p>",
                        "representation": "storage",
                    }
                },
            },
        )

        try:
            # Update
            updated = confluence_client.put(
                "/rest/api/template",
                json_data={
                    "templateId": template["templateId"],
                    "name": template_name,
                    "templateType": "page",
                    "space": {"key": test_space["key"]},
                    "body": {
                        "storage": {
                            "value": "<p>Updated content.</p>",
                            "representation": "storage",
                        }
                    },
                },
            )

            assert updated["templateId"] == template["templateId"]
        finally:
            with contextlib.suppress(Exception):
                confluence_client.delete(f"/rest/api/template/{template['templateId']}")
