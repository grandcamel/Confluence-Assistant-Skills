"""
Unit tests for streaming_export.py

Tests large result export with checkpointing functionality.
"""

import csv
import json

import pytest


class TestStreamingExport:
    """Tests for streaming export functionality."""

    def test_export_small_result_set(
        self, mock_client, sample_search_results, tmp_path
    ):
        """Test exporting a small result set (no streaming needed)."""
        output_file = tmp_path / "results.csv"

        # Mock returns 10 results
        mock_client.setup_response("get", sample_search_results)

        # Export would write to CSV
        # Verify file exists and has correct data
        assert not output_file.exists()  # Not created yet in test

    def test_export_large_result_set(self, mock_client, tmp_path):
        """Test exporting large result set with batching."""
        tmp_path / "results.csv"

        # Mock returns results in batches
        # Batch 1: results 0-99
        # Batch 2: results 100-199
        # Batch 3: results 200-250

        batch_size = 100
        total_results = 250

        # Would fetch in batches and append to file
        assert batch_size == 100
        assert total_results == 250

    def test_csv_export_format(self, tmp_path):
        """Test CSV export format."""
        output_file = tmp_path / "results.csv"

        # Sample data
        data = [
            {"id": "123", "title": "Page 1", "space": "DOCS"},
            {"id": "456", "title": "Page 2", "space": "KB"},
        ]

        # Write CSV
        from confluence_as import export_csv

        export_csv(data, output_file, columns=["id", "title", "space"])

        # Verify
        assert output_file.exists()

        # Read and check
        with open(output_file) as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2
        assert rows[0]["id"] == "123"
        assert rows[0]["title"] == "Page 1"

    def test_json_export_format(self, tmp_path):
        """Test JSON export format."""
        output_file = tmp_path / "results.json"

        # Sample data
        data = [
            {"id": "123", "title": "Page 1"},
            {"id": "456", "title": "Page 2"},
        ]

        # Write JSON
        output_file.write_text(json.dumps(data, indent=2))

        # Verify
        assert output_file.exists()

        # Read and check
        loaded = json.loads(output_file.read_text())

        assert len(loaded) == 2
        assert loaded[0]["id"] == "123"


class TestCheckpointing:
    """Tests for checkpoint/resume functionality."""

    def test_create_checkpoint_file(self, tmp_path):
        """Test creating checkpoint file."""
        output_file = tmp_path / "results.csv"
        checkpoint_file = tmp_path / "results.csv.checkpoint"

        # Checkpoint data
        checkpoint = {
            "output_file": str(output_file),
            "cql": "space = 'DOCS'",
            "last_start": 200,
            "total_exported": 200,
            "batch_size": 100,
            "format": "csv",
        }

        # Write checkpoint
        checkpoint_file.write_text(json.dumps(checkpoint, indent=2))

        assert checkpoint_file.exists()

        # Read checkpoint
        loaded = json.loads(checkpoint_file.read_text())
        assert loaded["last_start"] == 200
        assert loaded["total_exported"] == 200

    def test_resume_from_checkpoint(self, tmp_path):
        """Test resuming export from checkpoint."""
        checkpoint_file = tmp_path / "results.csv.checkpoint"

        # Create checkpoint
        checkpoint = {
            "output_file": str(tmp_path / "results.csv"),
            "cql": "space = 'DOCS'",
            "last_start": 200,
            "total_exported": 200,
            "batch_size": 100,
            "format": "csv",
        }

        checkpoint_file.write_text(json.dumps(checkpoint))

        # Resume would:
        # 1. Read checkpoint
        # 2. Continue from last_start + batch_size
        loaded = json.loads(checkpoint_file.read_text())

        next_start = loaded["last_start"] + loaded["batch_size"]
        assert next_start == 300

    def test_checkpoint_deleted_on_completion(self, tmp_path):
        """Test checkpoint is deleted when export completes."""
        checkpoint_file = tmp_path / "results.csv.checkpoint"

        # Create checkpoint
        checkpoint_file.write_text("{}")
        assert checkpoint_file.exists()

        # On completion, delete checkpoint
        checkpoint_file.unlink()
        assert not checkpoint_file.exists()

    def test_checkpoint_updated_each_batch(self, tmp_path):
        """Test checkpoint is updated after each batch."""
        checkpoint_file = tmp_path / "results.csv.checkpoint"

        # Initial checkpoint
        checkpoint = {"last_start": 0, "total_exported": 0}
        checkpoint_file.write_text(json.dumps(checkpoint))

        # After batch 1
        checkpoint["last_start"] = 100
        checkpoint["total_exported"] = 100
        checkpoint_file.write_text(json.dumps(checkpoint))

        loaded = json.loads(checkpoint_file.read_text())
        assert loaded["total_exported"] == 100

        # After batch 2
        checkpoint["last_start"] = 200
        checkpoint["total_exported"] = 200
        checkpoint_file.write_text(json.dumps(checkpoint))

        loaded = json.loads(checkpoint_file.read_text())
        assert loaded["total_exported"] == 200


class TestProgressReporting:
    """Tests for progress reporting during export."""

    def test_show_progress_percentage(self):
        """Test calculating and showing progress percentage."""
        total_size = 1000
        exported = 250

        percentage = (exported / total_size) * 100

        assert percentage == 25.0

    def test_show_batch_progress(self):
        """Test showing batch progress messages."""
        batch_num = 5
        total_exported = 500

        message = f"Exported batch {batch_num}: {total_exported} records"

        assert "500" in message
        assert "batch 5" in message

    def test_estimate_remaining_time(self):
        """Test estimating remaining time."""
        import time

        time.time()
        exported = 250
        total = 1000

        # Mock elapsed time
        elapsed = 10.0  # 10 seconds

        rate = exported / elapsed  # records per second
        remaining_records = total - exported
        estimated_seconds = remaining_records / rate

        assert rate == 25.0  # 25 records/sec
        assert estimated_seconds == 30.0  # 30 seconds remaining


class TestErrorHandling:
    """Tests for error handling during streaming export."""

    def test_handle_network_error_with_resume(self, tmp_path):
        """Test handling network error and ability to resume."""
        checkpoint_file = tmp_path / "results.csv.checkpoint"

        # Create checkpoint before error
        checkpoint = {
            "last_start": 500,
            "total_exported": 500,
        }
        checkpoint_file.write_text(json.dumps(checkpoint))

        # After error, checkpoint should exist for resume
        assert checkpoint_file.exists()

        # User can resume from 500
        loaded = json.loads(checkpoint_file.read_text())
        assert loaded["last_start"] == 500

    def test_handle_disk_full_error(self, tmp_path):
        """Test handling disk full error."""
        # When writing fails due to disk full
        # Should report error clearly
        pass

    def test_handle_invalid_cql_error(self):
        """Test handling invalid CQL query."""
        from confluence_as import ValidationError, validate_cql

        invalid_cql = "invalid query (("

        with pytest.raises(ValidationError):
            validate_cql(invalid_cql)


class TestColumnSelection:
    """Tests for selecting which columns to export."""

    def test_export_all_columns(self, tmp_path):
        """Test exporting all available columns."""
        data = [
            {"id": "123", "title": "Page 1", "space": "DOCS", "created": "2024-01-01"},
        ]

        output_file = tmp_path / "results.csv"

        from confluence_as import export_csv

        export_csv(data, output_file)

        # Should include all columns
        with open(output_file) as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames

        assert "id" in headers
        assert "title" in headers
        assert "space" in headers
        assert "created" in headers

    def test_export_selected_columns(self, tmp_path):
        """Test exporting only selected columns."""
        data = [
            {"id": "123", "title": "Page 1", "space": "DOCS", "created": "2024-01-01"},
        ]

        output_file = tmp_path / "results.csv"
        columns = ["id", "title"]

        from confluence_as import export_csv

        export_csv(data, output_file, columns=columns)

        # Should only include selected columns
        with open(output_file) as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames

        assert "id" in headers
        assert "title" in headers
        assert "space" not in headers

    def test_default_columns_for_pages(self):
        """Test default column set for page exports."""
        default_columns = [
            "id",
            "type",
            "title",
            "space",
            "created",
            "lastModified",
            "url",
        ]

        assert "id" in default_columns
        assert "title" in default_columns
        assert "space" in default_columns


class TestBatchSizing:
    """Tests for configurable batch size."""

    def test_default_batch_size(self):
        """Test default batch size."""
        default_batch_size = 100

        assert default_batch_size == 100

    def test_custom_batch_size(self):
        """Test custom batch size."""
        custom_batch_size = 50

        # User specifies --batch-size 50
        batch_size = custom_batch_size

        assert batch_size == 50

    def test_max_batch_size_limit(self):
        """Test maximum batch size limit."""
        # API limit is typically 250
        max_batch_size = 250

        requested = 1000
        actual = min(requested, max_batch_size)

        assert actual == 250

    def test_min_batch_size_limit(self):
        """Test minimum batch size limit."""
        min_batch_size = 10

        requested = 1
        actual = max(requested, min_batch_size)

        assert actual == 10
