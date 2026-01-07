#!/usr/bin/env python3
"""
Retrieve a Confluence page's content and metadata.

Examples:
    python get_page.py 12345
    python get_page.py 12345 --body
    python get_page.py 12345 --body --format markdown
    python get_page.py 12345 --output json
"""

import argparse

from confluence_assistant_skills_lib import (
    format_json,
    format_page,
    get_confluence_client,
    handle_errors,
    print_success,
    validate_page_id,
    xhtml_to_markdown,
)


@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Get a Confluence page by ID",
        epilog="""
Examples:
  python get_page.py 12345
  python get_page.py 12345 --body
  python get_page.py 12345 --body --format markdown
  python get_page.py 12345 --output json
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("page_id", help="Page ID")
    parser.add_argument(
        "--body", action="store_true", help="Include body content in output"
    )
    parser.add_argument(
        "--format",
        choices=["storage", "view", "markdown"],
        default="storage",
        help="Body format (default: storage)",
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
    page_id = validate_page_id(args.page_id)

    # Get client
    client = get_confluence_client()

    # Build request params
    params = {}
    if args.body:
        params["body-format"] = "storage"

    # Get the page
    result = client.get(f"/api/v2/pages/{page_id}", params=params, operation="get page")

    # Convert body format if needed
    if args.body and args.format == "markdown":
        body = result.get("body", {})
        storage = body.get("storage", {}).get("value", "")
        if storage:
            result["body"]["markdown"] = xhtml_to_markdown(storage)

    # Output
    if args.output == "json":
        print(format_json(result))
    else:
        print(format_page(result, detailed=args.body))

        if args.body:
            print("\n--- Content ---")
            body = result.get("body", {})

            if args.format == "markdown" and "markdown" in body:
                print(body["markdown"])
            elif "storage" in body:
                print(body["storage"].get("value", ""))

    print_success(f"Retrieved page {page_id}")


if __name__ == "__main__":
    main()
