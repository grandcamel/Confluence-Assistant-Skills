# Confluence Assistant Skills

[![Release](https://img.shields.io/github/v/release/your-org/confluence-assistant-skills?style=flat-square)](https://github.com/your-org/confluence-assistant-skills/releases)
[![License](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg?style=flat-square)](https://www.python.org/downloads/)

Claude Code skills for automating Confluence Cloud operations via natural language.

## Features

- **Natural Language Interface**: Interact with Confluence using plain English
- **14 Specialized Skills**: Covering all major Confluence operations
- **Multi-Profile Support**: Switch between different Confluence instances
- **CQL Query Support**: Full Confluence Query Language support with export
- **Content Format Conversion**: Markdown to/from ADF and XHTML
- **Robust Error Handling**: Clear error messages with helpful suggestions
- **Response Caching**: Reduce API calls for better performance

## Quick Start

### 1. Install Dependencies

```bash
pip install -r .claude/skills/shared/scripts/lib/requirements.txt
```

### 2. Configure Authentication

Get an API token from [Atlassian Account Settings](https://id.atlassian.com/manage-profile/security/api-tokens).

Set environment variables:

```bash
export CONFLUENCE_SITE_URL="https://your-site.atlassian.net"
export CONFLUENCE_EMAIL="your-email@company.com"
export CONFLUENCE_API_TOKEN="your-api-token"
```

Or create `.claude/settings.local.json`:

```json
{
  "confluence": {
    "url": "https://your-site.atlassian.net",
    "email": "your-email@company.com",
    "api_token": "your-api-token"
  }
}
```

### 3. Use with Claude Code

Simply ask Claude to perform Confluence operations:

```
"Create a page called 'Meeting Notes' in the DOCS space"
"Search for pages about API documentation"
"List all spaces"
"Add label 'approved' to page 12345"
```

## Available Skills

| Skill | Purpose |
|-------|---------|
| `confluence-assistant` | Central hub that routes requests |
| `confluence-page` | Create, read, update, delete pages and blog posts |
| `confluence-space` | Manage spaces |
| `confluence-search` | CQL queries, search, and export |
| `confluence-comment` | Page and inline comments |
| `confluence-attachment` | File attachments |
| `confluence-label` | Content labeling |
| `confluence-template` | Page templates |
| `confluence-property` | Content properties (metadata) |
| `confluence-permission` | Space and page permissions |
| `confluence-analytics` | Content analytics |
| `confluence-watch` | Content watching |
| `confluence-hierarchy` | Page tree navigation |
| `confluence-jira` | JIRA integration |

## Example Commands

### Page Operations

```bash
# Create a page
python .claude/skills/confluence-page/scripts/create_page.py \
  --space DOCS --title "My Page" --body "Content here"

# Get a page
python .claude/skills/confluence-page/scripts/get_page.py 12345 --body

# Update a page
python .claude/skills/confluence-page/scripts/update_page.py 12345 \
  --body "New content" --message "Updated content"
```

### Search Operations

```bash
# CQL search
python .claude/skills/confluence-search/scripts/cql_search.py \
  "space = 'DOCS' AND type = page"

# Simple text search
python .claude/skills/confluence-search/scripts/search_content.py \
  "API documentation" --space DOCS

# Export results
python .claude/skills/confluence-search/scripts/export_results.py \
  "label = 'approved'" --format csv --output results.csv
```

### Space Operations

```bash
# List spaces
python .claude/skills/confluence-space/scripts/list_spaces.py

# Create space
python .claude/skills/confluence-space/scripts/create_space.py \
  --key ENG --name "Engineering"
```

## CQL Query Examples

```sql
-- Find pages in a space
space = "DOCS" AND type = page

-- Find by label
label = "documentation" AND label = "approved"

-- Text search
text ~ "API documentation"

-- Date filtering
created >= "2024-01-01" AND creator = currentUser()

-- Multiple spaces
space in ("DOCS", "KB") ORDER BY lastModified DESC
```

## Configuration

### Multiple Profiles

Configure different Confluence instances:

```json
{
  "confluence": {
    "default_profile": "production",
    "profiles": {
      "production": {
        "url": "https://company.atlassian.net",
        "default_space": "DOCS"
      },
      "sandbox": {
        "url": "https://company-sandbox.atlassian.net",
        "default_space": "TEST"
      }
    }
  }
}
```

Use with `--profile`:

```bash
python get_page.py 12345 --profile sandbox
```

### API Settings

```json
{
  "confluence": {
    "api": {
      "version": "2",
      "timeout": 30,
      "max_retries": 3,
      "retry_backoff": 2.0
    }
  }
}
```

## Project Structure

```
.claude/
├── settings.json          # Team settings (committed)
├── settings.local.json    # Personal settings (gitignored)
└── skills/
    ├── confluence-assistant/  # Hub skill
    ├── confluence-page/       # Page CRUD
    ├── confluence-space/      # Space management
    ├── confluence-search/     # CQL queries
    ├── confluence-comment/    # Comments
    ├── confluence-attachment/ # Attachments
    ├── confluence-label/      # Labels
    ├── confluence-template/   # Templates
    ├── confluence-property/   # Properties
    ├── confluence-permission/ # Permissions
    ├── confluence-analytics/  # Analytics
    ├── confluence-watch/      # Watching
    ├── confluence-hierarchy/  # Page tree
    ├── confluence-jira/       # JIRA integration
    └── shared/
        ├── scripts/lib/       # Shared Python library
        ├── config/            # Config schema
        └── tests/             # Shared test fixtures
```

## Development

### Running Tests

```bash
# Unit tests
pytest .claude/skills/*/tests/ -v --ignore="**/live_integration"

# Live integration tests (requires --profile)
pytest .claude/skills/confluence-page/tests/live_integration/ \
  --profile=sandbox -v
```

### Adding a New Script

See `CLAUDE.md` for the full development guide, including:
- Script template
- Import patterns
- Error handling
- Testing guidelines

## API Reference

This project uses the Confluence Cloud REST API:

- **v2 API** (primary): Modern JSON API for pages, spaces, comments
- **v1 API** (legacy): CQL search, content properties

Documentation: https://developer.atlassian.com/cloud/confluence/rest/v2/intro/

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

Please follow [Conventional Commits](https://www.conventionalcommits.org/) for commit messages.
