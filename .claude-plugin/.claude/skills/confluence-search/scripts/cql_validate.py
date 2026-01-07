#!/usr/bin/env python3
"""
Validate CQL query syntax.

Examples:
    python cql_validate.py "space = 'DOCS' AND type = page"
    python cql_validate.py "invalid query (("
"""

import argparse
import sys

from confluence_assistant_skills_lib import (
    get_confluence_client,
    handle_errors,
    print_success,
    print_warning,
    validate_cql,
)


@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Validate CQL query syntax",
        epilog="""
Examples:
  python cql_validate.py "space = 'DOCS' AND type = page"
  python cql_validate.py "invalid query (("
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("cql", help="CQL query to validate")
    parser.add_argument(
        "--server", action="store_true", help="Also validate against server"
    )
    args = parser.parse_args(argv)

    # Local validation
    print(f"\nValidating CQL: {args.cql}\n")

    try:
        cql = validate_cql(args.cql)
        print_success("Local syntax validation passed")
    except Exception as e:
        print_warning(f"Local validation failed: {e}")
        sys.exit(1)

    # Server validation (optional)
    if args.server:
        print("\nValidating against server...")

        try:
            client = get_confluence_client()

            # Try to execute with limit=0 to just validate
            response = client.get(
                "/rest/api/search",
                params={"cql": cql, "limit": 0},
                operation="validate CQL",
            )

            print_success("Server validation passed")

            # Show total results if available
            total = response.get("totalSize", response.get("size", 0))
            print(f"Query would return approximately {total} result(s)")

        except Exception as e:
            print_warning(f"Server validation failed: {e}")
            sys.exit(1)

    # Print parsed components
    print("\n" + "=" * 50)
    print("Query Analysis:")
    print("=" * 50)

    # Simple parsing for display
    parts = []
    if "space" in cql.lower():
        parts.append("- Filters by space")
    if "type" in cql.lower():
        parts.append("- Filters by content type")
    if "label" in cql.lower():
        parts.append("- Filters by label")
    if "text" in cql.lower() or "~" in cql:
        parts.append("- Performs text search")
    if "created" in cql.lower() or "lastmodified" in cql.lower():
        parts.append("- Filters by date")
    if "creator" in cql.lower() or "contributor" in cql.lower():
        parts.append("- Filters by user")
    if "order by" in cql.lower():
        parts.append("- Has custom ordering")

    if parts:
        for part in parts:
            print(part)
    else:
        print("- Simple query")

    print()


if __name__ == "__main__":
    main()
