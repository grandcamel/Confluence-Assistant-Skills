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
@click.argument("partial")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def cql_suggest(
    ctx: click.Context,
    partial: str,
    profile: str | None,
    output: str,
) -> None:
    """Get CQL query suggestions."""
    argv = [partial]
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-search", "cql_suggest", argv))


@search.command(name="export")
@click.argument("cql")
@click.option("--format", "export_format", type=click.Choice(["csv", "json"]), default="csv", help="Export format")
@click.option("--output-file", "-f", help="Output file path")
@click.option("--limit", "-l", type=int, help="Maximum results to export")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.pass_context
def export_results(
    ctx: click.Context,
    cql: str,
    export_format: str,
    output_file: str | None,
    limit: int | None,
    profile: str | None,
) -> None:
    """Export search results to file."""
    argv = [cql]
    if export_format != "csv":
        argv.extend(["--format", export_format])
    if output_file:
        argv.extend(["--output-file", output_file])
    if limit:
        argv.extend(["--limit", str(limit)])
    if profile:
        argv.extend(["--profile", profile])

    ctx.exit(call_skill_main("confluence-search", "export_results", argv))


@search.command(name="stream-export")
@click.argument("cql")
@click.option("--format", "export_format", type=click.Choice(["csv", "json", "jsonl"]), default="jsonl", help="Export format")
@click.option("--output-file", "-f", help="Output file path")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.pass_context
def streaming_export(
    ctx: click.Context,
    cql: str,
    export_format: str,
    output_file: str | None,
    profile: str | None,
) -> None:
    """Stream export large result sets."""
    argv = [cql]
    if export_format != "jsonl":
        argv.extend(["--format", export_format])
    if output_file:
        argv.extend(["--output-file", output_file])
    if profile:
        argv.extend(["--profile", profile])

    ctx.exit(call_skill_main("confluence-search", "streaming_export", argv))


@search.command(name="history")
@click.option("--limit", "-l", type=int, default=10, help="Number of recent queries")
@click.option("--clear", is_flag=True, help="Clear search history")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def cql_history(
    ctx: click.Context,
    limit: int,
    clear: bool,
    profile: str | None,
    output: str,
) -> None:
    """View or manage CQL query history."""
    argv = []
    if limit != 10:
        argv.extend(["--limit", str(limit)])
    if clear:
        argv.append("--clear")
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-search", "cql_history", argv))


@search.command(name="interactive")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.pass_context
def cql_interactive(
    ctx: click.Context,
    profile: str | None,
) -> None:
    """Start interactive CQL session."""
    argv = []
    if profile:
        argv.extend(["--profile", profile])

    ctx.exit(call_skill_main("confluence-search", "cql_interactive", argv))
