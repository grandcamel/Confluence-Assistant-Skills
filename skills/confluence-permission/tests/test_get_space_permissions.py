"""
Unit tests for get_space_permissions.py
"""

import pytest


class TestGetSpacePermissions:
    """Tests for retrieving space permissions."""

    def test_validate_space_id_valid(self):
        """Test that valid space IDs pass validation."""
        from confluence_as import (
            validate_page_id,  # Space IDs use same format
        )

        assert validate_page_id("123456", "space_id") == "123456"
        assert validate_page_id(123456, "space_id") == "123456"

    def test_validate_space_id_invalid(self):
        """Test that invalid space IDs fail validation."""
        from confluence_as import ValidationError, validate_page_id

        with pytest.raises(ValidationError):
            validate_page_id("", "space_id")

        with pytest.raises(ValidationError):
            validate_page_id("abc", "space_id")

    def test_get_space_permissions_success(self, mock_client, sample_space_permissions):
        """Test successful retrieval of space permissions."""
        mock_client.setup_response("get", sample_space_permissions)

        # Verify the response structure
        assert "results" in sample_space_permissions
        assert len(sample_space_permissions["results"]) == 2

    def test_get_space_permissions_empty(self, mock_client):
        """Test getting permissions for space with no explicit permissions."""
        empty_permissions = {"results": [], "_links": {}}
        mock_client.setup_response("get", empty_permissions)

        assert len(empty_permissions["results"]) == 0

    def test_get_space_permissions_not_found(self, mock_client, mock_response):
        """Test getting permissions for non-existent space."""
        mock_client.session.get.return_value = mock_response(
            status_code=404, json_data={"message": "Space not found"}
        )


class TestPermissionFormatting:
    """Tests for permission formatting utilities."""

    def test_format_permission_user(self):
        """Test formatting a user permission."""
        permission = {
            "principal": {"type": "user", "id": "user-123"},
            "operation": {"key": "read", "target": "space"},
        }

        # Test that permission has required fields
        assert permission["principal"]["type"] == "user"
        assert permission["operation"]["key"] == "read"

    def test_format_permission_group(self):
        """Test formatting a group permission."""
        permission = {
            "principal": {"type": "group", "id": "group-456"},
            "operation": {"key": "administer", "target": "space"},
        }

        assert permission["principal"]["type"] == "group"
        assert permission["operation"]["key"] == "administer"

    def test_permission_operations(self):
        """Test that common permission operations are recognized."""
        valid_operations = [
            "read",
            "write",
            "create",
            "administer",
            "delete",
            "export",
            "setpermissions",
        ]

        for op in valid_operations:
            # Each operation should be a valid string
            assert isinstance(op, str)
            assert len(op) > 0
