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
python add_label.py 12345 --label documentation
python add_label.py 12345 --labels doc,approved,v2
```

### remove_label.py
Remove a label from content.

**Usage:**
```bash
python remove_label.py 12345 --label draft
```

### get_labels.py
List labels on content.

**Usage:**
```bash
python get_labels.py 12345
```

### search_by_label.py
Find content by label.

**Usage:**
```bash
python search_by_label.py documentation
python search_by_label.py approved --space DOCS
```

### list_popular_labels.py
List most used labels.

**Usage:**
```bash
python list_popular_labels.py --space DOCS
python list_popular_labels.py --limit 20
```
