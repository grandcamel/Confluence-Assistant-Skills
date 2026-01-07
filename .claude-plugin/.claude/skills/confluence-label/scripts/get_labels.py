#!/usr/bin/env python3
"""
Get all labels on a Confluence page or blog post.

Examples:
    python get_labels.py 12345
    python get_labels.py 12345 --output json
"""

import argparse

from confluence_assistant_skills_lib import (
    format_json,
    format_label,
    get_confluence_client,
    handle_errors,
    print_info,
    print_success,
    validate_page_id,
)


@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Get all labels on a Confluence page",
        epilog="""
Examples:
  python get_labels.py 12345
  python get_labels.py 12345 --output json
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("page_id", help="Page or blog post ID")
    parser.add_argument(
        "--output",
        "-o",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    args = parser.parse_args(argv)

    # Validate page ID
    page_id = validate_page_id(args.page_id)

    # Get client
    client = get_confluence_client()

    # Get labels
    response = client.get(f"/api/v2/pages/{page_id}/labels", operation="get labels")

    labels = response.get("results", [])

    # Output
    if args.output == "json":
        print(format_json(labels))
    else:
        if not labels:
            print_info(f"No labels found on page {page_id}")
        else:
            print(f"Labels on page {page_id}:")
            for i, label in enumerate(labels, 1):
                print(f"{i}. {format_label(label)}")
            print_success(f"Found {len(labels)} label(s)")


if __name__ == "__main__":
    main()
