---
name: confluence-label
description: Manage content labels - add, remove, and search by labels
triggers:
  - label
  - tag
  - add label
  - remove label
  - labels
---

# Confluence Label Skill

Manage labels on Confluence content.

## Available Scripts

### add_label.py
Add a label to content.

**Usage:**
```bash
confluence label add 12345 --label documentation
confluence label add 12345 --labels doc,approved,v2
```

### remove_label.py
Remove a label from content.

**Usage:**
```bash
confluence label remove 12345 --label draft
```

### get_labels.py
List labels on content.

**Usage:**
```bash
confluence label list 12345
```

### search_by_label.py
Find content by label.

**Usage:**
```bash
confluence label search documentation
confluence label search approved --space DOCS
```

### list_popular_labels.py
List most used labels.

**Usage:**
```bash
confluence label popular --space DOCS
confluence label popular --limit 20
```
