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
@click.option(
    "--type",
    "-t",
    "template_type",
    type=click.Choice(["page", "blogpost"]),
    help="Template type (page or blogpost)",
)
@click.option("--blueprints", is_flag=True, help="List blueprints instead of templates")
@click.option(
    "--limit", "-l", type=int, default=100, help="Maximum templates to return"
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def list_templates(
    ctx: click.Context,
    space: str | None,
    template_type: str | None,
    blueprints: bool,
    limit: int,
    output: str,
) -> None:
    """List available templates."""
    argv = []
    if space:
        argv.extend(["--space", space])
    if template_type:
        argv.extend(["--type", template_type])
    if blueprints:
        argv.append("--blueprints")
    if limit != 100:
        argv.extend(["--limit", str(limit)])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-template", "list_templates", argv))


@template.command(name="get")
@click.argument("template_id")
@click.option("--body", is_flag=True, help="Include body content in output")
@click.option(
    "--format",
    "body_format",
    type=click.Choice(["storage", "markdown"]),
    default="storage",
    help="Body format (storage or markdown)",
)
@click.option("--blueprint", is_flag=True, help="Get blueprint instead of template")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def get_template(
    ctx: click.Context,
    template_id: str,
    body: bool,
    body_format: str,
    blueprint: bool,
    output: str,
) -> None:
    """Get a template by ID."""
    argv = [template_id]
    if body:
        argv.append("--body")
    if body_format != "storage":
        argv.extend(["--format", body_format])
    if blueprint:
        argv.append("--blueprint")
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-template", "get_template", argv))


@template.command(name="create")
@click.option("--name", required=True, help="Template name")
@click.option("--space", "-s", required=True, help="Space key for the template")
@click.option("--description", help="Template description")
@click.option("--content", help="Template body content (HTML/XHTML)")
@click.option(
    "--file",
    "content_file",
    type=click.Path(exists=True),
    help="File with template content",
)
@click.option("--labels", help="Comma-separated labels")
@click.option(
    "--type",
    "-t",
    "template_type",
    type=click.Choice(["page", "blogpost"]),
    default="page",
    help="Template type (default: page)",
)
@click.option("--blueprint-id", help="Base on existing blueprint")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def create_template(
    ctx: click.Context,
    name: str,
    space: str,
    description: str | None,
    content: str | None,
    content_file: str | None,
    labels: str | None,
    template_type: str,
    blueprint_id: str | None,
    output: str,
) -> None:
    """Create a new template."""
    argv = ["--name", name, "--space", space]
    if description:
        argv.extend(["--description", description])
    if content:
        argv.extend(["--content", content])
    if content_file:
        argv.extend(["--file", content_file])
    if labels:
        argv.extend(["--labels", labels])
    if template_type != "page":
        argv.extend(["--type", template_type])
    if blueprint_id:
        argv.extend(["--blueprint-id", blueprint_id])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-template", "create_template", argv))


@template.command(name="update")
@click.argument("template_id")
@click.option("--name", help="New template name")
@click.option("--description", help="New template description")
@click.option("--content", help="New template body content (HTML/XHTML)")
@click.option(
    "--file", "content_file", type=click.Path(exists=True), help="File with new content"
)
@click.option("--add-labels", help="Comma-separated labels to add")
@click.option("--remove-labels", help="Comma-separated labels to remove")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def update_template(
    ctx: click.Context,
    template_id: str,
    name: str | None,
    description: str | None,
    content: str | None,
    content_file: str | None,
    add_labels: str | None,
    remove_labels: str | None,
    output: str,
) -> None:
    """Update an existing template."""
    argv = [template_id]
    if name:
        argv.extend(["--name", name])
    if description:
        argv.extend(["--description", description])
    if content:
        argv.extend(["--content", content])
    if content_file:
        argv.extend(["--file", content_file])
    if add_labels:
        argv.extend(["--add-labels", add_labels])
    if remove_labels:
        argv.extend(["--remove-labels", remove_labels])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-template", "update_template", argv))


@template.command(name="create-from")
@click.option("--template", "template_id", help="Template ID to use")
@click.option(
    "--blueprint",
    "blueprint_id",
    help="Blueprint ID to use (alternative to --template)",
)
@click.option("--space", "-s", required=True, help="Space key for the new page")
@click.option("--title", required=True, help="Title for the new page")
@click.option("--parent-id", help="Parent page ID")
@click.option("--labels", help="Comma-separated labels to add")
@click.option("--content", help="Custom content (overrides template)")
@click.option(
    "--file",
    "content_file",
    type=click.Path(exists=True),
    help="File with custom content",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def create_from_template(
    ctx: click.Context,
    template_id: str | None,
    blueprint_id: str | None,
    space: str,
    title: str,
    parent_id: str | None,
    labels: str | None,
    content: str | None,
    content_file: str | None,
    output: str,
) -> None:
    """Create a page from a template."""
    argv = []
    if template_id:
        argv.extend(["--template", template_id])
    if blueprint_id:
        argv.extend(["--blueprint", blueprint_id])
    argv.extend(["--space", space, "--title", title])
    if parent_id:
        argv.extend(["--parent-id", parent_id])
    if labels:
        argv.extend(["--labels", labels])
    if content:
        argv.extend(["--content", content])
    if content_file:
        argv.extend(["--file", content_file])
    if output != "text":
        argv.extend(["--output", output])

    ctx.exit(call_skill_main("confluence-template", "create_from_template", argv))
