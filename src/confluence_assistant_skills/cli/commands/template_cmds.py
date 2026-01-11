"""Template commands - CLI-only implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from confluence_assistant_skills_lib import (
    ValidationError,
    format_json,
    format_table,
    get_confluence_client,
    handle_errors,
    markdown_to_xhtml,
    print_success,
    validate_limit,
    validate_space_key,
    xhtml_to_markdown,
)


def _get_space_by_key(client: Any, space_key: str) -> dict[str, Any]:
    """Get space by key."""
    spaces = list(client.paginate(
        "/api/v2/spaces",
        params={"keys": space_key},
        operation="get space",
    ))
    if not spaces:
        raise ValidationError(f"Space not found: {space_key}")
    return spaces[0]


def _read_content_file(file_path: Path) -> str:
    """Read content from a file."""
    if not file_path.exists():
        raise ValidationError(f"File not found: {file_path}")
    return file_path.read_text(encoding="utf-8")


def _is_markdown_file(file_path: Path) -> bool:
    """Check if file is a Markdown file."""
    return file_path.suffix.lower() in (".md", ".markdown")


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
@handle_errors
def list_templates(
    space: str | None,
    template_type: str | None,
    blueprints: bool,
    limit: int,
    output: str,
) -> None:
    """List available templates."""
    if space:
        space = validate_space_key(space)

    limit = validate_limit(limit, max_value=250)

    client = get_confluence_client()

    if blueprints:
        # List blueprints using v1 API
        params: dict[str, Any] = {
            "limit": min(limit, 25),
            "expand": "description,body.storage",
        }

        if space:
            params["spaceKey"] = space

        templates = []
        for blueprint in client.paginate(
            "/rest/api/content/blueprint/instance",
            params=params,
            operation="list blueprints",
        ):
            templates.append(blueprint)
            if len(templates) >= limit:
                break
    else:
        # List space templates using v1 API
        params = {
            "limit": min(limit, 25),
            "expand": "body.storage",
        }

        if space:
            templates = []
            for tmpl in client.paginate(
                f"/rest/api/template/page?spaceKey={space}",
                params=params,
                operation="list space templates",
            ):
                if template_type is None or tmpl.get("templateType", "").lower() == template_type:
                    templates.append(tmpl)
                if len(templates) >= limit:
                    break
        else:
            # List global templates
            templates = []
            for tmpl in client.paginate(
                "/rest/api/template/page",
                params=params,
                operation="list global templates",
            ):
                if template_type is None or tmpl.get("templateType", "").lower() == template_type:
                    templates.append(tmpl)
                if len(templates) >= limit:
                    break

    if output == "json":
        click.echo(format_json({
            "space": space,
            "type": "blueprints" if blueprints else "templates",
            "templates": templates,
            "count": len(templates),
        }))
    else:
        title = "Blueprints" if blueprints else "Templates"
        click.echo(f"\n{title}")
        if space:
            click.echo(f"Space: {space}")
        click.echo(f"{'=' * 60}\n")

        if not templates:
            click.echo(f"No {title.lower()} found.")
        else:
            data = []
            for tmpl in templates:
                data.append({
                    "id": tmpl.get("templateId", tmpl.get("id", ""))[:20],
                    "name": tmpl.get("name", tmpl.get("title", ""))[:35],
                    "type": tmpl.get("templateType", "page")[:10],
                    "space": tmpl.get("_expandable", {}).get("space", "global")[-10:],
                })

            click.echo(format_table(
                data,
                columns=["id", "name", "type", "space"],
                headers=["ID", "Name", "Type", "Space"],
            ))

    print_success(f"Found {len(templates)} template(s)")


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
@handle_errors
def get_template(
    template_id: str,
    body: bool,
    body_format: str,
    blueprint: bool,
    output: str,
) -> None:
    """Get a template by ID."""
    if not template_id:
        raise ValidationError("Template ID is required")

    client = get_confluence_client()

    if blueprint:
        # Get blueprint
        tmpl = client.get(
            f"/rest/api/content/blueprint/instance/{template_id}",
            params={"expand": "body.storage,description"},
            operation="get blueprint",
        )
    else:
        # Get template
        tmpl = client.get(
            f"/rest/api/template/{template_id}",
            params={"expand": "body.storage"},
            operation="get template",
        )

    # Get body content if requested
    body_content = None
    if body:
        body_data = tmpl.get("body", {}).get("storage", {})
        body_content = body_data.get("value", "")
        if body_format == "markdown" and body_content:
            body_content = xhtml_to_markdown(body_content)

    if output == "json":
        result: dict[str, Any] = {
            "template": tmpl,
        }
        if body_content is not None:
            result["body"] = body_content
            result["bodyFormat"] = body_format
        click.echo(format_json(result))
    else:
        name = tmpl.get("name", tmpl.get("title", "Unknown"))
        click.echo(f"\nTemplate: {name}")
        click.echo(f"{'=' * 60}\n")

        click.echo(f"ID: {tmpl.get('templateId', tmpl.get('id', 'N/A'))}")
        click.echo(f"Name: {name}")
        click.echo(f"Type: {tmpl.get('templateType', 'page')}")

        description = tmpl.get("description", "")
        if description:
            click.echo(f"Description: {description}")

        if body and body_content:
            click.echo(f"\nBody ({body_format}):")
            click.echo("-" * 40)
            click.echo(body_content[:2000])
            if len(body_content) > 2000:
                click.echo(f"\n... (truncated, {len(body_content)} chars total)")

    print_success("Retrieved template")


@template.command(name="create")
@click.option("--name", required=True, help="Template name")
@click.option("--space", "-s", required=True, help="Space key for the template")
@click.option("--description", help="Template description")
@click.option("--content", help="Template body content (HTML/XHTML)")
@click.option(
    "--file",
    "content_file",
    type=click.Path(exists=True, path_type=Path),
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
@handle_errors
def create_template(
    name: str,
    space: str,
    description: str | None,
    content: str | None,
    content_file: Path | None,
    labels: str | None,
    template_type: str,
    blueprint_id: str | None,
    output: str,
) -> None:
    """Create a new template."""
    space = validate_space_key(space)

    if not content and not content_file:
        raise ValidationError("Either --content or --file is required")
    if content and content_file:
        raise ValidationError("Cannot specify both --content and --file")

    client = get_confluence_client()

    # Get space info
    space_info = _get_space_by_key(client, space)

    # Read content
    body_content = content
    if content_file:
        body_content = _read_content_file(content_file)
        if _is_markdown_file(content_file):
            body_content = markdown_to_xhtml(body_content)

    # Build template data
    template_data: dict[str, Any] = {
        "name": name,
        "templateType": template_type,
        "body": {
            "storage": {
                "value": body_content or "",
                "representation": "storage",
            }
        },
        "space": {
            "key": space,
        },
    }

    if description:
        template_data["description"] = description

    if labels:
        label_list = [l.strip() for l in labels.split(",") if l.strip()]
        template_data["labels"] = [{"name": l} for l in label_list]

    if blueprint_id:
        template_data["referencedBlueprint"] = {"moduleKey": blueprint_id}

    # Create template using v1 API
    result = client.post(
        "/rest/api/template",
        json_data=template_data,
        operation="create template",
    )

    if output == "json":
        click.echo(format_json(result))
    else:
        click.echo(f"\nTemplate created successfully")
        click.echo(f"  ID: {result.get('templateId', 'N/A')}")
        click.echo(f"  Name: {name}")
        click.echo(f"  Space: {space}")
        click.echo(f"  Type: {template_type}")

    print_success(f"Created template '{name}' in space {space}")


@template.command(name="update")
@click.argument("template_id")
@click.option("--name", help="New template name")
@click.option("--description", help="New template description")
@click.option("--content", help="New template body content (HTML/XHTML)")
@click.option(
    "--file", "content_file", type=click.Path(exists=True, path_type=Path), help="File with new content"
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
@handle_errors
def update_template(
    template_id: str,
    name: str | None,
    description: str | None,
    content: str | None,
    content_file: Path | None,
    add_labels: str | None,
    remove_labels: str | None,
    output: str,
) -> None:
    """Update an existing template."""
    if not template_id:
        raise ValidationError("Template ID is required")

    if content and content_file:
        raise ValidationError("Cannot specify both --content and --file")

    client = get_confluence_client()

    # Get current template
    current = client.get(
        f"/rest/api/template/{template_id}",
        params={"expand": "body.storage,labels"},
        operation="get template",
    )

    # Build update data
    update_data: dict[str, Any] = {
        "templateId": template_id,
    }

    if name:
        update_data["name"] = name
    else:
        update_data["name"] = current.get("name", "")

    if description is not None:
        update_data["description"] = description

    # Handle content
    if content:
        update_data["body"] = {
            "storage": {
                "value": content,
                "representation": "storage",
            }
        }
    elif content_file:
        body_content = _read_content_file(content_file)
        if _is_markdown_file(content_file):
            body_content = markdown_to_xhtml(body_content)
        update_data["body"] = {
            "storage": {
                "value": body_content,
                "representation": "storage",
            }
        }

    # Handle labels
    current_labels = [l.get("name") for l in current.get("labels", {}).get("results", [])]

    if add_labels:
        for label in add_labels.split(","):
            label = label.strip()
            if label and label not in current_labels:
                current_labels.append(label)

    if remove_labels:
        for label in remove_labels.split(","):
            label = label.strip()
            if label in current_labels:
                current_labels.remove(label)

    if add_labels or remove_labels:
        update_data["labels"] = [{"name": l} for l in current_labels]

    # Update template
    result = client.put(
        f"/rest/api/template/{template_id}",
        json_data=update_data,
        operation="update template",
    )

    if output == "json":
        click.echo(format_json(result))
    else:
        click.echo(f"\nTemplate updated successfully")
        click.echo(f"  ID: {template_id}")
        click.echo(f"  Name: {result.get('name', name or current.get('name'))}")

    print_success(f"Updated template {template_id}")


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
    type=click.Path(exists=True, path_type=Path),
    help="File with custom content",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def create_from_template(
    template_id: str | None,
    blueprint_id: str | None,
    space: str,
    title: str,
    parent_id: str | None,
    labels: str | None,
    content: str | None,
    content_file: Path | None,
    output: str,
) -> None:
    """Create a page from a template."""
    space = validate_space_key(space)

    if not template_id and not blueprint_id:
        raise ValidationError("Either --template or --blueprint is required")
    if template_id and blueprint_id:
        raise ValidationError("Cannot specify both --template and --blueprint")
    if content and content_file:
        raise ValidationError("Cannot specify both --content and --file")

    client = get_confluence_client()

    # Get space info
    space_info = _get_space_by_key(client, space)
    space_id = space_info.get("id")

    # Get template content if not overriding
    body_content = content
    if content_file:
        body_content = _read_content_file(content_file)
        if _is_markdown_file(content_file):
            body_content = markdown_to_xhtml(body_content)

    if not body_content:
        if template_id:
            tmpl = client.get(
                f"/rest/api/template/{template_id}",
                params={"expand": "body.storage"},
                operation="get template",
            )
            body_content = tmpl.get("body", {}).get("storage", {}).get("value", "")
        elif blueprint_id:
            # Blueprint content needs to be fetched differently
            body_content = ""  # Start with empty, blueprint applied on creation

    # Build page data for v2 API
    page_data: dict[str, Any] = {
        "spaceId": space_id,
        "title": title,
        "status": "current",
        "body": {
            "representation": "storage",
            "value": body_content or "",
        },
    }

    if parent_id:
        page_data["parentId"] = parent_id

    # Create page
    result = client.post(
        "/api/v2/pages",
        json_data=page_data,
        operation="create page from template",
    )

    new_page_id = result.get("id")

    # Add labels if specified
    if labels and new_page_id:
        label_list = [{"name": l.strip()} for l in labels.split(",") if l.strip()]
        if label_list:
            client.post(
                f"/api/v2/pages/{new_page_id}/labels",
                json_data=label_list,
                operation="add labels",
            )

    if output == "json":
        click.echo(format_json({
            "page": result,
            "templateId": template_id,
            "blueprintId": blueprint_id,
        }))
    else:
        click.echo(f"\nPage created from template")
        click.echo(f"  ID: {new_page_id}")
        click.echo(f"  Title: {title}")
        click.echo(f"  Space: {space}")
        if template_id:
            click.echo(f"  Template: {template_id}")
        if blueprint_id:
            click.echo(f"  Blueprint: {blueprint_id}")

    print_success(f"Created page '{title}' from template in space {space}")
