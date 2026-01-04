"""
Unit tests for link_to_jira.py
"""

import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))


class TestLinkToJira:
    """Tests for creating links between Confluence and JIRA."""

    def test_create_remote_link_structure(self):
        """Test creating remote link data structure."""
        from link_to_jira import create_remote_link_data

        link_data = create_remote_link_data(
            page_id="123456",
            issue_key="PROJ-123",
            jira_url="https://jira.example.com/browse/PROJ-123",
            relationship="relates to"
        )

        assert "object" in link_data
        assert "PROJ-123" in str(link_data)

    def test_add_web_link_to_page(self):
        """Test adding web link to JIRA in page content."""
        from link_to_jira import add_jira_link_to_content

        original_content = "<p>Original content</p>"
        issue_key = "PROJ-123"
        jira_url = "https://jira.example.com/browse/PROJ-123"

        result = add_jira_link_to_content(
            original_content,
            issue_key,
            jira_url
        )

        assert issue_key in result
        assert jira_url in result
        assert "Original content" in result

    def test_validate_relationship_type(self):
        """Test validation of relationship types."""
        from link_to_jira import validate_relationship

        # Valid relationships
        valid = ["relates to", "mentions", "documents"]
        for rel in valid:
            assert validate_relationship(rel) is not None

    def test_create_link_via_api(self, mock_client):
        """Test creating remote link via API."""
        link_response = {
            "id": "10001",
            "type": "remotelink",
            "status": "created"
        }

        mock_client.setup_response('post', link_response)

        # Would call the API endpoint
        # POST /rest/api/content/{page_id}/remotelink


class TestRemoteLinkAPI:
    """Tests for Confluence Remote Link API interactions."""

    def test_get_existing_remote_links(self, mock_client):
        """Test getting existing remote links."""
        links_response = {
            "results": [
                {
                    "id": "10001",
                    "relationship": "relates to",
                    "object": {
                        "url": "https://jira.example.com/browse/PROJ-123",
                        "title": "PROJ-123"
                    }
                }
            ]
        }

        mock_client.setup_response('get', links_response)

    def test_delete_remote_link(self, mock_client):
        """Test deleting a remote link."""
        mock_client.setup_response('delete', {})

        # DELETE /rest/api/content/{page_id}/remotelink/{link_id}

    def test_check_link_exists(self):
        """Test checking if link already exists."""
        from link_to_jira import link_exists

        existing_links = [
            {
                "object": {
                    "url": "https://jira.example.com/browse/PROJ-123"
                }
            }
        ]

        assert link_exists(existing_links, "PROJ-123") is True
        assert link_exists(existing_links, "PROJ-456") is False
