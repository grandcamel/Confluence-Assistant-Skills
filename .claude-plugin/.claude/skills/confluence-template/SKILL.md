---
name: confluence-template
description: Work with page templates and blueprints
triggers:
  - template
  - blueprint
  - create from template
  - page template
  - list templates
  - update template
---

# Confluence Template Skill

Work with Confluence page templates and blueprints. This skill provides comprehensive template management including listing, creating, retrieving, and updating templates and blueprints.

## Overview

Templates in Confluence allow you to standardize page creation. Blueprints are pre-built templates provided by Confluence or apps. This skill uses the Confluence v1 REST API (`/rest/api/template/*`) to manage templates.

## Available Scripts

### list_templates.py
List available page templates and blueprints in your Confluence instance.

**Usage:**
```bash
# List all templates
confluence template list

# Filter by space
confluence template list --space DOCS

# Filter by type (page or blogpost)
confluence template list --type page

# List blueprints instead of templates
confluence template list --blueprints

# JSON output
confluence template list --output json

# Limit results
confluence template list --limit 50
```

**Arguments:**
- `--space`: Filter templates by space key
- `--type`: Filter by template type (page or blogpost)
- `--blueprints`: List blueprints instead of templates
- `--output`, `-o`: Output format (text or json)
- `--limit`: Maximum number of results (default: 100)

### get_template.py
Retrieve detailed information about a specific template or blueprint.

**Usage:**
```bash
# Get template details
confluence template get tmpl-123

# Include body content
confluence template get tmpl-123 --body

# Convert body to Markdown
confluence template get tmpl-123 --body --format markdown

# Get blueprint details
confluence template get bp-456 --blueprint

# JSON output
confluence template get tmpl-123 --output json
```

**Arguments:**
- `template_id`: Template ID or blueprint ID
- `--body`: Include template body content
- `--format`: Body format (storage or markdown)
- `--blueprint`: Get blueprint instead of template
- `--output`, `-o`: Output format (text or json)

### create_from_template.py
Create a new Confluence page based on an existing template or blueprint.

**Usage:**
```bash
# Create page from template
confluence template create-from --template tmpl-123 --space DOCS --title "New Page"

# Create page with parent
confluence template create-from --template tmpl-123 --space DOCS --title "Page" --parent-id 12345

# Create from blueprint
confluence template create-from --blueprint bp-456 --space DOCS --title "Project Plan"

# Add labels
confluence template create-from --template tmpl-123 --space DOCS --title "Page" --labels "tag1,tag2"

# Override template content
confluence template create-from --template tmpl-123 --space DOCS --title "Page" --content "<p>Custom content</p>"

# Use content from file
confluence template create-from --template tmpl-123 --space DOCS --title "Page" --file content.md
```

**Arguments:**
- `--template`: Template ID to use
- `--blueprint`: Blueprint ID to use (alternative to --template)
- `--space`: Space key for the new page (required)
- `--title`: Title for the new page (required)
- `--parent-id`: Parent page ID
- `--labels`: Comma-separated labels
- `--content`: Custom HTML/XHTML content
- `--file`: File with content (Markdown or HTML)
- `--output`, `-o`: Output format (text or json)

### create_template.py
Create a new page template in Confluence.

**Usage:**
```bash
# Create basic template
confluence template create --name "Meeting Notes" --space DOCS

# With description
confluence template create --name "Status Report" --space DOCS --description "Weekly status report"

# From HTML file
confluence template create --name "Template" --space DOCS --file template.html

# From Markdown file
confluence template create --name "Template" --space DOCS --file template.md

# With labels
confluence template create --name "Template" --space DOCS --labels "template,meeting"

# Blogpost template
confluence template create --name "Blog Template" --space DOCS --type blogpost

# Based on blueprint
confluence template create --name "Custom" --space DOCS --blueprint-id com.atlassian...
```

**Arguments:**
- `--name`: Template name (required)
- `--space`: Space key (required)
- `--description`: Template description
- `--content`: Template body content (HTML/XHTML)
- `--file`: File with template content (Markdown or HTML)
- `--labels`: Comma-separated labels
- `--type`: Template type - page or blogpost (default: page)
- `--blueprint-id`: Base on existing blueprint
- `--output`, `-o`: Output format (text or json)

### update_template.py
Update an existing page template.

**Usage:**
```bash
# Update name
confluence template update tmpl-123 --name "Updated Template"

# Update description
confluence template update tmpl-123 --description "New description"

# Update content from HTML file
confluence template update tmpl-123 --file updated.html

# Update from Markdown file
confluence template update tmpl-123 --file updated.md

# Update inline content
confluence template update tmpl-123 --content "<h1>Updated</h1>"

# Add labels
confluence template update tmpl-123 --add-labels "tag1,tag2"

# Remove labels
confluence template update tmpl-123 --remove-labels "old-tag"

# Multiple updates
confluence template update tmpl-123 --name "New Name" --description "New desc" --add-labels "new"
```

**Arguments:**
- `template_id`: Template ID to update (required)
- `--name`: New template name
- `--description`: New description
- `--content`: New body content (HTML/XHTML)
- `--file`: File with new content (Markdown or HTML)
- `--add-labels`: Comma-separated labels to add
- `--remove-labels`: Comma-separated labels to remove
- `--output`, `-o`: Output format (text or json)

Note: At least one field must be specified to update.

## API Endpoints Used

This skill uses the Confluence v1 REST API:

- `GET /rest/api/template/page` - List page templates
- `GET /rest/api/template/blueprint` - List blueprints
- `GET /rest/api/template/{templateId}` - Get template details
- `POST /rest/api/template` - Create template
- `PUT /rest/api/template/{templateId}` - Update template
- `POST /rest/api/content` - Create page from template

## Examples

### Finding and Using Templates

```bash
# List all available templates
confluence template list

# Find templates in a specific space
confluence template list --space DOCS

# Get template details
confluence template get tmpl-123 --body --format markdown

# Create a page from that template
confluence template create-from --template tmpl-123 --space DOCS --title "My Meeting Notes"
```

### Creating Custom Templates

```bash
# Create a simple template
confluence template create --name "Weekly Report" --space DOCS --description "Template for weekly status reports"

# Create from a Markdown file
confluence template create --name "Project Plan" --space DOCS --file project-template.md --labels "template,planning"
```

### Maintaining Templates

```bash
# Update template content from file
confluence template update tmpl-123 --file updated-template.md

# Add tags to categorize
confluence template update tmpl-123 --add-labels "engineering,documentation"

# Update name and description
confluence template update tmpl-123 --name "New Template Name" --description "Updated description"
```

## Tips

1. **Template IDs**: Template IDs are typically in the format `tmpl-123` or similar. Use `list_templates.py` to find IDs.

2. **Markdown Support**: All scripts support Markdown input files, which are automatically converted to Confluence's storage format (XHTML).

3. **Blueprints vs Templates**: Blueprints are system-provided templates. You can create pages from blueprints but typically cannot modify them. Use `--blueprint` flag to work with blueprints.

4. **Labels**: Use labels to organize and categorize templates for easier discovery.

5. **Preserving Content**: When updating templates, only the fields you specify are changed. Other fields are preserved.

6. **Parent Pages**: When creating pages from templates, you can specify a parent page to create a page hierarchy.

## Troubleshooting

**Template not found**: Verify the template ID with `list_templates.py`. Template IDs are space-specific in some cases.

**Permission denied**: Ensure you have permission to create/modify templates in the specified space. Template management typically requires space admin permissions.

**Content format issues**: If template content doesn't render correctly, ensure HTML/XHTML is well-formed. Use Markdown files for easier authoring.
