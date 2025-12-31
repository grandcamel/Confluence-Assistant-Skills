# Confluence Assistant Skills

This project provides Claude Code skills for automating Confluence Cloud operations via natural language.

## Project Overview

### Available Skills

| Skill | Purpose | Key Operations |
|-------|---------|----------------|
| `confluence-assistant` | Hub/router skill | Routes requests to specialized skills |
| `confluence-page` | Page/blog post CRUD | Create, read, update, delete pages and blog posts |
| `confluence-space` | Space management | Create, list, configure spaces |
| `confluence-search` | CQL queries | Search, export, saved queries |
| `confluence-comment` | Comments | Page and inline comments |
| `confluence-attachment` | File attachments | Upload, download, manage files |
| `confluence-label` | Content labeling | Add, remove, search by labels |
| `confluence-template` | Templates | Create pages from templates |
| `confluence-property` | Content properties | Custom metadata management |
| `confluence-permission` | Access control | Space and page permissions |
| `confluence-analytics` | Content analytics | Views, popularity, watchers |
| `confluence-watch` | Notifications | Watch/unwatch content |
| `confluence-hierarchy` | Content tree | Ancestors, descendants, navigation |
| `confluence-jira` | JIRA integration | Embed issues, cross-product links |

## Architecture

### Shared Library (PyPI Package)

All skills use the [`confluence-assistant-skills-lib`](https://pypi.org/project/confluence-assistant-skills-lib/) package from PyPI.

**Installation:**
```bash
pip install confluence-assistant-skills-lib
```

**Key Components:**
- `ConfluenceClient` - HTTP client with retry logic
- `ConfigManager` - Multi-source configuration
- `handle_errors` - Exception handling decorator
- `validators` - Input validation utilities
- `formatters` - Output formatting
- `adf_helper` - Atlassian Document Format utilities
- `xhtml_helper` - Legacy storage format utilities
- `Cache` - Response caching

### Import Pattern

Every script should import shared utilities like this:

```python
#!/usr/bin/env python3
import argparse
from confluence_assistant_skills_lib import (
    get_confluence_client,
    handle_errors,
    validate_page_id,
    validate_space_key,
    print_success,
    format_page,
)
```

## Configuration System

### Configuration Priority (highest to lowest)

1. **Environment variables** - Override everything
2. **settings.local.json** - Personal settings (gitignored)
3. **settings.json** - Team defaults (committed)
4. **Built-in defaults** - Fallback values

### Environment Variables

```bash
export CONFLUENCE_SITE_URL="https://your-site.atlassian.net"
export CONFLUENCE_EMAIL="your-email@example.com"
export CONFLUENCE_API_TOKEN="your-api-token"
export CONFLUENCE_PROFILE="production"  # Optional, defaults to "default"
```

### Profile Configuration

Profiles allow switching between different Confluence instances:

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

Use profiles:
```bash
python get_page.py 12345 --profile sandbox
```

## Error Handling Strategy

### 4-Layer Approach

1. **Validation Layer** - Catch invalid inputs early
2. **API Layer** - HTTP error handling with retries
3. **Script Layer** - @handle_errors decorator
4. **Output Layer** - User-friendly error messages

### Exception Hierarchy

```
ConfluenceError (base)
├── AuthenticationError (401)
├── PermissionError (403)
├── ValidationError (400)
├── NotFoundError (404)
├── RateLimitError (429)
├── ConflictError (409)
└── ServerError (5xx)
```

### Using the Error Handler

```python
from confluence_assistant_skills_lib import (
    handle_errors, ValidationError, get_confluence_client, print_success,
)

@handle_errors
def main():
    # Validation
    if not page_id:
        raise ValidationError("Page ID is required")

    # API call - errors auto-handled
    client = get_confluence_client()
    page = client.get(f"/api/v2/pages/{page_id}")

    print_success(f"Retrieved page: {page['title']}")

if __name__ == '__main__':
    main()
```

## Content Formats

### ADF (Atlassian Document Format) - v2 API

The v2 API uses JSON-based ADF for content:

```python
from confluence_assistant_skills_lib import markdown_to_adf, adf_to_markdown

# Convert Markdown to ADF for API
adf = markdown_to_adf("# Heading\n\nParagraph with **bold** text.")

# Convert API response to Markdown
markdown = adf_to_markdown(page['body']['atlas_doc_format']['value'])
```

### XHTML Storage Format - v1 API

The v1 API uses XHTML storage format:

```python
from confluence_assistant_skills_lib import markdown_to_xhtml, xhtml_to_markdown

# Convert Markdown to XHTML for v1 API
xhtml = markdown_to_xhtml("# Heading\n\nParagraph")

# Convert v1 response to Markdown
markdown = xhtml_to_markdown(page['body']['storage']['value'])
```

## Testing Scripts

### Unit Tests

```bash
# Run all unit tests
pytest .claude/skills/confluence-*/tests/test_*.py -v

# Run tests for a specific skill
pytest .claude/skills/confluence-page/tests/test_*.py -v

# Run with coverage
pytest --cov=confluence_assistant_skills_lib --cov-report=html
```

### Live Integration Tests

```bash
# Run live tests with a profile
pytest .claude/skills/confluence-page/tests/live_integration/ \
    --profile=sandbox \
    -v

# Skip destructive tests
pytest --ignore-glob="**/test_delete*"
```

## Adding New Scripts

### Step-by-Step Guide

1. **Create the script file** in the appropriate skill's `scripts/` directory

2. **Use the standard template**:

```python
#!/usr/bin/env python3
"""
Brief description of what this script does.

Examples:
    python script_name.py SPACE-KEY --option value
"""

import argparse
from confluence_assistant_skills_lib import (
    get_confluence_client,
    handle_errors,
    validate_space_key,
    print_success,
    format_json,
)


@handle_errors
def main():
    parser = argparse.ArgumentParser(
        description='Script description',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('space_key', help='Space key')
    parser.add_argument('--profile', '-p', help='Confluence profile')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text')
    args = parser.parse_args()

    # Validate
    space_key = validate_space_key(args.space_key)

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Perform operation
    result = client.get(f'/api/v2/spaces/{space_key}')

    # Output
    if args.output == 'json':
        print(format_json(result))
    else:
        print(f"Space: {result['name']}")

    print_success("Operation completed")


if __name__ == '__main__':
    main()
```

3. **Add tests** in the skill's `tests/` directory

4. **Update the skill's SKILL.md** with new triggers and examples

## Adding New Skills

### Required Structure

```
.claude/skills/confluence-{name}/
├── SKILL.md           # Skill definition and triggers
├── scripts/           # Python scripts
│   ├── __init__.py
│   └── operation.py
├── tests/             # Unit tests
│   ├── conftest.py
│   ├── test_operation.py
│   └── live_integration/
│       └── test_operation_live.py
└── references/        # API docs, examples
```

### SKILL.md Template

```markdown
---
name: confluence-{name}
description: Brief description
triggers:
  - keyword1
  - keyword2
  - phrase trigger
---

# Confluence {Name} Skill

## Overview
What this skill does.

## Available Scripts

### operation.py
Description of operation.

**Usage:**
\`\`\`bash
python operation.py ARG --option VALUE
\`\`\`

## Examples
Natural language examples that trigger this skill.
```

## Configuration Changes

### Modifying the Schema

1. Edit `.claude/skills/shared/config/config.schema.json`
2. Update `config.example.json` with examples
3. Document in this file

Note: Configuration handling is provided by the `confluence-assistant-skills-lib` package.

### Validation

The schema is JSON Schema draft-07. Validate with:
```bash
python -c "import json; print(json.load(open('.claude/skills/shared/config/config.schema.json')))"
```

## Credentials Security

### NEVER COMMIT

- `.claude/settings.local.json`
- Any file containing API tokens
- Environment variable files (`.env`)

### Recommended Setup

1. Use environment variables for CI/CD
2. Use `settings.local.json` for local development
3. Keep `settings.json` for non-sensitive defaults only

### Getting API Token

1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Give it a descriptive name
4. Copy the token immediately (shown only once)
5. Store in environment variable or `settings.local.json`

## Common Patterns

### Pagination

```python
# Automatic pagination with generator
for page in client.paginate('/api/v2/pages', params={'space-id': space_id}):
    print(page['title'])

# With limit
for page in client.paginate('/api/v2/pages', limit=100):
    process(page)
```

### Bulk Operations

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def update_page(page_id, data):
    return client.put(f'/api/v2/pages/{page_id}', json_data=data)

# Process in parallel
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = {executor.submit(update_page, p['id'], data): p for p in pages}
    for future in as_completed(futures):
        page = futures[future]
        try:
            result = future.result()
            print_success(f"Updated {page['title']}")
        except Exception as e:
            print_error(f"Failed to update {page['title']}", e)
```

## CQL Query Patterns

### Basic Queries

```cql
# Find pages in a space
space = "DOCS" AND type = page

# Find by label
label = "documentation"

# Text search
text ~ "API documentation"

# Recent content
created >= "2025-01-01" AND creator = currentUser()
```

### Advanced Queries

```cql
# Multiple spaces
space in ("DOCS", "KB", "DEV") AND type = page

# Exclude labels
label = "approved" AND label != "draft"

# Date ranges
lastModified >= "2025-01-01" AND lastModified < "2025-02-01"

# Ancestor (child pages)
ancestor = 12345

# Combined with ordering
space = "DOCS" AND label = "api" ORDER BY lastModified DESC
```

## Git Commit Guidelines

Follow Conventional Commits:

```
feat(page): add copy page functionality
fix(search): handle empty CQL results
docs: update README with new examples
test(space): add integration tests
refactor(client): simplify retry logic
chore: update dependencies
```

## Live Integration Testing

### Setup

1. Create a test space in your Confluence instance
2. Configure a test profile:

```json
{
  "confluence": {
    "profiles": {
      "test": {
        "url": "https://your-site.atlassian.net",
        "default_space": "TEST"
      }
    }
  }
}
```

3. Set credentials:
```bash
export CONFLUENCE_EMAIL="your-email@example.com"
export CONFLUENCE_API_TOKEN="your-token"
```

### Running Tests

```bash
# All live tests
pytest .claude/skills/*/tests/live_integration/ --profile=test -v

# Specific skill
pytest .claude/skills/confluence-page/tests/live_integration/ --profile=test -v

# With verbose output
pytest -v -s --profile=test
```

### Test Fixtures

Tests use session-scoped fixtures for setup/teardown:

```python
@pytest.fixture(scope="session")
def test_space(confluence_client):
    """Create test space for the session."""
    space = confluence_client.post('/api/v2/spaces', json_data={
        'key': 'CASTEST',
        'name': 'CAS Integration Tests'
    })
    yield space
    # Cleanup after all tests
    confluence_client.delete(f"/api/v2/spaces/{space['id']}")
```

## API Reference

### v2 API (Primary)

- Pages: `GET/POST/PUT/DELETE /api/v2/pages/{id}`
- Spaces: `GET/POST/PUT/DELETE /api/v2/spaces/{id}`
- Blog Posts: `GET/POST/PUT/DELETE /api/v2/blogposts/{id}`
- Comments: `GET/POST/PUT/DELETE /api/v2/pages/{id}/footer-comments`
- Attachments: `GET/POST/DELETE /api/v2/attachments/{id}`
- Labels: `GET/POST/DELETE /api/v2/pages/{id}/labels`

### v1 API (Legacy)

- Content: `/rest/api/content/{id}`
- Space: `/rest/api/space/{key}`
- Search: `/rest/api/search?cql={query}`
- Properties: `/rest/api/content/{id}/property/{key}`

Documentation: https://developer.atlassian.com/cloud/confluence/rest/v2/intro/


## E2E Testing

### Run E2E Tests

```bash
# Requires ANTHROPIC_API_KEY
./scripts/run-e2e-tests.sh           # Docker
./scripts/run-e2e-tests.sh --local   # Local
./scripts/run-e2e-tests.sh --verbose # Verbose
```
