# Confluence-JIRA Skill

Cross-product integration between Confluence and JIRA, enabling seamless linking and embedding of issues in documentation.

## Features

- Embed JIRA issues in Confluence pages using macros
- Extract and list JIRA issues referenced in pages
- Create bidirectional links between Confluence and JIRA
- Create JIRA issues from Confluence page content
- Sync and refresh JIRA macro content

## Scripts

### 1. embed_jira_issues.py

Embed JIRA issues in a Confluence page using JIRA macros.

**Usage:**
```bash
# Embed issues via JQL query
python embed_jira_issues.py 12345 --jql "project = PROJ AND status = Open"

# Embed specific issues
python embed_jira_issues.py 12345 --issues PROJ-123,PROJ-456

# Replace page content with macro
python embed_jira_issues.py 12345 --jql "project = PROJ" --mode replace

# With custom columns
python embed_jira_issues.py 12345 --jql "status = Open" --columns key,summary,status,assignee
```

**Options:**
- `--jql`: JQL query to filter issues
- `--issues`: Comma-separated list of issue keys
- `--mode`: `append` (default) or `replace`
- `--server-id`: JIRA server ID (optional)
- `--columns`: Columns to display in macro
- `--max-results`: Maximum issues to display (default: 20)

### 2. get_linked_issues.py

Extract and list JIRA issues linked to a Confluence page.

**Usage:**
```bash
# Get all JIRA issues mentioned in a page
python get_linked_issues.py 12345

# JSON output
python get_linked_issues.py 12345 --output json
```

**What it extracts:**
- JIRA issue keys from macros
- Issue keys mentioned in text (PROJ-123 format)
- JQL queries from JIRA issues macros

### 3. link_to_jira.py

Create a remote link between a Confluence page and JIRA issue.

**Usage:**
```bash
# Create link
python link_to_jira.py 12345 PROJ-123 --jira-url https://jira.example.com

# With relationship type
python link_to_jira.py 12345 PROJ-123 --jira-url https://jira.example.com --relationship "documents"

# Skip if already exists
python link_to_jira.py 12345 PROJ-123 --jira-url https://jira.example.com --skip-if-exists
```

**Relationship types:**
- `relates to` (default)
- `documents`
- `mentions`
- `references`
- `implements`

### 4. create_jira_from_page.py

Create a JIRA issue from Confluence page content.

**Usage:**
```bash
# Create a task from page
python create_jira_from_page.py 12345 --project PROJ --type Task

# Create a bug with priority
python create_jira_from_page.py 12345 --project PROJ --type Bug --priority High

# Assign to user
python create_jira_from_page.py 12345 --project PROJ --type Story --assignee username
```

**Required environment variables:**
```bash
export JIRA_URL="https://jira.example.com"
export JIRA_EMAIL="your-email@example.com"
export JIRA_API_TOKEN="your-jira-token"
```

### 5. sync_jira_macro.py

Refresh or update JIRA macro content in a Confluence page.

**Usage:**
```bash
# Trigger page update to refresh macros
python sync_jira_macro.py 12345

# Update JQL in all macros
python sync_jira_macro.py 12345 --update-jql "project = PROJ AND status = Open"

# Update specific macro
python sync_jira_macro.py 12345 --update-jql "status = Done" --macro-index 0
```

## Architecture

### JIRA Macros

This skill uses Confluence's native JIRA macros in XHTML storage format:

**Single Issue Macro:**
```xml
<ac:structured-macro ac:name="jira" ac:schema-version="1">
    <ac:parameter ac:name="key">PROJ-123</ac:parameter>
</ac:structured-macro>
```

**Multiple Issues (JQL) Macro:**
```xml
<ac:structured-macro ac:name="jira" ac:schema-version="1">
    <ac:parameter ac:name="jqlQuery">project = PROJ AND status = Open</ac:parameter>
    <ac:parameter ac:name="maximumIssues">20</ac:parameter>
</ac:structured-macro>
```

### Remote Links

Remote links create bidirectional relationships that appear in both Confluence and JIRA:
- Uses Confluence REST API `/rest/api/content/{pageId}/remotelink`
- Creates application links visible in both systems
- Supports custom relationship types

## Testing

### Unit Tests

```bash
# Run all tests
pytest .claude/skills/confluence-jira/tests/ -v

# Run specific test file
pytest .claude/skills/confluence-jira/tests/test_embed_jira_issues.py -v
```

### Test Coverage

- Macro creation and validation
- JQL query building and validation
- Issue key extraction and regex patterns
- Remote link API interactions
- Content update modes (append/replace)

## Common Use Cases

### 1. Track Related Issues in Documentation

```bash
# Embed all open issues for a project
python embed_jira_issues.py 12345 --jql "project = PROJ AND status != Done"
```

### 2. Document-Issue Relationships

```bash
# Create bidirectional link
python link_to_jira.py 12345 PROJ-123 --jira-url https://jira.example.com --relationship "documents"
```

### 3. Issue Audit

```bash
# Find all JIRA references in a page
python get_linked_issues.py 12345 --output json
```

### 4. Issue from Requirements

```bash
# Create task from requirements page
python create_jira_from_page.py 12345 --project PROJ --type Task --priority Medium
```

### 5. Update Issue Filters

```bash
# Update JQL to show completed items
python sync_jira_macro.py 12345 --update-jql "project = PROJ AND status = Done"
```

## Error Handling

All scripts use the shared error handling framework:

- **ValidationError**: Invalid inputs (issue keys, JQL, etc.)
- **AuthenticationError**: Invalid credentials
- **PermissionError**: Insufficient permissions
- **NotFoundError**: Page or issue not found
- **RateLimitError**: API rate limit exceeded

Errors are reported with clear messages and suggestions.

## Best Practices

1. **Use JQL for Dynamic Content**: Prefer JQL queries over static issue lists for automatic updates
2. **Set Reasonable Limits**: Use `--max-results` to prevent macro performance issues
3. **Check Existing Links**: Use `--skip-if-exists` to avoid duplicate remote links
4. **Validate JQL First**: Test JQL queries in JIRA before embedding
5. **Macro Refresh**: Confluence auto-refreshes macros, but use sync script if needed

## Integration with Other Skills

- **confluence-page**: Use page CRUD operations before/after embedding issues
- **confluence-search**: Find pages with specific JIRA references
- **confluence-analytics**: Track engagement with issue-linked pages

## API Compatibility

- Uses Confluence v1 API for XHTML storage format (required for macros)
- Compatible with JIRA REST API v2 (for issue creation)
- Remote links API is v1 only

## Limitations

- JIRA macro rendering requires Confluence-JIRA application link to be configured
- Issue creation requires separate JIRA API credentials
- Some JIRA fields may require project-specific configuration
- Remote links appear differently in Confluence Cloud vs Server

## Future Enhancements

Potential additions:
- Bulk issue creation from page hierarchy
- Issue import/sync capabilities
- Advanced macro parameter customization
- JIRA webhook integration for automatic updates
