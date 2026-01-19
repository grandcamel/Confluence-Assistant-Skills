---
name: confluence-admin
description: >
  Complete Confluence administration including spaces, templates, users, groups,
  permissions, and site settings. Use when managing space structure, configuring
  templates, controlling access, or setting up Confluence for teams.
triggers:
  - admin
  - administration
  - site settings
  - global settings
  - user management
  - group management
  - template management
  - space settings
  - configure
  - setup
---

# Confluence Admin Skill

Comprehensive administration tools for Confluence Cloud covering space management, templates, users, groups, and permissions.

---

## ⚠️ PRIMARY USE CASE

**This skill handles Confluence administration tasks.** Use for:
- Space settings and configuration
- Template management and creation
- User and group management
- Permission scheme configuration
- Site-level settings

---

## When to Use / When NOT to Use

| Use This Skill | Use Instead |
|----------------|-------------|
| Space settings/configuration | - |
| Create/manage templates | - |
| User/group management | - |
| Permission schemes | - |
| Site settings | - |
| Page content CRUD | `confluence-page` |
| Single page permissions | `confluence-permission` |
| Search content | `confluence-search` |

---

## Risk Levels

| Operation | Risk | Notes |
|-----------|------|-------|
| List users/groups | - | Read-only |
| View settings | - | Read-only |
| Create templates | ⚠️ | Can be deleted |
| Update space settings | ⚠️ | Affects space behavior |
| Modify groups | ⚠️⚠️ | Affects access |
| Change permission schemes | ⚠️⚠️ | Can lock users out |
| Delete space | ⚠️⚠️⚠️ | **IRREVERSIBLE** |

---

## What This Skill Does

**5 Major Administration Areas:**

| Area | Scripts | Key Operations |
|------|---------|----------------|
| **Space Administration** | 8 | Configure settings, themes, features |
| **Template Management** | 6 | Create, update, delete templates |
| **User Management** | 5 | Search, view, manage users |
| **Group Management** | 6 | Create, manage groups, membership |
| **Permission Management** | 7 | Schemes, grants, diagnostics |

---

## When to Use This Skill

Reach for this skill when you need to:

**Space Administration:**
- Configure space settings (homepage, description)
- Enable/disable space features
- Set space themes and look-and-feel
- Manage space categories

**Template Management:**
- Create page templates for standardization
- Update existing templates
- Manage blueprint configurations
- Set default templates for spaces

**User Management:**
- Search for users by name or email
- View user details and permissions
- Check user's group memberships

**Group Management:**
- Create and manage groups
- Add/remove users from groups
- View group membership

**Permission Administration:**
- Create permission schemes
- Assign permissions to groups/users
- Diagnose permission issues
- Audit access control

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

### Space Administration

```bash
# View space settings
confluence admin space settings SPACEKEY

# Update space description
confluence admin space update SPACEKEY --description "New description"

# Set space homepage
confluence admin space set-homepage SPACEKEY --page-id 12345

# Enable/disable features
confluence admin space feature enable SPACEKEY --feature blog
confluence admin space feature disable SPACEKEY --feature blog

# View space theme
confluence admin space theme SPACEKEY

# List all space categories
confluence admin category list
```

### Template Management

```bash
# List templates
confluence admin template list
confluence admin template list --space DOCS

# Get template details
confluence admin template get TEMPLATE_ID

# Create template
confluence admin template create --space DOCS --name "Meeting Notes" --file template.md

# Update template
confluence admin template update TEMPLATE_ID --file updated.md

# Delete template
confluence admin template delete TEMPLATE_ID --confirm

# Set default template for space
confluence admin template set-default --space DOCS --template-id TEMPLATE_ID
```

### User Management

```bash
# Search users
confluence admin user search "name or email"
confluence admin user search "john" --include-groups

# Get user details
confluence admin user get ACCOUNT_ID

# List user's groups
confluence admin user groups ACCOUNT_ID

# Check user permissions on space
confluence admin user permissions ACCOUNT_ID --space DOCS
```

### Group Management

```bash
# List all groups
confluence admin group list

# Get group details
confluence admin group get "group-name"

# List group members
confluence admin group members "group-name"

# Create group
confluence admin group create "new-group-name"

# Delete group
confluence admin group delete "group-name" --confirm

# Add user to group
confluence admin group add-user "group-name" --user "user@email.com"

# Remove user from group
confluence admin group remove-user "group-name" --user "user@email.com" --confirm
```

### Permission Management

```bash
# List permission schemes
confluence admin permission-scheme list

# Get scheme details
confluence admin permission-scheme get SCHEME_ID

# Create permission scheme
confluence admin permission-scheme create --name "Custom Scheme" --description "..."

# Add permission grant
confluence admin permission-scheme add-grant SCHEME_ID --permission edit --group "editors"

# Remove permission grant
confluence admin permission-scheme remove-grant SCHEME_ID --permission edit --group "editors"

# Assign scheme to space
confluence admin permission-scheme assign --space DOCS --scheme-id SCHEME_ID

# Diagnose permissions (check your access)
confluence admin permissions check --space DOCS
confluence admin permissions check --space DOCS --only-missing
```

---

## Common Patterns

### Preview Before Changing

```bash
confluence admin group delete "group-name" --dry-run
confluence admin template delete TEMPLATE_ID --dry-run
confluence admin permission-scheme assign --space DOCS --scheme-id 123 --dry-run
```

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
| Template CRUD | Space Admin |
| User/Group (read) | Browse Users |
| User/Group (write) | Site Admin |
| Permission schemes | Site Admin |

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
confluence admin space permissions --space DOCS

# Check your group memberships
confluence admin user groups YOUR_ACCOUNT_ID
```

### Verify User Access

```bash
# Find user by email
confluence admin user search "user@email.com"

# Check their groups
confluence admin user groups ACCOUNT_ID

# Check their space permissions
confluence admin user permissions ACCOUNT_ID --space DOCS
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
| **confluence-space** | Create/delete spaces (uses settings from here) |
| **confluence-page** | Page CRUD (uses templates created here) |
| **confluence-permission** | Single-page permissions |
| **confluence-bulk** | Bulk operations (uses permission schemes) |
| **confluence-template** | Template creation from pages |
| **confluence-ops** | Cache management for admin operations |

---

## Best Practices

### Space Setup Workflow

1. Create space: `confluence space create ...`
2. Configure settings: `confluence admin space settings ...`
3. Set up templates: `confluence admin template create ...`
4. Configure permissions: `confluence admin permission-scheme assign ...`
5. Add users: `confluence admin group add-user ...`

### Permission Scheme Design

- Create role-based groups (viewers, editors, admins)
- Use permission schemes for consistent access control
- Test with `--dry-run` before applying changes
- Document permission decisions

### Template Management

- Use templates for standardized content
- Name templates descriptively
- Include placeholder sections
- Set default templates for common page types
