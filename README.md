# Confluence Assistant Skills

<p align="center">
  <img src=".github/assets/logo.png" alt="Confluence Assistant Skills" width="200">
</p>

<p align="center">
  <strong>Claude Code skills for automating Confluence Cloud operations via natural language</strong>
</p>

<p align="center">
  <a href="https://github.com/grandcamel/Confluence-Assistant-Skills/releases">
    <img src="https://img.shields.io/github/v/release/grandcamel/Confluence-Assistant-Skills?style=flat-square" alt="Release">
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square" alt="License">
  </a>
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/python-3.9+-blue.svg?style=flat-square" alt="Python">
  </a>
  <a href="https://github.com/grandcamel/Confluence-Assistant-Skills/actions">
    <img src="https://img.shields.io/github/actions/workflow/status/grandcamel/Confluence-Assistant-Skills/ci.yml?style=flat-square" alt="CI">
  </a>
</p>

---

## Features

- **Natural Language Interface** - Interact with Confluence using plain English
- **14 Specialized Skills** - Covering all major Confluence operations
- **Multi-Profile Support** - Switch between different Confluence instances
- **CQL Query Support** - Full Confluence Query Language with export capabilities
- **Content Format Conversion** - Markdown to/from ADF and XHTML
- **Robust Error Handling** - Clear error messages with helpful suggestions
- **Response Caching** - Reduce API calls for better performance

## Quick Start

### 1. Install Dependencies

```bash
pip install -r .claude/skills/shared/scripts/lib/requirements.txt
```

### 2. Configure Authentication

Get an API token from [Atlassian Account Settings](https://id.atlassian.com/manage-profile/security/api-tokens).

**Option A: Environment Variables (recommended for CI/CD)**

```bash
export CONFLUENCE_SITE_URL="https://your-site.atlassian.net"
export CONFLUENCE_EMAIL="your-email@company.com"
export CONFLUENCE_API_TOKEN="your-api-token"
```

**Option B: Local Configuration File**

Create `.claude/settings.local.json` (gitignored):

```json
{
  "confluence": {
    "url": "https://your-site.atlassian.net",
    "email": "your-email@company.com",
    "api_token": "your-api-token"
  }
}
```

### 3. Verify Connection

```bash
python .claude/skills/confluence-space/scripts/list_spaces.py --limit 1
```

You should see your first space listed. If you get an error, check the [Troubleshooting](#troubleshooting) section.

### 4. Use with Claude Code

Simply ask Claude to perform Confluence operations:

```
"Create a page called 'Meeting Notes' in the DOCS space"
"Search for pages about API documentation"
"List all spaces"
"Add label 'approved' to page 12345"
```

## Available Skills

| Skill | Purpose | Key Commands |
|-------|---------|--------------|
| `confluence-assistant` | Central hub that routes requests | - |
| `confluence-page` | Pages and blog posts | `create_page`, `get_page`, `update_page`, `copy_page` |
| `confluence-space` | Space management | `list_spaces`, `create_space`, `get_space` |
| `confluence-search` | CQL queries and export | `cql_search`, `search_content`, `export_results` |
| `confluence-comment` | Page and inline comments | `add_comment`, `list_comments` |
| `confluence-attachment` | File attachments | `upload_attachment`, `download_attachment` |
| `confluence-label` | Content labeling | `add_label`, `remove_label`, `search_by_label` |
| `confluence-template` | Page templates | `list_templates`, `create_from_template` |
| `confluence-property` | Content properties | `get_property`, `set_property` |
| `confluence-permission` | Access control | `get_permissions`, `set_permissions` |
| `confluence-analytics` | Content analytics | `get_views`, `get_watchers` |
| `confluence-watch` | Content watching | `watch_page`, `unwatch_page` |
| `confluence-hierarchy` | Page tree navigation | `get_ancestors`, `get_children` |
| `confluence-jira` | JIRA integration | `link_issue`, `embed_jira` |

## Example Commands

### Page Operations

```bash
# Create a page
python .claude/skills/confluence-page/scripts/create_page.py \
  --space DOCS --title "My Page" --body "Content here"

# Get a page with body content
python .claude/skills/confluence-page/scripts/get_page.py 12345 --body

# Update a page
python .claude/skills/confluence-page/scripts/update_page.py 12345 \
  --body "New content" --message "Updated content"

# Copy a page
python .claude/skills/confluence-page/scripts/copy_page.py 12345 \
  --title "Copy of Page" --space DOCS
```

### Search Operations

```bash
# CQL search
python .claude/skills/confluence-search/scripts/cql_search.py \
  "space = 'DOCS' AND type = page"

# Simple text search
python .claude/skills/confluence-search/scripts/search_content.py \
  "API documentation" --space DOCS

# Export results to CSV
python .claude/skills/confluence-search/scripts/export_results.py \
  "label = 'approved'" --format csv --output results.csv

# Validate CQL syntax
python .claude/skills/confluence-search/scripts/cql_validate.py \
  "space = 'DOCS' AND type = page"
```

### Space Operations

```bash
# List all spaces
python .claude/skills/confluence-space/scripts/list_spaces.py

# Get space details
python .claude/skills/confluence-space/scripts/get_space.py DOCS

# Create a new space
python .claude/skills/confluence-space/scripts/create_space.py \
  --key ENG --name "Engineering"
```

## CQL Query Reference

### Basic Queries

```sql
-- Find pages in a space
space = "DOCS" AND type = page

-- Find by label
label = "documentation" AND label = "approved"

-- Text search
text ~ "API documentation"

-- Find by creator
creator = currentUser()
```

### Date Filtering

```sql
-- Created after a date
created >= "2024-01-01"

-- Modified in date range
lastModified >= "2024-01-01" AND lastModified < "2024-02-01"

-- Using date functions
created >= startOfMonth() AND creator = currentUser()
```

### Advanced Queries

```sql
-- Multiple spaces
space in ("DOCS", "KB", "DEV") ORDER BY lastModified DESC

-- Exclude labels
label = "approved" AND label != "draft"

-- Child pages of a specific page
ancestor = 12345

-- Combine with sorting
space = "DOCS" AND label = "api" ORDER BY title ASC
```

### Available CQL Fields

| Field | Description | Example |
|-------|-------------|---------|
| `space` | Space key | `space = "DOCS"` |
| `title` | Page title | `title ~ "API"` |
| `text` | Full text content | `text ~ "documentation"` |
| `type` | Content type | `type = page` |
| `label` | Content label | `label = "approved"` |
| `creator` | Content creator | `creator = currentUser()` |
| `created` | Creation date | `created >= "2024-01-01"` |
| `lastModified` | Last modified date | `lastModified >= startOfWeek()` |
| `ancestor` | Parent page ID | `ancestor = 12345` |

## Configuration

### Multiple Profiles

Configure different Confluence instances in `.claude/settings.local.json`:

```json
{
  "confluence": {
    "default_profile": "production",
    "profiles": {
      "production": {
        "url": "https://company.atlassian.net",
        "email": "you@company.com",
        "api_token": "prod-token",
        "default_space": "DOCS"
      },
      "sandbox": {
        "url": "https://company-sandbox.atlassian.net",
        "email": "you@company.com",
        "api_token": "sandbox-token",
        "default_space": "TEST"
      }
    }
  }
}
```

Use with `--profile`:

```bash
python .claude/skills/confluence-page/scripts/get_page.py 12345 --profile sandbox
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
├── settings.json              # Team settings (committed)
├── settings.local.json        # Personal settings (gitignored)
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

### Setup

```bash
# Clone the repository
git clone https://github.com/grandcamel/Confluence-Assistant-Skills.git
cd Confluence-Assistant-Skills

# Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r .claude/skills/shared/scripts/lib/requirements.txt

# Install dev dependencies
pip install pytest pytest-cov
```

### Running Tests

```bash
# Run all unit tests
pytest .claude/skills/*/tests/ -v --ignore="**/live_integration"

# Run tests for a specific skill
pytest .claude/skills/confluence-page/tests/ -v

# Run with coverage
pytest --cov=.claude/skills/shared/scripts/lib --cov-report=html

# Run live integration tests (requires Confluence access)
pytest .claude/skills/confluence-page/tests/live_integration/ \
  --profile=sandbox -v
```

### Adding a New Script

See [CLAUDE.md](CLAUDE.md) for the full development guide, including:
- Script template with proper imports
- Error handling patterns
- Testing guidelines
- Commit message conventions

## Troubleshooting

### Authentication Errors

**Error**: `Authentication failed. Check your email and API token.`

1. Verify your API token is valid at [Atlassian Account Settings](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Ensure your email matches the one associated with the token
3. Check that the URL includes `https://` and ends with `.atlassian.net`

### Permission Errors

**Error**: `Permission denied: ...`

1. Verify you have access to the space/page in the Confluence web UI
2. Some operations require admin permissions
3. Check if the content is restricted

### Connection Errors

**Error**: `Connection timeout` or `Connection refused`

1. Check your internet connection
2. Verify the Confluence URL is correct
3. Check if your organization uses a VPN

### Rate Limiting

**Error**: `Rate limit exceeded. Retry after X seconds.`

1. Wait the specified time before retrying
2. Consider using the `--limit` parameter to reduce batch sizes
3. Enable caching to reduce API calls

### CQL Syntax Errors

**Error**: `Could not parse cql`

1. Use the validation script: `python cql_validate.py "your query"`
2. Check quotes are balanced (single or double, not mixed)
3. Verify field names are valid (see [CQL Reference](#cql-query-reference))

## API Reference

This project uses the Confluence Cloud REST API:

- **v2 API** (primary): Modern JSON API for pages, spaces, comments
- **v1 API** (legacy): CQL search, content properties

Documentation: https://developer.atlassian.com/cloud/confluence/rest/v2/intro/

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Run tests (`pytest`)
6. Commit with [Conventional Commits](https://www.conventionalcommits.org/) format
7. Push and submit a pull request

### Commit Message Format

```
feat(page): add copy page functionality
fix(search): handle empty CQL results
docs: update README with troubleshooting
test(space): add integration tests
```

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release history.
