---
name: confluence-comment
description: Manage page and inline comments - add, edit, delete, and resolve comments
triggers:
  - comment
  - add comment
  - inline comment
  - reply
  - resolve comment
  - delete comment
---

# Confluence Comment Skill

Manage comments on Confluence pages.

## Available Scripts

### add_comment.py
Add a footer comment to a page.

**Usage:**
```bash
python add_comment.py 12345 --body "This is a comment"
python add_comment.py 12345 --file comment.md
```

### get_comments.py
List comments on a page.

**Usage:**
```bash
python get_comments.py 12345
python get_comments.py 12345 --limit 50
```

### update_comment.py
Edit an existing comment.

**Usage:**
```bash
python update_comment.py COMMENT_ID --body "Updated comment"
```

### delete_comment.py
Delete a comment.

**Usage:**
```bash
python delete_comment.py COMMENT_ID
```

### add_inline_comment.py
Add an inline comment with text selection.

### resolve_comment.py
Mark an inline comment as resolved.
