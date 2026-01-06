---
name: confluence-space
description: Manage Confluence spaces - create, list, update, delete, and configure spaces
triggers:
  - create space
  - new space
  - get space
  - list spaces
  - show spaces
  - update space
  - edit space
  - delete space
  - remove space
  - space settings
  - space content
  - space pages
---

# Confluence Space Skill

Manage Confluence spaces through natural language commands.

## Overview

This skill handles all space management operations, including:
- Creating new spaces
- Listing and searching spaces
- Updating space properties
- Deleting spaces
- Viewing space content and settings

## Available Scripts

### create_space.py

Create a new Confluence space.

**Usage:**
```bash
# Create a basic space
confluence space create --key DOCS --name "Documentation"

# Create with description
confluence space create --key KB --name "Knowledge Base" --description "Company knowledge base"

# Create personal space
confluence space create --key ~username --name "Personal Space" --type personal
```

**Arguments:**
- `--key, -k` - Space key (required, 2-255 chars, alphanumeric)
- `--name, -n` - Space name (required)
- `--description, -d` - Space description
- `--type` - Space type: global (default) or personal
- `--profile, -p` - Confluence profile to use
- `--output, -o` - Output format: text or json

### get_space.py

Retrieve space details.

**Usage:**
```bash
confluence space get DOCS
confluence space get DOCS --output json
```

**Arguments:**
- `space_key` - Space key (required)
- `--profile, -p` - Confluence profile
- `--output, -o` - Output format

### list_spaces.py

List all accessible spaces.

**Usage:**
```bash
# List all spaces
confluence space list

# Filter by type
confluence space list --type global

# Search by name
confluence space list --query "docs"

# Limit results
confluence space list --limit 10
```

**Arguments:**
- `--type` - Filter by type: global or personal
- `--query, -q` - Search query
- `--status` - Filter by status: current or archived
- `--limit, -l` - Maximum results
- `--profile, -p` - Confluence profile
- `--output, -o` - Output format

### update_space.py

Update space properties.

**Usage:**
```bash
confluence space update DOCS --name "New Name"
confluence space update DOCS --description "Updated description"
confluence space update DOCS --homepage 12345
```

**Arguments:**
- `space_key` - Space key (required)
- `--name, -n` - New space name
- `--description, -d` - New description
- `--homepage` - Homepage page ID
- `--profile, -p` - Confluence profile
- `--output, -o` - Output format

### delete_space.py

Delete a space.

**Usage:**
```bash
confluence space delete DOCS
confluence space delete DOCS --force
```

**Arguments:**
- `space_key` - Space key (required)
- `--force, -f` - Skip confirmation
- `--profile, -p` - Confluence profile

### get_space_content.py

List pages in a space.

**Usage:**
```bash
# List all pages
confluence space content DOCS

# Filter by depth
confluence space content DOCS --depth root

# Include archived
confluence space content DOCS --include-archived
```

**Arguments:**
- `space_key` - Space key (required)
- `--depth` - Content depth: root, children, or all (default)
- `--status` - Filter by status (current, archived, draft)
- `--include-archived` - Include archived content
- `--limit, -l` - Maximum results
- `--profile, -p` - Confluence profile
- `--output, -o` - Output format

### get_space_settings.py

Get space settings and theme.

**Usage:**
```bash
confluence space settings DOCS
```

**Arguments:**
- `space_key` - Space key (required)
- `--profile, -p` - Confluence profile
- `--output, -o` - Output format

## Examples

### Natural Language Triggers

- "Create a new space called 'Engineering Docs' with key ENG"
- "List all spaces"
- "Get details for space DOCS"
- "Show me all pages in the KB space"
- "Update space DOCS with new description"
- "Delete space TEST"

### Common Workflows

**Create and configure a space:**
```
User: Create a documentation space for the API team
```
