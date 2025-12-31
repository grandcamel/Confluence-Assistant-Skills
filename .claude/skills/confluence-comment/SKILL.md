---
name: confluence-comment
description: Manage comments on Confluence pages - add, get, update, delete, and resolve comments
triggers:
  - comment
  - comments
  - add comment
  - get comments
  - update comment
  - delete comment
  - inline comment
  - resolve comment
  - footer comment
---

# Confluence Comment Skill

## Overview

This skill provides comprehensive comment management for Confluence pages, supporting both footer comments and inline comments. Use it to add feedback, manage discussions, and track comment resolution.

## Available Scripts

### add_comment.py

Add a footer comment to a Confluence page.

**Usage:**
```bash
confluence comment add PAGE_ID "Comment text"
confluence comment add PAGE_ID --file comment.txt
confluence comment add PAGE_ID "Great page!" --profile production
```

**Arguments:**
- `page_id` - Page ID to add comment to
- `body` - Comment body text (or use --file)

**Options:**
- `--file`, `-f` - Read comment body from file
- `--profile` - Confluence profile to use
- `--output`, `-o` - Output format (text or json)

### get_comments.py

Retrieve all footer comments on a Confluence page.

**Usage:**
```bash
confluence comment list PAGE_ID
confluence comment list PAGE_ID --limit 10
confluence comment list PAGE_ID --sort created
confluence comment list PAGE_ID --output json
```

**Arguments:**
- `page_id` - Page ID to get comments from

**Options:**
- `--limit`, `-l` - Maximum number of comments to retrieve
- `--sort`, `-s` - Sort order (created or -created for newest first)
- `--profile` - Confluence profile to use
- `--output`, `-o` - Output format (text or json)

### update_comment.py

Update an existing comment's body.

**Usage:**
```bash
confluence comment update COMMENT_ID "Updated text"
confluence comment update COMMENT_ID --file updated.txt
confluence comment update COMMENT_ID "Fixed typo" --profile production
```

**Arguments:**
- `comment_id` - Comment ID to update
- `body` - Updated comment body (or use --file)

**Options:**
- `--file`, `-f` - Read updated body from file
- `--profile` - Confluence profile to use
- `--output`, `-o` - Output format (text or json)

### delete_comment.py

Delete a comment from a Confluence page.

**Usage:**
```bash
confluence comment delete COMMENT_ID
confluence comment delete COMMENT_ID --force
confluence comment delete COMMENT_ID --profile production
```

**Arguments:**
- `comment_id` - Comment ID to delete

**Options:**
- `--force`, `-f` - Skip confirmation prompt
- `--profile` - Confluence profile to use

### add_inline_comment.py

Add an inline comment to specific text in a Confluence page.

**Usage:**
```bash
confluence comment add-inline PAGE_ID "selected text" "Comment about this text"
confluence comment add-inline PAGE_ID "text" "Needs revision" --profile production
```

**Arguments:**
- `page_id` - Page ID to add inline comment to
- `selection` - Text selection to attach comment to
- `body` - Comment body text

**Options:**
- `--profile` - Confluence profile to use
- `--output`, `-o` - Output format (text or json)

**Note:** The text selection must match existing text in the page content.

### resolve_comment.py

Mark a comment as resolved or reopen it.

**Usage:**
```bash
confluence comment resolve COMMENT_ID --resolve
confluence comment resolve COMMENT_ID --unresolve
confluence comment resolve COMMENT_ID --resolve --profile production
```

**Arguments:**
- `comment_id` - Comment ID to resolve/unresolve

**Options:**
- `--resolve`, `-r` - Mark comment as resolved
- `--unresolve`, `-u` - Mark comment as unresolved/open
- `--profile` - Confluence profile to use
- `--output`, `-o` - Output format (text or json)

**Note:** Exactly one of --resolve or --unresolve must be specified.

## Examples

### Natural Language Triggers

**Adding Comments:**
- "Add a comment to page 12345 saying 'Great work!'"
- "Comment on page 67890 with the content from feedback.txt"
- "Leave a comment on the API docs page"

**Getting Comments:**
- "Show me all comments on page 12345"
- "Get the comments from the release notes"
- "List comments on page 67890, newest first"

**Updating Comments:**
- "Update comment 999 to say 'Revised feedback'"
- "Edit comment 888 with the text from file.txt"
- "Change my comment on that page"

**Deleting Comments:**
- "Delete comment 777"
- "Remove comment 666 without confirmation"
- "Delete my comment from that page"

**Inline Comments:**
- "Add inline comment to page 12345 on the text 'important section' saying 'Needs clarification'"
- "Comment on specific text in the documentation"

**Resolving Comments:**
- "Resolve comment 555"
- "Mark comment 444 as resolved"
- "Reopen comment 333"
- "Unresolve comment 222"

## API Endpoints Used

This skill uses the Confluence v2 REST API:

- **Footer Comments:**
  - `POST /api/v2/pages/{id}/footer-comments` - Add comment
  - `GET /api/v2/pages/{id}/footer-comments` - Get comments
  - `GET /api/v2/footer-comments/{id}` - Get specific comment
  - `PUT /api/v2/footer-comments/{id}` - Update comment
  - `DELETE /api/v2/footer-comments/{id}` - Delete comment

- **Inline Comments:**
  - `POST /api/v2/pages/{id}/inline-comments` - Add inline comment

## Error Handling

All scripts include proper error handling for:
- **404 Not Found** - Page or comment doesn't exist
- **403 Forbidden** - No permission to add/edit/delete comments
- **409 Conflict** - Version mismatch on updates
- **400 Bad Request** - Invalid input (empty body, invalid selection)

## Testing

Run the test suite:
```bash
# All tests
pytest .claude/skills/confluence-comment/tests/ -v

# Specific test file
pytest .claude/skills/confluence-comment/tests/test_add_comment.py -v
```

## Dependencies

This skill uses the shared library:
- `config_manager` - Confluence client and configuration
- `error_handler` - Exception handling with @handle_errors
- `validators` - Input validation (page IDs, comment bodies)
- `formatters` - Output formatting (format_comment, format_comments)

## Notes

- Comments support HTML storage format for rich text
- Inline comments require exact text matches in page content
- Comment IDs are numeric strings (same validation as page IDs)
- Resolution status is tracked separately from comment body
- Deletion requires confirmation unless --force is used
- All scripts support --profile for multi-instance configurations
