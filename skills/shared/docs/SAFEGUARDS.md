# Confluence Operations Safeguards

This document outlines safety guidelines for Confluence operations, helping prevent accidental data loss and ensuring smooth recovery from errors.

---

## Risk Levels

Operations are classified by their potential impact:

| Risk Level | Symbol | Description | Examples |
|------------|--------|-------------|----------|
| **CRITICAL** | :warning::warning::warning: | Irreversible, affects multiple items | Delete space, bulk delete pages |
| **HIGH** | :warning::warning: | Destructive, single item | Delete page, remove permissions |
| **MEDIUM** | :warning: | Modifiable, may cause issues | Update page, change permissions |
| **LOW** | - | Read-only or easily reversible | Get page, list spaces, add label |

---

## Operation Risk Matrix

| Skill | Operation | Risk | Recovery |
|-------|-----------|------|----------|
| **confluence-page** | Create page | - | Delete if needed |
| | Update page | :warning: | Restore from version history |
| | Delete page | :warning::warning: | Restore from trash (30 days) |
| | Copy page | - | Delete copy if needed |
| | Move page | :warning: | Move back to original location |
| **confluence-space** | Create space | - | Delete if needed |
| | Update space | :warning: | Revert settings manually |
| | Delete space | :warning::warning::warning: | **NOT RECOVERABLE** - all content lost |
| **confluence-permission** | Add permission | - | Remove permission |
| | Remove permission | :warning::warning: | Re-add permission manually |
| | Restrict page | :warning: | Remove restriction |
| **confluence-comment** | Add comment | - | Delete comment |
| | Delete comment | :warning: | **NOT RECOVERABLE** |
| **confluence-attachment** | Upload file | - | Delete attachment |
| | Delete attachment | :warning::warning: | Re-upload file |
| **confluence-label** | Add label | - | Remove label |
| | Remove label | - | Re-add label |
| **confluence-property** | Set property | - | Update or delete property |
| | Delete property | :warning: | Re-create property |

---

## Pre-Operation Checklists

### Before Deleting Content

1. **Verify the target** - Confirm page/space ID or title
2. **Check dependencies** - Are other pages linking to this?
3. **Backup if needed** - Export page content first
4. **Confirm permissions** - Do you have delete access?
5. **Consider alternatives** - Archive instead of delete?

### Before Bulk Operations

1. **Start small** - Test with 1-2 items first
2. **Use search preview** - Run CQL query to see affected items
3. **Document the scope** - Note which items will be affected
4. **Have a rollback plan** - Know how to undo changes
5. **Consider timing** - Avoid peak usage hours

### Before Permission Changes

1. **Document current state** - Note existing permissions
2. **Understand inheritance** - Space vs page permissions
3. **Test with one user** - Verify access works as expected
4. **Have admin backup** - Ensure someone can fix issues

---

## Recovery Procedures

### Deleted Pages

Confluence pages go to the **Trash** and can be restored for 30 days:

1. Navigate to Space Settings > Content Tools > Trash
2. Find the deleted page
3. Click "Restore"

**Via API:**
```bash
# List trashed content
confluence search cql "type=page AND status=trashed"

# Note: Restoration requires manual action in UI
```

### Deleted Spaces

:warning::warning::warning: **Space deletion is PERMANENT**

There is no recovery option for deleted spaces. Before deleting:
- Export all space content
- Move important pages to another space
- Verify with stakeholders

### Incorrect Permissions

If users lose access:

1. **Space Admin** can restore permissions via Space Settings
2. **Site Admin** can access via Confluence Administration
3. Use `confluence permission list` to audit current state

### Corrupted Content

If page content is corrupted:

1. **Version History** - Restore from previous version
   ```bash
   confluence page versions 12345
   confluence page restore 12345 --version 5
   ```

2. **Export/Import** - If version history is also corrupted

---

## Common Error Patterns

| Error Code | Meaning | Resolution |
|------------|---------|------------|
| **401** | Authentication failed | Check API token, verify email |
| **403** | Permission denied | Request access from space admin |
| **404** | Resource not found | Verify ID/key, check if deleted |
| **409** | Conflict (concurrent edit) | Refresh and retry |
| **429** | Rate limited | Wait 60 seconds, retry |
| **5xx** | Server error | Wait and retry, check Confluence status |

### Permission Error Diagnosis

When encountering 403 errors:

1. **Check space permissions**:
   ```bash
   confluence permission list SPACE-KEY
   ```

2. **Check page restrictions**:
   ```bash
   confluence permission page 12345
   ```

3. **Verify user access**:
   - Is the user in the required group?
   - Is there an explicit restriction on the page?
   - Are inherited permissions blocked?

---

## Skill-Specific Safeguards

### confluence-page

**Destructive Operations:**
- `delete_page.py` - Moves to trash, recoverable for 30 days
- `update_page.py` - Creates version history entry

**Safe Practices:**
- Always get page content before updating
- Use `--format json` to preserve structure
- Consider using `--dry-run` for scripts that support it

### confluence-space

**Destructive Operations:**
- `delete_space.py` - :warning::warning::warning: PERMANENT, no recovery

**Safe Practices:**
- Export space before deletion
- Require `--confirm` flag for deletion
- Double-check space key matches intended target

### confluence-permission

**Destructive Operations:**
- `remove_permission.py` - Can lock out users
- `restrict_page.py` - Can hide content from users

**Safe Practices:**
- Document current permissions before changes
- Test with a single user first
- Ensure at least one admin retains access

### confluence-attachment

**Destructive Operations:**
- `delete_attachment.py` - Permanent, no trash

**Safe Practices:**
- Download attachment before deleting
- Use `confluence attachment list` to verify target
- Consider versioning instead of deletion

---

## Error Response Templates

When operations fail, provide clear guidance:

### Authentication Error (401)
```
Authentication failed. Please check:
1. API token is valid (https://id.atlassian.com/manage-profile/security/api-tokens)
2. Email matches your Atlassian account
3. Site URL is correct (https://your-site.atlassian.net)
```

### Permission Error (403)
```
Permission denied for this operation.
- Space: {space_key}
- Required: {required_permission}
- Your access: {current_access}

Contact your space administrator to request access.
```

### Not Found Error (404)
```
Resource not found: {resource_type} {resource_id}
Possible causes:
1. The {resource_type} has been deleted
2. The ID/key is incorrect
3. You don't have permission to view it
```

---

## Best Practices Summary

### Before Operations
- Verify target resources exist
- Check your permission level
- Backup important data
- Test with non-production content first

### During Operations
- Monitor for errors
- Keep logs of changes
- Pause if unexpected results occur

### After Operations
- Verify expected outcomes
- Update documentation
- Notify affected users if needed

---

## Emergency Contacts

If you encounter critical issues:

1. **Confluence Status**: https://status.atlassian.com
2. **Support**: https://support.atlassian.com
3. **Community**: https://community.atlassian.com

---

<!-- PERMISSIONS
permissions:
  cli: confluence
  operations:
    # Safe - Read-only operations (page/space/search reads)
    - pattern: "confluence page get *"
      risk: safe
    - pattern: "confluence page view *"
      risk: safe
    - pattern: "confluence page list *"
      risk: safe
    - pattern: "confluence page versions *"
      risk: safe
    - pattern: "confluence page children *"
      risk: safe
    - pattern: "confluence page ancestors *"
      risk: safe
    - pattern: "confluence space get *"
      risk: safe
    - pattern: "confluence space list *"
      risk: safe
    - pattern: "confluence space view *"
      risk: safe
    - pattern: "confluence search cql *"
      risk: safe
    - pattern: "confluence search query *"
      risk: safe
    - pattern: "confluence permission list *"
      risk: safe
    - pattern: "confluence permission page *"
      risk: safe
    - pattern: "confluence comment list *"
      risk: safe
    - pattern: "confluence comment get *"
      risk: safe
    - pattern: "confluence attachment list *"
      risk: safe
    - pattern: "confluence attachment download *"
      risk: safe
    - pattern: "confluence label list *"
      risk: safe
    - pattern: "confluence property get *"
      risk: safe
    - pattern: "confluence property list *"
      risk: safe

    # Caution - Modifiable but easily reversible (create/update/labels)
    - pattern: "confluence page create *"
      risk: caution
    - pattern: "confluence page update *"
      risk: caution
    - pattern: "confluence page copy *"
      risk: caution
    - pattern: "confluence page move *"
      risk: caution
    - pattern: "confluence page restore *"
      risk: caution
    - pattern: "confluence space create *"
      risk: caution
    - pattern: "confluence space update *"
      risk: caution
    - pattern: "confluence permission add *"
      risk: caution
    - pattern: "confluence permission restrict *"
      risk: caution
    - pattern: "confluence comment add *"
      risk: caution
    - pattern: "confluence comment update *"
      risk: caution
    - pattern: "confluence attachment upload *"
      risk: caution
    - pattern: "confluence label add *"
      risk: caution
    - pattern: "confluence label remove *"
      risk: caution
    - pattern: "confluence property set *"
      risk: caution
    - pattern: "confluence property delete *"
      risk: caution

    # Warning - Destructive but potentially recoverable (page/comment deletes)
    - pattern: "confluence page delete *"
      risk: warning
    - pattern: "confluence comment delete *"
      risk: warning
    - pattern: "confluence attachment delete *"
      risk: warning
    - pattern: "confluence permission remove *"
      risk: warning

    # Danger - IRREVERSIBLE operations (space delete/purge)
    - pattern: "confluence space delete *"
      risk: danger
    - pattern: "confluence space purge *"
      risk: danger
    - pattern: "confluence page purge *"
      risk: danger
-->
