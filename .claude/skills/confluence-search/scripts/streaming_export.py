#!/usr/bin/env python3
"""
Export large search result sets with streaming and checkpoints.

Supports resuming interrupted exports.

Examples:
    python streaming_export.py "space = 'DOCS'" --output docs.csv
    python streaming_export.py "type = page" --output all_pages.json --format json
    python streaming_export.py "space = 'DOCS'" --output docs.csv --resume
"""

import sys
import argparse
import json
import csv
import time
from pathlib import Path
from datetime import datetime, timezone
from confluence_assistant_skills_lib import (
    get_confluence_client, handle_errors, ValidationError, validate_cql,
    validate_file_path, print_success, print_info, print_warning,
)


def get_checkpoint_path(output_file):
    """Get path to checkpoint file for given output file."""
    return Path(str(output_file) + '.checkpoint')

def load_checkpoint(output_file):
    """
    Load checkpoint data if exists.

    Args:
        output_file: Output file path

    Returns:
        Checkpoint dict or None
    """
    checkpoint_file = get_checkpoint_path(output_file)

    if not checkpoint_file.exists():
        return None

    try:
        return json.loads(checkpoint_file.read_text())
    except Exception as e:
        print_warning(f"Could not load checkpoint: {e}")
        return None

def save_checkpoint(output_file, cql, last_start, total_exported, batch_size, export_format):
    """
    Save checkpoint data.

    Args:
        output_file: Output file path
        cql: CQL query
        last_start: Last start position
        total_exported: Total records exported so far
        batch_size: Batch size
        export_format: Export format (csv or json)
    """
    checkpoint_file = get_checkpoint_path(output_file)

    checkpoint = {
        "output_file": str(output_file),
        "cql": cql,
        "last_start": last_start,
        "total_exported": total_exported,
        "batch_size": batch_size,
        "format": export_format,
        "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    }

    checkpoint_file.write_text(json.dumps(checkpoint, indent=2))

def delete_checkpoint(output_file):
    """Delete checkpoint file."""
    checkpoint_file = get_checkpoint_path(output_file)

    if checkpoint_file.exists():
        checkpoint_file.unlink()

def extract_record(result):
    """
    Extract record data from search result.

    Args:
        result: Search result item

    Returns:
        Dict of record data
    """
    # Handle both v1 search results and direct content
    content = result.get('content', result)

    record = {
        'id': content.get('id', ''),
        'type': content.get('type', ''),
        'title': content.get('title', ''),
    }

    # Space info
    space = content.get('space', {})
    if isinstance(space, dict):
        record['space'] = space.get('key', space.get('id', ''))
    else:
        record['space'] = str(space) if space else ''

    # Dates
    record['created'] = content.get('createdAt', content.get('created', ''))
    record['lastModified'] = result.get('lastModified', '')

    # URL
    links = content.get('_links', {})
    record['url'] = links.get('webui', '')

    # Excerpt (if available)
    record['excerpt'] = result.get('excerpt', '')

    return record

def export_batch_csv(records, output_file, columns, is_first_batch):
    """
    Export a batch of records to CSV.

    Args:
        records: List of record dicts
        output_file: Output file path
        columns: List of column names
        is_first_batch: Whether this is the first batch (write headers)
    """
    mode = 'w' if is_first_batch else 'a'

    with open(output_file, mode, newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')

        if is_first_batch:
            writer.writeheader()

        for record in records:
            writer.writerow(record)

def export_batch_json(records, output_file, is_first_batch, is_last_batch):
    """
    Export a batch of records to JSON.

    Args:
        records: List of record dicts
        output_file: Output file path
        is_first_batch: Whether this is the first batch
        is_last_batch: Whether this is the last batch
    """
    mode = 'w' if is_first_batch else 'a'

    with open(output_file, mode, encoding='utf-8') as f:
        if is_first_batch:
            f.write('[\n')

        for i, record in enumerate(records):
            if not is_first_batch and i == 0:
                f.write(',\n')
            elif i > 0:
                f.write(',\n')

            f.write('  ' + json.dumps(record, ensure_ascii=False))

        if is_last_batch:
            f.write('\n]\n')

@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description='Export large search result sets with streaming',
        epilog='''
Examples:
  # Export all pages in DOCS space to CSV
  python streaming_export.py "space = 'DOCS' AND type = page" --output docs.csv

  # Export to JSON
  python streaming_export.py "label = 'api'" --output api.json --format json

  # Resume interrupted export
  python streaming_export.py "space = 'DOCS'" --output docs.csv --resume

  # Custom batch size
  python streaming_export.py "type = page" --output pages.csv --batch-size 50
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('cql', help='CQL query')
    parser.add_argument('--output', '-o', required=True,
                        help='Output file path (CSV or JSON)')
    parser.add_argument('--format', '-f', choices=['csv', 'json'],
                        help='Output format (default: inferred from file extension)')
    parser.add_argument('--columns', help='Comma-separated list of columns for CSV')
    parser.add_argument('--batch-size', type=int, default=100,
                        help='Records per batch (default: 100)')
    parser.add_argument('--resume', action='store_true',
                        help='Resume from last checkpoint')
    parser.add_argument('--profile', help='Confluence profile to use')

    args = parser.parse_args(argv)

    # Determine format
    output_file = Path(args.output).resolve()
    export_format = args.format

    if not export_format:
        # Infer from extension
        ext = output_file.suffix.lower()
        if ext == '.json':
            export_format = 'json'
        elif ext == '.csv':
            export_format = 'csv'
        else:
            raise ValidationError(
                "Could not infer format from file extension. "
                "Use --format to specify 'csv' or 'json'"
            )

    # Validate batch size
    batch_size = max(10, min(args.batch_size, 250))
    if batch_size != args.batch_size:
        print_warning(f"Batch size adjusted to {batch_size} (valid range: 10-250)")

    # Parse columns
    if args.columns:
        columns = [c.strip() for c in args.columns.split(',')]
    else:
        # Default columns
        columns = ['id', 'type', 'title', 'space', 'created', 'lastModified', 'url']

    # Check for resume
    checkpoint = None
    if args.resume:
        checkpoint = load_checkpoint(output_file)

        if checkpoint:
            print_info(f"Resuming from checkpoint: {checkpoint['total_exported']} records exported")

            # Verify query matches
            if checkpoint['cql'] != args.cql:
                print_warning("CQL query differs from checkpoint. Starting fresh export.")
                checkpoint = None
        else:
            print_warning("No checkpoint found. Starting fresh export.")

    # Determine starting position
    if checkpoint:
        start = checkpoint['last_start'] + checkpoint['batch_size']
        total_exported = checkpoint['total_exported']
        cql = checkpoint['cql']
        is_first_batch = False
    else:
        start = 0
        total_exported = 0
        cql = validate_cql(args.cql)
        is_first_batch = True

        # Clear output file if starting fresh
        if output_file.exists() and not args.resume:
            print_warning(f"Output file exists. Will be overwritten.")

    # Get client
    client = get_confluence_client(profile=args.profile)

    print_info(f"Exporting results for: {cql}")
    print_info(f"Output: {output_file} ({export_format})")
    print_info(f"Batch size: {batch_size}")
    print()

    # Export loop
    start_time = time.time()
    batch_num = 0
    has_more = True

    try:
        while has_more:
            batch_num += 1

            # Fetch batch
            params = {
                'cql': cql,
                'limit': batch_size,
                'start': start,
                'expand': 'content.space'
            }

            response = client.get('/rest/api/search', params=params, operation='CQL search')

            results = response.get('results', [])

            if not results:
                has_more = False
                break

            # Extract records
            records = [extract_record(r) for r in results]

            # Export batch
            if export_format == 'csv':
                export_batch_csv(records, output_file, columns, is_first_batch)
            else:
                # Check if this is the last batch
                is_last_batch = len(results) < batch_size
                export_batch_json(records, output_file, is_first_batch, is_last_batch)

            # Update counters
            total_exported += len(records)
            start += len(results)
            is_first_batch = False

            # Save checkpoint
            save_checkpoint(output_file, cql, start, total_exported, batch_size, export_format)

            # Show progress
            elapsed = time.time() - start_time
            rate = total_exported / elapsed if elapsed > 0 else 0

            print_info(
                f"Batch {batch_num}: Exported {len(records)} records "
                f"(total: {total_exported}, rate: {rate:.1f} rec/sec)"
            )

            # Check if done
            if len(results) < batch_size:
                has_more = False

    except KeyboardInterrupt:
        print()
        print_warning("Export interrupted. Checkpoint saved.")
        print_info(f"Resume with: python streaming_export.py \"{cql}\" --output {output_file} --resume")
        sys.exit(1)

    except Exception as e:
        print_warning(f"Export failed: {e}")
        print_info("Checkpoint saved. You can resume the export.")
        raise

    # Success - delete checkpoint
    delete_checkpoint(output_file)

    # Final stats
    elapsed = time.time() - start_time
    print()
    print("="*60)
    print_success(f"Export complete: {total_exported} records")
    print_info(f"Output file: {output_file}")
    print_info(f"Format: {export_format}")
    print_info(f"Time: {elapsed:.1f} seconds")
    print_info(f"Rate: {total_exported/elapsed:.1f} records/second")
    print("="*60)

if __name__ == '__main__':
    main()
