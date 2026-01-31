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

- **Monitor cache status**: Check cache size, entry counts, and hit rates
- **Clear cache data**: Remove stale or sensitive cached data
- **Pre-warm cache**: Load commonly accessed data for better performance
- **Diagnose API issues**: Test connectivity and identify problems
- **Troubleshoot slowness**: Diagnose cache-related performance issues
- **Check rate limits**: Monitor API quota usage

**Trigger conditions:**
- Cache hit rate drops below 50%
- Confluence API responses slower than 2 seconds
- Setting up new Confluence instance
- Before bulk operations (warm cache first)
- After space changes (invalidate cache)
- Troubleshooting 429 rate limit errors

---

## Quick Start

```bash
# Check cache status
confluence ops cache-status

# Clear all cache
confluence ops cache-clear --force

# Warm cache with space metadata
confluence ops cache-warm --spaces

# Test API connectivity
confluence ops health-check
```

---

## CLI Commands

| Command | Purpose | Risk |
|---------|---------|------|
| `confluence ops cache-status` | Display cache statistics | - |
| `confluence ops cache-clear` | Clear cache entries | ⚠️ |
| `confluence ops cache-warm` | Pre-warm cache | - |
| `confluence ops health-check` | Test API connectivity | - |
| `confluence ops rate-limit-status` | Check rate limit usage | - |
| `confluence ops api-diagnostics` | Diagnose API issues | - |

---

## Common Tasks

### Check Cache Status

```bash
# Basic status
confluence ops cache-status

# Output as JSON
confluence ops cache-status --output json

# Verbose output with entry details
confluence ops cache-status --verbose
```

**Output example:**
```
Cache Status
────────────────────────────
Total entries:    1,234
Total size:       45.2 MB
Hit rate:         78.5%

By category:
  spaces:         23 entries (1.2 MB)
  pages:          892 entries (38.4 MB)
  users:          156 entries (2.1 MB)
  search:         163 entries (3.5 MB)

Oldest entry:     2024-01-15 10:30:00
Newest entry:     2024-01-20 14:45:00
```

### Warm the Cache

```bash
# Cache space list
confluence ops cache-warm --spaces

# Cache specific space metadata
confluence ops cache-warm --space DOCS

# Cache all available metadata
confluence ops cache-warm --all --verbose

# JSON output for scripting
confluence ops cache-warm --spaces --output json
```

### Clear Cache

```bash
# Clear all cache (with confirmation)
confluence ops cache-clear

# Clear all cache (skip confirmation)
confluence ops cache-clear --force

# Clear only page cache
confluence ops cache-clear --category pages --force

# Preview what would be cleared
confluence ops cache-clear --dry-run

# Clear keys matching pattern
confluence ops cache-clear --pattern "DOCS-*" --category pages --force

# Clear entries older than N days
confluence ops cache-clear --older-than 7 --force

# JSON output for scripting
confluence ops cache-clear --force --output json
```

### API Diagnostics

```bash
# Full health check
confluence ops health-check

# Test specific endpoint
confluence ops health-check --endpoint "/api/v2/spaces"

# Verbose output with timing
confluence ops health-check --verbose

# JSON output for scripting
confluence ops health-check --output json
```

**Output example:**
```
Confluence Health Check
────────────────────────────
Site URL:         https://your-site.atlassian.net
Status:           ✓ Connected
API Version:      v2
Response Time:    234ms

Endpoint Tests:
  /api/v2/spaces       ✓ 156ms
  /api/v2/pages        ✓ 189ms
  /rest/api/search     ✓ 312ms

Authentication:   ✓ Valid
User:             your-email@example.com
```

### Rate Limit Status

```bash
# Check current rate limit status
confluence ops rate-limit-status

# JSON output
confluence ops rate-limit-status --output json
```

**Output example:**
```
Rate Limit Status
────────────────────────────
Status:           ✓ No rate limit errors detected

Note: Confluence Cloud does not expose rate limit headers in API responses.
Rate limits are applied server-side and vary by endpoint and account tier.

Recommendations:
  - Monitor for HTTP 429 responses
  - Implement exponential backoff on retries
  - Limit bulk operations to 5-10 concurrent requests
  - Add small delays between rapid sequential calls
```

---

## Cache Categories

| Category | Description | Default TTL |
|----------|-------------|-------------|
| `spaces` | Space metadata | 1 hour |
| `pages` | Page content and metadata | 5 minutes |
| `users` | User information | 1 hour |
| `search` | Search results | 2 minutes |
| `labels` | Label data | 15 minutes |
| `permissions` | Permission data | 5 minutes |

---

## Configuration

Cache is stored in `~/.confluence-skills/cache/` with configurable TTL per category.

Environment variables:
- `CONFLUENCE_CACHE_DIR` - Custom cache directory
- `CONFLUENCE_CACHE_ENABLED` - Enable/disable caching (default: true)
- `CONFLUENCE_CACHE_TTL` - Default TTL in seconds (default: 300)

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Configuration error |
| 3 | Cache database error |
| 4 | Network/connectivity error |

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
