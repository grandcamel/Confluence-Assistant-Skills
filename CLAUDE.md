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
| `confluence-bulk` | Bulk operations | Bulk label, move, delete with dry-run |
| `confluence-ops` | Operations/cache | Cache management, API diagnostics |
| `confluence-admin` | Administration | Users, groups, templates, space settings |

### Shared Documentation

Reference documentation in `.claude-plugin/.claude/skills/shared/docs/`:

| Document | Purpose |
|----------|---------|
| `SAFEGUARDS.md` | Risk levels, recovery procedures, pre-operation checklists |
| `ERROR_HANDLING.md` | Retry logic, error classification, named patterns |
| `DECISION_TREE.md` | Skill routing flowchart, disambiguation rules |
| `QUICK_REFERENCE.md` | One-page skill reference, CQL examples |

### Risk Levels

Operations are marked with risk indicators throughout skill documentation:

| Risk | Meaning | Examples |
|------|---------|----------|
| - | Safe, read-only or easily reversible | Get page, list spaces, search |
| ⚠️ | Modifies content, can be undone | Update page, add label, create comment |
| ⚠️⚠️ | Destructive, difficult to recover | Delete page, remove permissions |
| ⚠️⚠️⚠️ | **IRREVERSIBLE**, permanent deletion | Delete space, purge content |

**Always use dry-run or preview when available for ⚠️⚠️+ operations.**

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

## CLI Interface

### Installation

The project provides a unified `confluence` CLI for all operations:

```bash
# Install in development mode
pip install -e .

# Verify installation
confluence --version
```

### Usage

```bash
# Get help
confluence --help
confluence page --help
confluence page get --help

# Page operations
confluence page get 12345
confluence page get 12345 --body --format markdown
confluence page create DOCS "My Page" --body "Content here"
confluence page update 12345 --title "New Title"
confluence page delete 12345 --confirm

# Space operations
confluence space list
confluence space list --output json
confluence space get DOCS

# Search operations
confluence search cql "space = DOCS AND type = page"
confluence search cql "label = 'approved'" --limit 50 --show-labels
confluence search export "space = DOCS" --format csv --output-file results.csv

# Other commands
confluence comment add 12345 "Great page!"
confluence label add 12345 api-docs approved
confluence attachment list 12345
confluence hierarchy tree 12345 --depth 3
```

### Global Options

All commands support these global options:

| Option | Description |
|--------|-------------|
| `--output, -o` | Output format: `text` or `json` |
| `--verbose, -v` | Enable verbose output |
| `--quiet, -q` | Suppress non-essential output |
| `--help` | Show command help |

### Shell Completion

Enable tab completion for bash:
```bash
eval "$(_CONFLUENCE_COMPLETE=bash_source confluence)"
```

For zsh:
```bash
eval "$(_CONFLUENCE_COMPLETE=zsh_source confluence)"
```

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

### Environment Variables

All configuration is done through environment variables:

```bash
export CONFLUENCE_SITE_URL="https://your-site.atlassian.net"
export CONFLUENCE_EMAIL="your-email@example.com"
export CONFLUENCE_API_TOKEN="your-api-token"
```

| Variable | Required | Description |
|----------|----------|-------------|
| `CONFLUENCE_SITE_URL` | Yes | Confluence Cloud site URL (e.g., `https://your-site.atlassian.net`) |
| `CONFLUENCE_EMAIL` | Yes | Atlassian account email for API authentication |
| `CONFLUENCE_API_TOKEN` | Yes | API token from [Atlassian Account Settings](https://id.atlassian.com/manage-profile/security/api-tokens) |

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

### Test Configuration

Tests are configured via centralized files at the project root:
- `pytest.ini` - Test paths, markers, import mode (`--import-mode=importlib`)
- `conftest.py` - Shared fixtures (`temp_path`, `temp_dir`) and pytest hooks

The `--live` option is defined in the root `conftest.py` and available to all tests.

### Unit Tests

```bash
# Run all tests (unit + e2e)
pytest -v

# Run only skill tests
pytest .claude-plugin/.claude/skills/ -v

# Run tests for a specific skill
pytest .claude-plugin/.claude/skills/confluence-page/tests/ -v

# Run with coverage
pytest --cov=confluence_assistant_skills_lib --cov-report=html
```

### Live Integration Tests

```bash
# Run all live integration tests
pytest .claude-plugin/.claude/skills/*/tests/live_integration/ --live -v

# Run live tests for a specific skill
pytest .claude-plugin/.claude/skills/confluence-page/tests/live_integration/ --live -v

# Use existing space instead of creating temporary one
pytest --live --space-key=EXISTING -v

# Keep test space after tests (for debugging)
pytest --live --keep-space -v

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
    confluence space get SPACE-KEY --option value
"""
from __future__ import annotations

import argparse
from confluence_assistant_skills_lib import (
    get_confluence_client,
    handle_errors,
    validate_space_key,
    print_success,
    format_json,
)


@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description='Script description',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('space_key', help='Space key')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text')
    args = parser.parse_args(argv)

    # Validate
    space_key = validate_space_key(args.space_key)

    # Get client
    client = get_confluence_client()

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

**Note:** The `argv` parameter enables direct function calls from the CLI framework and simplifies testing.

3. **Add tests** in the skill's `tests/` directory

4. **Update the skill's SKILL.md** with new triggers and examples

## Adding New Skills

### Required Structure

```
.claude-plugin/.claude/skills/confluence-{name}/
├── SKILL.md           # Skill definition and triggers
├── scripts/           # Python scripts
│   ├── __init__.py
│   └── operation.py
├── tests/             # Unit tests
│   ├── conftest.py    # Skill-specific fixtures only
│   ├── test_operation.py
│   └── live_integration/
│       └── test_operation_live.py
└── references/        # API docs, examples
```

**Note:** Do not add `__init__.py` to test directories. Pytest hooks (`pytest_addoption`, `pytest_configure`) are defined in the root `conftest.py`. Skill-specific `conftest.py` files should only contain fixtures unique to that skill.

### SKILL.md Template

```markdown
---
name: confluence-{name}
description: Brief description. ALWAYS use when user wants to [primary use case].
triggers:
  - keyword1
  - keyword2
  - phrase trigger
---

# Confluence {Name} Skill

Brief description of skill purpose.

---

## ⚠️ PRIMARY USE CASE

**This skill [does what].** Use for:
- Primary operation 1
- Primary operation 2
- Primary operation 3

---

## When to Use / When NOT to Use

| Use This Skill | Use Instead |
|----------------|-------------|
| Operation A | - |
| Operation B | - |
| Operation C | `other-skill` |

---

## Risk Levels

| Operation | Risk | Notes |
|-----------|------|-------|
| Get/list operations | - | Read-only |
| Create/update | ⚠️ | Can be undone |
| Delete operations | ⚠️⚠️ | Destructive |

---

## Overview
Detailed description of what this skill does.

## Available Scripts

### operation.py
Description of operation.

**Usage:**
\`\`\`bash
confluence {group} {command} ARG --option VALUE
\`\`\`

**Options:**
- `--option` - Description

## Examples
Natural language examples that trigger this skill.
```

## Configuration Changes

### Modifying the Schema

1. Edit `.claude-plugin/.claude/skills/shared/config/config.schema.json`
2. Update `config.example.json` with examples
3. Document in this file

Note: Configuration handling is provided by the `confluence-assistant-skills-lib` package.

### Validation

The schema is JSON Schema draft-07. Validate with:
```bash
python -c "import json; print(json.load(open('.claude-plugin/.claude/skills/shared/config/config.schema.json')))"
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

## Available Scripts

Scripts in `scripts/` for development and testing:

| Script | Purpose |
|--------|---------|
| `run_tests.sh` | Main unit test runner (runs each skill separately) |
| `run_single_test.sh` | Run individual test file, class, or method |
| `run_live_tests.sh` | Live integration tests with real Confluence credentials |
| `run-e2e-tests.sh` | End-to-end tests with Claude Code (Docker or local) |
| `setup-env.sh` | Environment configuration |
| `sync-version.sh` | Synchronize version across all project files |

### Testing Commands

```bash
# Run all unit tests (recommended before merge)
./scripts/run_tests.sh

# Run specific skill
./scripts/run_tests.sh --skill confluence-page

# Run single test
./scripts/run_single_test.sh confluence-page test_create_page.py

# Run with coverage
./scripts/run_tests.sh --coverage --min-coverage 90

# Run live integration tests (requires Confluence credentials)
./scripts/run_live_tests.sh

# Run live tests for specific skill
./scripts/run_live_tests.sh --skill confluence-page

# Run E2E tests
./scripts/run-e2e-tests.sh --local
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
2. Set environment variables:
```bash
export CONFLUENCE_SITE_URL="https://your-site.atlassian.net"
export CONFLUENCE_EMAIL="your-email@example.com"
export CONFLUENCE_API_TOKEN="your-token"
```

### Running Tests

Use the `run_live_tests.sh` script for convenient execution:

```bash
# All live tests
./scripts/run_live_tests.sh

# Specific skill
./scripts/run_live_tests.sh --skill confluence-page

# Use existing space (faster, no cleanup)
./scripts/run_live_tests.sh --space-key=MYTEST

# Keep space after tests (for debugging)
./scripts/run_live_tests.sh --keep-space

# With verbose output
./scripts/run_live_tests.sh --verbose
```

Or run pytest directly:

```bash
# All live tests
pytest .claude-plugin/.claude/skills/*/tests/live_integration/ --live -v

# Specific skill
pytest .claude-plugin/.claude/skills/confluence-page/tests/live_integration/ --live -v
```

### Test Fixtures

Shared fixtures are defined in:
- **Root `conftest.py`** - `temp_path`, `temp_dir`, pytest hooks, `--live` option
- **`.claude-plugin/.claude/skills/shared/tests/conftest.py`** - `mock_client`, `sample_page`, etc.
- **`.claude-plugin/.claude/skills/shared/tests/live_integration/conftest.py`** - `confluence_client`, `test_space`, `test_page`

Example session-scoped fixture for setup/teardown:

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
- Always Test Driven Development / TDD in planning and execution of new features


## Plugin Publishing

### plugin.json Schema

Claude Code strictly validates plugin.json. **Only recognized keys are allowed:**

```json
{
  "name": "confluence-assistant-skills",
  "version": "1.1.0",
  "description": "...",
  "author": { "name": "...", "url": "..." },
  "repository": "...",
  "license": "MIT",
  "keywords": ["..."],
  "skills": "./.claude/skills/",
  "commands": ["./commands/..."],
  "agents": ["./agents/..."],
  "hooks": ["./hooks/..."]
}
```

**Common mistakes:**
- Adding custom keys like `assistant_skills` - Claude Code rejects unrecognized keys
- Wrong marketplace name in install command - must match `marketplace.json` entry name
- Missing `.claude-plugin/` in cache path when verifying installation

### Marketplace Installation

```bash
# Add from marketplace (uses marketplace.json name, not plugin name)
claude plugin marketplace add https://github.com/grandcamel/confluence-assistant-skills.git#main

# Install format: <plugin-name>@<marketplace-name>
claude plugin install confluence-assistant-skills@confluence-assistant-skills-marketplace --scope user

# Verify - note .claude-plugin/ in path
cat ~/.claude/plugins/cache/*/confluence-assistant-skills/*/.claude-plugin/plugin.json
```

### PyPI Package (CLI)

The CLI is published to PyPI as `confluence-assistant-skills`:

```bash
pip install confluence-assistant-skills
confluence --version
```

Trusted Publishers on PyPI are configured per-package, not per-repository.