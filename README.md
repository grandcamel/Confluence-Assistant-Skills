<div align="center">

<!-- HERO SECTION -->
<img src=".github/assets/logo.svg" alt="Confluence Assistant Skills" width="300">

<br><br>

<!-- STATS BAR -->
<table>
<tr>
<td align="center"><strong>14</strong><br><sub>Skills</sub></td>
<td align="center"><strong>88</strong><br><sub>Scripts</sub></td>
<td align="center"><strong>1,039</strong><br><sub>Tests</sub></td>
<td align="center"><strong>CQL</strong><br><sub>Query Support</sub></td>
</tr>
</table>

<br>

<!-- BADGES -->
[![Release](https://img.shields.io/github/v/release/grandcamel/Confluence-Assistant-Skills?style=for-the-badge&logo=github&logoColor=white&color=36B37E)](https://github.com/grandcamel/Confluence-Assistant-Skills/releases)
[![License](https://img.shields.io/badge/license-MIT-blue?style=for-the-badge&logo=opensourceinitiative&logoColor=white&color=0052CC)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-blue?style=for-the-badge&logo=python&logoColor=white&color=0052CC)](https://www.python.org/downloads/)
[![Confluence](https://img.shields.io/badge/Confluence-Cloud-blue?style=for-the-badge&logo=confluence&logoColor=white&color=0052CC)](https://www.atlassian.com/software/confluence)

<br>

### 🚀 Stop clicking through Confluence. Start talking to it.

**Confluence Assistant Skills** brings the power of natural language automation to Confluence Cloud.<br>
Ask Claude to create pages, search content, manage permissions, and more — all without leaving your terminal.

<br>

<!-- QUICK DEMO -->
```
You: "Find all pages labeled 'api-docs' modified this week and export to CSV"

Claude: Found 23 pages matching your criteria.
        ✓ Exported to api-docs-report.csv
```

<br>

[Get Started](#-quick-start) · [View Skills](#-available-skills) · [Documentation](CLAUDE.md) · [Contributing](#-contributing)

</div>

<br>

---

<br>

<!-- PROBLEM / SOLUTION -->
<table>
<tr>
<td width="50%" valign="top">

### 😤 Without Assistant Skills

```
1. Open browser
2. Navigate to Confluence
3. Click through menus
4. Find the right space
5. Create page manually
6. Copy-paste content
7. Format everything
8. Add labels one by one
9. Set permissions
10. Repeat for next page...
```

**Time: 15+ minutes per page**

</td>
<td width="50%" valign="top">

### 🎯 With Assistant Skills

```
You: "Create a page called 'Q4 Planning'
      in the DOCS space with the content
      from my notes.md file, label it
      'planning' and 'q4-2024'"

Claude: ✓ Created page "Q4 Planning"
        ✓ Added 2 labels
        ✓ Page ID: 12345
```

**Time: 10 seconds**

</td>
</tr>
</table>

<br>

---

<br>

## ⚡ Quick Start

<table>
<tr>
<td>

### 1️⃣ Install

```bash
pip install -r .claude/skills/shared/scripts/lib/requirements.txt
```

</td>
</tr>
<tr>
<td>

### 2️⃣ Configure

```bash
export CONFLUENCE_SITE_URL="https://your-site.atlassian.net"
export CONFLUENCE_EMAIL="you@company.com"
export CONFLUENCE_API_TOKEN="your-api-token"
```

<sub>Get your API token from [Atlassian Account Settings](https://id.atlassian.com/manage-profile/security/api-tokens)</sub>

</td>
</tr>
<tr>
<td>

### 3️⃣ Use

```bash
# Verify connection
python .claude/skills/confluence-space/scripts/list_spaces.py --limit 1

# Then just ask Claude naturally:
"Create a page titled 'Meeting Notes' in the DOCS space"
"Search for pages about API documentation"
"Add label 'approved' to page 12345"
```

</td>
</tr>
</table>

<br>

---

<br>

## 🎯 What You Can Do

```mermaid
flowchart LR
    subgraph Input["💬 Natural Language"]
        A["Create a page about..."]
        B["Find all pages with..."]
        C["Update permissions for..."]
    end

    subgraph Skills["🔧 14 Skills"]
        D[Pages]
        E[Search]
        F[Permissions]
        G[Labels]
        H[Comments]
        I[+ 9 more]
    end

    subgraph Output["✅ Results"]
        J["Pages created"]
        K["Content found"]
        L["Settings updated"]
    end

    A --> D --> J
    B --> E --> K
    C --> F --> L

    style Input fill:#0052CC,color:#fff
    style Skills fill:#36B37E,color:#fff
    style Output fill:#00C7E6,color:#000
```

<br>

---

<br>

## 📦 Available Skills

| Skill | Purpose | Example Commands |
|-------|---------|------------------|
| **confluence-page** | Create, read, update, delete pages | `create_page`, `get_page`, `update_page`, `copy_page`, `move_page` |
| **confluence-space** | Manage spaces | `list_spaces`, `create_space`, `get_space`, `delete_space` |
| **confluence-search** | CQL queries & export | `cql_search`, `search_content`, `export_results`, `cql_validate` |
| **confluence-comment** | Page comments | `add_comment`, `get_comments`, `update_comment`, `delete_comment` |
| **confluence-attachment** | File attachments | `upload_attachment`, `download_attachment`, `list_attachments` |
| **confluence-label** | Content labeling | `add_label`, `remove_label`, `get_labels` |
| **confluence-template** | Page templates | `list_templates`, `get_template`, `create_from_template` |
| **confluence-property** | Content properties | `get_properties`, `set_property`, `delete_property` |
| **confluence-permission** | Access control | `get_space_permissions`, `add_space_permission` |
| **confluence-analytics** | View statistics | `get_page_views` |
| **confluence-watch** | Content watching | `watch_page`, `unwatch_page` |
| **confluence-hierarchy** | Page tree navigation | `get_ancestors`, `get_children`, `get_descendants` |
| **confluence-jira** | JIRA integration | `embed_jira_issues`, `get_linked_issues` |
| **confluence-assistant** | Central hub | Routes to specialized skills |

<br>

---

<br>

## 🔍 CQL Query Power

Full Confluence Query Language support with validation, suggestions, and export.

<table>
<tr>
<td width="50%">

### Find Content

```sql
-- Pages in a space
space = "DOCS" AND type = page

-- By label
label = "approved" AND label = "api"

-- Text search
text ~ "API documentation"

-- Recent changes
lastModified >= startOfWeek()
```

</td>
<td width="50%">

### Export Results

```bash
# Export to CSV
python export_results.py \
  "label = 'release-notes'" \
  --format csv \
  --output releases.csv

# Export to JSON
python export_results.py \
  "space = 'DOCS'" \
  --format json
```

</td>
</tr>
</table>

<br>

---

<br>

## 👥 Who Is This For?

<details>
<summary><strong>📝 Technical Writers</strong> — Automate documentation workflows</summary>

<br>

- Bulk create pages from templates
- Search and update outdated content
- Export content for review
- Manage labels across hundreds of pages

```bash
# Find all pages needing review
python cql_search.py "label = 'needs-review' AND lastModified < startOfMonth(-3)"
```

</details>

<details>
<summary><strong>🛠️ DevOps Engineers</strong> — Integrate Confluence into CI/CD</summary>

<br>

- Auto-generate release notes
- Update runbooks from code
- Sync documentation with deployments
- Create incident pages automatically

```bash
# Create release notes page
python create_page.py --space RELEASES --title "v2.5.0" --file CHANGELOG.md
```

</details>

<details>
<summary><strong>👔 Project Managers</strong> — Streamline project documentation</summary>

<br>

- Create project spaces from templates
- Generate status reports
- Track page analytics
- Manage team permissions

```bash
# Get page view statistics
python get_page_views.py 12345 --output json
```

</details>

<details>
<summary><strong>🔒 IT Administrators</strong> — Manage Confluence at scale</summary>

<br>

- Audit space permissions
- Bulk update settings
- Export content for compliance
- Automate user provisioning

```bash
# List all space permissions
python get_space_permissions.py DOCS --output json
```

</details>

<br>

---

<br>

## 🏗️ Architecture

```
.claude/skills/
├── confluence-assistant/     # Hub skill - routes requests
├── confluence-page/          # Page CRUD operations
├── confluence-space/         # Space management
├── confluence-search/        # CQL queries & export
├── confluence-comment/       # Comments
├── confluence-attachment/    # File attachments
├── confluence-label/         # Labels
├── confluence-template/      # Templates
├── confluence-property/      # Content properties
├── confluence-permission/    # Permissions
├── confluence-analytics/     # Analytics
├── confluence-watch/         # Watching
├── confluence-hierarchy/     # Page tree
├── confluence-jira/          # JIRA integration
└── shared/
    ├── scripts/lib/          # Shared Python library
    │   ├── confluence_client.py   # HTTP client with retry
    │   ├── config_manager.py      # Multi-profile config
    │   ├── error_handler.py       # Exception handling
    │   ├── validators.py          # Input validation
    │   └── formatters.py          # Output formatting
    ├── config/               # Configuration schema
    └── tests/                # Shared test fixtures
```

<br>

---

<br>

## 🔐 Configuration

### Environment Variables

```bash
export CONFLUENCE_SITE_URL="https://your-site.atlassian.net"
export CONFLUENCE_EMAIL="you@company.com"
export CONFLUENCE_API_TOKEN="your-api-token"
```

### Multiple Profiles

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

```bash
# Use specific profile
python get_page.py 12345 --profile sandbox
```

<br>

---

<br>

## ✅ Quality & Testing

| Metric | Value |
|--------|-------|
| Test Files | 1,039 |
| Unit Tests | Comprehensive coverage |
| Live Integration Tests | 64 test files |
| Code Style | PEP 8 compliant |

```bash
# Run all unit tests
pytest .claude/skills/*/tests/ -v --ignore="**/live_integration"

# Run with coverage
pytest --cov=.claude/skills/shared/scripts/lib --cov-report=html

# Run live integration tests
pytest .claude/skills/*/tests/live_integration/ --profile=sandbox -v
```

<br>

---

<br>

## 🛠️ Troubleshooting

<details>
<summary><strong>Authentication failed</strong></summary>

1. Verify API token at [Atlassian Account Settings](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Ensure email matches the token owner
3. Check URL includes `https://` and ends with `.atlassian.net`

</details>

<details>
<summary><strong>Permission denied</strong></summary>

1. Verify access in Confluence web UI
2. Some operations require admin permissions
3. Check if content is restricted

</details>

<details>
<summary><strong>CQL syntax error</strong></summary>

```bash
# Validate your query
python .claude/skills/confluence-search/scripts/cql_validate.py "your query"
```

Check quotes are balanced and field names are valid.

</details>

<br>

---

<br>

## 📚 Documentation

| Resource | Description |
|----------|-------------|
| [CLAUDE.md](CLAUDE.md) | Developer guide, patterns, API reference |
| [CHANGELOG.md](CHANGELOG.md) | Release history |
| [Confluence API Docs](https://developer.atlassian.com/cloud/confluence/rest/v2/intro/) | Official API reference |

<br>

---

<br>

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with tests
4. Commit with [Conventional Commits](https://www.conventionalcommits.org/) format
5. Push and submit a pull request

```bash
# Commit format
feat(page): add copy page functionality
fix(search): handle empty CQL results
docs: update README
test(space): add integration tests
```

<br>

---

<br>

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

<br>

---

<div align="center">

<br>

**[⬆ Back to Top](#)**

<br>

Made with ❤️ for the Confluence community

<br>

[![GitHub stars](https://img.shields.io/github/stars/grandcamel/Confluence-Assistant-Skills?style=social)](https://github.com/grandcamel/Confluence-Assistant-Skills)

</div>
