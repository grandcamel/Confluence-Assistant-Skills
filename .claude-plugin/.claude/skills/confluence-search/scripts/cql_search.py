#!/usr/bin/env python3
"""
Execute CQL queries against Confluence.

Examples:
    python cql_search.py "text ~ 'API documentation'"
    python cql_search.py "space = 'DOCS' AND type = page"
    python cql_search.py "label = 'approved'" --limit 50
"""

import argparse

from confluence_assistant_skills_lib import (
    format_json,
    format_search_results,
    get_confluence_client,
    handle_errors,
    print_success,
    validate_cql,
    validate_limit,
)


@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Execute CQL queries against Confluence",
        epilog="""
Examples:
  python cql_search.py "text ~ 'API documentation'"
  python cql_search.py "space = 'DOCS' AND type = page"
  python cql_search.py "label = 'approved'" --limit 50 --show-excerpts
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("cql", help="CQL query string")
    parser.add_argument(
        "--limit", "-l", type=int, default=25, help="Maximum results (default: 25)"
    )
    parser.add_argument(
        "--show-excerpts", action="store_true", help="Show content excerpts"
    )
    parser.add_argument(
        "--show-labels", action="store_true", help="Show content labels"
    )
    parser.add_argument(
        "--show-ancestors", action="store_true", help="Show ancestor pages"
    )
    parser.add_argument(
        "--output",
        "-o",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    args = parser.parse_args(argv)

    # Validate
    cql = validate_cql(args.cql)
    limit = validate_limit(args.limit, max_value=200)

    # Get client
    client = get_confluence_client()

    # Build expand parameter
    expand = ["content.space"]
    if args.show_labels:
        expand.append("content.metadata.labels")
    if args.show_ancestors:
        expand.append("content.ancestors")

    # Execute search using v1 API (better for CQL)
    params = {"cql": cql, "limit": min(limit, 50), "expand": ",".join(expand)}

    # Paginate through results
    results = []
    start = 0

    while len(results) < limit:
        params["start"] = start
        response = client.get("/rest/api/search", params=params, operation="CQL search")

        batch = response.get("results", [])
        if not batch:
            break

        results.extend(batch)
        start += len(batch)

        if len(batch) < params["limit"]:
            break

    # Trim to requested limit
    results = results[:limit]

    # Output
    if args.output == "json":
        print(format_json({"cql": cql, "results": results, "count": len(results)}))
    else:
        print(
            format_search_results(
                results,
                show_labels=args.show_labels,
                show_ancestors=args.show_ancestors,
                show_excerpt=args.show_excerpts,
            )
        )

    print_success(f"Found {len(results)} result(s)")


if __name__ == "__main__":
    main()
