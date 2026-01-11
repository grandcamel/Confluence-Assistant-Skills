---
name: confluence-permission
description: Manage space and page permissions and restrictions. ALWAYS use when user wants to control access, set restrictions, or manage who can view/edit content.
triggers:
  - permission
  - permissions
  - restrict
  - access
  - security
  - who can view
  - who can edit
  - lock page
  - restrict access
---

# Confluence Permission Skill

Manage space and page permissions and restrictions.

---

## ⚠️ PRIMARY USE CASE

**This skill controls who can access Confluence content.** Use this skill for:
- Setting space-level permissions (who can view/edit a space)
- Adding page restrictions (limit access to specific users/groups)
- Auditing current permissions and restrictions

**⚠️⚠️ WARNING**: Permission changes can lock users out of content. Always document current permissions before making changes.

---

## When to Use This Skill

| Trigger | Example |
|---------|---------|
| View permissions | "Who can access DOCS space?", "Show page restrictions" |
| Add permissions | "Give engineering-team read access to DOCS" |
| Remove permissions | "Remove John's access to page 12345" |
| Restrict pages | "Lock this page to admins only" |
| Audit access | "List all permissions for TEAMSPACE" |

---

## When NOT to Use This Skill

| Operation | Use Instead |
|-----------|-------------|
| Create/edit pages | `confluence-page` |
| Search for content | `confluence-search` |
| Manage space settings | `confluence-space` |
| View who's watching | `confluence-watch` |

---

## Risk Levels

| Operation | Risk | Notes |
|-----------|------|-------|
| Get permissions | - | Read-only |
| Add permission | ⚠️ | Grants access, can be removed |
| Remove permission | ⚠️⚠️ | **Can lock users out** |
| Add page restriction | ⚠️⚠️ | **Can hide content from users** |
| Remove all restrictions | ⚠️ | Opens page to all space members |

---

## Overview

This skill provides comprehensive permission management for Confluence:
- **Space Permissions**: Control who can access and administer entire spaces
- **Page Restrictions**: Limit read/edit access to specific pages

Note: Due to API limitations, this skill uses a hybrid approach:
- v2 API for reading space permissions
- v1 API for modifying space permissions and managing page restrictions

## CLI Commands

### confluence permission space get
Retrieve the list of permissions assigned to a space.

**Usage:**
```bash
confluence permission space get SPACE_KEY
confluence permission space get DOCS --output json
```

**Output:** Lists all users and groups with their assigned operations (read, write, administer, etc.)

### confluence permission space add
Grant a permission to a user or group for a space.

**Usage:**
```bash
confluence permission space add SPACE_KEY --user email@example.com --operation read
confluence permission space add DOCS --group confluence-users --operation write
confluence permission space add TEST --user account-id:123456 --operation administer
```

**Valid Operations:**
- `read` - View space content
- `write` - Create and edit content
- `create` - Create pages
- `delete` - Delete content
- `export` - Export content
- `administer` - Manage space
- `setpermissions` - Modify permissions
- `createattachment` - Add attachments

### confluence permission space remove
Revoke a permission from a user or group for a space.

**Usage:**
```bash
confluence permission space remove SPACE_KEY --user email@example.com --operation read
confluence permission space remove DOCS --group confluence-users --operation write
```

### confluence permission page get
List restrictions on a page (who can read/edit).

**Usage:**
```bash
confluence permission page get PAGE_ID
confluence permission page get 123456 --output json
```

**Output:** Shows read and update restrictions with users and groups

### confluence permission page add
Add a restriction to limit page access.

**Usage:**
```bash
confluence permission page add PAGE_ID --operation read --user email@example.com
confluence permission page add 123456 --operation update --group confluence-users
confluence permission page add 123456 --operation read --user account-id:123456
```

**Restriction Types:**
- `read` - Who can view the page
- `update` - Who can edit the page

### confluence permission page remove
Remove a restriction from a page.

**Usage:**
```bash
confluence permission page remove PAGE_ID --operation read --user email@example.com
confluence permission page remove 123456 --operation update --group confluence-users
confluence permission page remove 123456 --operation read --all
```

Use `--all` to remove all restrictions of a type (makes page accessible to all space members).

## Examples

### Restrict a confidential page
```bash
# Get current restrictions
confluence permission page get 123456

# Add read restriction to specific users
confluence permission page add 123456 --operation read --user john@example.com
confluence permission page add 123456 --operation read --user jane@example.com

# Add edit restriction to admins group
confluence permission page add 123456 --operation update --group confluence-administrators
```

### Grant space access to a team
```bash
# Add read permission for the team
confluence permission space add TEAMSPACE --group engineering-team --operation read

# Add write permission for contributors
confluence permission space add TEAMSPACE --group engineering-leads --operation write

# Verify permissions
confluence permission space get TEAMSPACE
```

### Remove all restrictions from a page
```bash
# Remove all read restrictions (make viewable to all space members)
confluence permission page remove 123456 --operation read --all

# Remove all update restrictions (make editable to all space members)
confluence permission page remove 123456 --operation update --all
```

## Important Notes

### API Limitations
- Space permission management via API may be restricted by Confluence administrators
- Inherited page restrictions are not shown in API responses (CONFCLOUD-71108)
- Admin keys cannot bypass restrictions when using the API

### Permission Hierarchy
- Space permissions apply to all content in the space
- Page restrictions override space permissions (more restrictive)
- Removing all page restrictions makes it follow space permissions

### Best Practices
- Always verify changes with `get` commands
- Use groups instead of individual users when possible
- Document permission changes in page history or space description
- Test with a non-admin account to verify restrictions work

---

## Common Pitfalls

### 1. Locking Yourself Out
- **Problem**: Removing your own access to a page/space
- **Solution**: Always ensure at least one admin retains access before changes

### 2. Inherited Restrictions Not Visible
- **Problem**: Page appears accessible but users can't view it
- **Solution**: Check parent page restrictions (API doesn't show inherited)

### 3. User vs Account ID
- **Problem**: `--user` not finding the person
- **Solution**: Use email address or account ID (`account-id:123456`)

### 4. Group Name Mismatch
- **Problem**: Group not found when adding permissions
- **Solution**: Group names are case-sensitive, verify exact name in Confluence admin

### 5. Space Admin Override
- **Problem**: Page restrictions being bypassed
- **Solution**: Space admins can always access content - this is by design

### 6. API Restrictions
- **Problem**: Permission changes fail silently
- **Solution**: Some permission operations require Confluence admin privileges

---

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| **403 Forbidden** | Insufficient privileges to modify permissions | Request space admin access |
| **404 Not Found** | User, group, or resource doesn't exist | Verify user email, group name, page ID |
| **400 Bad Request** | Invalid operation or subject type | Check operation name, use correct subject type |
| **409 Conflict** | Permission already exists or conflicts | Check current permissions first |

### Recovery from Permission Errors

**Locked out of page:**
```bash
# Space admin can remove restrictions via UI or API
confluence permission page remove PAGE_ID --operation read --all
confluence permission page remove PAGE_ID --operation update --all
```

**Accidentally removed space access:**
```bash
# Confluence admin can restore via Confluence Admin > Space Permissions
# Or re-add the permission:
confluence permission space add SPACE_KEY --group GROUP_NAME --operation read
```

**Audit trail:**
- Space permission changes are logged in Confluence audit log
- Page restriction changes appear in page history
