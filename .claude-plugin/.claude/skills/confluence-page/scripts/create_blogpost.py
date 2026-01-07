#!/usr/bin/env python3
"""
Create a new Confluence blog post.

Examples:
    python create_blogpost.py --space BLOG --title "My Post" --body "Content"
    python create_blogpost.py --space BLOG --title "From File" --file post.md
"""

import argparse
from pathlib import Path

from confluence_assistant_skills_lib import (
    ValidationError,
    format_blogpost,
    format_json,
    get_confluence_client,
    handle_errors,
    markdown_to_xhtml,
    print_success,
    validate_space_key,
    validate_title,
)


def read_body_from_file(file_path: Path) -> str:
    """Read body content from a file."""
    if not file_path.exists():
        raise ValidationError(f"File not found: {file_path}")
    return file_path.read_text(encoding="utf-8")


def is_markdown_file(file_path: Path) -> bool:
    """Check if file is a Markdown file."""
    return file_path.suffix.lower() in (".md", ".markdown")


@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Create a new Confluence blog post",
        epilog="""
Examples:
  python create_blogpost.py --space BLOG --title "My Post" --body "Content"
  python create_blogpost.py --space BLOG --title "From File" --file post.md
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--space", "-s", required=True, help="Space key")
    parser.add_argument("--title", "-t", required=True, help="Blog post title")
    parser.add_argument("--body", "-b", help="Blog post body content")
    parser.add_argument("--file", "-f", type=Path, help="Read body from file")
    parser.add_argument(
        "--status",
        choices=["current", "draft"],
        default="current",
        help="Blog post status (default: current)",
    )
    parser.add_argument(
        "--output",
        "-o",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    args = parser.parse_args(argv)

    # Validate inputs
    space_key = validate_space_key(args.space)
    title = validate_title(args.title)

    # Get body content
    if args.file:
        body_content = read_body_from_file(args.file)
        is_markdown = is_markdown_file(args.file)
    elif args.body:
        body_content = args.body
        is_markdown = False
    else:
        raise ValidationError("Either --body or --file is required")

    # Get client
    client = get_confluence_client()

    # Get space ID from space key
    spaces = list(
        client.paginate(
            "/api/v2/spaces", params={"keys": space_key}, operation="get space"
        )
    )

    if not spaces:
        raise ValidationError(f"Space not found: {space_key}")

    space_id = spaces[0]["id"]

    # Convert Markdown if needed
    if is_markdown:
        body_content = markdown_to_xhtml(body_content)

    # Prepare blog post data
    blogpost_data = {
        "spaceId": space_id,
        "status": args.status,
        "title": title,
        "body": {"representation": "storage", "value": body_content},
    }

    # Create the blog post
    result = client.post(
        "/api/v2/blogposts", json_data=blogpost_data, operation="create blog post"
    )

    # Output
    if args.output == "json":
        print(format_json(result))
    else:
        print(format_blogpost(result))

    print_success(f"Created blog post '{title}' with ID {result['id']}")


if __name__ == "__main__":
    main()
