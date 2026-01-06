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

## When to Use This Skill

Use this skill when you need to work with Confluence and are unsure which specific skill to use. This hub will intelligently route your request to the appropriate specialized skill based on keywords in your request.

**Note**: Trigger keywords are case-insensitive.

## Overview

This skill acts as the main entry point for Confluence operations, intelligently routing requests to the appropriate specialized skill based on the user's intent.

## Available Skills

| Skill | Purpose | Triggers |
|-------|---------|----------|
| `confluence-page` | Page/blog CRUD | create page, update page, delete page, get page, copy, move, version, restore, blog post |
| `confluence-space` | Space management | create space, list spaces, get space, space settings, space content, delete space |
| `confluence-search` | CQL queries | search, find pages, find content, CQL, query, saved search, export |
| `confluence-comment` | Comments | comment, comments, add comment, reply, inline, resolve, footer comment |
| `confluence-attachment` | File attachments | attach, upload, download, file attachment |
| `confluence-label` | Content labeling | label, labels, tag, add label |
| `confluence-template` | Page templates | template, templates, blueprint, create from template |
| `confluence-property` | Content properties | property, properties, metadata, custom data, content property |
| `confluence-permission` | Access control | permission, permissions, restrict, access, security |
| `confluence-analytics` | Content analytics | analytics, views, statistics, watchers, contributors, page views, most viewed |
| `confluence-watch` | Notifications | watch, unwatch, notify, follow |
| `confluence-hierarchy` | Content tree | parent, children, tree, ancestors, hierarchy, breadcrumb, reorder |
| `confluence-jira` | JIRA integration | jira, jira macro, jira issues, embed issue, link jira |

## Routing Logic

The assistant uses keyword matching to route requests:

### Page Operations
- Keywords: `page`, `blog`, `create`, `update`, `delete`, `copy`, `move`, `version`, `read`, `get`, `edit`, `remove`, `duplicate`, `relocate`, `revert`, `restore`
- Routes to: `confluence-page`

### Space Operations
- Keywords: `space`, `spaces`, `create space`, `list space`, `get space`, `show spaces`, `update space`, `edit space`, `delete space`, `remove space`, `space settings`, `space content`, `space pages`
- Routes to: `confluence-space`

### Search Operations
- Keywords: `search`, `find`, `query`, `CQL`, `export`, `find content`, `saved search`, `search by label`
- Routes to: `confluence-search`

### Comment Operations
- Keywords: `comment`, `comments`, `reply`, `inline`, `resolve`, `footer comment`, `get comments`, `update comment`, `delete comment`
- Routes to: `confluence-comment`

### Attachment Operations
- Keywords: `attach`, `upload`, `download`, `file`, `attachment`, `attachments`
- Routes to: `confluence-attachment`

### Label Operations
- Keywords: `label`, `labels`, `tag`, `tags`
- Routes to: `confluence-label`

### Template Operations
- Keywords: `template`, `templates`, `blueprint`, `from template`, `page template`, `list templates`, `update template`, `create from template`
- Routes to: `confluence-template`

### Property Operations
- Keywords: `property`, `properties`, `metadata`, `custom data`, `content property`, `page property`, `set property`, `get property`, `delete property`, `list properties`
- Routes to: `confluence-property`

### Permission Operations
- Keywords: `permission`, `permissions`, `restrict`, `access`, `security`
- Routes to: `confluence-permission`

### Analytics Operations
- Keywords: `analytics`, `views`, `statistics`, `popular`, `watchers`, `contributors`, `page views`, `space analytics`, `most viewed`, `most popular`, `who is watching`, `content analytics`
- Routes to: `confluence-analytics`

### Watch Operations
- Keywords: `watch`, `unwatch`, `notify`, `follow`, `notifications`
- Routes to: `confluence-watch`

### Hierarchy Operations
- Keywords: `parent`, `children`, `child`, `tree`, `ancestor`, `descendant`, `hierarchy`, `breadcrumb`, `navigation`, `reorder`
- Routes to: `confluence-hierarchy`

### JIRA Operations
- Keywords: `jira`, `issue`, `embed jira`, `jira macro`, `jira issues`, `link jira`
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

### Template Operations
- "List all templates in DOCS space"
- "Create a page from the 'Meeting Notes' template"
- "Show available blueprints"
- "Update the 'Project Kickoff' template"

### Property Operations
- "Set property 'status' to 'approved' on page 12345"
- "Get all properties from page 12345"
- "List properties on page 12345"
- "Delete the 'draft' property from page 12345"

### Analytics Operations
- "Show me the view count for page 12345"
- "Who has viewed page 12345?"
- "What are the most viewed pages in DOCS space?"
- "Show watchers and contributors for page 12345"

### Watch Operations
- "Watch page 12345"
- "Unwatch page 12345"
- "Who is watching page 12345?"
- "Follow space DOCS"

### JIRA Integration Operations
- "Embed JIRA issue PROJ-123 in page 12345"
- "Show JIRA issues linked to page 12345"
- "Add a JIRA macro for project PROJ to the page"
- "Link page 12345 to JIRA issue DEV-456"

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
