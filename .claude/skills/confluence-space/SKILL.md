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
python create_space.py --key DOCS --name "Documentation"

# Create with description
python create_space.py --key KB --name "Knowledge Base" --description "Company knowledge base"

# Create personal space
python create_space.py --key ~username --name "Personal Space" --type personal
```

**Arguments:**
- `--key, -k` - Space key (required, 2-255 chars, alphanumeric)
- `--name, -n` - Space name (required)
- `--description, -d` - Space description
- `--type` - Space type: global (default) or personal
- `--profile` - Confluence profile to use
- `--output, -o` - Output format: text or json

### get_space.py

Retrieve space details.

**Usage:**
```bash
python get_space.py DOCS
python get_space.py DOCS --output json
```

**Arguments:**
- `space_key` - Space key (required)
- `--profile` - Confluence profile
- `--output, -o` - Output format

### list_spaces.py

List all accessible spaces.

**Usage:**
```bash
# List all spaces
python list_spaces.py

# Filter by type
python list_spaces.py --type global

# Search by name
python list_spaces.py --query "docs"

# Limit results
python list_spaces.py --limit 10
```

**Arguments:**
- `--type` - Filter by type: global or personal
- `--query, -q` - Search query
- `--status` - Filter by status: current or archived
- `--limit, -l` - Maximum results
- `--profile` - Confluence profile
- `--output, -o` - Output format

### update_space.py

Update space properties.

**Usage:**
```bash
python update_space.py DOCS --name "New Name"
python update_space.py DOCS --description "Updated description"
python update_space.py DOCS --homepage 12345
```

**Arguments:**
- `space_key` - Space key (required)
- `--name, -n` - New space name
- `--description, -d` - New description
- `--homepage` - Homepage page ID
- `--profile` - Confluence profile
- `--output, -o` - Output format

### delete_space.py

Delete a space.

**Usage:**
```bash
python delete_space.py DOCS
python delete_space.py DOCS --force
```

**Arguments:**
- `space_key` - Space key (required)
- `--force, -f` - Skip confirmation
- `--profile` - Confluence profile

### get_space_content.py

List pages in a space.

**Usage:**
```bash
# List all pages
python get_space_content.py DOCS

# Filter by depth
python get_space_content.py DOCS --depth root

# Include archived
python get_space_content.py DOCS --include-archived
```

**Arguments:**
- `space_key` - Space key (required)
- `--depth` - Content depth: root, children, or all (default)
- `--status` - Filter by status
- `--include-archived` - Include archived content
- `--limit, -l` - Maximum results
- `--profile` - Confluence profile
- `--output, -o` - Output format

### get_space_settings.py

Get space settings and theme.

**Usage:**
```bash
python get_space_settings.py DOCS
```

**Arguments:**
- `space_key` - Space key (required)
- `--profile` - Confluence profile
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
