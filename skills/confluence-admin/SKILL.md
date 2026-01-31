---
name: confluence-admin
description: >
  Confluence administration including users, groups, space settings,
  and permission diagnostics. Use when managing user access, group membership,
  viewing space configuration, or checking permissions.
triggers:
  - admin
  - administration
  - user management
  - group management
  - space settings
  - configure
---

# Confluence Admin Skill

Administration tools for Confluence Cloud covering user management, group management, space settings, and permission diagnostics.

---

## PRIMARY USE CASE

**This skill handles Confluence administration tasks.** Use for:
- User search and information
- Group management and membership
- Space settings and configuration
- Permission diagnostics

---

## When to Use / When NOT to Use

| Use This Skill | Use Instead |
|----------------|-------------|
| Space settings/configuration | - |
| User/group management | - |
| Permission diagnostics | - |
| View templates | - |
| Page content CRUD | `confluence-page` |
| Single page permissions | `confluence-permission` |
| Search content | `confluence-search` |
| Create pages from templates | `confluence-template` |

---

## Risk Levels

| Operation | Risk | Notes |
|-----------|------|-------|
| List users/groups | - | Read-only |
| View settings | - | Read-only |
| View templates | - | Read-only |
| Check permissions | - | Read-only |
| Update space settings | ⚠️ | Affects space behavior |
| Create groups | ⚠️ | Can be deleted |
| Modify group membership | ⚠️⚠️ | Affects access |
| Delete groups | ⚠️⚠️ | Affects access |

---

## What This Skill Does

**4 Major Administration Areas:**

| Area | Commands | Key Operations |
|------|----------|----------------|
| **User Management** | 3 | Search, view details, list groups |
| **Group Management** | 7 | Create, delete, manage membership |
| **Space Administration** | 3 | View settings, update, permissions |
| **Templates & Permissions** | 3 | List templates, check permissions |

---

## When to Use This Skill

Reach for this skill when you need to:

**User Management:**
- Search for users by name or email
- View user details
- Check user's group memberships

**Group Management:**
- Create and delete groups
- Add/remove users from groups
- View group membership

**Space Administration:**
- View space settings
- Update space description
- View space permissions

**Permission Diagnostics:**
- Check what permissions you have on a space
- Diagnose access issues

---

## Quick Start

```bash
# List all groups
confluence admin group list

# Search for users
confluence admin user search "john"

# View space settings
confluence admin space settings DOCS

# List templates in a space
confluence admin template list --space DOCS
```

---

## Available Commands

All commands support `--help` for full documentation.

### User Management

```bash
# Search users
confluence admin user search "name or email"
confluence admin user search "john" --include-groups
confluence admin user search "john" --limit 50

# Get user details
confluence admin user get ACCOUNT_ID

# List user's groups
confluence admin user groups ACCOUNT_ID
```

**Options for `user search`:**
- `--include-groups` - Include group membership in results
- `--limit, -l` - Maximum results (default: 25)
- `--output, -o` - Output format: text or json

### Group Management

```bash
# List all groups
confluence admin group list
confluence admin group list --limit 100

# Get group details
confluence admin group get "group-name"

# List group members
confluence admin group members "group-name"
confluence admin group members "group-name" --limit 100

# Create group
confluence admin group create "new-group-name"

# Delete group
confluence admin group delete "group-name" --confirm

# Add user to group
confluence admin group add-user "group-name" --user "user@email.com"

# Remove user from group
confluence admin group remove-user "group-name" --user "user@email.com" --confirm
```

**Options for `group list`:**
- `--limit, -l` - Maximum results (default: 50)
- `--output, -o` - Output format: text or json

**Options for `group members`:**
- `--limit, -l` - Maximum results (default: 50)
- `--output, -o` - Output format: text or json

### Space Administration

```bash
# View space settings
confluence admin space settings SPACEKEY

# Update space description
confluence admin space update SPACEKEY --description "New description"

# View space permissions
confluence admin space permissions SPACEKEY
```

### Templates

```bash
# List templates
confluence admin template list
confluence admin template list --space DOCS
confluence admin template list --limit 100

# Get template details
confluence admin template get TEMPLATE_ID
```

**Options for `template list`:**
- `--space, -s` - Filter by space key
- `--limit, -l` - Maximum results (default: 50)
- `--output, -o` - Output format: text or json

### Permission Diagnostics

```bash
# Check what permissions you have on a space
confluence admin permissions check --space DOCS

# Show only permissions you're missing
confluence admin permissions check --space DOCS --only-missing
```

---

## Common Patterns

### JSON Output for Scripting

```bash
confluence admin group list --output json
confluence admin user search "john" --output json
confluence admin template list --output json
```

---

## Permission Requirements

| Operation | Required Permission |
|-----------|---------------------|
| View settings | Space View |
| Update space | Space Admin |
| View templates | Space View |
| User/Group (read) | Browse Users |
| User/Group (write) | Site Admin |

---

## Common Errors

| Error | Solution |
|-------|----------|
| 403 Forbidden | Verify you have Space Admin or Site Admin permission |
| 404 Not Found | Check space key, template ID, or user ID |
| 409 Conflict | Resource exists - choose different name |
| 400 Bad Request | Validate input format (see command --help) |

---

## Troubleshooting

### Diagnose Permission Issues

```bash
# Check what permissions you have on a space
confluence admin permissions check --space DOCS

# Show only permissions you're missing
confluence admin permissions check --space DOCS --only-missing

# See who has access via groups
confluence admin space permissions DOCS

# Check your group memberships
confluence admin user groups YOUR_ACCOUNT_ID
```

### Verify User Access

```bash
# Find user by email
confluence admin user search "user@email.com"

# Check their groups
confluence admin user groups ACCOUNT_ID
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Permission denied |
| 3 | Resource not found |
| 4 | Validation error |

---

## Related Skills

| Skill | Use Case |
|-------|----------|
| **confluence-space** | Create/delete spaces |
| **confluence-page** | Page CRUD |
| **confluence-permission** | Single-page permissions |
| **confluence-bulk** | Bulk operations |
| **confluence-template** | Create pages from templates |
| **confluence-ops** | Cache management |

---

## Best Practices

### Group Management Workflow

1. Create role-based groups (viewers, editors, admins)
2. Add users to appropriate groups: `confluence admin group add-user ...`
3. Verify membership: `confluence admin group members ...`

### Permission Diagnostics Workflow

1. Check your permissions: `confluence admin permissions check --space DOCS`
2. Review space permissions: `confluence admin space permissions DOCS`
3. Verify group membership: `confluence admin user groups ACCOUNT_ID`
