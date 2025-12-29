---
name: confluence-hierarchy
description: Content tree navigation - ancestors, descendants, children
triggers:
  - parent
  - children
  - child pages
  - tree
  - hierarchy
  - ancestors
  - descendants
---

# Confluence Hierarchy Skill

Navigate the content tree structure.

## Available Scripts

### get_ancestors.py
Get parent pages.

**Usage:**
```bash
python get_ancestors.py 12345
```

### get_descendants.py
Get all child pages recursively.

**Usage:**
```bash
python get_descendants.py 12345
python get_descendants.py 12345 --depth 3
```

### get_children.py
Get direct child pages.

**Usage:**
```bash
python get_children.py 12345
```

### get_page_tree.py
Display full page tree.

**Usage:**
```bash
python get_page_tree.py --space DOCS
python get_page_tree.py --page 12345 --depth 5
```

### reorder_children.py
Change child page order.
