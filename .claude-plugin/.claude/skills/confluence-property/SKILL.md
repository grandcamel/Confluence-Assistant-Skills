---
name: confluence-property
description: Manage content properties (custom metadata) on Confluence pages and blog posts. ALWAYS use for custom metadata, key-value data, or application-specific fields.
triggers:
  - property
  - properties
  - metadata
  - custom data
  - content property
  - page property
  - set property
  - get property
  - delete property
  - list properties
---

# Confluence Property Skill

---

## ⚠️ PRIMARY USE CASE

**This skill manages custom metadata on pages.** Use for:
- Storing custom key-value data on pages
- Tracking workflow state (review status, approval)
- Integration metadata for external systems
- Structured data for automation

---

## When to Use / When NOT to Use

| Use This Skill | Use Instead |
|----------------|-------------|
| Get/set custom metadata | - |
| Store structured data | - |
| Edit page content | `confluence-page` |
| Add labels/tags | `confluence-label` |
| Set permissions | `confluence-permission` |

---

## Risk Levels

| Operation | Risk | Notes |
|-----------|------|-------|
| Get properties | - | Read-only |
| Set property | - | Can be overwritten |
| Delete property | ⚠️ | Data loss |

---

## Overview

Manages content properties on Confluence pages and blog posts. Content properties are custom metadata stored as key-value pairs that can be attached to any content. They are useful for storing application-specific data, configuration, or custom fields.

**Use Cases:**
- Store custom metadata on pages (e.g., review status, approval date)
- Implement custom workflows with property-based state tracking
- Store configuration data for external integrations
- Tag content with structured data for automated processing

## CLI Commands

### confluence property get
Retrieve content properties from a page or blog post.

**Usage:**
```bash
# Get all properties on content
confluence property get 12345

# Get specific property by key
confluence property get 12345 --key my-property

# Get with expanded version info
confluence property get 12345 --expand version

# Output as JSON
confluence property get 12345 --output json
```

**Options:**
- `content_id` - Content ID (required)
- `--key, -k` - Specific property key to retrieve
- `--expand` - Comma-separated fields to expand (e.g., version)
- `--output, -o` - Output format: text or json

### confluence property set
Create or update a content property.

**Usage:**
```bash
# Set simple string value
confluence property set 12345 my-property --value "text value"

# Set from JSON file
confluence property set 12345 config --file config.json

# Set complex JSON value
confluence property set 12345 data --value '{"enabled": true, "count": 42}'

# Update existing property (auto-increments version)
confluence property set 12345 my-property --value "updated" --update
```

**Options:**
- `content_id` - Content ID (required)
- `key` - Property key (required)
- `--value, -v` - Property value (string or JSON)
- `--file, -f` - Read value from JSON file
- `--update` - Update existing property (fetches current version)
- `--version` - Explicit version number for update
- `--output, -o` - Output format: text or json

**Value Types:**
Properties can store:
- Simple strings: `"text"`
- Numbers: `42`
- Booleans: `true`/`false`
- Complex JSON objects: `{"key": "value", "array": [1, 2, 3]}`

### confluence property delete
Delete a content property.

**Usage:**
```bash
# Delete property (with confirmation prompt)
confluence property delete 12345 my-property

# Force delete without confirmation
confluence property delete 12345 my-property --force
```

**Options:**
- `content_id` - Content ID (required)
- `key` - Property key to delete (required)
- `--force` - Delete without confirmation

### confluence property list
List and filter content properties.

**Usage:**
```bash
# List all properties
confluence property list 12345

# Filter by key prefix
confluence property list 12345 --prefix app.

# Filter by regex pattern
confluence property list 12345 --pattern "config.*"

# Sort by version
confluence property list 12345 --sort version

# Show detailed version info
confluence property list 12345 --expand version --verbose

# JSON output
confluence property list 12345 --output json
```

**Options:**
- `content_id` - Content ID (required)
- `--prefix` - Filter by key prefix
- `--pattern` - Filter by regex pattern
- `--sort` - Sort by: key or version (default: key)
- `--expand` - Comma-separated fields to expand
- `--verbose, -v` - Show detailed information
- `--output, -o` - Output format: text or json

## API Reference

Uses Confluence REST API v1 endpoints:

- **Get all properties**: `GET /rest/api/content/{id}/property`
- **Get property**: `GET /rest/api/content/{id}/property/{key}`
- **Create property**: `POST /rest/api/content/{id}/property`
- **Update property**: `PUT /rest/api/content/{id}/property/{key}`
- **Delete property**: `DELETE /rest/api/content/{id}/property/{key}`

## Examples

### Store Review Status

```bash
# Set review status
confluence property set 98765 review-status --value '{"status": "approved", "date": "2024-01-15", "reviewer": "john@example.com"}'

# Get review status
confluence property get 98765 --key review-status

# Update review status
confluence property set 98765 review-status --value '{"status": "published", "date": "2024-01-20"}' --update
```

### Configuration Management

```bash
# Store config from file
confluence property set 12345 app-config --file config.json

# List all config properties
confluence property list 12345 --prefix app-

# Get specific config
confluence property get 12345 --key app-config
```

### Workflow State Tracking

```bash
# Initialize workflow state
confluence property set 12345 workflow --value '{"stage": "draft", "assignee": "alice@example.com"}'

# Update to next stage
confluence property set 12345 workflow --value '{"stage": "review", "assignee": "bob@example.com"}' --update

# List all workflow properties
confluence property list 12345 --pattern "workflow.*" --verbose
```

### Cleanup Old Properties

```bash
# List all properties
confluence property list 12345

# Delete specific property
confluence property delete 12345 old-property --force

# Delete with confirmation
confluence property delete 12345 temp-data
```

## Property Versioning

Properties support versioning for conflict detection:

1. **Create**: Initial version is 1
2. **Update**: Increment version number
3. **Conflict**: 409 error if version is out of sync

**Auto-version update:**
```bash
confluence property set 12345 my-prop --value "new value" --update
```

This automatically fetches the current version and increments it.

## Common Property Patterns

### Namespace Your Keys

Use prefixes to organize properties:
- `app.config.*` - Application configuration
- `workflow.*` - Workflow state
- `review.*` - Review metadata
- `integration.*` - External integration data

### Store Timestamps

```json
{
  "created": "2024-01-15T10:30:00Z",
  "modified": "2024-01-20T14:45:00Z",
  "reviewed": "2024-01-18T16:20:00Z"
}
```

### Track Multi-Stage Workflows

```json
{
  "stage": "review",
  "stages": ["draft", "review", "approved", "published"],
  "current_assignee": "reviewer@example.com",
  "history": [
    {"stage": "draft", "user": "author@example.com", "date": "2024-01-15"},
    {"stage": "review", "user": "reviewer@example.com", "date": "2024-01-20"}
  ]
}
```

### Store Arrays and Complex Data

```json
{
  "tags": ["important", "needs-update", "customer-facing"],
  "approvers": [
    {"name": "Alice", "email": "alice@example.com", "approved": true},
    {"name": "Bob", "email": "bob@example.com", "approved": false}
  ],
  "metrics": {
    "views": 1234,
    "likes": 56,
    "shares": 12
  }
}
```

## Error Handling

All commands handle common errors:

- **404 Not Found**: Content or property doesn't exist
- **403 Permission Denied**: Insufficient permissions
- **409 Conflict**: Version conflict on update
- **400 Validation Error**: Invalid input

Use `--output json` for programmatic error handling.

## Integration Tips

### Use with Automation

```bash
# Get property value in scripts
VALUE=$(confluence property get 12345 --key status --output json | jq -r '.value.status')

# Conditional updates
if [ "$VALUE" == "draft" ]; then
  confluence property set 12345 status --value '{"status": "review"}' --update
fi
```

### Bulk Operations

```bash
# Update properties on multiple pages
for PAGE_ID in 111 222 333; do
  confluence property set $PAGE_ID deploy-status --value '{"deployed": true}' --update
done
```

### Property-Based Search

Properties are indexed and searchable via CQL:

```bash
# Find pages with specific property
confluence search cql "content.property[my-property].value = 'test'"
```

## Notes

- Properties are content-specific (not inherited by child pages)
- Property keys are case-sensitive
- Values can be any valid JSON data type
- Maximum property size depends on Confluence instance limits
- Properties are not included in page exports by default
- Use version numbers to prevent concurrent update conflicts
