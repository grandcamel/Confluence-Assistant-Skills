---
name: confluence-analytics
description: View analytics, statistics, and popularity metrics for Confluence content
triggers:
  - analytics
  - statistics
  - views
  - popular
  - watchers
  - contributors
  - page views
  - space analytics
  - most viewed
  - most popular
  - who is watching
  - content analytics
---

# Confluence Analytics Skill

## Overview

This skill provides analytics and statistics for Confluence content, including page view information, contributor data, space-level analytics, popular content identification, and watcher lists.

**Note:** Confluence Cloud has limited analytics APIs compared to Server/Data Center. This skill uses the v1 REST API's history endpoints and CQL queries to provide analytics insights.

## Available Scripts

### get_page_views.py

Get analytics and view information for a specific page.

Retrieves:
- Version history
- Last modified date and author
- Creation date and author
- List of contributors who have edited the page

**Usage:**
```bash
python get_page_views.py PAGE_ID [--output json] [--profile PROFILE]
```

**Arguments:**
- `PAGE_ID` - The page ID (required)
- `--output` - Output format: text or json (default: text)
- `--profile` - Confluence profile to use

**Examples:**
```bash
# Get page analytics
python get_page_views.py 12345

# Get as JSON
python get_page_views.py 12345 --output json

# Use specific profile
python get_page_views.py 12345 --profile production
```

**Output (text):**
```
Page: API Documentation
ID: 12345
Type: page
Space: DOCS

Version: 15
Last Modified: 2024-01-15T10:30:00.000Z
Modified By: John Doe

Created: 2024-01-01T10:00:00.000Z
Created By: Jane Smith

Contributors (5):
  - Jane Smith
  - John Doe
  - Alice Johnson
  - Bob Wilson
  - Carol Davis

Web UI: https://your-site.atlassian.net/wiki/spaces/DOCS/pages/12345
```

---

### get_space_analytics.py

Get aggregate analytics for an entire space.

Retrieves:
- Total content count
- Breakdown by content type (pages, blog posts)
- Top contributors
- Recent updates

**Usage:**
```bash
python get_space_analytics.py SPACE_KEY [--days N] [--output json] [--profile PROFILE]
```

**Arguments:**
- `SPACE_KEY` - The space key (required)
- `--days` - Limit to content from last N days (optional)
- `--output` - Output format: text or json (default: text)
- `--profile` - Confluence profile to use

**Examples:**
```bash
# Get all-time space analytics
python get_space_analytics.py DOCS

# Get last 30 days
python get_space_analytics.py DOCS --days 30

# Get as JSON
python get_space_analytics.py DOCS --output json
```

**Output (text):**
```
Space: DOCS
Period: Last 30 days

Total Items: 156

By Type:
  page: 142
  blogpost: 14

Top Contributors:
  John Doe: 45 items
  Jane Smith: 38 items
  Alice Johnson: 22 items
  ...

Recent Updates:
  - API Documentation (page) - 2024-01-15T10:30:00.000Z
  - Release Notes v2.1 (page) - 2024-01-14T15:20:00.000Z
  - Q1 Planning (blogpost) - 2024-01-13T09:45:00.000Z
  ...
```

---

### get_popular_content.py

Find the most popular or most recently updated content.

Uses CQL queries with ordering to identify popular content based on:
- Recent creation date
- Recent modification date
- Labels (e.g., "featured", "important")

**Usage:**
```bash
python get_popular_content.py [--space SPACE_KEY] [--label LABEL] [--type TYPE] [--sort SORT] [--limit N] [--output json] [--profile PROFILE]
```

**Arguments:**
- `--space` - Space key to search within (optional)
- `--label` - Filter by label (optional)
- `--type` - Content type: page, blogpost, or all (default: all)
- `--sort` - Sort by: created or modified (default: modified)
- `--limit` - Number of results (default: 10)
- `--output` - Output format: text or json (default: text)
- `--profile` - Confluence profile to use

**Note:** Must specify either `--space` or `--label`

**Examples:**
```bash
# Most recently modified in space
python get_popular_content.py --space DOCS

# Most recently created pages
python get_popular_content.py --space DOCS --type page --sort created --limit 5

# Content with featured label
python get_popular_content.py --label featured --limit 10

# Recent blog posts
python get_popular_content.py --space DOCS --type blogpost --limit 5
```

**Output (text):**
```
Popular Content (sorted by modified)
Space: DOCS
Type: all

Found 10 items:

1. API Documentation
   Type: page | Space: DOCS
   Last Modified: 2024-01-15T10:30:00.000Z
   URL: https://your-site.atlassian.net/wiki/spaces/DOCS/pages/12345

2. Getting Started Guide
   Type: page | Space: DOCS
   Last Modified: 2024-01-14T16:20:00.000Z
   URL: https://your-site.atlassian.net/wiki/spaces/DOCS/pages/12346

...
```

---

### get_content_watchers.py

Get the list of users watching a page (who will be notified of changes).

**Usage:**
```bash
python get_content_watchers.py PAGE_ID [--output json] [--profile PROFILE]
```

**Arguments:**
- `PAGE_ID` - The page or blog post ID (required)
- `--output` - Output format: text or json (default: text)
- `--profile` - Confluence profile to use

**Examples:**
```bash
# Get watchers for a page
python get_content_watchers.py 12345

# Get as JSON
python get_content_watchers.py 12345 --output json
```

**Output (text):**
```
Page: API Documentation
ID: 12345
Type: page
Space: DOCS

Watchers: 3

Watcher List:
  - John Doe (john.doe@example.com)
  - Jane Smith (jane.smith@example.com)
  - Alice Johnson (alice.johnson@example.com)
```

**Note:** Some Confluence Cloud instances may have restricted watcher API access. If the watchers endpoint is not available, the script will report this.

---

## Natural Language Examples

When you ask Claude about analytics, this skill will be triggered:

- "Show me the analytics for page 12345"
- "Who has contributed to this page?"
- "Get statistics for the DOCS space"
- "What are the most popular pages in the KB space?"
- "Show me the most recently updated content"
- "Who is watching page 12345?"
- "Find the top 5 most active pages"
- "Get space analytics for the last 30 days"
- "Show me featured content"
- "What are the most viewed pages?"

## API Endpoints Used

This skill uses the following Confluence REST API endpoints:

### v1 API (Legacy)
- `GET /rest/api/content/{id}?expand=history,version,history.contributors.publishers` - Page analytics
- `GET /rest/api/search?cql={query}` - CQL search for content
- `GET /rest/api/content/{id}/notification/child-created` - Watchers

### CQL Queries
- `space={key} AND type=page` - All pages in space
- `space={key} AND created >= "{date}"` - Recent content
- `type=page ORDER BY lastModified DESC` - Recently modified
- `type=page ORDER BY created DESC` - Recently created
- `label={name}` - Content with label

## Limitations

1. **No Direct View Count:** Confluence Cloud API does not expose actual view/visit counts like Server/Data Center
2. **Watchers API:** May be restricted on some Confluence Cloud instances
3. **Analytics Proxy:** Uses modification dates, contributor lists, and labels as proxies for popularity
4. **Rate Limits:** Large spaces may hit API rate limits during analytics gathering

## Testing

Run unit tests:
```bash
pytest .claude/skills/confluence-analytics/tests/ -v
```

The tests verify:
- Input validation (page IDs, space keys)
- API response handling
- Output formatting (text and JSON)
- Error handling (not found, invalid input)

## Related Skills

- **confluence-page** - Page CRUD operations
- **confluence-space** - Space management
- **confluence-search** - Advanced CQL search
- **confluence-watch** - Watch/unwatch content

## References

- [Confluence REST API v1 Documentation](https://developer.atlassian.com/cloud/confluence/rest/v1/intro/)
- [CQL (Confluence Query Language)](https://developer.atlassian.com/cloud/confluence/advanced-searching-using-cql/)
- API docs in `references/` directory
