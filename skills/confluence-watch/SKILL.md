---
name: confluence-watch
description: Content watching and notifications. ALWAYS use when user wants to follow content or manage notifications.
triggers:
  - watch
  - unwatch
  - notify
  - follow
  - watching
  - watchers
  - notifications
  - subscribe
---

# Confluence Watch Skill

Manage content watching and notifications in Confluence.

---

## ⚠️ PRIMARY USE CASE

**This skill manages watch/follow subscriptions.** Use for:
- Watching pages for updates
- Watching spaces for new content
- Unwatching content
- Checking who is watching

---

## When to Use / When NOT to Use

| Use This Skill | Use Instead |
|----------------|-------------|
| Watch/unwatch pages | - |
| Watch/unwatch spaces | - |
| List watchers | - |
| View analytics | `confluence-analytics` |
| Set permissions | `confluence-permission` |

---

## Risk Levels

| Operation | Risk | Notes |
|-----------|------|-------|
| List watchers | - | Read-only |
| Watch content | - | Can be unwatched |
| Unwatch content | - | Can re-watch |

---

## Overview

This skill provides comprehensive watching and notification management:
- Watch/unwatch individual pages
- Watch entire spaces for new content
- Check who is watching content
- Verify your own watch status

## CLI Commands

### confluence watch page
Start watching a Confluence page to receive notifications for updates.

**Usage:**
```bash
confluence watch page PAGE_ID [--output FORMAT]
```

**Arguments:**
- `PAGE_ID` - ID of the page to watch (required)
- `--output, -o` - Output format: text or json (default: text)

**Examples:**
```bash
# Watch a page
confluence watch page 123456

# Get JSON output
confluence watch page 123456 --output json
```

### confluence watch unwatch-page
Stop watching a Confluence page.

**Usage:**
```bash
confluence watch unwatch-page PAGE_ID [--output FORMAT]
```

**Arguments:**
- `PAGE_ID` - ID of the page to unwatch (required)
- `--output, -o` - Output format: text or json (default: text)

**Examples:**
```bash
# Unwatch a page
confluence watch unwatch-page 123456

# Unwatch with JSON output
confluence watch unwatch-page 123456 --output json
```

### confluence watch space
Start or stop watching an entire Confluence space to receive notifications for new content.

**Usage:**
```bash
confluence watch space SPACE_KEY [--unwatch] [--output FORMAT]
```

**Arguments:**
- `SPACE_KEY` - Key of the space to watch/unwatch (required)
- `--unwatch, -u` - Unwatch the space instead of watching it
- `--output, -o` - Output format: text or json (default: text)

**Examples:**
```bash
# Watch a space
confluence watch space DOCS

# Watch space with lowercase key (auto-converted to uppercase)
confluence watch space kb

# Unwatch a space
confluence watch space DOCS --unwatch

# Unwatch using short flag
confluence watch space TEST -u

# Get JSON output
confluence watch space TEST --output json
```

### confluence watch list
Get the list of users who are watching a page.

**Usage:**
```bash
confluence watch list PAGE_ID [--output FORMAT]
```

**Arguments:**
- `PAGE_ID` - ID of the page (required)
- `--output, -o` - Output format: text or json (default: text)

**Examples:**
```bash
# Get watchers for a page
confluence watch list 123456

# Get watchers as JSON
confluence watch list 123456 --output json
```

**Output (text format):**
```
Watchers for "My Project Page":

Name                  Type
--------------------  ----------
John Doe              user
Jane Smith            user

Total: 2 watcher(s)
```

**Output (JSON format):**
```json
{
  "page": {
    "id": "123456",
    "title": "My Project Page",
    "type": "page"
  },
  "watchers": [
    {
      "accountId": "user-123",
      "displayName": "John Doe",
      "type": "user"
    },
    {
      "accountId": "user-456",
      "displayName": "Jane Smith",
      "type": "user"
    }
  ],
  "count": 2
}
```

### confluence watch status
Check if the current authenticated user is watching a specific page.

**Usage:**
```bash
confluence watch status PAGE_ID [--output FORMAT]
```

**Arguments:**
- `PAGE_ID` - ID of the page to check (required)
- `--output, -o` - Output format: text or json (default: text)

**Examples:**
```bash
# Check if watching a page
confluence watch status 123456

# Get JSON output
confluence watch status 123456 --output json
```

**Output (text format - watching):**
```
Watch Status: My Project Page
  Page ID: 123456
  Status: Watching
  You will receive notifications for updates to this page.
```

**Output (text format - not watching):**
```
Watch Status: My Project Page
  Page ID: 123456
  Status: Not watching
  Use `confluence watch page 123456` to start watching.
```

**Output (JSON format):**
```json
{
  "page": {
    "id": "123456",
    "title": "My Project Page"
  },
  "watching": true
}
```

## API Endpoints Used

This skill uses the Confluence v1 REST API:

- `POST /rest/api/user/watch/content/{id}` - Watch a page
- `DELETE /rest/api/user/watch/content/{id}` - Unwatch a page
- `POST /rest/api/user/watch/space/{key}` - Watch a space
- `DELETE /rest/api/user/watch/space/{key}` - Unwatch a space
- `GET /rest/api/content/{id}/notification/child-created` - Get watchers (primary endpoint)
- `GET /rest/api/content/{id}/notification/created` - Get watchers (fallback endpoint)
- `GET /rest/api/user/current` - Get current user info

**Note:** The watchers list endpoint uses `/notification/child-created` as the primary endpoint, with automatic fallback to `/notification/created` for compatibility with different Confluence versions.

## Common Use Cases

### Watch Pages for a Project
```bash
# Watch all key pages for a project
confluence watch page 123456  # Requirements page
confluence watch page 789012  # Design doc
confluence watch page 345678  # Release notes
```

### Audit Watchers
```bash
# Check who's watching important pages
confluence watch list 123456 --output json > watchers.json
```

### Verify Watch Status
```bash
# Check if you're watching before unwatching
confluence watch status 123456
confluence watch unwatch-page 123456
```

### Bulk Space Watching
```bash
# Watch multiple spaces
for space in DOCS KB DEV; do
    confluence watch space $space
done
```

## Error Handling

All commands include comprehensive error handling:

- **ValidationError** - Invalid page ID or space key
- **NotFoundError (404)** - Page or space doesn't exist
- **PermissionError (403)** - No access to page/space
- **AuthenticationError (401)** - Invalid credentials
- **RateLimitError (429)** - Too many requests

## Notes

- Watching a page you're already watching is safe (no error)
- Unwatching a page you're not watching is safe (no error)
- Space watching sends notifications for new pages and blog posts
- Page watching sends notifications for edits and comments
- Watch settings are per-user and persist until explicitly removed
- Some Confluence instances may have notification settings that override individual watches

## Related Skills

- `confluence-page` - Manage pages and content
- `confluence-space` - Manage spaces
- `confluence-comment` - Manage comments (also trigger notifications)
- `confluence-analytics` - View page popularity and engagement
