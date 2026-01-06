"""Search commands."""

from __future__ import annotations

import click

from confluence_assistant_skills.utils import call_skill_main


@click.group()
def search() -> None:
    """Search Confluence content."""
    pass


@search.command(name="cql")
@click.argument("cql")
@click.option("--limit", "-l", type=int, default=25, help="Maximum results (default: 25)")
@click.option("--show-excerpts", is_flag=True, help="Show content excerpts")
@click.option("--show-labels", is_flag=True, help="Show content labels")
@click.option("--show-ancestors", is_flag=True, help="Show ancestor pages")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def cql_search(
    ctx: click.Context,
    cql: str,
    limit: int,
    show_excerpts: bool,
    show_labels: bool,
    show_ancestors: bool,
    profile: str | None,
    output: str,
) -> None:
    """Execute CQL queries against Confluence."""
    argv = [cql]
    if limit != 25:
        argv.extend(["--limit", str(limit)])
    if show_excerpts:
        argv.append("--show-excerpts")
    if show_labels:
        argv.append("--show-labels")
    if show_ancestors:
        argv.append("--show-ancestors")
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-search", "cql_search", argv))


@search.command(name="content")
@click.argument("query")
@click.option("--space", "-s", help="Limit to specific space")
@click.option("--type", "content_type", help="Content type (page, blogpost)")
@click.option("--limit", "-l", type=int, default=25, help="Maximum results")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def search_content(
    ctx: click.Context,
    query: str,
    space: str | None,
    content_type: str | None,
    limit: int,
    profile: str | None,
    output: str,
) -> None:
    """Search content by text."""
    argv = [query]
    if space:
        argv.extend(["--space", space])
    if content_type:
        argv.extend(["--type", content_type])
    if limit != 25:
        argv.extend(["--limit", str(limit)])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-search", "search_content", argv))


@search.command(name="validate")
@click.argument("cql")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.pass_context
def cql_validate(
    ctx: click.Context,
    cql: str,
    profile: str | None,
) -> None:
    """Validate a CQL query syntax."""
    argv = [cql]
    if profile:
        argv.extend(["--profile", profile])

    ctx.exit(call_skill_main("confluence-search", "cql_validate", argv))


@search.command(name="suggest")
@click.option("--fields", is_flag=True, help="List all CQL fields")
@click.option("--field", help="Get values for a specific field")
@click.option("--operators", is_flag=True, help="List all CQL operators")
@click.option("--functions", is_flag=True, help="List all CQL functions")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def cql_suggest(
    ctx: click.Context,
    fields: bool,
    field: str | None,
    operators: bool,
    functions: bool,
    profile: str | None,
    output: str,
) -> None:
    """Get CQL field and value suggestions."""
    argv = []
    if fields:
        argv.append("--fields")
    if field:
        argv.extend(["--field", field])
    if operators:
        argv.append("--operators")
    if functions:
        argv.append("--functions")
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-search", "cql_suggest", argv))


@search.command(name="export")
@click.argument("cql")
@click.option("--format", "-f", "export_format", type=click.Choice(["csv", "json"]), default="csv", help="Export format")
@click.option("--output", "-o", required=True, help="Output file path")
@click.option("--columns", help="Columns to include (comma-separated)")
@click.option("--limit", "-l", type=int, help="Maximum results to export")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.pass_context
def export_results(
    ctx: click.Context,
    cql: str,
    export_format: str,
    output: str,
    columns: str | None,
    limit: int | None,
    profile: str | None,
) -> None:
    """Export search results to file."""
    argv = [cql]
    if export_format != "csv":
        argv.extend(["--format", export_format])
    if output:
        argv.extend(["--output", output])
    if columns:
        argv.extend(["--columns", columns])
    if limit:
        argv.extend(["--limit", str(limit)])
    if profile:
        argv.extend(["--profile", profile])

    ctx.exit(call_skill_main("confluence-search", "export_results", argv))


@search.command(name="stream-export")
@click.argument("cql")
@click.option("--format", "-f", "export_format", type=click.Choice(["csv", "json"]), help="Export format (inferred from extension if not specified)")
@click.option("--output", "-o", required=True, help="Output file path")
@click.option("--columns", help="Columns to include (comma-separated)")
@click.option("--batch-size", type=int, default=100, help="Records per batch (default: 100)")
@click.option("--resume", is_flag=True, help="Resume from last checkpoint")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.pass_context
def streaming_export(
    ctx: click.Context,
    cql: str,
    export_format: str | None,
    output: str,
    columns: str | None,
    batch_size: int,
    resume: bool,
    profile: str | None,
) -> None:
    """Stream export large result sets."""
    argv = [cql]
    if export_format:
        argv.extend(["--format", export_format])
    if output:
        argv.extend(["--output", output])
    if columns:
        argv.extend(["--columns", columns])
    if batch_size != 100:
        argv.extend(["--batch-size", str(batch_size)])
    if resume:
        argv.append("--resume")
    if profile:
        argv.extend(["--profile", profile])

    ctx.exit(call_skill_main("confluence-search", "streaming_export", argv))


@search.group(name="history")
def history_group() -> None:
    """Manage CQL query history."""
    pass


@history_group.command(name="list")
@click.option("--limit", "-l", type=int, help="Number of recent queries")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def history_list(
    ctx: click.Context,
    limit: int | None,
    output: str,
) -> None:
    """List recent queries."""
    argv = ["list"]
    if limit:
        argv.extend(["--limit", str(limit)])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-search", "cql_history", argv))


@history_group.command(name="search")
@click.argument("keyword")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def history_search(
    ctx: click.Context,
    keyword: str,
    output: str,
) -> None:
    """Search history for queries containing keyword."""
    argv = ["search", keyword]
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-search", "cql_history", argv))


@history_group.command(name="show")
@click.argument("index", type=int)
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def history_show(
    ctx: click.Context,
    index: int,
    output: str,
) -> None:
    """Show specific query by index."""
    argv = ["show", str(index)]
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-search", "cql_history", argv))


@history_group.command(name="clear")
@click.pass_context
def history_clear(
    ctx: click.Context,
) -> None:
    """Clear all query history."""
    argv = ["clear"]
    ctx.exit(call_skill_main("confluence-search", "cql_history", argv))


@history_group.command(name="export")
@click.argument("output_file")
@click.option("--format", "-f", "export_format", type=click.Choice(["csv", "json"]), default="csv", help="Export format")
@click.pass_context
def history_export(
    ctx: click.Context,
    output_file: str,
    export_format: str,
) -> None:
    """Export history to file."""
    argv = ["export", output_file]
    if export_format != "csv":
        argv.extend(["--format", export_format])

    ctx.exit(call_skill_main("confluence-search", "cql_history", argv))


@history_group.command(name="cleanup")
@click.option("--days", type=int, default=90, help="Days to keep (default: 90)")
@click.pass_context
def history_cleanup(
    ctx: click.Context,
    days: int,
) -> None:
    """Remove entries older than specified days."""
    argv = ["cleanup"]
    if days != 90:
        argv.extend(["--days", str(days)])

    ctx.exit(call_skill_main("confluence-search", "cql_history", argv))


@search.command(name="interactive")
@click.option("--space", help="Pre-filter by space key")
@click.option("--type", "content_type", type=click.Choice(["page", "blogpost", "comment", "attachment"]), help="Pre-filter by content type")
@click.option("--limit", "-l", type=int, default=25, help="Maximum results (default: 25)")
@click.option("--execute", is_flag=True, help="Execute query after building")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.pass_context
def cql_interactive(
    ctx: click.Context,
    space: str | None,
    content_type: str | None,
    limit: int,
    execute: bool,
    profile: str | None,
) -> None:
    """Start interactive CQL query builder."""
    argv = []
    if space:
        argv.extend(["--space", space])
    if content_type:
        argv.extend(["--type", content_type])
    if limit != 25:
        argv.extend(["--limit", str(limit)])
    if execute:
        argv.append("--execute")
    if profile:
        argv.extend(["--profile", profile])

    ctx.exit(call_skill_main("confluence-search", "cql_interactive", argv))
