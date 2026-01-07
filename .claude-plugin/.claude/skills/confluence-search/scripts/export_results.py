#!/usr/bin/env python3
"""
Export search results to file.

Examples:
    python export_results.py "space = 'DOCS'" --format csv --output results.csv
    python export_results.py "label = 'api'" --format json --output results.json
"""

import argparse
import csv
import json
from pathlib import Path

from confluence_assistant_skills_lib import (
    get_confluence_client,
    handle_errors,
    print_info,
    print_success,
    validate_cql,
    validate_limit,
)

DEFAULT_COLUMNS = ["id", "title", "type", "space", "created", "lastModified", "url"]


def extract_field(result: dict, field: str) -> str:
    """Extract a field value from a search result."""
    content = result.get("content", result)

    if field == "id":
        return str(content.get("id", ""))
    elif field == "title":
        return content.get("title", "")
    elif field == "type":
        return content.get("type", "")
    elif field == "space":
        space = content.get("space", {})
        return space.get("key", content.get("spaceId", ""))
    elif field == "created":
        history = content.get("history", {})
        return history.get("createdDate", "")[:19] if history.get("createdDate") else ""
    elif field == "lastModified":
        version = content.get("version", {})
        return version.get("when", "")[:19] if version.get("when") else ""
    elif field == "creator":
        history = content.get("history", {})
        created_by = history.get("createdBy", {})
        return created_by.get("displayName", created_by.get("username", ""))
    elif field == "url":
        links = content.get("_links", {})
        return links.get("webui", "")
    elif field == "excerpt":
        return result.get("excerpt", "")[:200]
    elif field == "status":
        return content.get("status", "")
    else:
        return str(content.get(field, ""))


@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Export search results to file",
        epilog="""
Examples:
  python export_results.py "space = 'DOCS'" --format csv --output results.csv
  python export_results.py "label = 'api'" --format json --output results.json
  python export_results.py "type = page" --columns id,title,url
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("cql", help="CQL query")
    parser.add_argument(
        "--format",
        "-f",
        choices=["csv", "json"],
        default="csv",
        help="Output format (default: csv)",
    )
    parser.add_argument("--output", "-o", required=True, help="Output file path")
    parser.add_argument("--columns", help="Columns to include (comma-separated)")
    parser.add_argument(
        "--limit", "-l", type=int, default=1000, help="Maximum results (default: 1000)"
    )
    args = parser.parse_args(argv)

    # Validate
    cql = validate_cql(args.cql)
    limit = validate_limit(args.limit, max_value=10000)
    output_path = Path(args.output)

    columns = args.columns.split(",") if args.columns else DEFAULT_COLUMNS
    columns = [c.strip() for c in columns]

    # Get client
    client = get_confluence_client()

    print_info(f"Executing query: {cql}")
    print_info(f"Exporting to: {output_path}")

    # Collect results
    results = []
    start = 0
    batch_size = 50

    while len(results) < limit:
        params = {
            "cql": cql,
            "limit": batch_size,
            "start": start,
            "expand": "content.history,content.version,content.space",
        }

        response = client.get(
            "/rest/api/search", params=params, operation="search for export"
        )

        batch = response.get("results", [])
        if not batch:
            break

        results.extend(batch)
        start += len(batch)

        print_info(f"Fetched {len(results)} results...")

        if len(batch) < batch_size:
            break

    results = results[:limit]

    # Export
    if args.format == "json":
        # JSON export
        data = []
        for result in results:
            row = {col: extract_field(result, col) for col in columns}
            data.append(row)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    else:
        # CSV export
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(columns)

            for result in results:
                row = [extract_field(result, col) for col in columns]
                writer.writerow(row)

    print_success(f"Exported {len(results)} results to {output_path}")


if __name__ == "__main__":
    main()
