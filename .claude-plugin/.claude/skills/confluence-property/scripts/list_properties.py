#!/usr/bin/env python3
"""
List and filter content properties on a Confluence page or blog post.

This script lists all properties with optional filtering by key pattern.
Supports sorting and detailed output options.

Examples:
    # List all properties
    python list_properties.py 12345

    # Filter by key prefix
    python list_properties.py 12345 --prefix app.

    # Filter by regex pattern
    python list_properties.py 12345 --pattern "config.*"

    # Sort by key
    python list_properties.py 12345 --sort key

    # Show detailed version info
    python list_properties.py 12345 --expand version --verbose
"""

import argparse
import re

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
        description="List and filter content properties",
        epilog="""
Examples:
  # List all properties
  python list_properties.py 12345

  # Filter by prefix
  python list_properties.py 12345 --prefix app.

  # Filter by regex
  python list_properties.py 12345 --pattern "config.*"

  # Detailed output
  python list_properties.py 12345 --expand version --verbose

  # JSON output
  python list_properties.py 12345 --output json
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("content_id", help="Content ID (page or blog post)")
    parser.add_argument("--prefix", help="Filter properties by key prefix")
    parser.add_argument("--pattern", help="Filter properties by regex pattern")
    parser.add_argument(
        "--sort",
        choices=["key", "version"],
        default="key",
        help="Sort properties by field (default: key)",
    )
    parser.add_argument(
        "--expand", help="Comma-separated fields to expand (e.g., version)"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed information"
    )
    parser.add_argument("--profile", "-p", help="Confluence profile to use")
    parser.add_argument(
        "--output",
        "-o",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    args = parser.parse_args(argv)

    # Validate
    content_id = validate_page_id(args.content_id)

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Build request params
    params = {}
    if args.expand:
        params["expand"] = args.expand

    # Get all properties
    result = client.get(
        f"/rest/api/content/{content_id}/property",
        params=params,
        operation="list properties",
    )

    properties = result.get("results", [])

    # Filter by prefix if specified
    if args.prefix:
        properties = [p for p in properties if p.get("key", "").startswith(args.prefix)]

    # Filter by pattern if specified
    if args.pattern:
        try:
            pattern = re.compile(args.pattern)
            properties = [p for p in properties if pattern.match(p.get("key", ""))]
        except re.error as e:
            from confluence_assistant_skills_lib import ValidationError

            raise ValidationError(f"Invalid regex pattern: {e}")

    # Sort properties
    if args.sort == "key":
        properties.sort(key=lambda p: p.get("key", ""))
    elif args.sort == "version":
        properties.sort(key=lambda p: p.get("version", {}).get("number", 0))

    # Output
    if args.output == "json":
        print(format_json({"results": properties, "size": len(properties)}))
    else:
        if not properties:
            print("No properties found")
            if args.prefix:
                print(f"(with prefix: {args.prefix})")
            if args.pattern:
                print(f"(matching pattern: {args.pattern})")
        else:
            filter_info = ""
            if args.prefix:
                filter_info = f" (prefix: {args.prefix})"
            elif args.pattern:
                filter_info = f" (pattern: {args.pattern})"

            print(f"Found {len(properties)} properties{filter_info}:\n")

            for i, prop in enumerate(properties, 1):
                key = prop.get("key", "N/A")
                value = prop.get("value", {})

                if args.verbose:
                    print(f"{i}. Property:")
                    print(f"   Key: {key}")
                    print(f"   ID: {prop.get('id', 'N/A')}")

                    # Format value
                    if isinstance(value, dict):
                        print(f"   Value: {format_json(value)}")
                    else:
                        print(f"   Value: {value}")

                    # Version info
                    if "version" in prop:
                        version = prop["version"]
                        print(f"   Version: {version.get('number', 'N/A')}")
                        if "when" in version:
                            print(f"   Modified: {version['when']}")
                        if "by" in version:
                            print(f"   By: {version.get('by', 'N/A')}")
                    print()
                else:
                    # Compact output
                    value_str = (
                        str(value)
                        if not isinstance(value, dict)
                        else format_json(value)
                    )
                    if len(value_str) > 60:
                        value_str = value_str[:57] + "..."

                    version_num = prop.get("version", {}).get("number", "N/A")
                    print(f"  {key:<30} v{version_num:<5} {value_str}")

    print_success(f"Listed {len(properties)} properties from content {content_id}")


if __name__ == "__main__":
    main()
