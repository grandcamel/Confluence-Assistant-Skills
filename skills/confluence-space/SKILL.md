---
name: confluence-space
description: Manage Confluence spaces - create, list, update, delete, and configure spaces. ALWAYS use when user wants to work with spaces (not individual pages).
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

---

## ⚠️ PRIMARY USE CASE

**This skill manages Confluence spaces (containers for pages).** Use this skill for:
- Creating new spaces
- Listing and browsing spaces
- Updating space properties (name, description, homepage)
- Viewing space content summary
- **Deleting spaces** (⚠️⚠️⚠️ IRREVERSIBLE)

---

## When to Use This Skill

| Trigger | Example |
|---------|---------|
| Create space | "Create a new space for the engineering team" |
| List spaces | "Show me all spaces", "List global spaces" |
| Get space | "Get details for DOCS space" |
| Space content | "What pages are in KB space?" |
| Update space | "Change the name of space DOCS" |
| Delete space | "Delete the TEST space" |

---

## When NOT to Use This Skill

| Operation | Use Instead |
|-----------|-------------|
| Create/edit individual pages | `confluence-page` |
| Search within a space | `confluence-search` |
| Set space permissions | `confluence-permission` |
| Navigate page hierarchy | `confluence-hierarchy` |

---

## Risk Levels

| Operation | Risk | Notes |
|-----------|------|-------|
| List/get spaces | - | Read-only |
| Create space | - | Can be deleted |
| Update space | ⚠️ | Changes can be reverted |
| Get space content | - | Read-only |
| Delete space | ⚠️⚠️⚠️ | **IRREVERSIBLE - ALL CONTENT LOST** |

---

## Overview

This skill handles all space management operations, including:
- Creating new spaces
- Listing and searching spaces
- Updating space properties
- Deleting spaces
- Viewing space content and settings

## CLI Commands

### confluence space create

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
- `--output, -o` - Output format: text or json

### confluence space get

Retrieve space details.

**Usage:**
```bash
confluence space get DOCS
confluence space get DOCS --output json
```

**Arguments:**
- `space_key` - Space key (required)
- `--output, -o` - Output format

### confluence space list

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
- `--output, -o` - Output format

### confluence space update

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
- `--output, -o` - Output format

### confluence space delete

Delete a space.

**Usage:**
```bash
confluence space delete DOCS
confluence space delete DOCS --force
```

**Arguments:**
- `space_key` - Space key (required)
- `--force, -f` - Skip confirmation

### confluence space content

List pages in a space.

**Usage:**
```bash
# List all pages
confluence space content DOCS

# Filter by depth (only "root" is supported)
confluence space content DOCS --depth root

# Include archived
confluence space content DOCS --include-archived
```

**Arguments:**
- `space_key` - Space key (required)
- `--depth` - Content depth filter (only `root` is currently supported)
- `--status` - Filter by status (current, archived, draft)
- `--include-archived` - Include archived content
- `--limit, -l` - Maximum results
- `--output, -o` - Output format

### confluence space settings

Get space settings and theme.

**Usage:**
```bash
confluence space settings DOCS
```

**Arguments:**
- `space_key` - Space key (required)
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

---

## Common Pitfalls

### 1. Space Key Restrictions
- **Problem**: Space creation fails with invalid key
- **Solution**: Keys must be 2-255 chars, alphanumeric only, uppercase recommended

### 2. Duplicate Space Key
- **Problem**: Space key already exists
- **Solution**: Use unique keys, check existing spaces first with `confluence space list`

### 3. Deleting Non-Empty Spaces
- **Problem**: Accidentally deleting a space with important content
- **Solution**: **Space deletion is PERMANENT** - export content first, double-check space key

### 4. Personal Space Naming
- **Problem**: Personal space creation fails
- **Solution**: Personal space keys must start with `~` followed by username

### 5. Homepage Not Found
- **Problem**: Setting homepage fails with 404
- **Solution**: Homepage page ID must be a page within the same space

---

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| **404 Not Found** | Space doesn't exist | Verify space key with `confluence space list` |
| **403 Forbidden** | No permission to access/modify space | Request space admin access |
| **409 Conflict** | Space key already exists | Use a different, unique key |
| **400 Bad Request** | Invalid space key format | Use alphanumeric characters only |

### Recovery from Errors

**Accidentally deleted space:**
```
⚠️⚠️⚠️ SPACE DELETION IS PERMANENT - NO RECOVERY POSSIBLE

Prevention:
- Always export space content before deletion
- Use --force flag only when absolutely certain
- Consider archiving instead of deleting
```

**Space permission issues:**
```bash
# Check current space permissions
confluence permission space get SPACE_KEY

# Request admin access from space administrator
```
