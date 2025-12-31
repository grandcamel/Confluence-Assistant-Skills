"""Template commands."""

from __future__ import annotations

import click

from confluence_assistant_skills.utils import call_skill_main


@click.group()
def template() -> None:
    """Manage page templates."""
    pass


@template.command(name="list")
@click.option("--space", "-s", help="Limit to specific space")
@click.option("--type", "template_type", help="Template type (page, blog)")
@click.option("--limit", "-l", type=int, default=25, help="Maximum templates to return")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def list_templates(
    ctx: click.Context,
    space: str | None,
    template_type: str | None,
    limit: int,
    profile: str | None,
    output: str,
) -> None:
    """List available templates."""
    argv = []
    if space:
        argv.extend(["--space", space])
    if template_type:
        argv.extend(["--type", template_type])
    if limit != 25:
        argv.extend(["--limit", str(limit)])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-template", "list_templates", argv))


@template.command(name="get")
@click.argument("template_id")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def get_template(
    ctx: click.Context,
    template_id: str,
    profile: str | None,
    output: str,
) -> None:
    """Get a template by ID."""
    argv = [template_id]
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-template", "get_template", argv))


@template.command(name="create")
@click.argument("space_key")
@click.argument("name")
@click.option("--body", help="Template body content")
@click.option("--body-file", type=click.Path(exists=True), help="Read body from file")
@click.option("--description", help="Template description")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def create_template(
    ctx: click.Context,
    space_key: str,
    name: str,
    body: str | None,
    body_file: str | None,
    description: str | None,
    profile: str | None,
    output: str,
) -> None:
    """Create a new template."""
    argv = [space_key, name]
    if body:
        argv.extend(["--body", body])
    if body_file:
        argv.extend(["--body-file", body_file])
    if description:
        argv.extend(["--description", description])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-template", "create_template", argv))


@template.command(name="update")
@click.argument("template_id")
@click.option("--name", help="New template name")
@click.option("--body", help="New template body")
@click.option("--body-file", type=click.Path(exists=True), help="Read body from file")
@click.option("--description", help="New template description")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def update_template(
    ctx: click.Context,
    template_id: str,
    name: str | None,
    body: str | None,
    body_file: str | None,
    description: str | None,
    profile: str | None,
    output: str,
) -> None:
    """Update an existing template."""
    argv = [template_id]
    if name:
        argv.extend(["--name", name])
    if body:
        argv.extend(["--body", body])
    if body_file:
        argv.extend(["--body-file", body_file])
    if description:
        argv.extend(["--description", description])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-template", "update_template", argv))


@template.command(name="create-from")
@click.argument("template_id")
@click.argument("space_key")
@click.argument("title")
@click.option("--parent-id", help="Parent page ID")
@click.option("--variables", help="Template variables as JSON")
@click.option("--profile", "-p", help="Confluence profile to use")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.pass_context
def create_from_template(
    ctx: click.Context,
    template_id: str,
    space_key: str,
    title: str,
    parent_id: str | None,
    variables: str | None,
    profile: str | None,
    output: str,
) -> None:
    """Create a page from a template."""
    argv = [template_id, space_key, title]
    if parent_id:
        argv.extend(["--parent-id", parent_id])
    if variables:
        argv.extend(["--variables", variables])
    if profile:
        argv.extend(["--profile", profile])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-template", "create_from_template", argv))
