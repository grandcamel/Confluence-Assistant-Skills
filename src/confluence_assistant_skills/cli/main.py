"""Main CLI entry point for Confluence Assistant Skills."""

from __future__ import annotations

import click

from confluence_assistant_skills import __version__
from confluence_assistant_skills.cli.commands.admin_cmds import admin
from confluence_assistant_skills.cli.commands.analytics_cmds import analytics
from confluence_assistant_skills.cli.commands.attachment_cmds import attachment
from confluence_assistant_skills.cli.commands.bulk_cmds import bulk
from confluence_assistant_skills.cli.commands.comment_cmds import comment
from confluence_assistant_skills.cli.commands.hierarchy_cmds import hierarchy
from confluence_assistant_skills.cli.commands.jira_cmds import jira
from confluence_assistant_skills.cli.commands.label_cmds import label
from confluence_assistant_skills.cli.commands.ops_cmds import ops

# Import command groups
from confluence_assistant_skills.cli.commands.page_cmds import page
from confluence_assistant_skills.cli.commands.permission_cmds import permission
from confluence_assistant_skills.cli.commands.property_cmds import property_cmd
from confluence_assistant_skills.cli.commands.search_cmds import search
from confluence_assistant_skills.cli.commands.space_cmds import space
from confluence_assistant_skills.cli.commands.template_cmds import template
from confluence_assistant_skills.cli.commands.watch_cmds import watch


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="confluence")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output.",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Suppress non-essential output.",
)
@click.pass_context
def cli(
    ctx: click.Context,
    output: str,
    verbose: bool,
    quiet: bool,
) -> None:
    """Confluence Assistant Skills CLI.

    A command-line interface for interacting with Confluence Cloud.

    Use --help on any command for more information.

    Examples:

        confluence page get 12345

        confluence search "space = DOCS AND type = page"

        confluence space list --output json
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# Register command groups
cli.add_command(page)
cli.add_command(space)
cli.add_command(search)
cli.add_command(comment)
cli.add_command(label)
cli.add_command(attachment)
cli.add_command(hierarchy)
cli.add_command(permission)
cli.add_command(analytics)
cli.add_command(watch)
cli.add_command(template)
cli.add_command(property_cmd, name="property")
cli.add_command(jira)
cli.add_command(admin)
cli.add_command(bulk)
cli.add_command(ops)


if __name__ == "__main__":
    cli()
