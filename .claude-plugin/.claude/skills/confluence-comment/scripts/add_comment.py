#!/usr/bin/env python3
"""
Add a footer comment to a Confluence page.

Examples:
    python add_comment.py 12345 "This is my comment"
    python add_comment.py 12345 --file comment.txt
"""

import argparse
from pathlib import Path

from confluence_assistant_skills_lib import (
    ValidationError,
    format_comment,
    format_json,
    get_confluence_client,
    handle_errors,
    print_success,
    validate_page_id,
)


def validate_comment_body(body: str, field_name: str = "body") -> str:
    """
    Validate comment body.

    Args:
        body: The comment body to validate
        field_name: Name of the field for error messages

    Returns:
        Validated body (stripped)

    Raises:
        ValidationError: If the body is invalid
    """
    if body is None:
        raise ValidationError(f"{field_name} is required", field=field_name)

    body = str(body).strip()

    if not body:
        raise ValidationError(
            f"{field_name} cannot be empty", field=field_name, value=body
        )

    return body


def read_body_from_file(file_path: Path) -> str:
    """Read comment body from a file."""
    if not file_path.exists():
        raise ValidationError(f"File not found: {file_path}")

    return file_path.read_text(encoding="utf-8")


@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Add a footer comment to a Confluence page",
        epilog="""
Examples:
  python add_comment.py 12345 "This is my comment"
  python add_comment.py 12345 --file comment.txt
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("page_id", help="Page ID to add comment to")
    parser.add_argument("body", nargs="?", help="Comment body text")
    parser.add_argument("--file", "-f", type=Path, help="Read body from file")
    parser.add_argument(
        "--output",
        "-o",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    args = parser.parse_args(argv)

    # Validate inputs
    page_id = validate_page_id(args.page_id)

    # Get body content
    if args.file:
        body_content = read_body_from_file(args.file)
    elif args.body:
        body_content = args.body
    else:
        raise ValidationError("Either body argument or --file is required")

    # Validate body
    body_content = validate_comment_body(body_content)

    # Get client
    client = get_confluence_client()

    # Prepare comment data using v1 API (v2 API doesn't support POST for comments)
    comment_data = {
        "type": "comment",
        "container": {"id": page_id, "type": "page"},
        "body": {
            "storage": {"value": f"<p>{body_content}</p>", "representation": "storage"}
        },
    }

    # Create the comment using v1 API
    result = client.post(
        "/rest/api/content", json_data=comment_data, operation="add comment"
    )

    # Output
    if args.output == "json":
        print(format_json(result))
    else:
        print(format_comment(result))

    print_success(f"Added comment {result['id']} to page {page_id}")


if __name__ == "__main__":
    main()
