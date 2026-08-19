---
name: confluence-ops
description: Cache management, API diagnostics, and operational utilities. Use when optimizing performance, managing cache, diagnosing API issues, or troubleshooting Confluence connectivity.
triggers:
  - cache
  - cache status
  - cache clear
  - cache warm
  - api diagnostics
  - performance
  - rate limit
  - troubleshoot
  - connectivity
  - health check
---

# Confluence Operations Skill

Cache management, API diagnostics, and operational utilities for Confluence Assistant.

---

## ⚠️ PRIMARY USE CASE

**This skill manages operational aspects of Confluence integration.** Use for:
- Monitoring and managing cache
- Diagnosing API connectivity issues
- Performance optimization
- Troubleshooting rate limits

---

## When to Use / When NOT to Use

| Use This Skill | Use Instead |
|----------------|-------------|
| Check cache status | - |
| Clear/warm cache | - |
| Diagnose API issues | - |
| Check rate limits | - |
| Manage pages | `confluence-page` |
| Search content | `confluence-search` |
| Manage spaces | `confluence-space` |

---

## Risk Levels

| Operation | Risk | Notes |
|-----------|------|-------|
| Cache status | - | Read-only |
| API diagnostics | - | Read-only |
| Cache warm | - | Adds cache entries |
| Cache clear | ⚠️ | Removes cache, may slow next requests |

---

## When to Use This Skill

Use this skill when you need to:

- **Monitor cache status**: Check cache size and entry counts by category
- **Clear cache data**: Remove stale or sensitive cached data
- **Pre-warm cache**: Load commonly accessed data for better performance
- **Diagnose API issues**: Test connectivity and identify problems
- **Troubleshoot slowness**: Diagnose cache-related performance issues
- **Check rate limits**: Monitor API quota usage

**Trigger conditions:**
- Confluence API responses slower than 2 seconds
- Setting up new Confluence instance
- Before bulk operations (warm cache first)
- After space changes (invalidate cache)
- Troubleshooting 429 rate limit errors

---

## Quick Start

```bash
# Check cache status
confluence-as ops cache-status

# Clear all cache
confluence-as ops cache-clear --force

# Warm cache with space metadata
confluence-as ops cache-warm --spaces

# Test API connectivity
confluence-as ops health-check

# Full API diagnostics
confluence-as ops api-diagnostics
```

---

## CLI Commands

| Command | Purpose | Risk |
|---------|---------|------|
| `confluence-as ops cache-status` | Display cache statistics | - |
| `confluence-as ops cache-clear` | Clear cache entries | ⚠️ |
| `confluence-as ops cache-warm` | Pre-warm cache | - |
| `confluence-as ops health-check` | Test API connectivity | - |
| `confluence-as ops rate-limit-status` | Check rate limit usage | - |
| `confluence-as ops api-diagnostics` | Diagnose API issues | - |

The global `-o/--output` flag placed before the subcommand (e.g. `confluence-as -o json ops cache-status`) sets the default output format for all subcommands; an explicit subcommand-level `--output` wins.

---

## Common Tasks

### Check Cache Status

```bash
# Basic status
confluence-as ops cache-status

# Output as JSON
confluence-as ops cache-status --output json

# Verbose output with entry details
confluence-as ops cache-status --verbose
```

**Output example:**
```
Cache Status
============================================================

Status:         Enabled
Cache Dir:      /Users/you/.confluence-skills/cache
Dir Exists:     Yes
Total Entries:  1,234
Total Size:     45.2 MB

By Category:
  pages             892 entries (38.4 MB)
  search            163 entries (3.5 MB)
  spaces             23 entries (1.2 MB)
  users             156 entries (2.1 MB)

Oldest Entry:   2024-01-15T10:30:00
Newest Entry:   2024-01-20T14:45:00
✓ Cache status retrieved
```

### Warm the Cache

```bash
# Cache space list
confluence-as ops cache-warm --spaces

# Cache specific space metadata
confluence-as ops cache-warm --space DOCS

# Cache all available metadata
confluence-as ops cache-warm --all --verbose

# JSON output for scripting
confluence-as ops cache-warm --spaces --output json
```

### Clear Cache

```bash
# Clear all cache (with confirmation)
confluence-as ops cache-clear

# Clear all cache (skip confirmation)
confluence-as ops cache-clear --force

# Clear only page cache
confluence-as ops cache-clear --category pages --force

# Preview what would be cleared
confluence-as ops cache-clear --dry-run

# Clear keys matching pattern
confluence-as ops cache-clear --pattern "DOCS-*" --category pages --force

# Clear entries older than N days
confluence-as ops cache-clear --older-than 7 --force

# JSON output for scripting
confluence-as ops cache-clear --force --output json
```

### API Diagnostics

```bash
# Full health check
confluence-as ops health-check

# Test specific endpoint
confluence-as ops health-check --endpoint "/api/v2/spaces"

# Verbose output with timing
confluence-as ops health-check --verbose

# JSON output for scripting
confluence-as ops health-check --output json
```

**Output example:**
```
Confluence Health Check
============================================================

Site URL:       https://your-site.atlassian.net
Status:         + Connected
API Version:    v2
Response Time:  234ms

Endpoint Tests:
  [+] /api/v2/spaces            156ms
  [+] /api/v2/pages             189ms
  [+] /rest/api/search          312ms

Authentication: + Valid
User:           your-email@example.com
✓ Health check complete
```

### Rate Limit Status

```bash
# Check current rate limit status
confluence-as ops rate-limit-status

# JSON output
confluence-as ops rate-limit-status --output json
```

**Output example:**
```
Rate Limit Status
============================================================

Status:         + OK

→ Rate limit information:
  - Confluence Cloud has rate limits of ~100-500 requests/minute
  - Use --batch-size option in bulk operations to stay within limits
  - 429 errors indicate rate limit exceeded - wait and retry
✓ Rate limit status retrieved
```

Note: rate limit headers may not be exposed in all Atlassian tiers; if a request hits a 429, the status is reported as `Rate Limited`.

---

## Cache Categories

Cache entries are organized into category subdirectories of the cache directory (e.g. `spaces`, `pages`, `users`). Use `cache-status` to see which categories exist and `cache-clear --category NAME` to clear a single category.

---

## Configuration

Cache is stored in `~/.confluence-skills/cache/`.

Environment variables:
- `CONFLUENCE_CACHE_DIR` - Custom cache directory
- `CONFLUENCE_CACHE_ENABLED` - Enable/disable caching (default: true)

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (validation, API, cache, or connectivity failure) |
| 2 | Malformed command line (unknown flag, missing argument) |
| 130 | Cancelled by user (Ctrl+C) |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Slow API responses | Run `cache-warm --all` to pre-populate cache |
| Stale data | Run `cache-clear --force` then `cache-warm` |
| 429 Rate limit | Wait for reset, reduce request frequency |
| Connection timeout | Check `health-check`, verify credentials |
| Cache corruption | Run `cache-clear --force` |

---

## Related Skills

- **confluence-bulk**: Bulk operations (benefit from warmed cache)
- **confluence-search**: Search queries (results are cached)
- **confluence-admin**: Administrative operations
