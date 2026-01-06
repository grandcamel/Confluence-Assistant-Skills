---
name: confluence-permission
description: Manage space and page permissions
triggers:
  - permission
  - permissions
  - restrict
  - access
  - security
---

# Confluence Permission Skill

Manage space and page permissions and restrictions.

## Overview

This skill provides comprehensive permission management for Confluence:
- **Space Permissions**: Control who can access and administer entire spaces
- **Page Restrictions**: Limit read/edit access to specific pages

Note: Due to API limitations, this skill uses a hybrid approach:
- v2 API for reading space permissions
- v1 API for modifying space permissions and managing page restrictions

## Available Scripts

### get_space_permissions.py
Retrieve the list of permissions assigned to a space.

**Usage:**
```bash
confluence permission space get SPACE_KEY
confluence permission space get DOCS --output json
confluence permission space get DOCS --profile production
```

**Output:** Lists all users and groups with their assigned operations (read, write, administer, etc.)

### add_space_permission.py
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

### remove_space_permission.py
Revoke a permission from a user or group for a space.

**Usage:**
```bash
confluence permission space remove SPACE_KEY --user email@example.com --operation read
confluence permission space remove DOCS --group confluence-users --operation write
```

### get_page_restrictions.py
List restrictions on a page (who can read/edit).

**Usage:**
```bash
confluence permission page get PAGE_ID
confluence permission page get 123456 --output json
confluence permission page get 123456 --profile production
```

**Output:** Shows read and update restrictions with users and groups

### add_page_restriction.py
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

### remove_page_restriction.py
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
- Always verify changes with `get_*` commands
- Use groups instead of individual users when possible
- Document permission changes in page history or space description
- Test with a non-admin account to verify restrictions work
