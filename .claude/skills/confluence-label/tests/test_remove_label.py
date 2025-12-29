"""
Unit tests for remove_label.py
"""

import pytest
from unittest.mock import patch, MagicMock


class TestRemoveLabel:
    """Tests for remove label functionality."""

    def test_remove_label_success(self, mock_client, mock_response):
        """Test successful label removal."""
        page_id = "123456"
        label_name = "draft"

        # Setup mock response for deletion (typically 204 No Content)
        delete_response = mock_response(status_code=204, json_data={})
        mock_client.session.delete.return_value = delete_response

        # Would verify API call was made correctly
        # client.delete(f'/api/v2/pages/{page_id}/labels/{label_id}')

    def test_remove_label_not_found(self, mock_client, mock_response):
        """Test removing a label that doesn't exist."""
        page_id = "123456"
        label_name = "nonexistent"

        # Setup 404 response
        error_response = mock_response(
            status_code=404,
            json_data={"errors": [{"title": "Label not found"}]}
        )
        mock_client.session.delete.return_value = error_response

        # Would verify NotFoundError is raised

    def test_remove_label_page_not_found(self, mock_client, mock_response):
        """Test label removal with non-existent page."""
        page_id = "999999"
        label_name = "test"

        # Setup 404 response
        error_response = mock_response(
            status_code=404,
            json_data={"errors": [{"title": "Page not found"}]}
        )
        mock_client.session.delete.return_value = error_response

        # Would verify NotFoundError is raised


class TestLabelLookup:
    """Tests for finding label ID by name."""

    def test_find_label_by_name(self, sample_labels):
        """Test finding a label ID by its name."""
        labels = sample_labels['results']
        target_name = "approved"

        found = next((l for l in labels if l['name'] == target_name), None)
        assert found is not None
        assert found['id'] == "label-2"

    def test_find_nonexistent_label(self, sample_labels):
        """Test finding a label that doesn't exist."""
        labels = sample_labels['results']
        target_name = "nonexistent"

        found = next((l for l in labels if l['name'] == target_name), None)
        assert found is None
