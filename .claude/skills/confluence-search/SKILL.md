---
name: confluence-search
description: Search Confluence using CQL queries, validate syntax, export results, and manage search history
triggers:
  - search confluence
  - find pages
  - search pages
  - CQL
  - query confluence
  - export search
  - search results
  - find content
  - search by label
  - saved search
---

# Confluence Search Skill

Search Confluence content using CQL (Confluence Query Language).

## Overview

This skill provides powerful search capabilities:
- Execute CQL queries
- Validate CQL syntax
- Get field and value suggestions
- Interactive query builder
- Export results to CSV/JSON
- Streaming export for large result sets
- Query history management

## CQL Query Patterns

### Basic Queries

```cql
# Find pages in a space
space = "DOCS" AND type = page

# Find by label
label = "documentation"

# Text search
text ~ "API documentation"

# By creator
creator = "john.doe@company.com"
creator = currentUser()

# By date
created >= "2024-01-01"
lastModified > startOfMonth()
```

### Advanced Queries

```cql
# Multiple spaces
space in ("DOCS", "KB", "DEV") AND type = page

# Exclude labels
label = "approved" AND label != "draft"

# Date ranges
lastModified >= "2024-01-01" AND lastModified < "2024-02-01"

# Ancestor (child pages)
ancestor = 12345

# Combined with ordering
space = "DOCS" AND label = "api" ORDER BY lastModified DESC

# Content with attachments
type = attachment AND container.space = "DOCS"

# Blog posts by date
type = blogpost AND created >= startOfYear()
```

### CQL Fields Reference

| Field | Description | Example |
|-------|-------------|---------|
| space | Space key | `space = "DOCS"` |
| title | Page title | `title ~ "API"` |
| text | Full text search | `text ~ "configuration"` |
| type | Content type | `type = page` |
| label | Content label | `label = "docs"` |
| creator | Content creator | `creator = currentUser()` |
| contributor | Any contributor | `contributor = "email"` |
| created | Creation date | `created >= "2024-01-01"` |
| lastModified | Last modified date | `lastModified > startOfWeek()` |
| parent | Parent page ID | `parent = 12345` |
| ancestor | Ancestor page ID | `ancestor = 12345` |
| id | Content ID | `id = 12345` |

## Available Scripts

### cql_search.py

Execute CQL queries against Confluence.

**Usage:**
```bash
# Simple text search
python cql_search.py "text ~ 'API documentation'"

# Search with space filter
python cql_search.py "space = 'DOCS' AND type = page"

# With limit
python cql_search.py "label = 'approved'" --limit 50

# Show excerpts
python cql_search.py "text ~ 'config'" --show-excerpts
```

**Arguments:**
- `cql` - CQL query string (required)
- `--limit, -l` - Maximum results (default: 25)
- `--show-excerpts` - Show content excerpts
- `--show-labels` - Show content labels
- `--profile` - Confluence profile
- `--output, -o` - Output format: text or json

### cql_validate.py

Validate CQL query syntax.

**Usage:**
```bash
python cql_validate.py "space = 'DOCS' AND type = page"
python cql_validate.py "invalid query (("
```

**Arguments:**
- `cql` - CQL query to validate (required)
- `--profile` - Confluence profile (for server-side validation)

### cql_suggest.py

Get CQL field and value suggestions.

**Usage:**
```bash
# Get field suggestions
python cql_suggest.py --fields

# Get values for a field
python cql_suggest.py --field space
python cql_suggest.py --field type
```

**Arguments:**
- `--fields` - List available CQL fields
- `--field` - Get values for a specific field
- `--profile` - Confluence profile

### cql_interactive.py

Interactive CQL query builder.

**Usage:**
```bash
python cql_interactive.py
python cql_interactive.py --space DOCS
```

**Arguments:**
- `--space` - Pre-filter by space
- `--profile` - Confluence profile

### export_results.py

Export search results to file.

**Usage:**
```bash
# Export to CSV
python export_results.py "space = 'DOCS'" --format csv --output results.csv

# Export to JSON
python export_results.py "label = 'api'" --format json --output results.json

# Select columns
python export_results.py "type = page" --columns id,title,space,created
```

**Arguments:**
- `cql` - CQL query (required)
- `--format, -f` - Output format: csv or json (default: csv)
- `--output, -o` - Output file path (required)
- `--columns` - Columns to include (comma-separated)
- `--limit, -l` - Maximum results
- `--profile` - Confluence profile

### streaming_export.py

Export large result sets with checkpoints.

**Usage:**
```bash
# Full export with progress
python streaming_export.py "space = 'DOCS'" --output docs.csv

# Resume from checkpoint
python streaming_export.py "space = 'DOCS'" --output docs.csv --resume
```

**Arguments:**
- `cql` - CQL query (required)
- `--output, -o` - Output file path (required)
- `--format, -f` - Output format: csv or json
- `--batch-size` - Records per batch (default: 100)
- `--resume` - Resume from last checkpoint
- `--profile` - Confluence profile

### cql_history.py

Manage local query history.

**Usage:**
```bash
# List recent queries
python cql_history.py list

# Search history
python cql_history.py search "space = DOCS"

# Clear history
python cql_history.py clear
```

**Arguments:**
- `command` - list, search, clear, or show
- `--limit, -l` - Maximum entries for list

### search_content.py

Simple text search (no CQL knowledge required).

**Usage:**
```bash
python search_content.py "meeting notes"
python search_content.py "meeting notes" --space DOCS
python search_content.py "API documentation" --type page
```

**Arguments:**
- `query` - Search text (required)
- `--space` - Limit to space
- `--type` - Content type: page, blogpost, or all
- `--limit, -l` - Maximum results
- `--profile` - Confluence profile
- `--output, -o` - Output format

## Examples

### Natural Language Triggers

- "Search for pages about API documentation"
- "Find all pages with label 'approved' in DOCS space"
- "Search for content created this month"
- "Export all pages in KB space to CSV"
- "Find pages modified by me today"
