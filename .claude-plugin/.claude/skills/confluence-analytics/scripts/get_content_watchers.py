#!/usr/bin/env python3
"""
Get the list of users watching a Confluence page.

This script retrieves the watchers (users who will be notified of changes)
for a specific page or blog post.

Examples:
    python get_content_watchers.py 12345
    python get_content_watchers.py 12345 --output json
    python get_content_watchers.py 12345 --profile production
"""

import argparse

from confluence_assistant_skills_lib import (
    format_json,
    get_confluence_client,
    handle_errors,
    print_success,
    validate_page_id,
)


@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Get the list of users watching a Confluence page",
        epilog="""
Examples:
  python get_content_watchers.py 12345
  python get_content_watchers.py 12345 --output json
  python get_content_watchers.py 12345 --profile production
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("page_id", help="Page or blog post ID")
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

    # Get client
    client = get_confluence_client(profile=args.profile)

    # First, get the page to verify it exists and get its title
    page = client.get(
        f"/rest/api/content/{page_id}", params={"expand": "space"}, operation="get page"
    )

    # Get watchers using v1 API
    # Note: Confluence Cloud API has limited watcher support
    # Using the notification/child-created endpoint as a proxy
    try:
        watchers_response = client.get(
            f"/rest/api/content/{page_id}/notification/child-created",
            operation="get watchers",
        )
        watchers = watchers_response.get("results", [])
    except Exception as e:
        # If watchers endpoint fails, try alternative approach
        # Some Confluence instances may not have this enabled
        print(f"Note: Unable to retrieve watchers directly: {e}")
        watchers = []

    # Output
    if args.output == "json":
        output = {
            "page_id": page_id,
            "page_title": page.get("title"),
            "page_type": page.get("type"),
            "space_key": page.get("space", {}).get("key"),
            "watcher_count": len(watchers),
            "watchers": [
                {
                    "name": w.get("watcher", {}).get("displayName"),
                    "email": w.get("watcher", {}).get("email"),
                    "account_id": w.get("watcher", {}).get("accountId"),
                    "type": w.get("type"),
                }
                for w in watchers
            ],
        }
        print(format_json(output))
    else:
        # Text output
        print(f"Page: {page.get('title')}")
        print(f"ID: {page_id}")
        print(f"Type: {page.get('type')}")
        print(f"Space: {page.get('space', {}).get('key')}")
        print(f"\nWatchers: {len(watchers)}")

        if watchers:
            print("\nWatcher List:")
            for watcher_data in watchers:
                watcher = watcher_data.get("watcher", {})
                name = watcher.get("displayName", "Unknown")
                email = watcher.get("email", "N/A")
                print(f"  - {name} ({email})")
        else:
            print("\nNo watchers found or watchers endpoint not available.")
            print(
                "Note: Some Confluence instances may have restricted watcher API access."
            )

    print_success(f"Retrieved watcher information for page {page_id}")


if __name__ == "__main__":
    main()
