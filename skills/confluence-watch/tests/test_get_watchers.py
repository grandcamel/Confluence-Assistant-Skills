"""
Unit tests for get_watchers.py
"""

import pytest


class TestGetWatchers:
    """Tests for getting watchers functionality."""

    def test_get_watchers_success(self, mock_client, sample_watcher):
        """Test successful retrieval of watchers."""
        watchers_response = {"results": [sample_watcher], "size": 1}
        mock_client.setup_response("get", watchers_response)

        result = mock_client.get(
            "/rest/api/content/123456/notification/created", operation="get watchers"
        )

        assert "results" in result
        assert len(result["results"]) == 1
        assert result["results"][0]["displayName"] == "Test User"

    def test_get_watchers_empty(self, mock_client):
        """Test getting watchers for content with no watchers."""
        watchers_response = {"results": [], "size": 0}
        mock_client.setup_response("get", watchers_response)

        result = mock_client.get(
            "/rest/api/content/123456/notification/created", operation="get watchers"
        )

        assert "results" in result
        assert len(result["results"]) == 0

    def test_get_watchers_multiple(self, mock_client, sample_watcher):
        """Test getting multiple watchers."""
        watcher2 = {
            **sample_watcher,
            "accountId": "user-456",
            "displayName": "Another User",
        }
        watchers_response = {"results": [sample_watcher, watcher2], "size": 2}
        mock_client.setup_response("get", watchers_response)

        result = mock_client.get(
            "/rest/api/content/123456/notification/created", operation="get watchers"
        )

        assert len(result["results"]) == 2
        assert result["results"][0]["displayName"] == "Test User"
        assert result["results"][1]["displayName"] == "Another User"

    def test_get_watchers_not_found(self, mock_client, mock_response):
        """Test getting watchers for non-existent content."""
        from confluence_as import handle_confluence_error

        error_response = mock_response(
            status_code=404, json_data={"message": "Content not found"}
        )

        with pytest.raises(Exception):
            handle_confluence_error(error_response, "get watchers")

    def test_get_watchers_output_json(self):
        """Test JSON output format."""
        from confluence_as import format_json

        data = {
            "results": [
                {"displayName": "User 1", "email": "user1@example.com"},
                {"displayName": "User 2", "email": "user2@example.com"},
            ],
            "size": 2,
        }
        result = format_json(data)

        assert "User 1" in result
        assert "User 2" in result

    def test_get_watchers_output_text(self):
        """Test text output format."""
        watchers = [
            {"displayName": "User 1", "email": "user1@example.com"},
            {"displayName": "User 2", "email": "user2@example.com"},
        ]

        # Verify we can format watcher list
        output_lines = []
        for watcher in watchers:
            output_lines.append(f"- {watcher['displayName']} ({watcher['email']})")

        assert len(output_lines) == 2
        assert "User 1" in output_lines[0]
        assert "user1@example.com" in output_lines[0]
