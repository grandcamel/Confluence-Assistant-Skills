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

Reference documentation in `skills/shared/docs/`:

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

All skills use the [`confluence-as`](https://pypi.org/project/confluence-as/) package from PyPI.

**Installation:**
```bash
pip install confluence-as
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
from confluence_as import (
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
from confluence_as import (
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
from confluence_as import markdown_to_adf, adf_to_markdown

# Convert Markdown to ADF for API
adf = markdown_to_adf("# Heading\n\nParagraph with **bold** text.")

# Convert API response to Markdown
markdown = adf_to_markdown(page['body']['atlas_doc_format']['value'])
```

### XHTML Storage Format - v1 API

The v1 API uses XHTML storage format:

```python
from confluence_as import markdown_to_xhtml, xhtml_to_markdown

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
pytest skills/ -v

# Run tests for a specific skill
pytest skills/confluence-page/tests/ -v

# Run with coverage
pytest --cov=confluence_as --cov-report=html
```

### Live Integration Tests

```bash
# Run all live integration tests
pytest skills/*/tests/live_integration/ --live -v

# Run live tests for a specific skill
pytest skills/confluence-page/tests/live_integration/ --live -v

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
from confluence_as import (
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
skills/confluence-{name}/
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

1. Edit `skills/shared/config/config.schema.json`
2. Update `config.example.json` with examples
3. Document in this file

Note: Configuration handling is provided by the `confluence-as` package.

### Validation

The schema is JSON Schema draft-07. Validate with:
```bash
python -c "import json; print(json.load(open('skills/shared/config/config.schema.json')))"
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
pytest skills/*/tests/live_integration/ --live -v

# Specific skill
pytest skills/confluence-page/tests/live_integration/ --live -v
```

### Test Fixtures

Shared fixtures are defined in:
- **Root `conftest.py`** - `temp_path`, `temp_dir`, pytest hooks, `--live` option
- **`skills/shared/tests/conftest.py`** - `mock_client`, `sample_page`, etc.
- **`skills/shared/tests/live_integration/conftest.py`** - `confluence_client`, `test_space`, `test_page`

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
  "skills": "./skills/",
  "commands": ["./commands/..."],
  "agents": ["./agents/..."],
  "hooks": ["./hooks/..."]
}
```

**Important:** Paths in plugin.json are relative to the plugin root (the directory containing `.claude-plugin/`), not relative to plugin.json itself. Component directories (`skills/`, `commands/`, etc.) must be at the plugin root level, not inside `.claude-plugin/`.

**Common mistakes:**
- Adding custom keys like `assistant_skills` - Claude Code rejects unrecognized keys
- Wrong marketplace name in install command - must match `marketplace.json` entry name
- Putting skills/commands inside `.claude-plugin/` instead of at the plugin root

### Marketplace Installation

```bash
# Add the as-plugins marketplace
claude plugin marketplace add grandcamel/as-plugins

# Install format: <plugin-name>@<marketplace-name>
claude plugin install confluence-assistant-skills@as-plugins --scope user

# Verify installation
claude plugin list | grep confluence
```

### PyPI Package (CLI)

The CLI is published to PyPI as `confluence-assistant-skills`:

```bash
pip install confluence-assistant-skills
confluence --version
```

Trusted Publishers on PyPI are configured per-package, not per-repository.

## Test Framework Architecture

The live integration test framework uses several patterns to ensure thread-safe, efficient testing.

### Singleton Pattern with Double-Checked Locking

Docker containers and external connections use a thread-safe singleton pattern to support parallel test execution with `pytest-xdist`:

```python
# In confluence_container.py
_shared_container = None
_container_lock = threading.Lock()

def get_confluence_connection():
    global _shared_container
    if _shared_container is None:
        with _container_lock:
            if _shared_container is None:  # Double-check inside lock
                _shared_container = ConfluenceContainer()
    return _shared_container
```

### Reference Counting for Container Lifecycle

`ConfluenceContainer` uses reference counting to share a single container across multiple test sessions:

```python
class ConfluenceContainer:
    def start(self):
        with self._lock:
            self._ref_count += 1
            if self._is_started:
                return self  # Reuse existing container
            # ... start container

    def stop(self):
        with self._lock:
            self._ref_count -= 1
            if self._ref_count > 0:
                return  # Keep running for other sessions
            # ... stop container
```

### Dual-Phase Health Check

Container startup uses a two-phase approach:
1. Wait for "Ansible playbook complete" log message (Atlassian containers use Ansible)
2. Verify REST API responds at `/rest/api/user/current`

This handles variations across Confluence versions where log messages may differ.

### Connection Modes

The test framework supports two connection modes:

| Mode | Environment Variables | Description |
|------|----------------------|-------------|
| Docker Container | None (auto-starts) | Spins up Atlassian Confluence Docker image |
| External Instance | `CONFLUENCE_TEST_URL`, `CONFLUENCE_TEST_EMAIL`, `CONFLUENCE_TEST_TOKEN` | Uses existing Confluence Cloud/Server |

## Test Fixture Reference

### Unit Test Fixtures (Root conftest.py)

| Fixture | Scope | Description |
|---------|-------|-------------|
| `temp_path` | function | Temporary directory as Path object (auto-cleanup) |
| `temp_dir` | function | Temporary directory as string (legacy) |
| `claude_project_structure` | function | Standard .claude project directory structure |
| `sample_skill_md` | function | Sample SKILL.md content for testing |

### Shared Unit Test Fixtures (shared/tests/conftest.py)

| Fixture | Scope | Description |
|---------|-------|-------------|
| `mock_response` | function | Factory for creating mock HTTP responses |
| `mock_client` | function | Mock `ConfluenceClient` with setup helpers |
| `mock_config` | function | Mock configuration dictionary |
| `sample_page` | function | Sample page data from API |
| `sample_space` | function | Sample space data from API |
| `sample_comment` | function | Sample comment data from API |
| `sample_attachment` | function | Sample attachment data from API |
| `sample_label` | function | Sample label data from API |
| `sample_search_results` | function | Sample search results from API |
| `sample_adf` | function | Sample Atlassian Document Format document |
| `live_client` | session | Real ConfluenceClient for live tests |
| `live_test_space` | session | Test space for live integration tests |
| `live_test_page` | function | Test page created per test |
| `temp_file` | function | Factory for temporary test files |
| `capture_output` | function | Helper to capture stdout/stderr |

### Live Integration Fixtures (shared/tests/live_integration/conftest.py)

| Fixture | Scope | Description |
|---------|-------|-------------|
| `keep_space` | session | Check if `--keep-space` flag was provided |
| `existing_space_key` | session | Get `--space-key` option value |
| `confluence_client` | session | Configured `ConfluenceClient` instance |
| `test_space` | session | Dedicated test space (auto-created/cleaned) |
| `test_page` | function | Test page created per test |
| `test_page_with_content` | function | Test page with rich content |
| `test_child_page` | function | Child page under test_page |
| `test_blogpost` | function | Test blog post |
| `test_label` | function | Unique test label string |
| `unique_title` | function | Unique page title generator |
| `unique_space_key` | function | Unique space key generator |

### Fixture Scope Guidelines

- **session**: Shared across all tests (fastest, less isolated)
- **module**: Fresh per test file (moderate isolation)
- **function**: Fresh per test (slowest, full isolation)

Use function-scoped fixtures when tests modify data. Use session-scoped fixtures for read-only operations and shared setup.

## Test Data Generation

### PageBuilder Fluent API

```python
from test_utils import PageBuilder

# Build page creation data
page_data = (PageBuilder()
    .with_title("My Test Page")
    .with_space_id("123456")
    .with_body("# Heading\n\nParagraph content")
    .with_parent_id("789")
    .with_status("current")
    .build())

# Returns dict ready for API call
client.post('/api/v2/pages', json_data=page_data)
```

### Generate Test Content

```python
from test_utils import generate_test_content, wait_for_indexing

# Generate test pages with random content
pages = generate_test_content(
    client,
    space_id="123",
    count=10,
    content_type="page",
    with_labels=["test", "automation"],
)

# Wait for search indexing
wait_for_indexing(client, space_id="123", min_pages=10, timeout=60)
```

### Assertion Helpers

```python
from test_utils import (
    assert_page_exists,
    assert_page_not_exists,
    assert_search_returns_results,
    assert_search_returns_empty,
)

# Assert page exists
page = assert_page_exists(client, page_id="12345")

# Assert search returns results
results = assert_search_returns_results(
    client,
    cql='space = "TEST" AND label = "approved"',
    min_count=5,
)

# Assert search is empty
assert_search_returns_empty(client, cql='space = "TEST" AND label = "nonexistent"')
```

## Pytest Configuration Details

### pytest.ini Configuration

```ini
[pytest]
# Test discovery paths
testpaths = tests skills

# Directories to ignore
norecursedirs = __pycache__ .git .venv node_modules templates docker scripts references

# Test file patterns
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Import mode - avoid conflicts with multiple tests/ directories
pythonpath = .
addopts = -v --tb=short --import-mode=importlib

# Markers
markers =
    e2e: End-to-end tests requiring Claude API access
    slow: Tests that may take a long time
    live: Live integration tests requiring Confluence access
    integration: Integration tests
    destructive: Tests making destructive changes
```

### pythonpath Configuration

The shared live integration directory is included in `pythonpath`:

```ini
pythonpath = . skills/shared/tests/live_integration
```

This enables importing shared fixtures without relative imports:

```python
# In any skill's live_integration/conftest.py
pytest_plugins = ["conftest"]  # Imports from shared conftest
```

### Test Discovery

- Unit tests are discovered automatically in `testpaths`
- Live integration tests require `--live` flag
- Use `--collect-only` to preview test collection without running

### Import Mode

```ini
addopts = --import-mode=importlib
```

Uses `importlib` mode to avoid module name conflicts when multiple skills have `tests/` directories with same-named test files.

### Container Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CONFLUENCE_TEST_IMAGE` | `atlassian/confluence` | Docker image |
| `CONFLUENCE_TEST_ADMIN_USER` | `admin` | Admin username |
| `CONFLUENCE_TEST_ADMIN_PASSWORD` | `admin` | Admin password |
| `CONFLUENCE_TEST_LICENSE` | (none) | Confluence license key (required for Docker) |
| `CONFLUENCE_TEST_STARTUP_TIMEOUT` | `300` | Max startup wait (seconds) |
| `CONFLUENCE_TEST_URL` | (none) | External Confluence URL (skips Docker) |
| `CONFLUENCE_TEST_EMAIL` | (none) | Email for external Confluence |
| `CONFLUENCE_TEST_TOKEN` | (none) | API token for external Confluence |

### Test Markers

```python
import pytest

@pytest.mark.live
def test_requires_connection():
    """Requires live Confluence connection."""
    pass

@pytest.mark.destructive
def test_modifies_data():
    """Creates/modifies/deletes Confluence objects."""
    pass

@pytest.mark.slow
def test_takes_long():
    """Long-running test (>30s)."""
    pass

@pytest.mark.e2e
def test_end_to_end():
    """Requires Claude API access."""
    pass

@pytest.mark.integration
def test_integration():
    """Integration test with external services."""
    pass
```

### Running Specific Test Categories

```bash
# Run only live tests
pytest --live -v

# Run non-destructive live tests
pytest --live -m "not destructive" -v

# Run only slow tests
pytest -m slow -v

# Run everything except slow tests
pytest -m "not slow" -v

# Run with specific markers combination
pytest --live -m "live and not destructive and not slow" -v
```

## Troubleshooting

### Common Issues

#### Authentication Errors

**Error:** `AuthenticationError: 401 Unauthorized`

**Solutions:**
1. Verify API token is valid (regenerate at https://id.atlassian.com/manage-profile/security/api-tokens)
2. Check email matches your Atlassian account exactly
3. Ensure site URL is correct (`https://your-site.atlassian.net`, not `atlassian.net/wiki`)
4. Test with curl: `curl -u email:token https://your-site.atlassian.net/wiki/rest/api/user/current`

#### Permission Errors

**Error:** `PermissionError: 403 Forbidden`

**Solutions:**
1. Check space permissions: `confluence permission space get SPACE-KEY`
2. Verify page restrictions: `confluence permission page get PAGE-ID`
3. Ensure user has required capabilities (view/edit/admin)
4. Request access from space administrator

#### Rate Limiting

**Error:** `RateLimitError: 429 Too Many Requests`

**Solutions:**
1. Wait for `Retry-After` header duration (usually 60s)
2. Reduce parallel request count in bulk operations
3. Add delays between operations: `time.sleep(0.5)`
4. Use batch endpoints where available
5. Check Atlassian rate limit documentation for your tier

#### Connection Timeouts

**Error:** `TimeoutError: Request timed out after 30 seconds`

**Solutions:**
1. Increase timeout in client configuration
2. Check network connectivity to Confluence
3. Verify Confluence is responsive (check status.atlassian.com)
4. Use async mode for long operations

### Docker Container Issues

#### Container Won't Start

**Error:** `Container exited with code 1`

**Solutions:**
1. Ensure Docker has sufficient memory (4GB+ recommended)
2. Check if ports 8090/8091 are available
3. Verify license key is valid (Confluence requires license even for Docker)
4. Review container logs: `docker logs confluence-test`

#### Slow Container Startup

**Problem:** Container takes 3-5 minutes to start

**Solutions:**
1. Use a pre-warmed base image with common plugins
2. Increase startup timeout: `CONFLUENCE_TEST_STARTUP_TIMEOUT=600`
3. Consider using external Confluence instance for CI/CD

#### Container Health Check Failures

**Error:** `Health check timeout after 300 seconds`

**Solutions:**
1. Check container logs for startup errors
2. Verify license key is valid
3. Ensure sufficient disk space
4. Try increasing health check interval

### Test Failures

#### Flaky Tests

**Problem:** Tests pass/fail inconsistently

**Solutions:**
1. Add explicit waits for async operations
2. Use unique identifiers for test resources
3. Ensure proper cleanup between tests
4. Check for race conditions in parallel tests

#### Search Index Delay

**Problem:** Content not found immediately after creation

**Solutions:**
1. Use `wait_for_indexing()` helper
2. Add short delay after content creation
3. Use direct API calls instead of search for immediate verification

#### Cleanup Failures

**Problem:** Test resources not cleaned up

**Solutions:**
1. Use `@pytest.fixture` with cleanup in `yield` pattern
2. Implement session-level cleanup hooks
3. Add `--keep-space` flag for debugging
4. Review test logs for cleanup errors

### CQL Query Issues

#### Syntax Errors

**Error:** `400 Bad Request - Invalid CQL`

**Solutions:**
1. Validate query first: `confluence search validate "your query"`
2. Check field names are correct (case-sensitive)
3. Quote values with spaces: `space = "My Space"`
4. Use correct operators for field types

#### Empty Results

**Problem:** Query returns no results when content exists

**Solutions:**
1. Check space permissions
2. Verify space key case sensitivity
3. Wait for search indexing (new content)
4. Try broader query to confirm access

### Version-Specific Issues

#### v2 API Not Available

**Error:** `404 Not Found` on v2 API endpoints

**Solutions:**
1. Verify Confluence Cloud (not Server/Data Center)
2. Check API version support for your Confluence version
3. Fall back to v1 API for unsupported features

#### Feature Deprecation

**Problem:** API endpoint returns unexpected results

**Solutions:**
1. Check Atlassian deprecation notices
2. Review API changelog for changes
3. Update to latest API version
4. Use feature detection instead of version detection

### Debug Mode

Enable debug logging for troubleshooting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger('confluence_as').setLevel(logging.DEBUG)
```

Or via environment variable:

```bash
export CONFLUENCE_LOG_LEVEL=DEBUG
```

### Getting Help

1. **Check documentation**: Review SKILL.md files and this CLAUDE.md
2. **Search issues**: Check GitHub issues for similar problems
3. **Run diagnostics**: Use `confluence-ops` skill for API diagnostics
4. **Contact support**: For Confluence API issues, contact Atlassian support

## Test Coverage Summary

### Current Test Coverage

| Category | Tests | Status |
|----------|-------|--------|
| Unit Tests (shared library) | 50+ | Passing |
| Unit Tests (per skill) | 100+ | Passing |
| Live Integration Tests | 150+ | Requires `--live` flag |
| E2E Tests | 10+ | Requires `ANTHROPIC_API_KEY` |

### Coverage by Skill

| Skill | Unit | Live | Notes |
|-------|------|------|-------|
| confluence-page | 15+ | 20+ | Core CRUD operations |
| confluence-space | 10+ | 15+ | Space management |
| confluence-search | 20+ | 25+ | CQL validation, export |
| confluence-comment | 10+ | 15+ | Comments and replies |
| confluence-attachment | 12+ | 18+ | Upload, download, versions |
| confluence-label | 8+ | 12+ | Add, remove, search |
| confluence-hierarchy | 8+ | 15+ | Parent/child, ancestors |
| confluence-permission | 10+ | 12+ | Space and page permissions |
| confluence-property | 8+ | 10+ | Custom metadata |
| confluence-analytics | 5+ | 8+ | Views, watchers |
| confluence-watch | 4+ | 6+ | Watch/unwatch |
| confluence-template | 6+ | 8+ | Template management |
| confluence-jira | 5+ | 8+ | JIRA integration |
| confluence-bulk | 8+ | 10+ | Bulk operations |
| confluence-ops | 4+ | 4+ | Cache, diagnostics |
| confluence-admin | 6+ | 6+ | Administration |

### Running Coverage Report

```bash
# Run tests with coverage
pytest --cov=confluence_as --cov-report=html

# View coverage report
open htmlcov/index.html

# Run with minimum coverage threshold
pytest --cov=confluence_as --cov-fail-under=80
```