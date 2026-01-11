---
name: confluence-hierarchy
description: Navigate and manage Confluence page hierarchies, ancestors, descendants, and trees. ALWAYS use for parent/child relationships and page tree navigation.
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

---

## ⚠️ PRIMARY USE CASE

**This skill navigates page relationships.** Use for:
- Finding parent/ancestor pages
- Listing child/descendant pages
- Viewing page tree structure
- Reordering child pages

---

## When to Use / When NOT to Use

| Use This Skill | Use Instead |
|----------------|-------------|
| Get parent/ancestors | - |
| List children | - |
| View page tree | - |
| Move pages | `confluence-page` |
| Create pages | `confluence-page` |
| Search pages | `confluence-search` |

---

## Risk Levels

| Operation | Risk | Notes |
|-----------|------|-------|
| Get ancestors/children | - | Read-only |
| View tree | - | Read-only |
| Reorder pages | ⚠️ | Changes sort order |

---

## Overview

This skill provides operations for navigating and managing page hierarchies in Confluence, including getting ancestors, children, descendants, and full page trees.

## Available Scripts

### get_ancestors.py

Get all ancestor pages for a given page (parent, grandparent, etc.).

**Usage:**
```bash
confluence hierarchy ancestors <page_id>
confluence hierarchy ancestors <page_id> --breadcrumb
confluence hierarchy ancestors <page_id> --output json
```

**Options:**
- `--breadcrumb` - Display as breadcrumb path (Root > Parent > Current)
- `--output` - Output format: text (default) or json

**Examples:**
- Get ancestors: `confluence hierarchy ancestors 12345`
- Show breadcrumb: `confluence hierarchy ancestors 12345 --breadcrumb`

### get_children.py

Get direct child pages of a parent page (one level down only).

**Usage:**
```bash
confluence hierarchy children <page_id>
confluence hierarchy children <page_id> --limit 50
confluence hierarchy children <page_id> --sort title
```

**Options:**
- `--limit` - Maximum number of children to retrieve (default: 25, max: 250)
- `--sort` - Sort by: title, id, or created
- `--output` - Output format: text (default) or json

**Examples:**
- Get children: `confluence hierarchy children 12345`
- Sort by title: `confluence hierarchy children 12345 --sort title`

### get_descendants.py

Get all descendant pages recursively (children, grandchildren, etc.).

**Usage:**
```bash
confluence hierarchy descendants <page_id>
confluence hierarchy descendants <page_id> --max-depth 2
confluence hierarchy descendants <page_id> --output json
```

**Options:**
- `--max-depth` - Maximum depth to traverse (default: unlimited)
- `--output` - Output format: text (default) or json

**Examples:**
- Get all descendants: `confluence hierarchy descendants 12345`
- Limit depth: `confluence hierarchy descendants 12345 --max-depth 2`

### get_page_tree.py

Get full hierarchical tree structure with nested children.

**Usage:**
```bash
confluence hierarchy tree <page_id>
confluence hierarchy tree <page_id> --max-depth 3
confluence hierarchy tree <page_id> --stats
```

**Options:**
- `--max-depth` - Maximum depth to traverse (default: unlimited)
- `--stats` - Show tree statistics (total pages, max depth, leaf pages)
- `--output` - Output format: text (default) or json

**Examples:**
- Get page tree: `confluence hierarchy tree 12345`
- With statistics: `confluence hierarchy tree 12345 --stats`

### reorder_children.py

Reorder child pages of a parent page.

**Usage:**
```bash
confluence hierarchy reorder <parent_id>
confluence hierarchy reorder <parent_id> <id1,id2,id3>
confluence hierarchy reorder <parent_id> --reverse
```

**Options:**
- `--order` - Comma-separated child page IDs in desired order
- `--reverse` - Reverse current order

**Examples:**
- Show current order: `confluence hierarchy reorder 12345`
- Reorder: `confluence hierarchy reorder 12345 200,201,202`
- Reverse order: `confluence hierarchy reorder 12345 --reverse`

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
confluence hierarchy ancestors 12345 --breadcrumb
# Output: Space Root > Section > Subsection > Current Page
```

### Visualizing Page Structure

```bash
confluence hierarchy tree 12345 --stats
# Shows hierarchical tree with statistics
```

### Finding All Pages Below

```bash
confluence hierarchy descendants 12345 --output json > descendants.json
# Export all descendants to JSON
```

### Limiting Traversal Depth

```bash
confluence hierarchy descendants 12345 --max-depth 2
# Only get children and grandchildren
```

## Notes

- All scripts prevent infinite loops by tracking visited pages
- Depth is tracked starting from 1 for direct children
- Tree operations can be resource-intensive for large hierarchies
- Use `--max-depth` to limit traversal when needed
- Reordering may require API updates to fully function
