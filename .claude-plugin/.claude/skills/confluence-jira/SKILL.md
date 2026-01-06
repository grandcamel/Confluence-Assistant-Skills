---
name: confluence-jira
description: JIRA integration - embed issues, create links between products
triggers:
  - jira
  - embed issue
  - link jira
  - jira macro
  - jira issues
---

# Confluence JIRA Skill

Cross-product JIRA integration for embedding JIRA issues in Confluence pages, creating bidirectional links, and managing JIRA macros.

## Available Scripts

### embed_jira_issues.py
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

# JSON output with profile
confluence jira embed 12345 --issues PROJ-123 --output json --profile production
```

**Options:**
- `--jql`: JQL query to filter issues (mutually exclusive with --issues)
- `--issues`: Comma-separated list of issue keys
- `--mode`: How to add the macro: `append` (default) or `replace`
- `--server-id`: JIRA server ID (optional)
- `--columns`: Columns to display (comma-separated)
- `--max-results`: Maximum number of issues (default: 20)
- `--profile`: Confluence profile to use
- `--output`: Output format (`text` or `json`)

### get_linked_issues.py
List JIRA issues linked to a page.

**Usage:**
```bash
confluence jira linked 12345
confluence jira linked 12345 --output json --profile production
```

**Options:**
- `--profile`: Confluence profile to use
- `--output`: Output format (`text` or `json`)

### create_jira_from_page.py
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

# JSON output with profile
confluence jira create-from-page 12345 --project PROJ --type Task --output json --profile production
```

**Options:**
- `--project`, `-p`: JIRA project key (required)
- `--type`, `-t`: Issue type (default: Task). Options: Task, Story, Bug, Epic, Subtask, Improvement, New Feature
- `--priority`: Priority level (e.g., High, Medium, Low)
- `--assignee`: Assignee username
- `--jira-url`: JIRA base URL (or set JIRA_URL env var)
- `--jira-email`: JIRA email (or set JIRA_EMAIL env var)
- `--jira-token`: JIRA API token (or set JIRA_API_TOKEN env var)
- `--profile`: Confluence profile to use
- `--output`: Output format (`text` or `json`)

### link_to_jira.py
Create a remote link between a Confluence page and a JIRA issue. The link appears in both systems.

**Usage:**
```bash
# Basic link (jira-url is required)
confluence jira link 12345 PROJ-123 --jira-url https://jira.example.com

# With custom relationship type
confluence jira link 12345 PROJ-123 --jira-url https://jira.example.com --relationship documents

# Skip if link already exists
confluence jira link 12345 PROJ-123 --jira-url https://jira.example.com --skip-if-exists

# JSON output with profile
confluence jira link 12345 PROJ-123 --jira-url https://jira.example.com --output json --profile production
```

**Options:**
- `--jira-url`: Base JIRA URL (required, e.g., https://jira.example.com)
- `--relationship`: Relationship type (default: "relates to"). Options: relates to, documents, mentions, references, implements
- `--skip-if-exists`: Skip if link already exists
- `--profile`: Confluence profile to use
- `--output`: Output format (`text` or `json`)

### sync_jira_macro.py
Refresh or update JIRA macros on a page. Can force a page update to trigger macro refresh or update JQL queries in existing macros.

**Usage:**
```bash
# Force page update to refresh all JIRA macros
confluence jira sync-macro 12345

# Update JQL in all JIRA macros on the page
confluence jira sync-macro 12345 --update-jql "project = PROJ AND status = Open"

# Update JQL in a specific macro by index (0-based)
confluence jira sync-macro 12345 --update-jql "status = Done" --macro-index 0

# JSON output with profile
confluence jira sync-macro 12345 --output json --profile production
```

**Options:**
- `--update-jql`: New JQL query to set in macros
- `--macro-index`: Index of macro to update (0-based). If not specified, updates all macros
- `--profile`: Confluence profile to use
- `--output`: Output format (`text` or `json`)
