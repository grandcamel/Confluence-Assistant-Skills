"""Search commands - CLI-only implementation."""

from __future__ import annotations

import contextlib
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import click

from confluence_assistant_skills_lib import (
    ValidationError,
    format_json,
    format_table,
    get_confluence_client,
    handle_errors,
    print_info,
    print_success,
    print_warning,
    validate_limit,
    validate_space_key,
)

# CQL field and operator reference data
CQL_FIELDS = [
    {"name": "space", "description": "Space key", "example": 'space = "DOCS"'},
    {"name": "title", "description": "Page title", "example": 'title ~ "API"'},
    {"name": "text", "description": "Full text search", "example": 'text ~ "config"'},
    {"name": "type", "description": "Content type", "example": "type = page"},
    {"name": "label", "description": "Content label", "example": 'label = "docs"'},
    {"name": "creator", "description": "Content creator", "example": "creator = currentUser()"},
    {"name": "contributor", "description": "Any contributor", "example": 'contributor = "email"'},
    {"name": "created", "description": "Creation date", "example": 'created >= "2024-01-01"'},
    {"name": "lastModified", "description": "Last modified", "example": "lastModified > startOfWeek()"},
    {"name": "parent", "description": "Parent page ID", "example": "parent = 12345"},
    {"name": "ancestor", "description": "Ancestor page ID", "example": "ancestor = 12345"},
    {"name": "id", "description": "Content ID", "example": "id = 12345"},
]

CQL_OPERATORS = [
    {"operator": "=", "description": "Equals (exact match)"},
    {"operator": "!=", "description": "Not equals"},
    {"operator": "~", "description": "Contains (text search)"},
    {"operator": "!~", "description": "Does not contain"},
    {"operator": ">", "description": "Greater than"},
    {"operator": ">=", "description": "Greater than or equal"},
    {"operator": "<", "description": "Less than"},
    {"operator": "<=", "description": "Less than or equal"},
    {"operator": "in", "description": "In list of values"},
    {"operator": "not in", "description": "Not in list of values"},
]

CQL_FUNCTIONS = [
    {"function": "currentUser()", "description": "Current authenticated user"},
    {"function": "startOfDay()", "description": "Start of current day"},
    {"function": "startOfWeek()", "description": "Start of current week"},
    {"function": "startOfMonth()", "description": "Start of current month"},
    {"function": "startOfYear()", "description": "Start of current year"},
    {"function": "endOfDay()", "description": "End of current day"},
    {"function": "endOfWeek()", "description": "End of current week"},
    {"function": "endOfMonth()", "description": "End of current month"},
    {"function": "endOfYear()", "description": "End of current year"},
    {"function": 'now("-7d")', "description": "Current time minus 7 days"},
]

CONTENT_TYPES = ["page", "blogpost", "comment", "attachment"]


def _build_cql_from_text(query: str, space: str | None, content_type: str | None) -> str:
    """Build CQL query from text search parameters."""
    parts = [f'text ~ "{query}"']

    if space:
        parts.append(f'space = "{space}"')

    if content_type:
        parts.append(f"type = {content_type}")

    return " AND ".join(parts)


def _format_search_result(result: dict[str, Any], show_excerpts: bool = False) -> dict[str, Any]:
    """Format a search result for display."""
    content = result.get("content", result)

    formatted = {
        "id": content.get("id", ""),
        "title": content.get("title", "Untitled"),
        "type": content.get("type", "page"),
        "space": content.get("space", {}).get("key", result.get("resultGlobalContainer", {}).get("title", "")),
    }

    if show_excerpts:
        excerpt = result.get("excerpt", "")
        if excerpt:
            # Clean up excerpt HTML
            excerpt = excerpt.replace("<b>", "").replace("</b>", "")
            excerpt = excerpt.replace("@@@hl@@@", "").replace("@@@endhl@@@", "")
            formatted["excerpt"] = excerpt[:200]

    return formatted


def _get_history_file() -> Path:
    """Get path to CQL history file."""
    cache_dir = Path.home() / ".cache" / "confluence-assistant-skills"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "cql_history.json"


def _load_history() -> list[dict[str, Any]]:
    """Load CQL query history."""
    history_file = _get_history_file()
    if history_file.exists():
        try:
            return json.loads(history_file.read_text())
        except (json.JSONDecodeError, OSError):
            return []
    return []


def _save_history(history: list[dict[str, Any]]) -> None:
    """Save CQL query history."""
    history_file = _get_history_file()
    history_file.write_text(json.dumps(history, indent=2))


def _add_to_history(cql: str, result_count: int) -> None:
    """Add a query to history."""
    history = _load_history()

    entry = {
        "query": cql,
        "timestamp": datetime.now().isoformat(),
        "result_count": result_count,
    }

    # Avoid duplicate consecutive queries
    if history and history[0].get("query") == cql:
        history[0] = entry
    else:
        history.insert(0, entry)

    # Keep last 100 queries
    history = history[:100]
    _save_history(history)


@click.group()
def search() -> None:
    """Search Confluence content."""
    pass


@search.command(name="cql")
@click.argument("cql")
@click.option(
    "--limit", "-l", type=int, default=25, help="Maximum results (default: 25)"
)
@click.option("--show-excerpts", is_flag=True, help="Show content excerpts")
@click.option("--show-labels", is_flag=True, help="Show content labels")
@click.option("--show-ancestors", is_flag=True, help="Show ancestor pages")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def cql_search(
    cql: str,
    limit: int,
    show_excerpts: bool,
    show_labels: bool,
    show_ancestors: bool,
    output: str,
) -> None:
    """Execute CQL queries against Confluence."""
    if not cql or not cql.strip():
        raise ValidationError("CQL query is required")

    limit = validate_limit(limit, max_value=250)

    client = get_confluence_client()

    params: dict[str, Any] = {
        "cql": cql.strip(),
        "limit": min(limit, 25),  # API max per request
    }

    expand = []
    if show_excerpts:
        expand.append("content.body.view")
    if show_labels:
        expand.append("content.metadata.labels")
    if show_ancestors:
        expand.append("content.ancestors")

    if expand:
        params["expand"] = ",".join(expand)

    results = []
    for result in client.paginate(
        "/rest/api/search", params=params, operation="CQL search"
    ):
        results.append(result)
        if len(results) >= limit:
            break

    # Add to history
    _add_to_history(cql.strip(), len(results))

    if output == "json":
        click.echo(format_json({
            "query": cql,
            "count": len(results),
            "results": results,
        }))
    else:
        click.echo(f"\nCQL: {cql}")
        click.echo(f"{'=' * 60}\n")

        if not results:
            click.echo("No results found.")
        else:
            data = []
            for r in results:
                formatted = _format_search_result(r, show_excerpts)
                row = {
                    "id": formatted["id"],
                    "title": formatted["title"][:40],
                    "type": formatted["type"],
                    "space": formatted["space"],
                }

                if show_labels:
                    content = r.get("content", r)
                    labels = content.get("metadata", {}).get("labels", {}).get("results", [])
                    row["labels"] = ", ".join(lbl.get("name", "") for lbl in labels[:3])

                data.append(row)

            columns = ["id", "title", "type", "space"]
            headers = ["ID", "Title", "Type", "Space"]

            if show_labels:
                columns.append("labels")
                headers.append("Labels")

            click.echo(format_table(data, columns=columns, headers=headers))

            if show_excerpts:
                click.echo("\n--- Excerpts ---\n")
                for r in results[:5]:  # Show first 5 excerpts
                    formatted = _format_search_result(r, True)
                    if formatted.get("excerpt"):
                        click.echo(f"[{formatted['id']}] {formatted['title']}")
                        click.echo(f"    {formatted['excerpt']}\n")

    print_success(f"Found {len(results)} result(s)")


@search.command(name="content")
@click.argument("query")
@click.option("--space", "-s", help="Limit to specific space")
@click.option("--type", "content_type", help="Content type (page, blogpost)")
@click.option("--limit", "-l", type=int, default=25, help="Maximum results")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def search_content(
    query: str,
    space: str | None,
    content_type: str | None,
    limit: int,
    output: str,
) -> None:
    """Search content by text."""
    if not query or not query.strip():
        raise ValidationError("Search query is required")

    if space:
        space = validate_space_key(space)

    if content_type and content_type.lower() not in ("page", "blogpost", "all"):
        raise ValidationError("Content type must be 'page', 'blogpost', or 'all'")

    limit = validate_limit(limit, max_value=250)

    # Build CQL query
    cql = _build_cql_from_text(query.strip(), space, content_type)

    client = get_confluence_client()

    params: dict[str, Any] = {
        "cql": cql,
        "limit": min(limit, 25),
    }

    results = []
    for result in client.paginate(
        "/rest/api/search", params=params, operation="content search"
    ):
        results.append(result)
        if len(results) >= limit:
            break

    if output == "json":
        click.echo(format_json({
            "query": query,
            "cql": cql,
            "count": len(results),
            "results": results,
        }))
    else:
        click.echo(f"\nSearch: {query}")
        if space:
            click.echo(f"Space: {space}")
        click.echo(f"{'=' * 60}\n")

        if not results:
            click.echo("No results found.")
        else:
            data = []
            for r in results:
                formatted = _format_search_result(r)
                data.append({
                    "id": formatted["id"],
                    "title": formatted["title"][:50],
                    "type": formatted["type"],
                    "space": formatted["space"],
                })

            click.echo(format_table(
                data,
                columns=["id", "title", "type", "space"],
                headers=["ID", "Title", "Type", "Space"],
            ))

    print_success(f"Found {len(results)} result(s)")


@search.command(name="validate")
@click.argument("cql")
@handle_errors
def cql_validate(cql: str) -> None:
    """Validate a CQL query syntax."""
    if not cql or not cql.strip():
        raise ValidationError("CQL query is required")

    client = get_confluence_client()

    # Try to execute the query with limit 0 to validate syntax
    try:
        client.get(
            "/rest/api/search",
            params={"cql": cql.strip(), "limit": 0},
            operation="validate CQL",
        )
        print_success(f"CQL query is valid: {cql}")
    except Exception as e:
        error_msg = str(e)
        print_warning(f"CQL query validation failed: {error_msg}")

        # Provide suggestions
        click.echo("\n--- CQL Tips ---")
        click.echo("• Use double quotes for values: space = \"DOCS\"")
        click.echo("• Use ~ for text search: text ~ \"search term\"")
        click.echo("• Dates format: YYYY-MM-DD or functions like startOfWeek()")
        click.echo("\nRun 'confluence search suggest --fields' for available fields")


@search.command(name="suggest")
@click.option("--fields", is_flag=True, help="List all CQL fields")
@click.option("--field", help="Get values for a specific field")
@click.option("--operators", is_flag=True, help="List all CQL operators")
@click.option("--functions", is_flag=True, help="List all CQL functions")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def cql_suggest(
    fields: bool,
    field: str | None,
    operators: bool,
    functions: bool,
    output: str,
) -> None:
    """Get CQL field and value suggestions."""
    if not any([fields, field, operators, functions]):
        raise ValidationError(
            "Specify at least one option: --fields, --field, --operators, or --functions"
        )

    result: dict[str, Any] = {}

    if fields:
        result["fields"] = CQL_FIELDS

    if field:
        # Get values for specific field
        field_lower = field.lower()
        if field_lower == "space":
            client = get_confluence_client()
            spaces = list(client.paginate(
                "/api/v2/spaces", params={"limit": 25}, operation="get spaces"
            ))
            result["space_values"] = [s.get("key") for s in spaces]
        elif field_lower == "type":
            result["type_values"] = CONTENT_TYPES
        else:
            result["note"] = f"Dynamic values for '{field}' - check your Confluence instance"

    if operators:
        result["operators"] = CQL_OPERATORS

    if functions:
        result["functions"] = CQL_FUNCTIONS

    if output == "json":
        click.echo(format_json(result))
    else:
        if fields:
            click.echo("\n--- CQL Fields ---\n")
            for f in CQL_FIELDS:
                click.echo(f"  {f['name']:15} - {f['description']}")
                click.echo(f"                    Example: {f['example']}\n")

        if field:
            click.echo(f"\n--- Values for '{field}' ---\n")
            if "space_values" in result:
                for s in result["space_values"]:
                    click.echo(f"  {s}")
            elif "type_values" in result:
                for t in result["type_values"]:
                    click.echo(f"  {t}")
            else:
                click.echo(f"  {result.get('note', 'No suggestions available')}")

        if operators:
            click.echo("\n--- CQL Operators ---\n")
            for op in CQL_OPERATORS:
                click.echo(f"  {op['operator']:10} - {op['description']}")

        if functions:
            click.echo("\n--- CQL Functions ---\n")
            for fn in CQL_FUNCTIONS:
                click.echo(f"  {fn['function']:20} - {fn['description']}")

    print_success("CQL suggestions retrieved")


@search.command(name="export")
@click.argument("cql")
@click.option(
    "--format",
    "-f",
    "export_format",
    type=click.Choice(["csv", "json"]),
    default="csv",
    help="Export format",
)
@click.option("--output", "-o", "output_file", required=True, help="Output file path")
@click.option("--columns", help="Columns to include (comma-separated)")
@click.option("--limit", "-l", type=int, help="Maximum results to export")
@handle_errors
def export_results(
    cql: str,
    export_format: str,
    output_file: str,
    columns: str | None,
    limit: int | None,
) -> None:
    """Export search results to file."""
    if not cql or not cql.strip():
        raise ValidationError("CQL query is required")

    if limit:
        limit = validate_limit(limit, max_value=10000)

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Default columns
    default_columns = ["id", "title", "type", "space", "created", "lastModified"]
    selected_columns = columns.split(",") if columns else default_columns

    client = get_confluence_client()

    params: dict[str, Any] = {
        "cql": cql.strip(),
        "limit": 25,
        "expand": "content.space,content.version",
    }

    results = []
    print_info(f"Executing query: {cql}")

    for result in client.paginate(
        "/rest/api/search", params=params, operation="export search"
    ):
        content = result.get("content", result)
        row = {
            "id": content.get("id", ""),
            "title": content.get("title", ""),
            "type": content.get("type", ""),
            "space": content.get("space", {}).get("key", ""),
            "created": content.get("version", {}).get("when", "")[:10] if content.get("version") else "",
            "lastModified": result.get("lastModified", "")[:10] if result.get("lastModified") else "",
            "url": result.get("url", ""),
        }
        results.append(row)

        if limit and len(results) >= limit:
            break

        if len(results) % 100 == 0:
            print_info(f"  Processed {len(results)} results...")

    # Write to file
    if export_format == "csv":
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=selected_columns, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(results)
    else:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

    print_success(f"Exported {len(results)} results to {output_path}")


@search.command(name="stream-export")
@click.argument("cql")
@click.option(
    "--format",
    "-f",
    "export_format",
    type=click.Choice(["csv", "json"]),
    help="Export format (inferred from extension if not specified)",
)
@click.option("--output", "-o", "output_file", required=True, help="Output file path")
@click.option("--columns", help="Columns to include (comma-separated)")
@click.option(
    "--batch-size", type=int, default=100, help="Records per batch (default: 100)"
)
@click.option("--resume", is_flag=True, help="Resume from last checkpoint")
@handle_errors
def streaming_export(
    cql: str,
    export_format: str | None,
    output_file: str,
    columns: str | None,
    batch_size: int,
    resume: bool,
) -> None:
    """Stream export large result sets."""
    if not cql or not cql.strip():
        raise ValidationError("CQL query is required")

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Infer format from extension if not specified
    if not export_format:
        ext = output_path.suffix.lower()
        export_format = "json" if ext == ".json" else "csv"

    checkpoint_file = output_path.with_suffix(".checkpoint")

    start_index = 0
    if resume and checkpoint_file.exists():
        try:
            checkpoint = json.loads(checkpoint_file.read_text())
            start_index = checkpoint.get("index", 0)
            print_info(f"Resuming from index {start_index}")
        except (json.JSONDecodeError, OSError):
            pass

    default_columns = ["id", "title", "type", "space", "created", "lastModified"]
    selected_columns = columns.split(",") if columns else default_columns

    client = get_confluence_client()

    params: dict[str, Any] = {
        "cql": cql.strip(),
        "limit": min(batch_size, 25),
        "start": start_index,
        "expand": "content.space,content.version",
    }

    results = []
    total_processed = start_index

    print_info(f"Starting streaming export: {cql}")

    for result in client.paginate(
        "/rest/api/search", params=params, operation="stream export"
    ):
        content = result.get("content", result)
        row = {
            "id": content.get("id", ""),
            "title": content.get("title", ""),
            "type": content.get("type", ""),
            "space": content.get("space", {}).get("key", ""),
            "created": content.get("version", {}).get("when", "")[:10] if content.get("version") else "",
            "lastModified": result.get("lastModified", "")[:10] if result.get("lastModified") else "",
            "url": result.get("url", ""),
        }
        results.append(row)
        total_processed += 1

        # Save checkpoint periodically
        if total_processed % batch_size == 0:
            checkpoint_file.write_text(json.dumps({"index": total_processed}))
            print_info(f"  Checkpoint at {total_processed} results...")

    # Write final results
    if export_format == "csv":
        mode = "a" if resume and output_path.exists() else "w"
        with open(output_path, mode, newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=selected_columns, extrasaction="ignore")
            if mode == "w":
                writer.writeheader()
            writer.writerows(results)
    else:
        # For JSON, we need to merge with existing
        existing = []
        if resume and output_path.exists():
            with contextlib.suppress(json.JSONDecodeError, OSError):
                existing = json.loads(output_path.read_text())

        existing.extend(results)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)

    # Clean up checkpoint
    if checkpoint_file.exists():
        checkpoint_file.unlink()

    print_success(f"Exported {total_processed} total results to {output_path}")


@search.group(name="history")
def history_group() -> None:
    """Manage CQL query history."""
    pass


@history_group.command(name="list")
@click.option("--limit", "-l", type=int, default=20, help="Number of recent queries")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def history_list(limit: int | None, output: str) -> None:
    """List recent queries."""
    history = _load_history()

    if limit:
        history = history[:limit]

    if output == "json":
        click.echo(format_json({"history": history, "count": len(history)}))
    else:
        if not history:
            click.echo("No query history found.")
        else:
            click.echo("\n--- Recent Queries ---\n")
            for i, entry in enumerate(history, 1):
                timestamp = entry.get("timestamp", "")[:16].replace("T", " ")
                count = entry.get("result_count", "?")
                query = entry.get("query", "")[:60]
                click.echo(f"  [{i:2}] {timestamp}  ({count} results)")
                click.echo(f"       {query}")
                if len(entry.get("query", "")) > 60:
                    click.echo("       ...")
                click.echo()

    print_success(f"Showing {len(history)} query(ies)")


@history_group.command(name="search")
@click.argument("keyword")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def history_search(keyword: str, output: str) -> None:
    """Search history for queries containing keyword."""
    history = _load_history()

    matches = [
        entry for entry in history
        if keyword.lower() in entry.get("query", "").lower()
    ]

    if output == "json":
        click.echo(format_json({"matches": matches, "count": len(matches)}))
    else:
        if not matches:
            click.echo(f"No queries found containing '{keyword}'")
        else:
            click.echo(f"\n--- Queries matching '{keyword}' ---\n")
            for i, entry in enumerate(matches, 1):
                timestamp = entry.get("timestamp", "")[:16].replace("T", " ")
                click.echo(f"  [{i}] {timestamp}")
                click.echo(f"      {entry.get('query', '')}")
                click.echo()

    print_success(f"Found {len(matches)} matching query(ies)")


@history_group.command(name="show")
@click.argument("index", type=int)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def history_show(index: int, output: str) -> None:
    """Show specific query by index."""
    history = _load_history()

    if index < 1 or index > len(history):
        raise ValidationError(f"Invalid index. Valid range: 1-{len(history)}")

    entry = history[index - 1]

    if output == "json":
        click.echo(format_json(entry))
    else:
        click.echo(f"\n--- Query #{index} ---\n")
        click.echo(f"Timestamp: {entry.get('timestamp', 'N/A')}")
        click.echo(f"Results: {entry.get('result_count', 'N/A')}")
        click.echo("\nQuery:")
        click.echo(f"  {entry.get('query', '')}")

    print_success(f"Query #{index} retrieved")


@history_group.command(name="clear")
@handle_errors
def history_clear() -> None:
    """Clear all query history."""
    history_file = _get_history_file()

    if history_file.exists():
        history_file.unlink()

    print_success("Query history cleared")


@history_group.command(name="export")
@click.argument("output_file")
@click.option(
    "--format",
    "-f",
    "export_format",
    type=click.Choice(["csv", "json"]),
    default="csv",
    help="Export format",
)
@handle_errors
def history_export(output_file: str, export_format: str) -> None:
    """Export history to file."""
    history = _load_history()

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if export_format == "csv":
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            if history:
                writer = csv.DictWriter(f, fieldnames=["timestamp", "query", "result_count"])
                writer.writeheader()
                writer.writerows(history)
    else:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)

    print_success(f"Exported {len(history)} queries to {output_path}")


@history_group.command(name="cleanup")
@click.option("--days", type=int, default=90, help="Days to keep (default: 90)")
@handle_errors
def history_cleanup(days: int) -> None:
    """Remove entries older than specified days."""
    from datetime import timedelta

    history = _load_history()
    cutoff = datetime.now() - timedelta(days=days)

    original_count = len(history)
    history = [
        entry for entry in history
        if datetime.fromisoformat(entry.get("timestamp", "1970-01-01")) > cutoff
    ]

    _save_history(history)
    removed = original_count - len(history)

    print_success(f"Removed {removed} entries older than {days} days")


@search.command(name="interactive")
@click.option("--space", help="Pre-filter by space key")
@click.option(
    "--type",
    "content_type",
    type=click.Choice(["page", "blogpost", "comment", "attachment"]),
    help="Pre-filter by content type",
)
@click.option(
    "--limit", "-l", type=int, default=25, help="Maximum results (default: 25)"
)
@click.option("--execute", is_flag=True, help="Execute query after building")
@handle_errors
def cql_interactive(
    space: str | None,
    content_type: str | None,
    limit: int,
    execute: bool,
) -> None:
    """Start interactive CQL query builder."""
    parts = []

    if space:
        space = validate_space_key(space)
        parts.append(f'space = "{space}"')

    if content_type:
        parts.append(f"type = {content_type}")

    click.echo("\n--- Interactive CQL Builder ---\n")
    click.echo("Build your query step by step. Enter 'done' when finished.\n")

    if parts:
        click.echo(f"Starting query: {' AND '.join(parts)}\n")

    # Prompt for additional conditions
    while True:
        click.echo("Available fields: space, title, text, type, label, creator, created, lastModified")
        field = click.prompt("Enter field (or 'done' to finish)", default="done")

        if field.lower() == "done":
            break

        if field.lower() not in [f["name"] for f in CQL_FIELDS]:
            print_warning(f"Unknown field: {field}")
            continue

        operator = click.prompt("Enter operator (=, !=, ~, >, <, >=, <=)", default="=")
        value = click.prompt("Enter value")

        # Quote string values
        if field.lower() in ("space", "title", "text", "label", "creator"):
            value = f'"{value}"'

        parts.append(f"{field} {operator} {value}")
        click.echo(f"\nCurrent query: {' AND '.join(parts)}\n")

    if not parts:
        click.echo("No query built.")
        return

    cql = " AND ".join(parts)
    click.echo("\n--- Final Query ---")
    click.echo(f"\n  {cql}\n")

    if execute or click.confirm("Execute this query?", default=True):
        # Call the cql_search function with the built query
        client = get_confluence_client()

        params = {"cql": cql, "limit": limit}
        results = list(client.paginate(
            "/rest/api/search", params=params, operation="interactive search"
        ))

        _add_to_history(cql, len(results))

        click.echo(f"\n--- Results ({len(results)}) ---\n")

        if results:
            data = []
            for r in results[:limit]:
                formatted = _format_search_result(r)
                data.append({
                    "id": formatted["id"],
                    "title": formatted["title"][:40],
                    "type": formatted["type"],
                    "space": formatted["space"],
                })

            click.echo(format_table(
                data,
                columns=["id", "title", "type", "space"],
                headers=["ID", "Title", "Type", "Space"],
            ))

        print_success(f"Found {len(results)} result(s)")
    else:
        click.echo("Query not executed. Copy and run later:")
        click.echo(f"\n  confluence search cql \"{cql}\"")
