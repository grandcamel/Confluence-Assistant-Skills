#!/usr/bin/env python3
"""
List all attachments on a Confluence page.

Examples:
    python list_attachments.py 123456
    python list_attachments.py 123456 --output json
    python list_attachments.py 123456 --limit 10
"""

import argparse

from confluence_assistant_skills_lib import (
    format_attachment,
    format_json,
    format_table,
    get_confluence_client,
    handle_errors,
    print_success,
    validate_page_id,
)


def format_file_size(bytes_size: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"


@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="List all attachments on a Confluence page",
        epilog="""
Examples:
  python list_attachments.py 123456
  python list_attachments.py 123456 --output json
  python list_attachments.py 123456 --limit 10
  python list_attachments.py 123456 --media-type application/pdf
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("page_id", help="Page ID to list attachments from")
    parser.add_argument(
        "--limit", "-l", type=int, help="Maximum number of attachments to return"
    )
    parser.add_argument(
        "--media-type",
        "-m",
        help="Filter by media type (e.g., application/pdf, image/png)",
    )
    parser.add_argument("--profile", help="Confluence profile to use")
    parser.add_argument(
        "--output",
        "-o",
        choices=["text", "json", "table"],
        default="text",
        help="Output format (default: text)",
    )
    args = parser.parse_args(argv)

    # Validate inputs
    page_id = validate_page_id(args.page_id)

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Build params
    params = {}
    if args.media_type:
        params["mediaType"] = args.media_type

    # Get attachments
    endpoint = f"/api/v2/pages/{page_id}/attachments"

    if args.limit:
        # Use pagination with limit
        attachments = list(
            client.paginate(
                endpoint,
                params=params,
                limit=args.limit,
                operation=f"list attachments on page {page_id}",
            )
        )
    else:
        # Get all attachments
        attachments = list(
            client.paginate(
                endpoint, params=params, operation=f"list attachments on page {page_id}"
            )
        )

    # Output
    if args.output == "json":
        print(format_json(attachments))
    elif args.output == "table":
        if not attachments:
            print("No attachments found.")
        else:
            # Prepare table data
            table_data = []
            for att in attachments:
                table_data.append(
                    {
                        "ID": att.get("id", "N/A"),
                        "Title": att.get("title", "N/A"),
                        "Type": att.get("mediaType", "N/A"),
                        "Size": format_file_size(att.get("fileSize", 0)),
                        "Version": att.get("version", {}).get("number", "N/A"),
                    }
                )
            print(
                format_table(
                    table_data, columns=["ID", "Title", "Type", "Size", "Version"]
                )
            )
    else:
        # Text format
        if not attachments:
            print("No attachments found.")
        else:
            print(f"Found {len(attachments)} attachment(s):\n")
            for i, att in enumerate(attachments, 1):
                print(f"{i}. {format_attachment(att)}")
                print()

    if attachments:
        print_success(f"Listed {len(attachments)} attachment(s) from page {page_id}")


if __name__ == "__main__":
    main()
