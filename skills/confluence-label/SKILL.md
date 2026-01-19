---
name: confluence-label
description: Manage content labels - add, remove, and search by labels. ALWAYS use when user wants to tag, label, or categorize content.
triggers:
  - label
  - tag
  - add label
  - remove label
  - labels
  - categorize
  - tag page
---

# Confluence Label Skill

Manage labels on Confluence content.

---

## ⚠️ PRIMARY USE CASE

**This skill manages labels (tags) on Confluence content.** Use for:
- Adding labels to pages
- Removing labels
- Finding content by label
- Viewing popular labels

---

## When to Use / When NOT to Use

| Use This Skill | Use Instead |
|----------------|-------------|
| Add/remove labels | - |
| Find by label | `confluence-search` (for complex queries) |
| List page labels | - |
| Create/edit pages | `confluence-page` |
| Set permissions | `confluence-permission` |

---

## Risk Levels

All operations are **low risk** and easily reversible:

| Operation | Risk | Notes |
|-----------|------|-------|
| List labels | - | Read-only |
| Add label | - | Can be removed |
| Remove label | - | Can be re-added |
| Search by label | - | Read-only |

---

## CLI Commands

### confluence label add
Add a label to content.

**Usage:**
```bash
confluence label add 12345 --label documentation
confluence label add 12345 --labels doc,approved,v2
```

### confluence label remove
Remove a label from content.

**Usage:**
```bash
confluence label remove 12345 --label draft
```

### confluence label list
List labels on content.

**Usage:**
```bash
confluence label list 12345
```

### confluence label search
Find content by label.

**Usage:**
```bash
confluence label search documentation
confluence label search approved --space DOCS
```

### confluence label popular
List most used labels.

**Usage:**
```bash
confluence label popular --space DOCS
confluence label popular --limit 20
```
