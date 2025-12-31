#!/usr/bin/env python3
"""
Manage local CQL query history.

Examples:
    python cql_history.py list
    python cql_history.py list --limit 10
    python cql_history.py search "space = DOCS"
    python cql_history.py show 5
    python cql_history.py clear
    python cql_history.py export history.csv
"""

import sys
import argparse
import json
import csv
from pathlib import Path
from datetime import datetime, timedelta, timezone
from confluence_assistant_skills_lib import (
    handle_errors, ValidationError, print_success, print_info,
    print_warning, format_timestamp,
)


HISTORY_FILE = Path.home() / '.confluence_cql_history.json'
MAX_HISTORY_ENTRIES = 100

def load_history():
    """
    Load query history from file.

    Returns:
        List of history entries
    """
    if not HISTORY_FILE.exists():
        return []

    try:
        return json.loads(HISTORY_FILE.read_text())
    except json.JSONDecodeError as e:
        print_warning(f"History file corrupted: {e}")
        print_warning("Starting with empty history.")
        return []

def save_history(history):
    """
    Save query history to file.

    Args:
        history: List of history entries
    """
    # Keep only last MAX_HISTORY_ENTRIES
    history = history[-MAX_HISTORY_ENTRIES:]

    HISTORY_FILE.write_text(json.dumps(history, indent=2))

def add_entry(query, results_count=None, execution_time=None):
    """
    Add a query to history.

    Args:
        query: CQL query string
        results_count: Number of results (optional)
        execution_time: Execution time in seconds (optional)
    """
    history = load_history()

    # Don't add if same as last query
    if history and history[-1].get('query') == query:
        return

    entry = {
        'query': query,
        'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    }

    if results_count is not None:
        entry['results_count'] = results_count

    if execution_time is not None:
        entry['execution_time'] = execution_time

    history.append(entry)
    save_history(history)

def list_entries(limit=None):
    """
    List history entries.

    Args:
        limit: Maximum entries to show

    Returns:
        List of history entries (most recent first)
    """
    history = load_history()

    # Reverse for most recent first
    history = list(reversed(history))

    if limit:
        history = history[:limit]

    return history

def search_entries(keyword):
    """
    Search history for queries containing keyword.

    Args:
        keyword: Search keyword

    Returns:
        List of matching entries
    """
    history = load_history()

    keyword_lower = keyword.lower()
    matches = [e for e in history if keyword_lower in e['query'].lower()]

    # Return most recent first
    return list(reversed(matches))

def get_entry(index):
    """
    Get a specific history entry by index.

    Args:
        index: Entry index (1-based, from most recent)

    Returns:
        History entry dict
    """
    history = load_history()

    # Reverse for most recent first
    history = list(reversed(history))

    if index < 1 or index > len(history):
        raise ValidationError(f"Invalid index: {index}. Valid range: 1-{len(history)}")

    return history[index - 1]

def clear_history(confirm=True):
    """
    Clear all history.

    Args:
        confirm: Require confirmation
    """
    if confirm:
        response = input("Clear all query history? (y/n): ").strip().lower()
        if response != 'y':
            print("Cancelled.")
            return

    save_history([])
    print_success("History cleared")

def cleanup_old_entries(days=90):
    """
    Remove entries older than specified days.

    Args:
        days: Number of days to keep
    """
    history = load_history()

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat().replace('+00:00', 'Z')

    filtered = [e for e in history if e['timestamp'] >= cutoff]

    removed = len(history) - len(filtered)

    if removed > 0:
        save_history(filtered)
        print_success(f"Removed {removed} old entries (older than {days} days)")
    else:
        print_info("No old entries to remove")

def export_history(output_file, format='csv'):
    """
    Export history to file.

    Args:
        output_file: Output file path
        format: Export format (csv or json)
    """
    history = load_history()

    output_path = Path(output_file)

    if format == 'json':
        output_path.write_text(json.dumps(history, indent=2))

    elif format == 'csv':
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            # Determine all possible fields
            all_fields = set()
            for entry in history:
                all_fields.update(entry.keys())

            fields = ['timestamp', 'query', 'results_count', 'execution_time']
            fields = [f for f in fields if f in all_fields]

            writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
            writer.writeheader()

            for entry in history:
                writer.writerow(entry)

    print_success(f"Exported {len(history)} entries to {output_path}")

@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description='Manage CQL query history',
        epilog='''
Examples:
  # List recent queries
  python cql_history.py list
  python cql_history.py list --limit 10

  # Search history
  python cql_history.py search "space = DOCS"
  python cql_history.py search "label"

  # Show specific query
  python cql_history.py show 5

  # Clear history
  python cql_history.py clear

  # Export history
  python cql_history.py export history.csv
  python cql_history.py export history.json --format json

  # Cleanup old entries
  python cql_history.py cleanup --days 30
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('command',
                        choices=['list', 'search', 'show', 'clear', 'export', 'cleanup'],
                        help='Command to execute')
    parser.add_argument('argument', nargs='?',
                        help='Command argument (search term, index, or file path)')
    parser.add_argument('--limit', '-l', type=int,
                        help='Limit number of entries shown')
    parser.add_argument('--format', '-f', choices=['csv', 'json'], default='csv',
                        help='Export format (default: csv)')
    parser.add_argument('--days', type=int, default=90,
                        help='Days to keep for cleanup (default: 90)')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')

    args = parser.parse_args(argv)

    # List entries
    if args.command == 'list':
        entries = list_entries(limit=args.limit)

        if not entries:
            print("No query history found.")
            return

        if args.output == 'json':
            print(json.dumps(entries, indent=2))
        else:
            print(f"\nQuery History ({len(entries)} entries):\n")

            for i, entry in enumerate(entries, 1):
                query = entry['query']
                timestamp = format_timestamp(entry['timestamp'])
                results = entry.get('results_count', '?')

                print(f"{i:3}. [{timestamp}] {query}")
                print(f"     Results: {results}")

                if 'execution_time' in entry:
                    print(f"     Time: {entry['execution_time']:.2f}s")

                print()

    # Search entries
    elif args.command == 'search':
        if not args.argument:
            raise ValidationError("Search requires a keyword argument")

        matches = search_entries(args.argument)

        if not matches:
            print(f"No queries found matching: {args.argument}")
            return

        if args.output == 'json':
            print(json.dumps(matches, indent=2))
        else:
            print(f"\nFound {len(matches)} matching queries:\n")

            for i, entry in enumerate(matches, 1):
                query = entry['query']
                timestamp = format_timestamp(entry['timestamp'])

                print(f"{i}. [{timestamp}] {query}")

            print()

    # Show specific entry
    elif args.command == 'show':
        if not args.argument:
            raise ValidationError("Show requires an index argument")

        try:
            index = int(args.argument)
        except ValueError:
            raise ValidationError("Index must be a number")

        entry = get_entry(index)

        if args.output == 'json':
            print(json.dumps(entry, indent=2))
        else:
            print("\nQuery Details:\n")
            print("="*60)
            print(f"Query:     {entry['query']}")
            print(f"Timestamp: {format_timestamp(entry['timestamp'])}")

            if 'results_count' in entry:
                print(f"Results:   {entry['results_count']}")

            if 'execution_time' in entry:
                print(f"Time:      {entry['execution_time']:.2f}s")

            print("="*60)
            print()

            # Offer to copy/re-execute
            print("To re-execute this query:")
            print(f'  python cql_search.py "{entry["query"]}"')
            print()

    # Clear history
    elif args.command == 'clear':
        clear_history(confirm=True)

    # Export history
    elif args.command == 'export':
        if not args.argument:
            raise ValidationError("Export requires an output file path")

        export_history(args.argument, format=args.format)

    # Cleanup old entries
    elif args.command == 'cleanup':
        cleanup_old_entries(days=args.days)

if __name__ == '__main__':
    main()
