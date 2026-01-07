#!/usr/bin/env python3
"""
List all accessible Confluence spaces.

Examples:
    python list_spaces.py
    python list_spaces.py --type global
    python list_spaces.py --query "docs"
    python list_spaces.py --limit 10
"""

import argparse

from confluence_assistant_skills_lib import (
    format_json,
    format_table,
    get_confluence_client,
    handle_errors,
    print_success,
    validate_limit,
)


@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="List all accessible Confluence spaces",
        epilog="""
Examples:
  python list_spaces.py
  python list_spaces.py --type global
  python list_spaces.py --query "docs" --limit 10
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--type", choices=["global", "personal"], help="Filter by space type"
    )
    parser.add_argument("--query", "-q", help="Search query")
    parser.add_argument(
        "--status", choices=["current", "archived"], help="Filter by status"
    )
    parser.add_argument(
        "--limit", "-l", type=int, default=50, help="Maximum results (default: 50)"
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
    limit = validate_limit(args.limit, max_value=250)

    # Get client
    client = get_confluence_client()

    # Build params
    params = {"limit": min(limit, 25)}  # API limit per request

    if args.type:
        params["type"] = args.type

    if args.status:
        params["status"] = args.status

    # Get spaces
    spaces = list(
        client.paginate(
            "/api/v2/spaces", params=params, limit=limit, operation="list spaces"
        )
    )

    # Filter by query if provided (client-side filter for name matching)
    if args.query:
        query_lower = args.query.lower()
        spaces = [
            s
            for s in spaces
            if query_lower in s.get("name", "").lower()
            or query_lower in s.get("key", "").lower()
        ]

    # Output
    if args.output == "json":
        print(format_json({"spaces": spaces, "count": len(spaces)}))
    else:
        if not spaces:
            print("No spaces found.")
        else:
            print(f"\nFound {len(spaces)} space(s):\n")

            # Table format
            data = []
            for space in spaces:
                desc = space.get("description", {})
                if isinstance(desc, dict):
                    desc_text = desc.get("plain", {}).get("value", "")[:50]
                else:
                    desc_text = str(desc)[:50] if desc else ""

                data.append(
                    {
                        "key": space.get("key", ""),
                        "name": space.get("name", "")[:30],
                        "type": space.get("type", "global"),
                        "status": space.get("status", "current"),
                        "description": desc_text or "-",
                    }
                )

            print(
                format_table(
                    data,
                    columns=["key", "name", "type", "status", "description"],
                    headers=["Key", "Name", "Type", "Status", "Description"],
                )
            )

    print_success(f"Listed {len(spaces)} space(s)")


if __name__ == "__main__":
    main()
