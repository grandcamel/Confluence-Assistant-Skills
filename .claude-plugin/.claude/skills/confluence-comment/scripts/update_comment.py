#!/usr/bin/env python3
"""
Update an existing Confluence comment.

Examples:
    python update_comment.py 999 "Updated comment text"
    python update_comment.py 999 --file updated.txt
    python update_comment.py 999 "Updated" --profile production
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
        description="Update an existing Confluence comment",
        epilog="""
Examples:
  python update_comment.py 999 "Updated comment text"
  python update_comment.py 999 --file updated.txt
  python update_comment.py 999 "Updated" --profile production
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("comment_id", help="Comment ID to update")
    parser.add_argument("body", nargs="?", help="Updated comment body text")
    parser.add_argument("--file", "-f", type=Path, help="Read body from file")
    parser.add_argument("--profile", help="Confluence profile to use")
    parser.add_argument(
        "--output",
        "-o",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    args = parser.parse_args(argv)

    # Validate inputs
    comment_id = validate_page_id(args.comment_id, "comment_id")

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
    client = get_confluence_client(profile=args.profile)

    # First, get the current comment to get the version (using v1 API)
    current_comment = client.get(
        f"/rest/api/content/{comment_id}", operation="get current comment"
    )

    # Prepare updated comment data using v1 API format
    comment_data = {
        "type": "comment",
        "version": {"number": current_comment["version"]["number"] + 1},
        "body": {
            "storage": {"value": f"<p>{body_content}</p>", "representation": "storage"}
        },
    }

    # Update the comment using v1 API
    result = client.put(
        f"/rest/api/content/{comment_id}",
        json_data=comment_data,
        operation="update comment",
    )

    # Output
    if args.output == "json":
        print(format_json(result))
    else:
        print(format_comment(result))

    print_success(f"Updated comment {comment_id}")


if __name__ == "__main__":
    main()
