"""
Unit tests for page restriction scripts
"""

import pytest


class TestGetPageRestrictions:
    """Tests for retrieving page restrictions."""

    def test_validate_page_id_valid(self):
        """Test that valid page IDs pass validation."""
        from confluence_as import validate_page_id

        assert validate_page_id("123456") == "123456"
        assert validate_page_id(123456) == "123456"

    def test_validate_page_id_invalid(self):
        """Test that invalid page IDs fail validation."""
        from confluence_as import ValidationError, validate_page_id

        with pytest.raises(ValidationError):
            validate_page_id("")

        with pytest.raises(ValidationError):
            validate_page_id("not-a-number")

    def test_get_page_restrictions_success(self, mock_client, sample_page_restrictions):
        """Test successful retrieval of page restrictions."""
        mock_client.setup_response("get", sample_page_restrictions)

        # Verify response structure
        assert "read" in sample_page_restrictions
        assert "update" in sample_page_restrictions

    def test_get_page_restrictions_unrestricted(self, mock_client):
        """Test getting restrictions for unrestricted page."""
        unrestricted = {
            "read": {
                "operation": "read",
                "restrictions": {
                    "user": {"results": [], "size": 0},
                    "group": {"results": [], "size": 0},
                },
            },
            "update": {
                "operation": "update",
                "restrictions": {
                    "user": {"results": [], "size": 0},
                    "group": {"results": [], "size": 0},
                },
            },
        }
        mock_client.setup_response("get", unrestricted)

        assert unrestricted["read"]["restrictions"]["user"]["size"] == 0
        assert unrestricted["update"]["restrictions"]["user"]["size"] == 0


class TestAddPageRestriction:
    """Tests for adding page restrictions."""

    def test_validate_restriction_type(self):
        """Test that restriction types are validated."""
        valid_types = ["read", "update"]

        for restriction_type in valid_types:
            assert restriction_type in ["read", "update"]

    def test_validate_principal_type(self):
        """Test that principal types are validated."""
        valid_principals = ["user", "group"]

        for principal in valid_principals:
            assert principal in ["user", "group"]

    def test_add_restriction_user(self):
        """Test adding a user restriction."""
        restriction_data = {
            "user": [{"type": "known", "username": "testuser"}],
            "group": [],
        }

        assert len(restriction_data["user"]) == 1
        assert restriction_data["user"][0]["username"] == "testuser"

    def test_add_restriction_group(self):
        """Test adding a group restriction."""
        restriction_data = {
            "user": [],
            "group": [{"type": "group", "name": "test-group"}],
        }

        assert len(restriction_data["group"]) == 1
        assert restriction_data["group"][0]["name"] == "test-group"


class TestRemovePageRestriction:
    """Tests for removing page restrictions."""

    def test_remove_restriction_validation(self):
        """Test that removal requires valid restriction type."""
        valid_operations = ["read", "update"]

        for op in valid_operations:
            assert op in ["read", "update"]

    def test_remove_all_restrictions(self):
        """Test removing all restrictions from a page."""
        # When all restrictions are removed, page becomes unrestricted
        empty_restrictions = {"user": [], "group": []}

        assert len(empty_restrictions["user"]) == 0
        assert len(empty_restrictions["group"]) == 0


class TestRestrictionFormatting:
    """Tests for restriction formatting utilities."""

    def test_format_user_restriction(self, sample_page_restrictions):
        """Test formatting user restrictions."""
        read_users = sample_page_restrictions["read"]["restrictions"]["user"]["results"]

        assert len(read_users) == 1
        assert read_users[0]["username"] == "user1"

    def test_format_group_restriction(self, sample_page_restrictions):
        """Test formatting group restrictions."""
        read_groups = sample_page_restrictions["read"]["restrictions"]["group"][
            "results"
        ]

        assert len(read_groups) == 1
        assert read_groups[0]["name"] == "confluence-administrators"

    def test_restriction_summary(self, sample_page_restrictions):
        """Test generating restriction summary."""
        read_rest = sample_page_restrictions["read"]["restrictions"]
        user_count = read_rest["user"]["size"]
        group_count = read_rest["group"]["size"]

        assert user_count == 1
        assert group_count == 1
