---
name: confluence-bulk
description: Bulk operations for 50+ pages - updates, moves, deletions, labels, and permissions. Use when updating multiple pages simultaneously (dry-run preview included), needing rollback safety, or coordinating team changes. Handles partial failures gracefully.
triggers:
  - bulk
  - multiple pages
  - batch
  - mass update
  - bulk delete
  - bulk label
  - bulk move
  - all pages in space
  - many pages
---

# Confluence Bulk Skill

Bulk operations for Confluence content management at scale - updates, moves, deletions, labels, and permissions.

---

## ⚠️ PRIMARY USE CASE

**This skill performs bulk operations on multiple pages.** Use for:
- Updating multiple pages simultaneously
- Bulk labeling/unlabeling content
- Moving many pages between spaces
- Bulk permission changes
- Mass deletion with dry-run preview

---

## When to Use / When NOT to Use

| Use This Skill | Use Instead |
|----------------|-------------|
| Update 10+ pages | - |
| Bulk label operations | - |
| Move pages between spaces | - |
| Bulk delete with preview | - |
| Single page operations | `confluence-page` |
| Search for pages | `confluence-search` |
| Single label add/remove | `confluence-label` |

---

## Risk Levels

| Operation | Risk | Notes |
|-----------|------|-------|
| Bulk label add | ⚠️ | Can be undone |
| Bulk label remove | ⚠️ | Can be undone |
| Bulk update | ⚠️⚠️ | Modifies content |
| Bulk move | ⚠️⚠️ | Changes hierarchy |
| Bulk permission change | ⚠️⚠️ | Access control |
| Bulk delete | ⚠️⚠️⚠️ | **DESTRUCTIVE** - Use dry-run first |

**Always use `--dry-run` for destructive operations!**

---

## When to Use This Skill

Use this skill when you need to:
- Update **multiple pages** with the same change
- Add or remove **labels from many pages** at once
- **Move pages** between spaces or under different parents
- **Delete multiple pages** with preview capability
- Change **permissions on many pages** simultaneously
- Execute operations with **dry-run preview** before making changes
- Handle **partial failures** gracefully with progress tracking

**Scale guidance:**
- 5-10 pages: Run directly, no special options needed
- 50-100 pages: Use `--dry-run` first, then execute
- 500+ pages: Use `--batch-size` and consider off-peak hours

---

## Quick Start

```bash
# Preview before making changes
confluence bulk label add --cql "space = DOCS AND type = page" --labels "approved" --dry-run

# Execute the labeling
confluence bulk label add --cql "space = DOCS AND type = page" --labels "approved"

# Bulk delete with preview
confluence bulk delete --cql "space = ARCHIVE AND created < '2023-01-01'" --dry-run
```

---

## CLI Commands

| Command | Purpose | Risk | Example |
|---------|---------|------|---------|
| `confluence bulk label add` | Add labels to pages | ⚠️ | `--cql "..." --labels "tag1,tag2"` |
| `confluence bulk label remove` | Remove labels from pages | ⚠️ | `--cql "..." --labels "old-tag"` |
| `confluence bulk update` | Update page properties | ⚠️⚠️ | `--cql "..." --title-prefix "[Archive]"` |
| `confluence bulk move` | Move pages to new location | ⚠️⚠️ | `--cql "..." --target-space NEWSPACE` |
| `confluence bulk delete` | **Delete pages permanently** | ⚠️⚠️⚠️ | `--cql "..." --dry-run` |
| `confluence bulk permission` | Change page permissions | ⚠️⚠️ | `--cql "..." --add-group viewers` |

---

## Common Options

All commands support these options:

| Option | Purpose | When to Use |
|--------|---------|-------------|
| `--dry-run` | Preview changes | **Always** use for ⚠️⚠️+ operations |
| `--yes` / `-y` | Skip confirmation | Scripted automation |
| `--max-pages N` | Limit scope (default: 100) | Testing, large operations |
| `--batch-size N` | Control batching | 500+ pages or rate limits |
| `--output json` | JSON output | Scripting, pipelines |

---

## Examples

### Bulk Label Operations

```bash
# Add labels to all pages in a space
confluence bulk label add --cql "space = DOCS AND type = page" --labels "documentation"

# Add multiple labels
confluence bulk label add --cql "space = DOCS AND label = 'api'" --labels "reviewed,approved"

# Remove labels
confluence bulk label remove --cql "space = ARCHIVE" --labels "active,current"

# Preview first
confluence bulk label add --cql "space = DOCS" --labels "new-tag" --dry-run
```

### Bulk Move Operations

```bash
# Move pages to different space
confluence bulk move --cql "space = OLD AND type = page" --target-space NEW --dry-run

# Move under specific parent
confluence bulk move --cql "label = 'archive-ready'" --target-parent 12345 --dry-run

# Execute after preview
confluence bulk move --cql "space = OLD" --target-space NEW --yes
```

### Bulk Delete (DESTRUCTIVE)

```bash
# ALWAYS preview first with dry-run
confluence bulk delete --cql "space = CLEANUP AND type = page" --dry-run

# Delete old content
confluence bulk delete --cql "space = ARCHIVE AND lastModified < '2022-01-01'" --dry-run

# Execute deletion (after confirming dry-run output)
confluence bulk delete --cql "space = CLEANUP" --yes

# Limit scope for safety
confluence bulk delete --cql "space = CLEANUP" --max-pages 50 --dry-run
```

**Safety features:**
- `--dry-run` shows exactly what will be deleted before making changes
- Confirmation required by default
- Default `--max-pages 100` prevents accidental mass deletion
- Per-page error tracking with summary of failures

### Bulk Permission Changes

```bash
# Add group to page permissions
confluence bulk permission --cql "space = INTERNAL" --add-group "engineering" --dry-run

# Remove user from permissions
confluence bulk permission --cql "label = 'sensitive'" --remove-user "contractor@email.com" --dry-run

# Restrict to specific group
confluence bulk permission --cql "space = PRIVATE" --restrict-to-group "executives" --dry-run
```

---

## Parameter Tuning Guide

**How many pages?**

| Page Count | Recommended Setup |
|------------|-------------------|
| <50 | Defaults are fine |
| 50-500 | `--dry-run` first, then execute |
| 500-1,000 | `--batch-size 100` |
| 1,000+ | `--batch-size 50`, run during off-peak |

**Getting rate limit (429) errors?**
- Reduce batch size: `--batch-size 25`
- Consider running during off-peak hours

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All operations successful |
| 1 | Some failures or validation error |
| 2 | All operations failed |
| 130 | Cancelled by user (Ctrl+C) |

---

## Troubleshooting

| Error | Solution |
|-------|----------|
| `No pages found` | Verify CQL query returns results |
| `Permission denied` | Check space/page permissions |
| `Rate limit (429)` | Reduce `--batch-size` or run during off-peak |
| `Invalid CQL` | Test CQL in Confluence search first |
| `Page locked` | Page may be being edited; retry later |

---

## Related Skills

- **confluence-page**: Single-page operations
- **confluence-label**: Individual label management
- **confluence-search**: Find pages with CQL queries
- **confluence-permission**: Single-page permission changes
