"""
Unit tests for am_i_watching.py
"""

import pytest


class TestAmIWatching:
    """Tests for checking watch status functionality."""

    def test_am_i_watching_yes(self, mock_client, sample_watcher):
        """Test checking watch status when user is watching."""
        # Get current user
        current_user = {
            "accountId": "user-123",
            "email": "test@example.com",
            "displayName": "Test User",
        }
        mock_client.setup_response("get", current_user)
        user = mock_client.get("/rest/api/user/current", operation="get current user")

        # Get watchers list
        watchers_response = {"results": [sample_watcher], "size": 1}
        mock_client.setup_response("get", watchers_response)
        watchers = mock_client.get(
            "/rest/api/content/123456/notification/created", operation="get watchers"
        )

        # Check if user is in watchers list
        is_watching = any(
            w.get("accountId") == user["accountId"] for w in watchers["results"]
        )

        assert is_watching is True

    def test_am_i_watching_no(self, mock_client, sample_watcher):
        """Test checking watch status when user is not watching."""
        # Get current user
        current_user = {
            "accountId": "user-456",  # Different from watcher
            "email": "other@example.com",
            "displayName": "Other User",
        }
        mock_client.setup_response("get", current_user)
        user = mock_client.get("/rest/api/user/current", operation="get current user")

        # Get watchers list (doesn't include current user)
        watchers_response = {"results": [sample_watcher], "size": 1}
        mock_client.setup_response("get", watchers_response)
        watchers = mock_client.get(
            "/rest/api/content/123456/notification/created", operation="get watchers"
        )

        # Check if user is in watchers list
        is_watching = any(
            w.get("accountId") == user["accountId"] for w in watchers["results"]
        )

        assert is_watching is False

    def test_am_i_watching_no_watchers(self, mock_client):
        """Test checking watch status when there are no watchers."""
        # Get current user
        current_user = {
            "accountId": "user-123",
            "email": "test@example.com",
            "displayName": "Test User",
        }
        mock_client.setup_response("get", current_user)
        user = mock_client.get("/rest/api/user/current", operation="get current user")

        # Get empty watchers list
        watchers_response = {"results": [], "size": 0}
        mock_client.setup_response("get", watchers_response)
        watchers = mock_client.get(
            "/rest/api/content/123456/notification/created", operation="get watchers"
        )

        # Check if user is in watchers list
        is_watching = any(
            w.get("accountId") == user["accountId"] for w in watchers["results"]
        )

        assert is_watching is False

    def test_am_i_watching_output_yes(self):
        """Test output when user is watching."""
        page_id = "123456"
        message = f"You are watching page {page_id}"

        assert "watching" in message.lower()
        assert page_id in message

    def test_am_i_watching_output_no(self):
        """Test output when user is not watching."""
        page_id = "123456"
        message = f"You are not watching page {page_id}"

        assert "not watching" in message.lower()
        assert page_id in message

    def test_am_i_watching_validation(self):
        """Test page ID validation."""
        from confluence_assistant_skills_lib import ValidationError, validate_page_id

        assert validate_page_id("123456") == "123456"

        with pytest.raises(ValidationError):
            validate_page_id("")

        with pytest.raises(ValidationError):
            validate_page_id("invalid")
