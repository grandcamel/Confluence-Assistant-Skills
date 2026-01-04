---
name: confluence-assistant
description: Central hub for Confluence operations - routes requests to specialized skills
triggers:
  - confluence
  - wiki
  - atlassian wiki
  - confluence cloud
---

# Confluence Assistant

The central hub skill that routes Confluence requests to specialized skills.

## Overview

This skill acts as the main entry point for Confluence operations, intelligently routing requests to the appropriate specialized skill based on the user's intent.

## Available Skills

| Skill | Purpose | Triggers |
|-------|---------|----------|
| `confluence-page` | Page/blog CRUD | create page, update page, delete page, blog post |
| `confluence-space` | Space management | create space, list spaces, space settings |
| `confluence-search` | CQL queries | search, find pages, CQL, query |
| `confluence-comment` | Comments | comment, add comment, resolve |
| `confluence-attachment` | File attachments | attach, upload, download |
| `confluence-label` | Content labeling | label, tag, add label |
| `confluence-template` | Page templates | template, blueprint |
| `confluence-property` | Content properties | property, metadata |
| `confluence-permission` | Access control | permission, restrict, access |
| `confluence-analytics` | Content analytics | analytics, views, statistics |
| `confluence-watch` | Notifications | watch, unwatch, notify |
| `confluence-hierarchy` | Content tree | parent, children, tree, ancestors |
| `confluence-jira` | JIRA integration | jira, embed issue, link jira |

## Routing Logic

The assistant uses keyword matching to route requests:

### Page Operations
- Keywords: `page`, `blog`, `create`, `update`, `delete`, `copy`, `move`, `version`
- Routes to: `confluence-page`

### Space Operations
- Keywords: `space`, `spaces`, `create space`, `list space`
- Routes to: `confluence-space`

### Search Operations
- Keywords: `search`, `find`, `query`, `CQL`, `export`
- Routes to: `confluence-search`

### Comment Operations
- Keywords: `comment`, `reply`, `inline`, `resolve`
- Routes to: `confluence-comment`

### Attachment Operations
- Keywords: `attach`, `upload`, `download`, `file`
- Routes to: `confluence-attachment`

### Label Operations
- Keywords: `label`, `tag`, `labels`
- Routes to: `confluence-label`

### Template Operations
- Keywords: `template`, `blueprint`, `from template`
- Routes to: `confluence-template`

### Property Operations
- Keywords: `property`, `properties`, `metadata`
- Routes to: `confluence-property`

### Permission Operations
- Keywords: `permission`, `restrict`, `access`, `security`
- Routes to: `confluence-permission`

### Analytics Operations
- Keywords: `analytics`, `views`, `statistics`, `popular`
- Routes to: `confluence-analytics`

### Watch Operations
- Keywords: `watch`, `unwatch`, `notify`, `follow`
- Routes to: `confluence-watch`

### Hierarchy Operations
- Keywords: `parent`, `children`, `child`, `tree`, `ancestor`, `descendant`
- Routes to: `confluence-hierarchy`

### JIRA Operations
- Keywords: `jira`, `issue`, `embed jira`
- Routes to: `confluence-jira`

## Configuration

### Authentication Setup

1. Get an API token from https://id.atlassian.com/manage-profile/security/api-tokens

2. Set environment variables:
```bash
export CONFLUENCE_SITE_URL="https://your-site.atlassian.net"
export CONFLUENCE_EMAIL="your-email@company.com"
export CONFLUENCE_API_TOKEN="your-api-token"
```

3. Or create `.claude/settings.local.json`:
```json
{
  "confluence": {
    "url": "https://your-site.atlassian.net",
    "email": "your-email@company.com",
    "api_token": "your-api-token"
  }
}
```

### Multiple Profiles

Configure multiple Confluence instances:

```json
{
  "confluence": {
    "default_profile": "production",
    "profiles": {
      "production": {
        "url": "https://company.atlassian.net",
        "default_space": "DOCS"
      },
      "sandbox": {
        "url": "https://company-sandbox.atlassian.net",
        "default_space": "TEST"
      }
    }
  }
}
```

## Example Commands

### Page Operations
- "Create a new page called 'Meeting Notes' in DOCS space"
- "Update page 12345 with new content"
- "Delete page 12345"
- "Copy page 12345 to ARCHIVE space"

### Space Operations
- "List all spaces"
- "Create a new space for the Engineering team"
- "Show me the contents of DOCS space"

### Search Operations
- "Search for pages about API documentation"
- "Find all pages with label 'approved'"
- "Export all pages in KB space to CSV"

### Comment Operations
- "Add a comment to page 12345"
- "Show me comments on page 12345"
- "Resolve the inline comment"

### Attachment Operations
- "Upload report.pdf to page 12345"
- "Download all attachments from page 12345"
- "List attachments on page 12345"

### Label Operations
- "Add label 'approved' to page 12345"
- "Find all pages with label 'documentation'"
- "Remove label 'draft' from page 12345"

### Hierarchy Operations
- "Show me the child pages of 12345"
- "Get the parent pages of 67890"
- "Display the page tree for DOCS space"

## API Reference

This skill uses the Confluence Cloud REST API:

- **v2 API** (primary): `/api/v2/*`
  - Pages, Spaces, Blog Posts, Comments, Attachments, Labels

- **v1 API** (legacy/fallback): `/rest/api/*`
  - Search (CQL), Content Properties, Space Settings

Documentation: https://developer.atlassian.com/cloud/confluence/rest/v2/intro/

## Error Handling

The assistant provides clear error messages for common issues:

- **401 Unauthorized**: Check your API token and email
- **403 Forbidden**: You don't have permission for this operation
- **404 Not Found**: The resource doesn't exist
- **429 Rate Limited**: Wait before retrying
- **5xx Server Error**: Confluence server issue

## Getting Help

- Use `/help` for general Claude Code help
- Check `CLAUDE.md` for project documentation
- See skill-specific SKILL.md files for detailed usage
