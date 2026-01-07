"""Label management commands."""

from __future__ import annotations

import click

from confluence_assistant_skills.utils import call_skill_main


@click.group()
def label() -> None:
    """Manage content labels."""
    pass


@label.command(name="list")
@click.argument("page_id")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def get_labels(
    ctx: click.Context,
    page_id: str,
    profile: str | None,
    output: str,
) -> None:
    """List labels on a page."""
    argv = [page_id]
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-label", "get_labels", argv))


@label.command(name="add")
@click.argument("page_id")
@click.option("--label", "-l", "single_label", help="Single label to add")
@click.option(
    "--labels", "multiple_labels", help="Comma-separated list of labels to add"
)
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def add_label(
    ctx: click.Context,
    page_id: str,
    single_label: str | None,
    multiple_labels: str | None,
    profile: str | None,
    output: str,
) -> None:
    """Add labels to a page.

    Examples:
        confluence label add 12345 --label documentation
        confluence label add 12345 --labels doc,approved,v2
    """
    if not single_label and not multiple_labels:
        raise click.UsageError("Either --label or --labels is required")

    argv = [page_id]
    if single_label:
        argv.extend(["--label", single_label])
    if multiple_labels:
        argv.extend(["--labels", multiple_labels])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-label", "add_label", argv))


@label.command(name="remove")
@click.argument("page_id")
@click.option("--label", "-l", required=True, help="Label to remove")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def remove_label(
    ctx: click.Context,
    page_id: str,
    label: str,
    profile: str | None,
    output: str,
) -> None:
    """Remove a label from a page.

    Examples:
        confluence label remove 12345 --label draft
        confluence label remove 12345 -l old-version --profile production
    """
    argv = [page_id, "--label", label]
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-label", "remove_label", argv))


@label.command(name="search")
@click.argument("label")
@click.option("--space", "-s", help="Limit to specific space")
@click.option("--type", "content_type", help="Content type (page, blogpost)")
@click.option("--limit", "-l", type=int, default=25, help="Maximum results")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def search_by_label(
    ctx: click.Context,
    label: str,
    space: str | None,
    content_type: str | None,
    limit: int,
    profile: str | None,
    output: str,
) -> None:
    """Search content by label."""
    argv = [label]
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

    ctx.exit(call_skill_main("confluence-label", "search_by_label", argv))


@label.command(name="popular")
@click.option("--space", "-s", help="Limit to specific space")
@click.option("--limit", "-l", type=int, default=25, help="Maximum labels to return")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def list_popular_labels(
    ctx: click.Context,
    space: str | None,
    limit: int,
    profile: str | None,
    output: str,
) -> None:
    """List popular labels."""
    argv = []
    if space:
        argv.extend(["--space", space])
    if limit != 25:
        argv.extend(["--limit", str(limit)])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-label", "list_popular_labels", argv))
