#!/usr/bin/env python3
"""
Update an existing Confluence page template.

Examples:
    python update_template.py tmpl-123 --name "Updated Template"
    python update_template.py tmpl-123 --description "New description"
    python update_template.py tmpl-123 --file updated.html
    python update_template.py tmpl-123 --file updated.md
    python update_template.py tmpl-123 --add-labels "tag1,tag2"
    python update_template.py tmpl-123 --remove-labels "old-tag"
"""

import argparse
from pathlib import Path

from confluence_assistant_skills_lib import (
    ValidationError,
    format_json,
    get_confluence_client,
    handle_errors,
    markdown_to_xhtml,
    print_success,
)


def validate_template_name(name: str) -> str:
    """Validate a template name."""
    if not name or not name.strip():
        raise ValidationError("Template name cannot be empty")

    name = name.strip()

    if len(name) > 255:
        raise ValidationError("Template name cannot exceed 255 characters")

    return name


@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Update an existing Confluence page template",
        epilog="""
Examples:
  python update_template.py tmpl-123 --name "Updated Template"
  python update_template.py tmpl-123 --description "New description"
  python update_template.py tmpl-123 --file updated.html
  python update_template.py tmpl-123 --file updated.md
  python update_template.py tmpl-123 --add-labels "tag1,tag2"
  python update_template.py tmpl-123 --remove-labels "old-tag"
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("template_id", help="Template ID to update")
    parser.add_argument("--name", help="New template name")
    parser.add_argument("--description", help="New template description")
    parser.add_argument("--content", help="New template body content (HTML/XHTML)")
    parser.add_argument(
        "--file", help="File with new template content (Markdown or HTML)"
    )
    parser.add_argument("--add-labels", help="Comma-separated labels to add")
    parser.add_argument("--remove-labels", help="Comma-separated labels to remove")
    parser.add_argument(
        "--output",
        "-o",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    args = parser.parse_args(argv)

    # Validate template ID
    if not args.template_id or not args.template_id.strip():
        raise ValidationError("Template ID is required")

    template_id = args.template_id.strip()

    # Check that at least one field is being updated
    if not any(
        [
            args.name,
            args.description,
            args.content,
            args.file,
            args.add_labels,
            args.remove_labels,
        ]
    ):
        raise ValidationError(
            "At least one field must be specified to update: "
            "--name, --description, --content, --file, --add-labels, --remove-labels"
        )

    # Get client
    client = get_confluence_client()

    # Get current template
    current = client.get(
        f"/rest/api/template/{template_id}", operation="get current template"
    )

    # Build updated template data
    template_data = {
        "name": current.get("name"),
        "templateType": current.get("templateType", "page"),
        "body": current.get("body", {}),
        "space": current.get("space", {}),
    }

    # Keep description if it exists
    if "description" in current:
        template_data["description"] = current["description"]

    # Keep labels if they exist
    if "labels" in current:
        template_data["labels"] = current["labels"]

    # Update name
    if args.name:
        template_data["name"] = validate_template_name(args.name)

    # Update description
    if args.description:
        template_data["description"] = args.description

    # Update body
    if args.content:
        template_data["body"] = {
            "storage": {"value": args.content, "representation": "storage"}
        }
    elif args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            raise ValidationError(f"File not found: {args.file}")

        content = file_path.read_text(encoding="utf-8")

        # Convert Markdown to XHTML if needed
        if file_path.suffix.lower() in [".md", ".markdown"]:
            body_value = markdown_to_xhtml(content)
        else:
            body_value = content

        template_data["body"] = {
            "storage": {"value": body_value, "representation": "storage"}
        }

    # Update labels
    current_labels = template_data.get("labels", [])
    label_names = {label.get("name") for label in current_labels}

    if args.add_labels:
        new_labels = [lbl.strip() for lbl in args.add_labels.split(",") if lbl.strip()]
        label_names.update(new_labels)

    if args.remove_labels:
        remove_labels = {lbl.strip() for lbl in args.remove_labels.split(",") if lbl.strip()}
        label_names -= remove_labels

    if args.add_labels or args.remove_labels:
        template_data["labels"] = [{"name": label} for label in sorted(label_names)]

    # Update the template
    result = client.put(
        f"/rest/api/template/{template_id}",
        json_data=template_data,
        operation="update template",
    )

    # Output
    if args.output == "json":
        print(format_json(result))
    else:
        print(f"Updated template: {result.get('name')}")
        print(f"ID: {result.get('templateId', 'N/A')}")
        print(f"Type: {result.get('templateType', 'page')}")

        desc = result.get("description", "")
        if desc:
            print(f"Description: {desc}")

        labels = result.get("labels", [])
        if labels:
            label_name_list = [lbl.get("name", "") for lbl in labels]
            print(f"Labels: {', '.join(label_name_list)}")

    print_success(f"Updated template {template_id}")


if __name__ == "__main__":
    main()
