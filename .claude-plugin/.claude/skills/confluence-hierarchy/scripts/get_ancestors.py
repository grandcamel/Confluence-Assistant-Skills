#!/usr/bin/env python3
"""
Get all ancestor pages for a given page.

Ancestors are all parent pages from the current page up to the space root.
Useful for building breadcrumbs or understanding page hierarchy.

Examples:
    python get_ancestors.py 12345
    python get_ancestors.py 12345 --output json
    python get_ancestors.py 12345 --breadcrumb
"""

import argparse

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
        description="Get ancestor pages for a Confluence page",
        epilog="""
Examples:
  python get_ancestors.py 12345
  python get_ancestors.py 12345 --output json
  python get_ancestors.py 12345 --breadcrumb
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("page_id", help="Page ID")
    parser.add_argument(
        "--breadcrumb",
        action="store_true",
        help="Show as breadcrumb path (Title > Title > ...)",
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

    # Validate
    page_id = validate_page_id(args.page_id)

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Get page with ancestors
    result = client.get(
        f"/api/v2/pages/{page_id}",
        params={"include": "ancestors"},
        operation="get page ancestors",
    )

    ancestors = result.get("ancestors", [])

    # Output
    if args.output == "json":
        print(format_json(ancestors))
    elif args.breadcrumb:
        # Build breadcrumb path
        titles = [a["title"] for a in ancestors]
        titles.append(result["title"])
        print(" > ".join(titles))
    else:
        # Text format
        if not ancestors:
            print(f"Page '{result['title']}' has no ancestors (it's a root page)")
        else:
            print(f"Ancestors of '{result['title']}':\n")
            for i, ancestor in enumerate(ancestors, 1):
                print(f"{i}. {ancestor['title']} (ID: {ancestor['id']})")

    print_success(f"Retrieved {len(ancestors)} ancestor(s)")


if __name__ == "__main__":
    main()
