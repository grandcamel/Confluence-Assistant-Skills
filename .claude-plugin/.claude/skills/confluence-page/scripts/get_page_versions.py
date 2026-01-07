#!/usr/bin/env python3
"""
Get version history for a Confluence page.

Examples:
    python get_page_versions.py 12345
    python get_page_versions.py 12345 --limit 10
    python get_page_versions.py 12345 --detailed
"""

import argparse

from confluence_assistant_skills_lib import (
    format_json,
    format_table,
    format_version,
    get_confluence_client,
    handle_errors,
    print_success,
    validate_limit,
    validate_page_id,
)


@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Get version history for a Confluence page",
        epilog="""
Examples:
  python get_page_versions.py 12345
  python get_page_versions.py 12345 --limit 10
  python get_page_versions.py 12345 --detailed --output json
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("page_id", help="Page ID")
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=25,
        help="Maximum versions to return (default: 25)",
    )
    parser.add_argument(
        "--detailed", action="store_true", help="Show full version details"
    )
    parser.add_argument("--profile", help="Confluence profile to use")
    parser.add_argument(
        "--output",
        "-o",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    args = parser.parse_args(argv)

    # Validate
    page_id = validate_page_id(args.page_id)
    limit = validate_limit(args.limit, max_value=100)

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Get the page first to show current info
    page = client.get(f"/api/v2/pages/{page_id}", operation="get page")

    # Get version history using v1 API (more detailed)
    versions_response = client.get(
        f"/rest/api/content/{page_id}/version",
        params={"limit": limit},
        operation="get versions",
    )

    versions = versions_response.get("results", [])

    # Output
    if args.output == "json":
        print(
            format_json(
                {
                    "page": {
                        "id": page_id,
                        "title": page.get("title"),
                        "currentVersion": page.get("version", {}).get("number"),
                    },
                    "versions": versions,
                }
            )
        )
    else:
        print(f"\nPage: {page.get('title')}")
        print(f"ID: {page_id}")
        print(f"Current Version: {page.get('version', {}).get('number', 1)}")
        print(f"\n{'=' * 60}")
        print("Version History:")
        print(f"{'=' * 60}\n")

        if not versions:
            print("No version history available.")
        else:
            if args.detailed:
                for version in versions:
                    print(format_version(version))
                    print()
            else:
                # Simple table format
                data = []
                for v in versions:
                    data.append(
                        {
                            "version": v.get("number", "?"),
                            "when": v.get("when", "")[:16] if v.get("when") else "N/A",
                            "by": v.get("by", {}).get(
                                "displayName",
                                v.get("by", {}).get("username", "Unknown"),
                            ),
                            "message": v.get("message", "")[:40] or "-",
                        }
                    )

                print(
                    format_table(
                        data,
                        columns=["version", "when", "by", "message"],
                        headers=["Version", "Date", "Author", "Message"],
                    )
                )

    print_success(f"Retrieved {len(versions)} version(s) for page {page_id}")


if __name__ == "__main__":
    main()
