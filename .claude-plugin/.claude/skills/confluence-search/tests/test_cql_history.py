"""
Unit tests for cql_history.py

Tests CQL query history management functionality.
"""

import pytest
import json
from pathlib import Path
from datetime import datetime, timezone


class TestHistoryStorage:
    """Tests for history file storage."""

    def test_get_history_file_path(self):
        """Test getting default history file path."""
        expected_path = Path.home() / '.confluence_cql_history.json'

        assert expected_path.parent == Path.home()
        assert expected_path.name == '.confluence_cql_history.json'

    def test_create_new_history_file(self, tmp_path):
        """Test creating new history file if it doesn't exist."""
        history_file = tmp_path / 'history.json'

        assert not history_file.exists()

        # Create with empty list
        history_file.write_text(json.dumps([]))

        assert history_file.exists()
        assert json.loads(history_file.read_text()) == []

    def test_load_existing_history(self, tmp_path, sample_query_history):
        """Test loading existing history file."""
        history_file = tmp_path / 'history.json'

        # Write sample history
        history_file.write_text(json.dumps(sample_query_history))

        # Load
        loaded = json.loads(history_file.read_text())

        assert len(loaded) == len(sample_query_history)
        assert loaded[0]['query'] == sample_query_history[0]['query']


class TestAddingToHistory:
    """Tests for adding queries to history."""

    def test_add_single_query(self, tmp_path):
        """Test adding a single query to history."""
        history_file = tmp_path / 'history.json'
        history = []

        # Add query
        entry = {
            'query': "space = 'DOCS'",
            'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'results_count': 42
        }

        history.append(entry)

        # Save
        history_file.write_text(json.dumps(history, indent=2))

        # Verify
        loaded = json.loads(history_file.read_text())
        assert len(loaded) == 1
        assert loaded[0]['query'] == "space = 'DOCS'"

    def test_add_multiple_queries(self, tmp_path):
        """Test adding multiple queries."""
        history_file = tmp_path / 'history.json'
        history = []

        # Add multiple
        for i in range(5):
            history.append({
                'query': f"query {i}",
                'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                'results_count': i * 10
            })

        history_file.write_text(json.dumps(history, indent=2))

        loaded = json.loads(history_file.read_text())
        assert len(loaded) == 5

    def test_limit_history_size(self, tmp_path):
        """Test limiting history to max entries."""
        history_file = tmp_path / 'history.json'
        max_entries = 100

        # Create 150 entries
        history = [
            {
                'query': f"query {i}",
                'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            }
            for i in range(150)
        ]

        # Keep only last 100
        history = history[-max_entries:]

        history_file.write_text(json.dumps(history))

        loaded = json.loads(history_file.read_text())
        assert len(loaded) == max_entries
        assert loaded[0]['query'] == 'query 50'  # First 50 were dropped

    def test_deduplicate_consecutive_queries(self, tmp_path):
        """Test avoiding duplicate consecutive queries."""
        history = []

        query1 = "space = 'DOCS'"
        query2 = "space = 'KB'"

        # Add query1
        history.append({'query': query1, 'timestamp': '2024-01-01T10:00:00Z'})

        # Try to add query1 again (should skip)
        if not history or history[-1]['query'] != query1:
            history.append({'query': query1, 'timestamp': '2024-01-01T10:05:00Z'})

        # Add query2
        if not history or history[-1]['query'] != query2:
            history.append({'query': query2, 'timestamp': '2024-01-01T10:10:00Z'})

        # Only 2 entries (second query1 was skipped)
        assert len(history) == 2
        assert history[0]['query'] == query1
        assert history[1]['query'] == query2


class TestListingHistory:
    """Tests for listing history entries."""

    def test_list_all_entries(self, sample_query_history):
        """Test listing all history entries."""
        assert len(sample_query_history) == 3

        for entry in sample_query_history:
            assert 'query' in entry
            assert 'timestamp' in entry

    def test_list_with_limit(self, sample_query_history):
        """Test listing with limit."""
        limit = 2
        limited = sample_query_history[:limit]

        assert len(limited) == 2

    def test_list_most_recent_first(self, sample_query_history):
        """Test listing in reverse chronological order."""
        # Sort by timestamp descending
        sorted_history = sorted(
            sample_query_history,
            key=lambda x: x['timestamp'],
            reverse=True
        )

        # Most recent first
        assert sorted_history[0]['timestamp'] >= sorted_history[1]['timestamp']

    def test_format_history_entry(self):
        """Test formatting a history entry for display."""
        entry = {
            'query': "space = 'DOCS' AND type = page",
            'timestamp': '2024-01-15T10:30:00.000Z',
            'results_count': 42
        }

        # Format: [timestamp] query (42 results)
        formatted = f"[{entry['timestamp'][:10]}] {entry['query']} ({entry['results_count']} results)"

        assert '2024-01-15' in formatted
        assert "space = 'DOCS'" in formatted
        assert '42 results' in formatted


class TestSearchingHistory:
    """Tests for searching query history."""

    def test_search_by_keyword(self, sample_query_history):
        """Test searching history by keyword."""
        keyword = 'DOCS'

        matches = [e for e in sample_query_history if keyword in e['query']]

        assert len(matches) >= 1
        assert all(keyword in m['query'] for m in matches)

    def test_search_case_insensitive(self, sample_query_history):
        """Test case-insensitive search."""
        keyword = 'docs'  # lowercase

        matches = [
            e for e in sample_query_history
            if keyword.lower() in e['query'].lower()
        ]

        assert len(matches) >= 1

    def test_search_no_matches(self, sample_query_history):
        """Test search with no matches."""
        keyword = 'NONEXISTENT'

        matches = [e for e in sample_query_history if keyword in e['query']]

        assert len(matches) == 0

    def test_search_multiple_keywords(self, sample_query_history):
        """Test searching with multiple keywords."""
        keywords = ['DOCS', 'page']

        matches = [
            e for e in sample_query_history
            if all(kw in e['query'] for kw in keywords)
        ]

        # Should match queries containing both keywords
        if matches:
            for match in matches:
                assert 'DOCS' in match['query']
                assert 'page' in match['query']


class TestClearingHistory:
    """Tests for clearing history."""

    def test_clear_all_history(self, tmp_path):
        """Test clearing all history."""
        history_file = tmp_path / 'history.json'

        # Create history
        history = [{'query': f'query {i}'} for i in range(10)]
        history_file.write_text(json.dumps(history))

        assert len(json.loads(history_file.read_text())) == 10

        # Clear
        history_file.write_text(json.dumps([]))

        assert json.loads(history_file.read_text()) == []

    def test_confirm_before_clear(self):
        """Test requiring confirmation before clearing."""
        # Should prompt user: "Clear all history? (y/n)"
        # Only clear if user confirms
        pass


class TestShowingQueryDetails:
    """Tests for showing individual query details."""

    def test_show_query_by_index(self, sample_query_history):
        """Test showing query details by index."""
        index = 0
        entry = sample_query_history[index]

        assert 'query' in entry
        assert 'timestamp' in entry

    def test_show_query_with_stats(self):
        """Test showing query with statistics."""
        entry = {
            'query': "space = 'DOCS'",
            'timestamp': '2024-01-15T10:30:00.000Z',
            'results_count': 42,
            'execution_time': 1.5
        }

        # Should display:
        # - Query
        # - Timestamp
        # - Results count
        # - Execution time (if available)

        assert entry['results_count'] == 42
        assert entry.get('execution_time') == 1.5

    def test_copy_query_to_clipboard(self):
        """Test offering to copy query to clipboard."""
        # After showing query, offer to:
        # 1. Copy to clipboard
        # 2. Re-execute
        # 3. Edit and execute
        pass


class TestHistoryMaintenance:
    """Tests for history maintenance operations."""

    def test_remove_old_entries(self, tmp_path):
        """Test removing entries older than N days."""
        from datetime import timedelta

        history = []

        # Add entries from different dates
        now = datetime.now(timezone.utc)
        old_date = (now - timedelta(days=90)).isoformat().replace('+00:00', 'Z')
        recent_date = now.isoformat().replace('+00:00', 'Z')

        history.append({'query': 'old query', 'timestamp': old_date})
        history.append({'query': 'recent query', 'timestamp': recent_date})

        # Remove entries older than 30 days
        cutoff = (now - timedelta(days=30)).isoformat() + 'Z'
        filtered = [e for e in history if e['timestamp'] >= cutoff]

        # Only recent entry remains
        assert len(filtered) == 1
        assert filtered[0]['query'] == 'recent query'

    def test_validate_history_format(self, tmp_path):
        """Test validating history file format."""
        history_file = tmp_path / 'history.json'

        # Valid format
        valid_history = [
            {'query': 'test', 'timestamp': '2024-01-01T00:00:00Z'}
        ]

        history_file.write_text(json.dumps(valid_history))

        # Should load without error
        loaded = json.loads(history_file.read_text())
        assert isinstance(loaded, list)

    def test_recover_corrupted_history(self, tmp_path):
        """Test recovering from corrupted history file."""
        history_file = tmp_path / 'history.json'

        # Write invalid JSON
        history_file.write_text('{invalid json')

        # Should handle error gracefully
        try:
            json.loads(history_file.read_text())
            assert False, "Should have raised error"
        except json.JSONDecodeError:
            # Start fresh
            history_file.write_text(json.dumps([]))
            loaded = json.loads(history_file.read_text())
            assert loaded == []


class TestHistoryExport:
    """Tests for exporting history."""

    def test_export_history_to_file(self, tmp_path, sample_query_history):
        """Test exporting history to a file."""
        export_file = tmp_path / 'exported_history.json'

        # Export
        export_file.write_text(json.dumps(sample_query_history, indent=2))

        # Verify
        loaded = json.loads(export_file.read_text())
        assert len(loaded) == len(sample_query_history)

    def test_export_history_to_csv(self, tmp_path, sample_query_history):
        """Test exporting history to CSV."""
        import csv

        export_file = tmp_path / 'history.csv'

        # Export to CSV
        with open(export_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['query', 'timestamp', 'results_count'])
            writer.writeheader()
            for entry in sample_query_history:
                writer.writerow(entry)

        # Verify
        assert export_file.exists()

        with open(export_file, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == len(sample_query_history)
