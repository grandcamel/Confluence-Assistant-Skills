#!/usr/bin/env python3
"""
Get CQL field and value suggestions.

Examples:
    python cql_suggest.py --fields
    python cql_suggest.py --field space
    python cql_suggest.py --operators
    python cql_suggest.py --functions
"""

import argparse

from confluence_assistant_skills_lib import (
    ValidationError,
    format_json,
    format_table,
    get_confluence_client,
    handle_errors,
    print_success,
)

# CQL Field Definitions
CQL_FIELDS = [
    {
        "name": "space",
        "type": "string",
        "description": "Space key (e.g., DOCS, KB)",
        "operators": ["=", "!=", "in", "not in"],
        "example": "space = 'DOCS'",
    },
    {
        "name": "title",
        "type": "string",
        "description": "Content title",
        "operators": ["=", "!=", "~", "!~"],
        "example": "title ~ 'API'",
    },
    {
        "name": "text",
        "type": "string",
        "description": "Full text search",
        "operators": ["~", "!~"],
        "example": "text ~ 'documentation'",
    },
    {
        "name": "type",
        "type": "enum",
        "description": "Content type",
        "values": ["page", "blogpost", "comment", "attachment"],
        "operators": ["=", "!=", "in", "not in"],
        "example": "type = page",
    },
    {
        "name": "label",
        "type": "string",
        "description": "Content label",
        "operators": ["=", "!=", "in", "not in"],
        "example": "label = 'api'",
    },
    {
        "name": "creator",
        "type": "string",
        "description": "Content creator (email or currentUser())",
        "operators": ["=", "!=", "in", "not in"],
        "example": "creator = currentUser()",
    },
    {
        "name": "contributor",
        "type": "string",
        "description": "Any contributor (creator or editor)",
        "operators": ["=", "!=", "in", "not in"],
        "example": "contributor = 'user@example.com'",
    },
    {
        "name": "created",
        "type": "date",
        "description": "Creation date",
        "operators": ["=", "!=", ">", "<", ">=", "<="],
        "example": "created >= '2024-01-01'",
    },
    {
        "name": "lastModified",
        "type": "date",
        "description": "Last modified date",
        "operators": ["=", "!=", ">", "<", ">=", "<="],
        "example": "lastModified > startOfMonth()",
    },
    {
        "name": "parent",
        "type": "string",
        "description": "Parent page ID",
        "operators": ["=", "!="],
        "example": "parent = 12345",
    },
    {
        "name": "ancestor",
        "type": "string",
        "description": "Ancestor page ID (includes all parents up tree)",
        "operators": ["=", "!="],
        "example": "ancestor = 12345",
    },
    {
        "name": "id",
        "type": "string",
        "description": "Content ID",
        "operators": ["=", "!=", "in", "not in"],
        "example": "id = 12345",
    },
    {
        "name": "macro",
        "type": "string",
        "description": "Macro name present in content",
        "operators": ["=", "!="],
        "example": "macro = 'code'",
    },
]

# CQL Operators
CQL_OPERATORS = [
    {
        "operator": "=",
        "description": "Equals",
        "types": ["string", "enum", "date", "number"],
    },
    {
        "operator": "!=",
        "description": "Not equals",
        "types": ["string", "enum", "date", "number"],
    },
    {"operator": "~", "description": "Contains (text search)", "types": ["string"]},
    {"operator": "!~", "description": "Does not contain", "types": ["string"]},
    {"operator": ">", "description": "Greater than", "types": ["date", "number"]},
    {"operator": "<", "description": "Less than", "types": ["date", "number"]},
    {
        "operator": ">=",
        "description": "Greater than or equal",
        "types": ["date", "number"],
    },
    {
        "operator": "<=",
        "description": "Less than or equal",
        "types": ["date", "number"],
    },
    {"operator": "in", "description": "In list", "types": ["string", "enum", "number"]},
    {
        "operator": "not in",
        "description": "Not in list",
        "types": ["string", "enum", "number"],
    },
]

# CQL Functions
CQL_FUNCTIONS = [
    {"name": "currentUser()", "description": "Current logged in user", "type": "user"},
    {"name": "startOfDay()", "description": "Start of today (00:00)", "type": "date"},
    {"name": "startOfWeek()", "description": "Start of this week", "type": "date"},
    {"name": "startOfMonth()", "description": "Start of this month", "type": "date"},
    {"name": "startOfYear()", "description": "Start of this year", "type": "date"},
    {"name": "endOfDay()", "description": "End of today (23:59)", "type": "date"},
    {"name": "endOfWeek()", "description": "End of this week", "type": "date"},
    {"name": "endOfMonth()", "description": "End of this month", "type": "date"},
    {"name": "endOfYear()", "description": "End of this year", "type": "date"},
    {"name": "now()", "description": "Current date/time", "type": "date"},
]


def get_field_values(client, field_name):
    """
    Get suggested values for a specific CQL field.

    Args:
        client: Confluence client
        field_name: Name of the field

    Returns:
        List of suggested values
    """
    values = []

    if field_name == "space":
        # Get all spaces
        try:
            for space in client.paginate("/api/v2/spaces", limit=100):
                values.append(
                    {
                        "value": space["key"],
                        "label": f"{space['key']} - {space.get('name', '')}",
                    }
                )
        except Exception:
            # If API call fails, return empty
            pass

    elif field_name == "type":
        # Static content types
        values = [
            {"value": "page", "label": "Page"},
            {"value": "blogpost", "label": "Blog Post"},
            {"value": "comment", "label": "Comment"},
            {"value": "attachment", "label": "Attachment"},
        ]

    elif field_name == "label":
        # Get popular labels (this is more complex, would need CQL search)
        # For now, return common examples
        values = [
            {"value": "documentation", "label": "documentation"},
            {"value": "api", "label": "api"},
            {"value": "tutorial", "label": "tutorial"},
            {"value": "reference", "label": "reference"},
            {"value": "howto", "label": "howto"},
        ]

    elif field_name in ["creator", "contributor"]:
        # User functions
        values = [
            {"value": "currentUser()", "label": "Current user"},
        ]

    elif field_name in ["created", "lastModified"]:
        # Date functions
        values = [f for f in CQL_FUNCTIONS if f["type"] == "date"]
        values = [
            {"value": f["name"], "label": f"{f['name']} - {f['description']}"}
            for f in values
        ]

    return values


@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Get CQL field and value suggestions",
        epilog="""
Examples:
  # List all CQL fields
  python cql_suggest.py --fields

  # Get suggested values for a field
  python cql_suggest.py --field space
  python cql_suggest.py --field type

  # List operators
  python cql_suggest.py --operators

  # List functions
  python cql_suggest.py --functions
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--fields", action="store_true", help="List all available CQL fields"
    )
    parser.add_argument(
        "--field", metavar="NAME", help="Get suggested values for a specific field"
    )
    parser.add_argument(
        "--operators", action="store_true", help="List all CQL operators"
    )
    parser.add_argument(
        "--functions", action="store_true", help="List all CQL functions"
    )
    parser.add_argument("--profile", help="Confluence profile to use")
    parser.add_argument(
        "--output",
        "-o",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    args = parser.parse_args(argv)

    # Validate that at least one option is provided
    if not any([args.fields, args.field, args.operators, args.functions]):
        parser.error("Must specify --fields, --field, --operators, or --functions")

    # List all fields
    if args.fields:
        if args.output == "json":
            print(format_json(CQL_FIELDS))
        else:
            print("\nAvailable CQL Fields:\n")
            print(
                format_table(
                    CQL_FIELDS,
                    columns=["name", "type", "description", "example"],
                    headers=["Field", "Type", "Description", "Example"],
                )
            )
            print()

    # List operators
    if args.operators:
        if args.output == "json":
            print(format_json(CQL_OPERATORS))
        else:
            print("\nCQL Operators:\n")
            print(
                format_table(
                    CQL_OPERATORS,
                    columns=["operator", "description"],
                    headers=["Operator", "Description"],
                )
            )
            print()

    # List functions
    if args.functions:
        if args.output == "json":
            print(format_json(CQL_FUNCTIONS))
        else:
            print("\nCQL Functions:\n")
            print(
                format_table(
                    CQL_FUNCTIONS,
                    columns=["name", "description"],
                    headers=["Function", "Description"],
                )
            )
            print()

    # Get values for a specific field
    if args.field:
        field_name = args.field.lower()

        # Find the field definition
        field_def = next(
            (f for f in CQL_FIELDS if f["name"].lower() == field_name), None
        )

        if not field_def:
            raise ValidationError(f"Unknown field: {args.field}")

        # Get client if needed
        client = None
        if field_name in ["space", "label"]:
            client = get_confluence_client(profile=args.profile)

        values = get_field_values(client, field_name)

        if args.output == "json":
            print(
                format_json(
                    {
                        "field": field_def["name"],
                        "type": field_def["type"],
                        "values": values,
                    }
                )
            )
        else:
            print(f"\nSuggested values for '{field_def['name']}':\n")

            if values:
                for v in values:
                    if isinstance(v, dict):
                        print(f"  {v['value']:<30} {v.get('label', '')}")
                    else:
                        print(f"  {v}")
            else:
                print("  (No predefined values - use any string)")

            print(f"\nValid operators: {', '.join(field_def.get('operators', []))}")
            print(f"Example: {field_def.get('example', '')}")
            print()

    print_success("Suggestions complete")


if __name__ == "__main__":
    main()
