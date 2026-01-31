---
name: confluence-jira
description: JIRA integration - embed issues, create links between products. ALWAYS use when user wants to connect Confluence and JIRA.
triggers:
  - jira
  - embed issue
  - link jira
  - jira macro
  - jira issues
  - jira link
---

# Confluence JIRA Skill

Cross-product JIRA integration for Confluence.

---

## ⚠️ PRIMARY USE CASE

**This skill connects Confluence and JIRA.** Use for:
- Embedding JIRA issues in pages
- Creating JIRA macros
- Linking pages to issues
- Displaying issue lists via JQL

---

## When to Use / When NOT to Use

| Use This Skill | Use Instead |
|----------------|-------------|
| Embed JIRA issues | - |
| Add JIRA macro | - |
| Link to JIRA | - |
| Create JIRA issues | Use JIRA directly |
| Edit page content | `confluence-page` |

---

## Risk Levels

| Operation | Risk | Notes |
|-----------|------|-------|
| Embed issues | ⚠️ | Modifies page content |
| Add JIRA macro | ⚠️ | Modifies page content |
| Link to JIRA | - | Creates link only |

---

## Overview

Cross-product JIRA integration for embedding JIRA issues in Confluence pages, creating bidirectional links, and managing JIRA macros.

## CLI Commands

### confluence jira embed
Embed JIRA issues in a page using JQL query or specific issue keys.

**Usage:**
```bash
# Embed issues matching a JQL query
confluence jira embed 12345 --jql "project = PROJ AND status = Open"

# Embed specific issues by key
confluence jira embed 12345 --issues PROJ-123,PROJ-456

# Replace page content with JIRA macro (instead of append)
confluence jira embed 12345 --jql "project = PROJ" --mode replace

# Customize columns and limit results
confluence jira embed 12345 --jql "assignee = currentUser()" --columns key,summary,status --max-results 50

# With specific JIRA server
confluence jira embed 12345 --jql "project = PROJ" --server-id abc123

# JSON output
confluence jira embed 12345 --issues PROJ-123 --output json
```

**Options:**
- `--jql`: JQL query to filter issues (mutually exclusive with --issues)
- `--issues`: Comma-separated list of issue keys
- `--mode`: How to add the macro: `append` (default) or `replace`
- `--server-id`: JIRA server ID (optional)
- `--columns`: Columns to display (comma-separated)
- `--max-results`: Maximum number of issues (default: 20)
- `--output`: Output format (`text` or `json`)

### confluence jira linked
List JIRA issues linked to a page.

**Usage:**
```bash
confluence jira linked 12345
confluence jira linked 12345 --output json
```

**Options:**
- `--output`: Output format (`text` or `json`)

### confluence jira create-from-page
Create a JIRA issue from Confluence page content. Uses page title as summary and extracted text as description.

**Usage:**
```bash
# Basic usage (requires JIRA env vars: JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN)
confluence jira create-from-page 12345 --project PROJ --type Task

# With priority and assignee
confluence jira create-from-page 12345 --project PROJ --type Bug --priority High --assignee jsmith

# With explicit JIRA credentials
confluence jira create-from-page 12345 --project PROJ --type Story \
  --jira-url https://jira.example.com \
  --jira-email user@example.com \
  --jira-token your-api-token

# JSON output
confluence jira create-from-page 12345 --project PROJ --type Task --output json
```

**Options:**
- `--project`, `-p`: JIRA project key (required)
- `--type`, `-t`: Issue type (default: Task). Common values include: Task, Story, Bug, Epic, Subtask, Improvement, New Feature. Any valid issue type for your JIRA project is accepted.
- `--priority`: Priority level (e.g., High, Medium, Low)
- `--assignee`: Assignee username
- `--jira-url`: JIRA base URL (or set JIRA_URL env var)
- `--jira-email`: JIRA email (or set JIRA_EMAIL env var)
- `--jira-token`: JIRA API token (or set JIRA_API_TOKEN env var)
- `--output`: Output format (`text` or `json`)

### confluence jira link
Create a remote link between a Confluence page and a JIRA issue. The link appears in both systems.

**Implementation Note:** Links are tracked using HTML comment markers in the page content (e.g., `<!-- JIRA-LINK: PROJ-123 -->`). The `--skip-if-exists` option checks for these markers to avoid duplicate links.

**Usage:**
```bash
# Basic link (jira-url is required)
confluence jira link 12345 PROJ-123 --jira-url https://jira.example.com

# With custom relationship type
confluence jira link 12345 PROJ-123 --jira-url https://jira.example.com --relationship documents

# Skip if link already exists
confluence jira link 12345 PROJ-123 --jira-url https://jira.example.com --skip-if-exists

# JSON output
confluence jira link 12345 PROJ-123 --jira-url https://jira.example.com --output json
```

**Options:**
- `--jira-url`: Base JIRA URL (required, e.g., https://jira.example.com)
- `--relationship`: Relationship type (default: "relates to"). Common values include: relates to, documents, mentions, references, implements. Any string value is accepted. Note: This is descriptive metadata stored in the link; it does not affect how Confluence or JIRA process the link itself.
- `--skip-if-exists`: Skip if link already exists
- `--output`: Output format (`text` or `json`)

### confluence jira sync-macro
Refresh or update JIRA macros on a page. Can force a page update to trigger macro refresh or update JQL queries in existing macros.

**Usage:**
```bash
# Force page update to refresh all JIRA macros
confluence jira sync-macro 12345

# Update JQL in all JIRA macros on the page
confluence jira sync-macro 12345 --update-jql "project = PROJ AND status = Open"

# Update JQL in a specific macro by index (0-based)
confluence jira sync-macro 12345 --update-jql "status = Done" --macro-index 0

# JSON output
confluence jira sync-macro 12345 --output json
```

**Options:**
- `--update-jql`: New JQL query to set in macros
- `--macro-index`: Index of macro to update (0-based). If not specified, updates all macros
- `--output`: Output format (`text` or `json`)
