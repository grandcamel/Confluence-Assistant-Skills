#!/usr/bin/env python3
"""
Add label(s) to a Confluence page or blog post.

Examples:
    python add_label.py 12345 --label documentation
    python add_label.py 12345 --labels doc,approved,v2
    python add_label.py 12345 -l api
"""

import argparse

from confluence_assistant_skills_lib import (
    ValidationError,
    format_json,
    format_label,
    get_confluence_client,
    handle_errors,
    print_success,
    validate_label,
    validate_page_id,
)


def parse_labels(labels_str: str) -> list:
    """Parse comma-separated label string into list."""
    return [l.strip() for l in labels_str.split(",") if l.strip()]


@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Add label(s) to a Confluence page",
        epilog="""
Examples:
  python add_label.py 12345 --label documentation
  python add_label.py 12345 --labels doc,approved,v2
  python add_label.py 12345 -l api
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("page_id", help="Page or blog post ID")
    parser.add_argument("--label", "-l", help="Single label to add")
    parser.add_argument("--labels", help="Comma-separated list of labels to add")
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

    # Get labels to add
    if args.labels:
        labels = parse_labels(args.labels)
    elif args.label:
        labels = [args.label]
    else:
        raise ValidationError("Either --label or --labels is required")

    # Validate all labels
    validated_labels = []
    for label in labels:
        validated_labels.append(validate_label(label))

    # Get client
    client = get_confluence_client()

    # Add labels using v1 API (v2 API doesn't support POST for labels)
    # v1 API accepts an array of labels in a single request
    label_data = [
        {"prefix": "global", "name": label_name} for label_name in validated_labels
    ]

    results = client.post(
        f"/rest/api/content/{page_id}/label",
        json_data=label_data,
        operation="add labels",
    )

    # v1 API returns the list of labels
    if args.output == "text":
        for label in results.get(
            "results", results if isinstance(results, list) else []
        ):
            print(format_label(label))

    # Output summary
    if args.output == "json":
        print(format_json(results))
    else:
        if len(validated_labels) == 1:
            print_success(f"Added label '{validated_labels[0]}' to page {page_id}")
        else:
            print_success(f"Added {len(validated_labels)} labels to page {page_id}")


if __name__ == "__main__":
    main()
