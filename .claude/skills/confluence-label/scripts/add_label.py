#!/usr/bin/env python3
"""
Add label(s) to a Confluence page or blog post.

Examples:
    python add_label.py 12345 --label documentation
    python add_label.py 12345 --labels doc,approved,v2
    python add_label.py 12345 -l api --profile production
"""

import sys
import argparse
from pathlib import Path

# Add shared lib to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'shared' / 'scripts' / 'lib'))

from config_manager import get_confluence_client
from error_handler import handle_errors, ValidationError
from validators import validate_page_id, validate_label
from formatters import print_success, format_label, format_json


def parse_labels(labels_str: str) -> list:
    """Parse comma-separated label string into list."""
    return [l.strip() for l in labels_str.split(',') if l.strip()]


@handle_errors
def main():
    parser = argparse.ArgumentParser(
        description='Add label(s) to a Confluence page',
        epilog='''
Examples:
  python add_label.py 12345 --label documentation
  python add_label.py 12345 --labels doc,approved,v2
  python add_label.py 12345 -l api --profile production
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('page_id', help='Page or blog post ID')
    parser.add_argument('--label', '-l', help='Single label to add')
    parser.add_argument('--labels', help='Comma-separated list of labels to add')
    parser.add_argument('--profile', '-p', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args()

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
    client = get_confluence_client(profile=args.profile)

    # Add each label
    results = []
    for label_name in validated_labels:
        # Add label to page
        label_data = {
            'prefix': 'global',
            'name': label_name
        }

        result = client.post(
            f'/api/v2/pages/{page_id}/labels',
            json_data=label_data,
            operation=f'add label {label_name}'
        )
        results.append(result)

        if args.output == 'text':
            print(format_label(result))

    # Output
    if args.output == 'json':
        print(format_json(results))
    else:
        if len(validated_labels) == 1:
            print_success(f"Added label '{validated_labels[0]}' to page {page_id}")
        else:
            print_success(f"Added {len(validated_labels)} labels to page {page_id}")


if __name__ == '__main__':
    main()
