---
name: confluence-hierarchy
description: Navigate and manage Confluence page hierarchies, ancestors, descendants, and trees
triggers:
  - hierarchy
  - ancestor
  - parent
  - child
  - children
  - descendant
  - tree
  - breadcrumb
  - navigation
  - reorder
---

# Confluence Hierarchy Skill

## Overview

This skill provides operations for navigating and managing page hierarchies in Confluence, including getting ancestors, children, descendants, and full page trees.

## Available Scripts

### get_ancestors.py

Get all ancestor pages for a given page (parent, grandparent, etc.).

**Usage:**
```bash
python get_ancestors.py <page_id>
python get_ancestors.py <page_id> --breadcrumb
python get_ancestors.py <page_id> --output json
```

**Options:**
- `--breadcrumb` - Display as breadcrumb path (Root > Parent > Current)
- `--output` - Output format: text (default) or json
- `--profile` - Confluence profile to use

**Examples:**
- Get ancestors: `python get_ancestors.py 12345`
- Show breadcrumb: `python get_ancestors.py 12345 --breadcrumb`

### get_children.py

Get direct child pages of a parent page (one level down only).

**Usage:**
```bash
python get_children.py <page_id>
python get_children.py <page_id> --limit 50
python get_children.py <page_id> --sort title
```

**Options:**
- `--limit` - Maximum number of children to retrieve (default: 25, max: 250)
- `--sort` - Sort by: title, id, or created
- `--output` - Output format: text (default) or json
- `--profile` - Confluence profile to use

**Examples:**
- Get children: `python get_children.py 12345`
- Sort by title: `python get_children.py 12345 --sort title`

### get_descendants.py

Get all descendant pages recursively (children, grandchildren, etc.).

**Usage:**
```bash
python get_descendants.py <page_id>
python get_descendants.py <page_id> --max-depth 2
python get_descendants.py <page_id> --output json
```

**Options:**
- `--max-depth` - Maximum depth to traverse (default: unlimited)
- `--output` - Output format: text (default) or json
- `--profile` - Confluence profile to use

**Examples:**
- Get all descendants: `python get_descendants.py 12345`
- Limit depth: `python get_descendants.py 12345 --max-depth 2`

### get_page_tree.py

Get full hierarchical tree structure with nested children.

**Usage:**
```bash
python get_page_tree.py <page_id>
python get_page_tree.py <page_id> --max-depth 3
python get_page_tree.py <page_id> --stats
```

**Options:**
- `--max-depth` - Maximum depth to traverse (default: unlimited)
- `--stats` - Show tree statistics (total pages, max depth, leaf pages)
- `--output` - Output format: text (default) or json
- `--profile` - Confluence profile to use

**Examples:**
- Get page tree: `python get_page_tree.py 12345`
- With statistics: `python get_page_tree.py 12345 --stats`

### reorder_children.py

Reorder child pages of a parent page.

**Usage:**
```bash
python reorder_children.py <parent_id>
python reorder_children.py <parent_id> <id1,id2,id3>
python reorder_children.py <parent_id> --reverse
```

**Options:**
- `--order` - Comma-separated child page IDs in desired order
- `--reverse` - Reverse current order
- `--profile` - Confluence profile to use

**Examples:**
- Show current order: `python reorder_children.py 12345`
- Reorder: `python reorder_children.py 12345 200,201,202`
- Reverse order: `python reorder_children.py 12345 --reverse`

**Note:** The Confluence v2 API may have limited support for page reordering. This script provides validation and structure for when the API fully supports it.

## Natural Language Examples

These phrases will trigger this skill:

- "Show me the ancestors of page 12345"
- "Get the breadcrumb path for page 12345"
- "List all children of page 12345"
- "Get all descendants of page 12345 up to depth 3"
- "Show me the page tree for 12345"
- "Reorder the children of page 12345"
- "What is the hierarchy for page 12345?"
- "Show the navigation path to page 12345"

## API Endpoints Used

- `GET /api/v2/pages/{id}?include=ancestors` - Get page with ancestors
- `GET /api/v2/pages/{id}/children` - Get direct children
- `GET /api/v2/pages/{id}` - Get page information

## Common Patterns

### Building Breadcrumbs

```bash
python get_ancestors.py 12345 --breadcrumb
# Output: Space Root > Section > Subsection > Current Page
```

### Visualizing Page Structure

```bash
python get_page_tree.py 12345 --stats
# Shows hierarchical tree with statistics
```

### Finding All Pages Below

```bash
python get_descendants.py 12345 --output json > descendants.json
# Export all descendants to JSON
```

### Limiting Traversal Depth

```bash
python get_descendants.py 12345 --max-depth 2
# Only get children and grandchildren
```

## Notes

- All scripts prevent infinite loops by tracking visited pages
- Depth is tracked starting from 1 for direct children
- Tree operations can be resource-intensive for large hierarchies
- Use `--max-depth` to limit traversal when needed
- Reordering may require API updates to fully function
