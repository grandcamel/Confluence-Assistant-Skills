"""Content property commands - CLI-only implementation."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import click

from confluence_assistant_skills_lib import (
    ValidationError,
    format_json,
    format_table,
    get_confluence_client,
    handle_errors,
    print_success,
    print_warning,
    validate_page_id,
)


@click.group(name="property")
def property_cmd() -> None:
    """Manage content properties (custom metadata)."""
    pass


@property_cmd.command(name="list")
@click.argument("page_id")
@click.option("--prefix", help="Filter properties by key prefix")
@click.option("--pattern", help="Filter properties by regex pattern")
@click.option(
    "--sort",
    type=click.Choice(["key", "version"]),
    default="key",
    help="Sort properties by field",
)
@click.option("--expand", help="Comma-separated fields to expand (e.g., version)")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def list_properties(
    page_id: str,
    prefix: str | None,
    pattern: str | None,
    sort: str,
    expand: str | None,
    verbose: bool,
    output: str,
) -> None:
    """List all properties on a page."""
    page_id = validate_page_id(page_id)

    client = get_confluence_client()

    # Get page info
    page = client.get(f"/api/v2/pages/{page_id}", operation="get page")
    page_title = page.get("title", "Unknown")

    # Get properties using v1 API
    params: dict[str, Any] = {
        "limit": 100,
    }

    if expand:
        params["expand"] = expand

    properties = []
    for prop in client.paginate(
        f"/rest/api/content/{page_id}/property",
        params=params,
        operation="list properties",
    ):
        key = prop.get("key", "")

        # Apply filters
        if prefix and not key.startswith(prefix):
            continue
        if pattern:
            try:
                if not re.search(pattern, key):
                    continue
            except re.error:
                raise ValidationError(f"Invalid regex pattern: {pattern}")

        properties.append(prop)

    # Sort properties
    if sort == "version":
        properties.sort(key=lambda p: p.get("version", {}).get("number", 0), reverse=True)
    else:
        properties.sort(key=lambda p: p.get("key", ""))

    if output == "json":
        click.echo(format_json({
            "page": {"id": page_id, "title": page_title},
            "properties": properties,
            "count": len(properties),
        }))
    else:
        click.echo(f"\nProperties on: {page_title} ({page_id})")
        click.echo(f"{'=' * 60}\n")

        if not properties:
            click.echo("No properties found.")
        else:
            if verbose:
                for prop in properties:
                    click.echo(f"Key: {prop.get('key', 'N/A')}")
                    click.echo(f"  ID: {prop.get('id', 'N/A')}")
                    click.echo(f"  Version: {prop.get('version', {}).get('number', 'N/A')}")
                    value = prop.get("value", {})
                    if isinstance(value, dict):
                        click.echo(f"  Value: {json.dumps(value, indent=4)[:200]}")
                    else:
                        click.echo(f"  Value: {str(value)[:200]}")
                    click.echo()
            else:
                data = []
                for prop in properties:
                    value = prop.get("value", {})
                    if isinstance(value, dict):
                        value_str = json.dumps(value)[:30]
                    else:
                        value_str = str(value)[:30]

                    data.append({
                        "key": prop.get("key", "")[:30],
                        "version": prop.get("version", {}).get("number", "N/A"),
                        "value": value_str,
                    })

                click.echo(format_table(
                    data,
                    columns=["key", "version", "value"],
                    headers=["Key", "Ver", "Value (preview)"],
                ))

    print_success(f"Found {len(properties)} property(ies)")


@property_cmd.command(name="get")
@click.argument("page_id")
@click.option("--key", "-k", help="Specific property key to retrieve")
@click.option("--expand", help="Comma-separated fields to expand (e.g., version)")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def get_properties(
    page_id: str,
    key: str | None,
    expand: str | None,
    output: str,
) -> None:
    """Get properties from a page. Optionally filter by key."""
    page_id = validate_page_id(page_id)

    client = get_confluence_client()

    # Get page info
    page = client.get(f"/api/v2/pages/{page_id}", operation="get page")
    page_title = page.get("title", "Unknown")

    params: dict[str, Any] = {}
    if expand:
        params["expand"] = expand

    if key:
        # Get specific property
        prop = client.get(
            f"/rest/api/content/{page_id}/property/{key}",
            params=params,
            operation="get property",
        )
        properties = [prop]
    else:
        # Get all properties
        properties = list(client.paginate(
            f"/rest/api/content/{page_id}/property",
            params=params,
            operation="get properties",
        ))

    if output == "json":
        result: dict[str, Any] = {
            "page": {"id": page_id, "title": page_title},
        }
        if key:
            result["property"] = properties[0] if properties else None
        else:
            result["properties"] = properties
            result["count"] = len(properties)
        click.echo(format_json(result))
    else:
        click.echo(f"\nProperties on: {page_title} ({page_id})")
        click.echo(f"{'=' * 60}\n")

        if not properties:
            click.echo("No properties found.")
        else:
            for prop in properties:
                click.echo(f"Key: {prop.get('key', 'N/A')}")
                click.echo(f"  ID: {prop.get('id', 'N/A')}")
                click.echo(f"  Version: {prop.get('version', {}).get('number', 'N/A')}")

                value = prop.get("value", {})
                if isinstance(value, dict):
                    click.echo("  Value (JSON):")
                    click.echo(f"    {json.dumps(value, indent=4)}")
                else:
                    click.echo(f"  Value: {value}")
                click.echo()

    print_success(f"Retrieved {len(properties)} property(ies)")


@property_cmd.command(name="set")
@click.argument("page_id")
@click.argument("key")
@click.option("--value", "-v", help="Property value (string or JSON)")
@click.option("--file", "-f", "file_path", type=click.Path(exists=True, path_type=Path), help="Read value from JSON file")
@click.option(
    "--update", is_flag=True, help="Update existing property (fetches current version)"
)
@click.option("--version", type=int, help="Explicit version number for update")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def set_property(
    page_id: str,
    key: str,
    value: str | None,
    file_path: Path | None,
    update: bool,
    version: int | None,
    output: str,
) -> None:
    """Set a property value."""
    page_id = validate_page_id(page_id)

    if not value and not file_path:
        raise ValidationError("Either --value or --file is required")
    if value and file_path:
        raise ValidationError("Cannot specify both --value and --file")

    if not key:
        raise ValidationError("Property key is required")

    client = get_confluence_client()

    # Get page info
    page = client.get(f"/api/v2/pages/{page_id}", operation="get page")
    page_title = page.get("title", "Unknown")

    # Parse value
    if file_path:
        content = file_path.read_text(encoding="utf-8")
        try:
            property_value = json.loads(content)
        except json.JSONDecodeError:
            property_value = content
    else:
        # Try to parse as JSON first
        try:
            property_value = json.loads(value or "")
        except json.JSONDecodeError:
            property_value = value

    # Build property data
    property_data: dict[str, Any] = {
        "key": key,
        "value": property_value,
    }

    if update or version is not None:
        # Get current version if not provided
        if version is None:
            try:
                current = client.get(
                    f"/rest/api/content/{page_id}/property/{key}",
                    operation="get current property",
                )
                version = current.get("version", {}).get("number", 0) + 1
            except Exception:
                # Property doesn't exist, create new
                version = 1

        property_data["version"] = {"number": version}

        # Update existing property
        result = client.put(
            f"/rest/api/content/{page_id}/property/{key}",
            json_data=property_data,
            operation="update property",
        )
    else:
        # Create new property
        result = client.post(
            f"/rest/api/content/{page_id}/property",
            json_data=property_data,
            operation="create property",
        )

    if output == "json":
        click.echo(format_json({
            "page": {"id": page_id, "title": page_title},
            "property": result,
        }))
    else:
        click.echo("\nProperty set successfully")
        click.echo(f"  Page: {page_title} ({page_id})")
        click.echo(f"  Key: {key}")
        click.echo(f"  Version: {result.get('version', {}).get('number', 'N/A')}")

        value_preview = result.get("value", {})
        if isinstance(value_preview, dict):
            value_preview = json.dumps(value_preview)[:100]
        click.echo(f"  Value: {str(value_preview)[:100]}")

    action = "Updated" if update else "Set"
    print_success(f"{action} property '{key}' on page {page_id}")


@property_cmd.command(name="delete")
@click.argument("page_id")
@click.argument("key")
@click.option("--force", is_flag=True, help="Delete without confirmation")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def delete_property(
    page_id: str,
    key: str,
    force: bool,
    output: str,
) -> None:
    """Delete a property."""
    page_id = validate_page_id(page_id)

    if not key:
        raise ValidationError("Property key is required")

    client = get_confluence_client()

    # Get page info
    page = client.get(f"/api/v2/pages/{page_id}", operation="get page")
    page_title = page.get("title", "Unknown")

    # Get property info before deletion
    try:
        client.get(
            f"/rest/api/content/{page_id}/property/{key}",
            operation="get property",
        )
        prop_exists = True
    except Exception:
        prop_exists = False

    if not prop_exists:
        if output == "json":
            click.echo(format_json({
                "page": {"id": page_id, "title": page_title},
                "key": key,
                "deleted": False,
                "error": "Property not found",
            }))
        else:
            print_warning(f"Property '{key}' not found on page {page_id}")
        return

    if not force:
        click.echo(f"\nYou are about to delete property: {key}")
        click.echo(f"  Page: {page_title} ({page_id})")
        print_warning("This action cannot be undone!")

        if not click.confirm("\nAre you sure?", default=False):
            click.echo("Delete cancelled.")
            return

    # Delete property
    client.delete(
        f"/rest/api/content/{page_id}/property/{key}",
        operation="delete property",
    )

    if output == "json":
        click.echo(format_json({
            "page": {"id": page_id, "title": page_title},
            "key": key,
            "deleted": True,
        }))
    else:
        click.echo("\nProperty deleted successfully")
        click.echo(f"  Page: {page_title} ({page_id})")
        click.echo(f"  Key: {key}")

    print_success(f"Deleted property '{key}' from page {page_id}")
