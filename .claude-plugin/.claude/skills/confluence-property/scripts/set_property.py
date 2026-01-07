#!/usr/bin/env python3
"""
Set or update a content property on a Confluence page or blog post.

Content properties allow storing custom metadata as key-value pairs.
Values can be simple strings, numbers, or complex JSON objects.

Examples:
    # Set property from command line
    python set_property.py 12345 my-property --value "simple value"

    # Set property from JSON file
    python set_property.py 12345 my-property --file data.json

    # Set property with complex JSON
    python set_property.py 12345 config --value '{"enabled": true, "count": 42}'

    # Update existing property (requires version)
    python set_property.py 12345 my-property --value "updated" --version 2
"""

import argparse
import json
from pathlib import Path

from confluence_assistant_skills_lib import (
    ValidationError,
    format_json,
    get_confluence_client,
    handle_errors,
    print_success,
    validate_page_id,
)


@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Set or update a content property",
        epilog="""
Examples:
  # Set simple string value
  python set_property.py 12345 my-property --value "text value"

  # Set from JSON file
  python set_property.py 12345 config --file config.json

  # Set complex JSON
  python set_property.py 12345 data --value '{"count": 42, "enabled": true}'

  # Update existing (auto-increments version)
  python set_property.py 12345 my-property --value "updated" --update
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("content_id", help="Content ID (page or blog post)")
    parser.add_argument("key", help="Property key")
    parser.add_argument("--value", "-v", help="Property value (string or JSON)")
    parser.add_argument("--file", "-f", help="Read value from JSON file")
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update existing property (fetches current version)",
    )
    parser.add_argument(
        "--version", type=int, help="Version number for update (if known)"
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
    content_id = validate_page_id(args.content_id)

    if not args.key or not args.key.strip():
        raise ValidationError("Property key cannot be empty")

    if not args.value and not args.file:
        raise ValidationError("Either --value or --file must be provided")

    if args.value and args.file:
        raise ValidationError("Cannot specify both --value and --file")

    # Get client
    client = get_confluence_client()

    # Parse value
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            raise ValidationError(f"File not found: {args.file}")

        with file_path.open(encoding="utf-8") as f:
            try:
                property_value = json.load(f)
            except json.JSONDecodeError as e:
                raise ValidationError(f"Invalid JSON in file: {e}")
    else:
        # Try to parse as JSON, fall back to string
        try:
            property_value = json.loads(args.value)
        except json.JSONDecodeError:
            # Use as plain string
            property_value = args.value

    # Prepare property data
    property_data = {"key": args.key, "value": property_value}

    # Handle update vs create
    if args.update or args.version:
        # Get current property to determine version
        current_version = args.version
        if current_version is None:
            try:
                current_prop = client.get(
                    f"/rest/api/content/{content_id}/property/{args.key}",
                    operation="get current property",
                )
                current_version = current_prop.get("version", {}).get("number", 0)
            except Exception:
                # Property doesn't exist yet, create it
                current_version = None

        if current_version is not None:
            # Update existing property
            property_data["version"] = {"number": current_version + 1}

            result = client.put(
                f"/rest/api/content/{content_id}/property/{args.key}",
                json_data=property_data,
                operation="update property",
            )
            action = "Updated"
        else:
            # Create new property
            result = client.post(
                f"/rest/api/content/{content_id}/property",
                json_data=property_data,
                operation="create property",
            )
            action = "Created"
    else:
        # Create new property
        result = client.post(
            f"/rest/api/content/{content_id}/property",
            json_data=property_data,
            operation="create property",
        )
        action = "Created"

    # Output
    if args.output == "json":
        print(format_json(result))
    else:
        print(f"{action} property: {result.get('key', 'N/A')}")
        print(f"Value: {format_json(result.get('value', {}))}")
        if "version" in result:
            print(f"Version: {result['version'].get('number', 'N/A')}")

    print_success(f"{action} property '{args.key}' on content {content_id}")


if __name__ == "__main__":
    main()
