# Confluence Assistant Skills Quick Reference

One-page reference for all skills and common operations.

---

## Skills Overview

| Skill | Purpose | Key Commands |
|-------|---------|--------------|
| `confluence-page` | Page/blog CRUD | `page get`, `page create`, `page update`, `page delete` |
| `confluence-space` | Space management | `space list`, `space get`, `space create` |
| `confluence-search` | CQL queries & export | `search cql`, `search export` |
| `confluence-comment` | Page comments | `comment add`, `comment list`, `comment delete` |
| `confluence-attachment` | File attachments | `attachment upload`, `attachment download`, `attachment list` |
| `confluence-label` | Content labeling | `label add`, `label remove`, `label list` |
| `confluence-template` | Templates | `template list`, `template create` |
| `confluence-property` | Content metadata | `property set`, `property get`, `property delete` |
| `confluence-permission` | Access control | `permission list`, `permission add`, `permission remove` |
| `confluence-analytics` | Views & stats | `analytics views`, `analytics watchers` |
| `confluence-watch` | Notifications | `watch add`, `watch remove`, `watch list` |
| `confluence-hierarchy` | Content tree | `hierarchy tree`, `hierarchy children`, `hierarchy parent` |
| `confluence-jira` | JIRA integration | `jira embed`, `jira link` |

---

## Common Operations

### Page Operations
```bash
# Get page content
confluence page get 12345
confluence page get 12345 --body --format markdown

# Create page
confluence page create SPACE "Page Title" --body "Content"

# Update page
confluence page update 12345 --title "New Title"
confluence page update 12345 --body-file content.md

# Delete page
confluence page delete 12345 --confirm

# Copy/Move
confluence page copy 12345 --to-space NEWSPACE
confluence page move 12345 --to-parent 67890
```

### Space Operations
```bash
# List spaces
confluence space list
confluence space list --type global --output json

# Get space details
confluence space get SPACE-KEY

# Create space
confluence space create KEY "Space Name" --description "Description"
```

### Search Operations
```bash
# Basic CQL search
confluence search cql "space = DOCS AND type = page"

# Search by label
confluence search cql "label = 'approved'"

# Export results
confluence search export "space = DOCS" --format csv --output-file results.csv

# Search with filters
confluence search cql "text ~ 'API' AND lastModified > '2025-01-01'" --limit 50
```

---

## CQL Quick Reference

### Basic Operators
| Operator | Example | Description |
|----------|---------|-------------|
| `=` | `space = "DOCS"` | Exact match |
| `!=` | `type != blogpost` | Not equal |
| `~` | `text ~ "API"` | Contains text |
| `>`, `<`, `>=`, `<=` | `created > "2025-01-01"` | Date comparison |
| `IN` | `space IN ("A", "B")` | Multiple values |

### Common Fields
| Field | Description | Example |
|-------|-------------|---------|
| `space` | Space key | `space = "DOCS"` |
| `type` | Content type | `type = page` |
| `label` | Content label | `label = "approved"` |
| `title` | Page title | `title ~ "Guide"` |
| `text` | Full text | `text ~ "installation"` |
| `creator` | Created by | `creator = currentUser()` |
| `created` | Creation date | `created >= "2025-01-01"` |
| `lastModified` | Last modified | `lastModified < now("-7d")` |
| `ancestor` | Parent page | `ancestor = 12345` |

### Example Queries
```cql
# Pages in space with label
space = "DOCS" AND label = "published" AND type = page

# Recent pages by current user
creator = currentUser() AND created >= startOfMonth()

# Child pages of a parent
ancestor = 12345 AND type = page

# Pages without a specific label
space = "DOCS" AND label != "draft"

# Combined text and date search
text ~ "API documentation" AND lastModified > "2025-01-01"
```

---

## API Reference

### v2 API (Primary)
| Resource | Endpoint |
|----------|----------|
| Pages | `/api/v2/pages/{id}` |
| Spaces | `/api/v2/spaces/{id}` |
| Blog Posts | `/api/v2/blogposts/{id}` |
| Comments | `/api/v2/footer-comments/{id}` |
| Attachments | `/api/v2/attachments/{id}` |
| Labels | `/api/v2/pages/{id}/labels` |

### v1 API (Legacy)
| Resource | Endpoint |
|----------|----------|
| Content | `/rest/api/content/{id}` |
| Space | `/rest/api/space/{key}` |
| Search | `/rest/api/search?cql={query}` |
| Properties | `/rest/api/content/{id}/property/{key}` |

---

## Environment Variables

```bash
# Required
export CONFLUENCE_SITE_URL="https://your-site.atlassian.net"
export CONFLUENCE_EMAIL="your-email@company.com"
export CONFLUENCE_API_TOKEN="your-api-token"

# Optional
export CONFLUENCE_PROFILE="default"  # For multi-instance
```

---

## Risk Levels

| Symbol | Level | Description |
|--------|-------|-------------|
| - | LOW | Read-only, easily reversible |
| :warning: | MEDIUM | Modifiable, version history available |
| :warning::warning: | HIGH | Destructive, single item |
| :warning::warning::warning: | CRITICAL | Irreversible, affects multiple items |

---

## Error Codes

| Code | Meaning | Action |
|------|---------|--------|
| 401 | Authentication failed | Check API token |
| 403 | Permission denied | Request access |
| 404 | Not found | Verify ID/key |
| 409 | Conflict | Refresh and retry |
| 429 | Rate limited | Wait and retry |
| 5xx | Server error | Check status.atlassian.com |

---

## Related Documentation

- [SAFEGUARDS.md](./SAFEGUARDS.md) - Safety guidelines and recovery
- [ERROR_HANDLING.md](./ERROR_HANDLING.md) - Error handling patterns
- [DECISION_TREE.md](./DECISION_TREE.md) - Skill selection guide
- [Confluence REST API](https://developer.atlassian.com/cloud/confluence/rest/v2/intro/)
