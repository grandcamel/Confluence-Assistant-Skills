---
name: confluence-jira
description: JIRA integration - embed issues, create links between products
triggers:
  - jira
  - embed issue
  - link jira
  - jira macro
  - jira issues
---

# Confluence JIRA Skill

Cross-product JIRA integration.

## Available Scripts

### embed_jira_issues.py
Embed JIRA issues in a page.

**Usage:**
```bash
confluence jira embed 12345 --jql "project = PROJ AND status = Open"
confluence jira embed 12345 --issues PROJ-123,PROJ-456
```

### get_linked_issues.py
List JIRA issues linked to a page.

**Usage:**
```bash
confluence jira linked 12345
```

### create_jira_from_page.py
Create a JIRA issue from page content.

**Usage:**
```bash
confluence jira create-from-page 12345 --project PROJ --type Task
```

### link_to_jira.py
Create an application link.

### sync_jira_macro.py
Update JIRA macro content.
