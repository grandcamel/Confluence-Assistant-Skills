#!/usr/bin/env python3
"""
Retrieve Confluence space details.

Examples:
    python get_space.py DOCS
    python get_space.py DOCS --output json
"""

import argparse

from confluence_assistant_skills_lib import (
    NotFoundError,
    format_json,
    format_space,
    get_confluence_client,
    handle_errors,
    print_success,
    validate_space_key,
)


@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Get Confluence space details",
        epilog="""
Examples:
  python get_space.py DOCS
  python get_space.py DOCS --output json
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("space_key", help="Space key")
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
    space_key = validate_space_key(args.space_key)

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Get spaces by key
    spaces = list(
        client.paginate(
            "/api/v2/spaces", params={"keys": space_key}, operation="get space"
        )
    )

    if not spaces:
        raise NotFoundError(f"Space not found: {space_key}")

    result = spaces[0]

    # Output
    if args.output == "json":
        print(format_json(result))
    else:
        print(format_space(result, detailed=True))

    print_success(f"Retrieved space {space_key}")


if __name__ == "__main__":
    main()
