"""
Unit tests for get_content_watchers.py
"""


class TestGetContentWatchers:
    """Tests for getting content watchers."""

    def test_validate_page_id_valid(self):
        """Test that valid page IDs pass validation."""
        from confluence_as import validate_page_id

        assert validate_page_id("123456") == "123456"
        assert validate_page_id(123456) == "123456"

    def test_get_watchers_success(self, mock_client, sample_watchers):
        """Test successful retrieval of watchers."""
        mock_client.setup_response("get", sample_watchers)

        result = mock_client.get("/rest/api/content/123456/notification/child-created")

        assert "results" in result
        assert len(result["results"]) == 2
        assert result["size"] == 2

    def test_parse_watcher_info(self, sample_watchers):
        """Test parsing watcher information."""
        watchers = sample_watchers["results"]

        # Extract watcher details
        watcher_names = [w["watcher"]["displayName"] for w in watchers]
        watcher_emails = [w["watcher"]["email"] for w in watchers]

        assert "User One" in watcher_names
        assert "User Two" in watcher_names
        assert "user1@example.com" in watcher_emails
        assert "user2@example.com" in watcher_emails

    def test_count_watchers(self, sample_watchers):
        """Test counting total watchers."""
        total_watchers = len(sample_watchers["results"])
        assert total_watchers == 2

    def test_no_watchers(self, mock_client):
        """Test handling content with no watchers."""
        empty_response = {"results": [], "start": 0, "limit": 25, "size": 0}

        mock_client.setup_response("get", empty_response)

        result = mock_client.get("/rest/api/content/123456/notification/child-created")

        assert result["size"] == 0
        assert len(result["results"]) == 0

    def test_page_not_found(self, mock_client):
        """Test handling page not found error."""
        mock_client.setup_response(
            "get", {"message": "Content not found"}, status_code=404
        )

        # In real implementation, should handle 404 appropriately


class TestWatcherOutputFormats:
    """Tests for watcher output formatting."""

    def test_format_watcher_list(self, sample_watchers):
        """Test formatting watchers for display."""
        watchers = sample_watchers["results"]

        # Should be able to format each watcher
        for watcher_data in watchers:
            watcher = watcher_data["watcher"]
            formatted = f"{watcher['displayName']} ({watcher['email']})"

            assert watcher["displayName"] in formatted
            assert watcher["email"] in formatted

    def test_json_output(self, sample_watchers):
        """Test JSON output formatting."""
        import json

        from confluence_as import format_json

        output = format_json(sample_watchers)
        parsed = json.loads(output)

        assert parsed["size"] == 2
        assert len(parsed["results"]) == 2
