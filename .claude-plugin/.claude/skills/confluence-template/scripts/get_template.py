#!/usr/bin/env python3
"""
Get a Confluence template's details and content.

Examples:
    python get_template.py tmpl-123
    python get_template.py tmpl-123 --body
    python get_template.py tmpl-123 --body --format markdown
    python get_template.py blueprint-id --blueprint
    python get_template.py tmpl-123 --output json
"""

import argparse

from confluence_assistant_skills_lib import (
    ValidationError,
    format_json,
    get_confluence_client,
    handle_errors,
    print_success,
    xhtml_to_markdown,
)


@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Get a Confluence template by ID",
        epilog="""
Examples:
  python get_template.py tmpl-123
  python get_template.py tmpl-123 --body
  python get_template.py tmpl-123 --body --format markdown
  python get_template.py bp-456 --blueprint
  python get_template.py tmpl-123 --output json
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("template_id", help="Template ID or blueprint ID")
    parser.add_argument(
        "--body", action="store_true", help="Include body content in output"
    )
    parser.add_argument(
        "--format",
        choices=["storage", "markdown"],
        default="storage",
        help="Body format (default: storage)",
    )
    parser.add_argument(
        "--blueprint", action="store_true", help="Get blueprint instead of template"
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
    if not args.template_id or not args.template_id.strip():
        raise ValidationError("Template ID is required")

    template_id = args.template_id.strip()

    # Get client
    client = get_confluence_client()

    # Determine endpoint
    if args.blueprint:
        endpoint = f"/rest/api/template/blueprint/{template_id}"
    else:
        endpoint = f"/rest/api/template/{template_id}"

    # Get the template/blueprint
    result = client.get(endpoint, operation="get template")

    # Convert body format if needed
    if args.body and not args.blueprint and args.format == "markdown":
        body = result.get("body", {})
        storage = body.get("storage", {}).get("value", "")
        if storage:
            result["body"]["markdown"] = xhtml_to_markdown(storage)

    # Output
    if args.output == "json":
        print(format_json(result))
    else:
        if args.blueprint:
            # Blueprint format
            print(f"Blueprint: {result.get('name', 'Unnamed')}")
            print(
                f"ID: {result.get('blueprintId', result.get('contentBlueprintId', 'N/A'))}"
            )

            desc = result.get("description", "")
            if desc:
                print(f"Description: {desc}")

            module_key = result.get("moduleCompleteKey", "")
            if module_key:
                print(f"Module Key: {module_key}")

            blueprint_id = result.get("contentBlueprintId", "")
            if blueprint_id:
                print(f"Content Blueprint ID: {blueprint_id}")
        else:
            # Template format
            print(f"Template: {result.get('name', 'Unnamed')}")
            print(f"ID: {result.get('templateId', 'N/A')}")
            print(f"Type: {result.get('templateType', 'page')}")

            space = result.get("space", {})
            if space:
                print(f"Space: {space.get('key', 'N/A')}")

            desc = result.get("description", "")
            if desc:
                print(f"Description: {desc}")

            labels = result.get("labels", [])
            if labels:
                label_names = [lbl.get("name", "") for lbl in labels]
                print(f"Labels: {', '.join(label_names)}")

            if args.body:
                print("\n--- Template Content ---")
                body = result.get("body", {})

                if args.format == "markdown" and "markdown" in body:
                    print(body["markdown"])
                elif "storage" in body:
                    print(body["storage"].get("value", ""))

    print_success(
        f"Retrieved {'blueprint' if args.blueprint else 'template'} {template_id}"
    )


if __name__ == "__main__":
    main()
