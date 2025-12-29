#!/usr/bin/env python3
"""
Interactive CQL query builder.

Guides users through building CQL queries step-by-step.

Examples:
    python cql_interactive.py
    python cql_interactive.py --space DOCS
    python cql_interactive.py --type page
"""

import sys
import argparse
from pathlib import Path

# Add shared lib to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'shared' / 'scripts' / 'lib'))

from config_manager import get_confluence_client
from error_handler import handle_errors, ValidationError
from validators import validate_cql, validate_space_key
from formatters import print_success, print_info, format_search_results


# Import field/operator definitions from cql_suggest
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

try:
    from cql_suggest import CQL_FIELDS, CQL_OPERATORS, CQL_FUNCTIONS, get_field_values
except ImportError:
    # Fallback if cql_suggest not found
    CQL_FIELDS = []
    CQL_OPERATORS = []
    CQL_FUNCTIONS = []

    def get_field_values(client, field_name):
        return []


def prompt_choice(prompt, choices, allow_custom=False):
    """
    Prompt user to select from a list of choices.

    Args:
        prompt: Prompt message
        choices: List of choices (strings or dicts with 'value' and 'label')
        allow_custom: Allow custom input

    Returns:
        Selected value
    """
    print(f"\n{prompt}")
    print("-" * 60)

    # Display choices
    for i, choice in enumerate(choices, 1):
        if isinstance(choice, dict):
            label = choice.get('label', choice.get('value', str(choice)))
            print(f"  {i}. {label}")
        else:
            print(f"  {i}. {choice}")

    if allow_custom:
        print(f"  {len(choices) + 1}. (Enter custom value)")

    print()

    while True:
        try:
            selection = input("Select (number or 'q' to quit): ").strip()

            if selection.lower() == 'q':
                print("Cancelled.")
                sys.exit(0)

            idx = int(selection) - 1

            if 0 <= idx < len(choices):
                choice = choices[idx]
                if isinstance(choice, dict):
                    return choice.get('value', choice)
                return choice

            elif allow_custom and idx == len(choices):
                custom = input("Enter value: ").strip()
                return custom

            else:
                print("Invalid selection. Try again.")

        except (ValueError, KeyError):
            print("Invalid input. Enter a number.")


def quote_value(value, field_type):
    """
    Quote a value appropriately based on field type.

    Args:
        value: The value to quote
        field_type: The field type

    Returns:
        Properly quoted value
    """
    # Don't quote if already quoted
    if value.startswith("'") or value.startswith('"'):
        return value

    # Don't quote functions
    if value.endswith("()"):
        return value

    # Don't quote numbers for numeric fields
    if field_type == "number" and value.replace(".", "").isdigit():
        return value

    # Don't quote bare type values
    if value in ["page", "blogpost", "comment", "attachment"]:
        return value

    # Quote strings
    return f"'{value}'"


def build_condition(client):
    """
    Build a single CQL condition interactively.

    Args:
        client: Confluence client for value suggestions

    Returns:
        CQL condition string
    """
    # Select field
    field = prompt_choice(
        "Select field:",
        [{"value": f['name'], "label": f"{f['name']} - {f['description']}"} for f in CQL_FIELDS]
    )

    field_def = next((f for f in CQL_FIELDS if f['name'] == field), None)
    if not field_def:
        raise ValidationError(f"Unknown field: {field}")

    field_type = field_def['type']

    # Select operator
    valid_operators = field_def.get('operators', ['=', '!='])
    operator = prompt_choice(
        f"Select operator for '{field}':",
        valid_operators
    )

    # Get value
    if operator in ['in', 'not in']:
        # Multiple values
        print(f"\nEnter values for '{field}' (comma-separated):")
        values_str = input("> ").strip()
        values = [v.strip() for v in values_str.split(',')]
        quoted_values = [quote_value(v, field_type) for v in values]
        value = f"({', '.join(quoted_values)})"

    else:
        # Single value - show suggestions if available
        suggestions = get_field_values(client, field)

        if suggestions:
            value = prompt_choice(
                f"Select value for '{field}':",
                suggestions,
                allow_custom=True
            )
        else:
            print(f"\nEnter value for '{field}':")
            value = input("> ").strip()

        value = quote_value(value, field_type)

    # Build condition
    return f"{field} {operator} {value}"


def build_query_interactive(client, initial_parts=None):
    """
    Build a complete CQL query interactively.

    Args:
        client: Confluence client
        initial_parts: Initial query parts (from pre-filters)

    Returns:
        Complete CQL query string
    """
    parts = initial_parts or []

    while True:
        # Show current query
        if parts:
            current = " ".join(parts)
            print(f"\n{'='*60}")
            print(f"Current query: {current}")
            print('='*60)

        # Build a condition
        condition = build_condition(client)
        parts.append(condition)

        # Ask what to do next
        next_action = prompt_choice(
            "What next?",
            [
                "Add AND condition",
                "Add OR condition",
                "Add ORDER BY",
                "Finish query"
            ]
        )

        if next_action == "Add AND condition":
            parts.append("AND")
        elif next_action == "Add OR condition":
            parts.append("OR")
        elif next_action == "Add ORDER BY":
            # Select field to order by
            orderable_fields = ["created", "lastModified", "title", "id"]
            order_field = prompt_choice("Order by:", orderable_fields)

            # Select direction
            direction = prompt_choice("Direction:", ["ASC", "DESC"])

            parts.append(f"ORDER BY {order_field} {direction}")
            break
        else:
            # Finish
            break

    return " ".join(parts)


@handle_errors
def main():
    parser = argparse.ArgumentParser(
        description='Interactive CQL query builder',
        epilog='''
Examples:
  # Start with blank query
  python cql_interactive.py

  # Pre-filter by space
  python cql_interactive.py --space DOCS

  # Pre-filter by type
  python cql_interactive.py --type page

  # Combine pre-filters
  python cql_interactive.py --space DOCS --type page
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--space', help='Pre-filter by space key')
    parser.add_argument('--type', choices=['page', 'blogpost', 'comment', 'attachment'],
                        help='Pre-filter by content type')
    parser.add_argument('--profile', help='Confluence profile to use')
    parser.add_argument('--limit', '-l', type=int, default=25,
                        help='Maximum results to show (default: 25)')
    parser.add_argument('--execute', action='store_true',
                        help='Execute query after building')

    args = parser.parse_args()

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Build initial parts from pre-filters
    initial_parts = []

    if args.space:
        space_key = validate_space_key(args.space)
        initial_parts.append(f"space = '{space_key}'")

    if args.type:
        initial_parts.append(f"type = {args.type}")

    if initial_parts:
        initial_parts.append("AND")

    # Show welcome
    print("\n" + "="*60)
    print("  Interactive CQL Query Builder")
    print("="*60)
    print("\nBuild a CQL query step-by-step.")
    print("Enter 'q' at any prompt to quit.\n")

    if initial_parts:
        print(f"Starting with: {' '.join(initial_parts[:-1])}\n")

    # Build query
    query = build_query_interactive(client, initial_parts)

    # Remove trailing AND/OR if present
    query = query.rstrip().rstrip('AND').rstrip('OR').strip()

    # Show final query
    print("\n" + "="*60)
    print("Final Query:")
    print("="*60)
    print(query)
    print()

    # Validate
    validate_cql(query)
    print_success("Query is valid")

    # Ask if user wants to execute
    if not args.execute:
        execute = input("\nExecute this query? (y/n): ").strip().lower()
        if execute != 'y':
            print("\nQuery built but not executed.")
            print(f"To execute later, use:\n  python cql_search.py \"{query}\"")
            return

    # Execute query
    print_info(f"Executing query with limit={args.limit}...")

    params = {
        'cql': query,
        'limit': min(args.limit, 50),
        'expand': 'content.space'
    }

    results = []
    start = 0

    while len(results) < args.limit:
        params['start'] = start
        response = client.get('/rest/api/search', params=params, operation='CQL search')

        batch = response.get('results', [])
        if not batch:
            break

        results.extend(batch)
        start += len(batch)

        if len(batch) < params['limit']:
            break

    results = results[:args.limit]

    # Show results
    print()
    print(format_search_results(results, show_excerpt=True))

    print_success(f"Found {len(results)} result(s)")

    # Offer to save query
    save = input("\nSave this query to history? (y/n): ").strip().lower()
    if save == 'y':
        # Import and use cql_history if available
        try:
            import json
            from datetime import datetime

            history_file = Path.home() / '.confluence_cql_history.json'
            history = []

            if history_file.exists():
                history = json.loads(history_file.read_text())

            history.append({
                'query': query,
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'results_count': len(results)
            })

            # Keep last 100 queries
            history = history[-100:]

            history_file.write_text(json.dumps(history, indent=2))
            print_success(f"Query saved to {history_file}")

        except Exception as e:
            print(f"Warning: Could not save to history: {e}")


if __name__ == '__main__':
    main()
