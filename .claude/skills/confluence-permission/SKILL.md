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
python get_space_permissions.py SPACE_ID
python get_space_permissions.py 123456 --output json
python get_space_permissions.py 123456 --profile production
```

**Output:** Lists all users and groups with their assigned operations (read, write, administer, etc.)

### add_space_permission.py
Grant a permission to a user or group for a space.

**Usage:**
```bash
python add_space_permission.py SPACE_KEY user:email@example.com read
python add_space_permission.py DOCS group:confluence-users write
python add_space_permission.py TEST user:account-id:123456 administer
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
python remove_space_permission.py SPACE_KEY user:email@example.com read
python remove_space_permission.py DOCS group:confluence-users write
```

### get_page_restrictions.py
List restrictions on a page (who can read/edit).

**Usage:**
```bash
python get_page_restrictions.py PAGE_ID
python get_page_restrictions.py 123456 --output json
python get_page_restrictions.py 123456 --profile production
```

**Output:** Shows read and update restrictions with users and groups

### add_page_restriction.py
Add a restriction to limit page access.

**Usage:**
```bash
python add_page_restriction.py PAGE_ID read user:email@example.com
python add_page_restriction.py 123456 update group:confluence-users
python add_page_restriction.py 123456 read user:account-id:123456
```

**Restriction Types:**
- `read` - Who can view the page
- `update` - Who can edit the page

**Principal Format:**
- `user:email@example.com` - User by email
- `user:username` - User by username
- `user:account-id:123456` - User by account ID
- `group:groupname` - Group by name

### remove_page_restriction.py
Remove a restriction from a page.

**Usage:**
```bash
python remove_page_restriction.py PAGE_ID read user:email@example.com
python remove_page_restriction.py 123456 update group:confluence-users
python remove_page_restriction.py 123456 read --all
```

Use `--all` to remove all restrictions of a type (makes page accessible to all space members).

## Examples

### Restrict a confidential page
```bash
# Get current restrictions
python get_page_restrictions.py 123456

# Add read restriction to specific users
python add_page_restriction.py 123456 read user:john@example.com
python add_page_restriction.py 123456 read user:jane@example.com

# Add edit restriction to admins group
python add_page_restriction.py 123456 update group:confluence-administrators
```

### Grant space access to a team
```bash
# Add read permission for the team
python add_space_permission.py TEAMSPACE group:engineering-team read

# Add write permission for contributors
python add_space_permission.py TEAMSPACE group:engineering-leads write

# Verify permissions
python get_space_permissions.py 789
```

### Remove all restrictions from a page
```bash
# Remove all read restrictions (make viewable to all space members)
python remove_page_restriction.py 123456 read --all

# Remove all update restrictions (make editable to all space members)
python remove_page_restriction.py 123456 update --all
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
