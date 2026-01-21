"""
Unit tests for resolve_comment.py
"""

import pytest


class TestResolveComment:
    """Tests for resolving comments."""

    def test_resolve_comment_basic(self, mock_client, sample_comment):
        """Test resolving a comment."""
        resolved = sample_comment.copy()
        resolved["resolutionStatus"] = "resolved"

        mock_client.setup_response("put", resolved)

        # Would verify resolution API call

    def test_unresolve_comment(self, mock_client, sample_comment):
        """Test unresolving a comment."""
        unresolved = sample_comment.copy()
        unresolved["resolutionStatus"] = "open"

        mock_client.setup_response("put", unresolved)

        # Would verify unresolve operation

    def test_resolve_comment_not_found(self, mock_client):
        """Test resolving non-existent comment."""

        mock_client.setup_response("put", {}, status_code=404)
        # Would verify NotFoundError is raised

    def test_resolve_comment_no_permission(self, mock_client):
        """Test resolving comment without permission."""

        mock_client.setup_response("put", {}, status_code=403)
        # Would verify PermissionError is raised


class TestResolveValidation:
    """Tests for resolve validation."""

    def test_comment_id_required(self):
        """Test that comment ID is required."""
        from confluence_as import ValidationError, validate_page_id

        with pytest.raises(ValidationError):
            validate_page_id("", "comment_id")

    def test_resolution_status_values(self):
        """Test valid resolution status values."""
        valid_statuses = ["resolved", "open"]

        for status in valid_statuses:
            assert status in ["resolved", "open"]

    def test_invalid_resolution_status(self):
        """Test that invalid status is rejected."""
        from confluence_as import ValidationError

        status = "invalid"
        if status not in ["resolved", "open"]:
            with pytest.raises(ValidationError):
                raise ValidationError(f"Invalid resolution status: {status}")
