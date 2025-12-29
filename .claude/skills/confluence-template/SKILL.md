---
name: confluence-template
description: Work with page templates and blueprints
triggers:
  - template
  - blueprint
  - create from template
  - page template
---

# Confluence Template Skill

Work with Confluence page templates and blueprints.

## Available Scripts

### list_templates.py
List available templates.

**Usage:**
```bash
python list_templates.py --space DOCS
python list_templates.py --type page
```

### get_template.py
Get template content.

**Usage:**
```bash
python get_template.py TEMPLATE_ID
```

### create_from_template.py
Create a page from a template.

**Usage:**
```bash
python create_from_template.py --template TEMPLATE_ID --space DOCS --title "New Page"
```

### create_template.py
Create a new template.

### update_template.py
Update an existing template.
