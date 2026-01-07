#!/usr/bin/env python3
"""
Search for Confluence content by label.

Examples:
    python search_by_label.py documentation
    python search_by_label.py approved --space DOCS
    python search_by_label.py api --type page --limit 50
"""

import argparse
from typing import Optional

from confluence_assistant_skills_lib import (
    format_json,
    format_search_results,
    get_confluence_client,
    handle_errors,
    print_success,
    validate_label,
    validate_limit,
    validate_space_key,
)


def build_cql_query(
    label: str, space: Optional[str] = None, content_type: Optional[str] = None
) -> str:
    """Build CQL query for label search."""
    query_parts = [f'label = "{label}"']

    if space:
        query_parts.append(f'space = "{space}"')

    if content_type:
        query_parts.append(f'type = "{content_type}"')

    return " AND ".join(query_parts)


@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Search for Confluence content by label",
        epilog="""
Examples:
  python search_by_label.py documentation
  python search_by_label.py approved --space DOCS
  python search_by_label.py api --type page --limit 50
  python search_by_label.py tutorial --output json
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("label", help="Label to search for")
    parser.add_argument("--space", "-s", help="Filter by space key")
    parser.add_argument(
        "--type",
        "-t",
        choices=["page", "blogpost", "comment"],
        help="Filter by content type",
    )
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=25,
        help="Maximum number of results (default: 25)",
    )
    parser.add_argument(
        "--output",
        "-o",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    args = parser.parse_args(argv)

    # Validate inputs
    label_name = validate_label(args.label)
    limit = validate_limit(args.limit, max_value=250)

    space_key = None
    if args.space:
        space_key = validate_space_key(args.space)

    # Build CQL query
    cql = build_cql_query(label_name, space=space_key, content_type=args.type)

    # Get client
    client = get_confluence_client()

    # Search using CQL
    results = []
    for result in client.paginate(
        "/api/v2/search",
        params={"cql": cql},
        limit=limit,
        operation=f"search by label {label_name}",
    ):
        results.append(result)

    # Output
    if args.output == "json":
        print(format_json(results))
    else:
        print(format_search_results(results, show_labels=True))
        if results:
            print_success(f"Found {len(results)} result(s) with label '{label_name}'")


if __name__ == "__main__":
    main()
