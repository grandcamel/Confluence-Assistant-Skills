---
name: confluence-page
description: Manage Confluence pages and blog posts - create, read, update, delete, copy, move, and version control
triggers:
  - create page
  - get page
  - read page
  - update page
  - edit page
  - delete page
  - remove page
  - blog post
  - blogpost
  - create blog
  - copy page
  - duplicate page
  - move page
  - relocate page
  - page version
  - version history
  - restore version
  - revert page
---

# Confluence Page Skill

Manage Confluence pages and blog posts through natural language commands.

## Overview

This skill handles all CRUD operations for Confluence pages and blog posts, including:
- Creating new pages and blog posts
- Reading page content and metadata
- Updating page content, title, and status
- Deleting pages (trash or permanent)
- Copying and moving pages
- Version history and restoration

## Available Scripts

### create_page.py

Create a new Confluence page.

**Usage:**
```bash
# Create a simple page
confluence page create --space DOCS --title "My New Page" --body "Page content here"

# Create with parent page
confluence page create --space DOCS --title "Child Page" --parent 12345 --body "Content"

# Create from Markdown file
confluence page create --space DOCS --title "From Markdown" --file content.md

# Create as draft
confluence page create --space DOCS --title "Draft Page" --body "WIP" --status draft
```

**Arguments:**
- `--space, -s` - Space key (required)
- `--title, -t` - Page title (required)
- `--body, -b` - Page body content
- `--file, -f` - Read body from file (Markdown supported)
- `--parent, -p` - Parent page ID
- `--status` - Page status: current (default) or draft
- `--profile` - Confluence profile to use
- `--output, -o` - Output format: text or json

### get_page.py

Retrieve a page's content and metadata.

**Usage:**
```bash
# Get by page ID
confluence page get 12345

# Get with full body content
confluence page get 12345 --body

# Get specific body format
confluence page get 12345 --body --format markdown

# JSON output
confluence page get 12345 --output json
```

**Arguments:**
- `page_id` - Page ID (required)
- `--body` - Include body content
- `--format` - Body format: storage, view, or markdown
- `--profile` - Confluence profile
- `--output, -o` - Output format: text or json

### update_page.py

Update an existing page.

**Usage:**
```bash
# Update title
confluence page update 12345 --title "New Title"

# Update body
confluence page update 12345 --body "New content"

# Update from file
confluence page update 12345 --file updated-content.md

# Update with version message
confluence page update 12345 --body "Updated" --message "Fixed typos"

# Change status
confluence page update 12345 --status draft
```

**Arguments:**
- `page_id` - Page ID (required)
- `--title, -t` - New title
- `--body, -b` - New body content
- `--file, -f` - Read body from file
- `--message, -m` - Version message
- `--status` - New status: current or draft
- `--profile` - Confluence profile
- `--output, -o` - Output format

### delete_page.py

Delete a page (move to trash or permanent delete).

**Usage:**
```bash
# Move to trash (default)
confluence page delete 12345

# Permanent delete
confluence page delete 12345 --permanent

# Force without confirmation
confluence page delete 12345 --force
```

**Arguments:**
- `page_id` - Page ID (required)
- `--permanent` - Permanently delete (cannot be recovered)
- `--force, -f` - Skip confirmation prompt
- `--profile` - Confluence profile

### create_blogpost.py

Create a new blog post.

**Usage:**
```bash
confluence page blog create --space BLOG --title "My Blog Post" --body "Blog content"

# From Markdown
confluence page blog create --space BLOG --title "From MD" --file post.md
```

**Arguments:**
- `--space, -s` - Space key (required)
- `--title, -t` - Blog post title (required)
- `--body, -b` - Blog post content
- `--file, -f` - Read body from file
- `--profile` - Confluence profile
- `--output, -o` - Output format

### get_blogpost.py

Retrieve a blog post.

**Usage:**
```bash
confluence page blog get 67890 --body
```

**Arguments:**
- `blogpost_id` - Blog post ID (required)
- `--body` - Include body content
- `--format` - Body format
- `--profile` - Confluence profile
- `--output, -o` - Output format

### copy_page.py

Copy a page to a new location.

**Usage:**
```bash
# Copy to same space
confluence page copy 12345 --title "Page Copy"

# Copy to different space
confluence page copy 12345 --title "Page Copy" --space NEWSPACE

# Copy with children
confluence page copy 12345 --title "Page Copy" --include-children
```

**Arguments:**
- `page_id` - Source page ID (required)
- `--title, -t` - New page title (default: "Copy of [original]")
- `--space, -s` - Target space key
- `--parent, -p` - Target parent page ID
- `--include-children` - Copy child pages recursively
- `--profile` - Confluence profile
- `--output, -o` - Output format

### move_page.py

Move a page to a new location.

**Usage:**
```bash
# Move to new parent
confluence page move 12345 --parent 67890

# Move to different space
confluence page move 12345 --space NEWSPACE

# Move to space root
confluence page move 12345 --space NEWSPACE --root
```

**Arguments:**
- `page_id` - Page ID to move (required)
- `--space, -s` - Target space key
- `--parent, -p` - Target parent page ID
- `--root` - Move to space root (no parent)
- `--profile` - Confluence profile

### get_page_versions.py

Get version history for a page.

**Usage:**
```bash
# List all versions
confluence page versions 12345

# Limit results
confluence page versions 12345 --limit 10

# Show version details
confluence page versions 12345 --detailed
```

**Arguments:**
- `page_id` - Page ID (required)
- `--limit, -l` - Maximum versions to return
- `--detailed` - Show full version details
- `--profile` - Confluence profile
- `--output, -o` - Output format

### restore_version.py

Restore a page to a previous version.

**Usage:**
```bash
# Restore to version 5
confluence page restore 12345 --version 5

# With version message
confluence page restore 12345 --version 5 --message "Restoring to known good state"
```

**Arguments:**
- `page_id` - Page ID (required)
- `--version, -v` - Version number to restore (required)
- `--message, -m` - Version message for the restoration
- `--profile` - Confluence profile

## Examples

### Natural Language Triggers

- "Create a new page called 'Meeting Notes' in the DOCS space"
- "Get the content of page 12345"
- "Update page 12345 with this content: [content]"
- "Delete the page with ID 12345"
- "Create a blog post titled 'Sprint Review' in TEAM space"
- "Copy page 12345 to the ARCHIVE space"
- "Move page 12345 under parent page 67890"
- "Show me the version history for page 12345"
- "Restore page 12345 to version 3"

### Common Workflows

**Create a page from natural language:**
```
User: Create a page called "API Documentation" in DOCS space with content explaining our REST API