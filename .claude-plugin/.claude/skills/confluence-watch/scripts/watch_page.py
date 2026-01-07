#!/usr/bin/env python3
"""
Start watching a Confluence page for notifications.

Examples:
    python watch_page.py 123456
    python watch_page.py 123456 --output json
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
        description="Start watching a Confluence page",
        epilog="""
Examples:
  python watch_page.py 123456
  python watch_page.py 123456 --output json
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("page_id", help="Page ID to watch")
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
    client = get_confluence_client()

    # Watch the page using v1 API
    client.post(f"/rest/api/user/watch/content/{page_id}", operation="watch page")

    # Output
    if args.output == "json":
        output = {"success": True, "page_id": page_id, "watching": True}
        print(format_json(output))
    else:
        print(f"Now watching page {page_id}")
        print("You will receive notifications for updates to this page.")

    print_success(f"Started watching page {page_id}")


if __name__ == "__main__":
    main()
