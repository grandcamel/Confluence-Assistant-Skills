"""Operations commands - CLI-only implementation."""

from __future__ import annotations

import contextlib
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import click

from confluence_assistant_skills_lib import (
    ValidationError,
    format_json,
    format_table,
    get_confluence_client,
    handle_errors,
    print_info,
    print_success,
    print_warning,
    validate_space_key,
)


def _get_cache_dir() -> Path:
    """Get the cache directory path."""
    cache_dir = os.environ.get("CONFLUENCE_CACHE_DIR")
    if cache_dir:
        return Path(cache_dir)
    return Path.home() / ".confluence-skills" / "cache"


def _format_bytes(size: int) -> str:
    """Format bytes to human readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size //= 1024
    return f"{size:.1f} TB"


@click.group()
def ops() -> None:
    """Operations and diagnostics commands."""
    pass


# ============================================================================
# Cache Status
# ============================================================================

@ops.command(name="cache-status")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed cache entries")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def cache_status(
    verbose: bool,
    output: str,
) -> None:
    """Display cache statistics."""
    cache_dir = _get_cache_dir()

    # Check if caching is enabled
    cache_enabled = os.environ.get("CONFLUENCE_CACHE_ENABLED", "true").lower() == "true"

    # Gather cache statistics
    stats: dict[str, Any] = {
        "enabled": cache_enabled,
        "cacheDir": str(cache_dir),
        "exists": cache_dir.exists(),
        "totalEntries": 0,
        "totalSize": 0,
        "categories": {},
        "oldestEntry": None,
        "newestEntry": None,
    }

    entries: list[dict[str, Any]] = []

    if cache_dir.exists():
        for category_dir in cache_dir.iterdir():
            if category_dir.is_dir():
                category_name = category_dir.name
                category_stats = {"entries": 0, "size": 0}

                for cache_file in category_dir.glob("**/*"):
                    if cache_file.is_file():
                        file_stat = cache_file.stat()
                        category_stats["entries"] += 1
                        category_stats["size"] += file_stat.st_size

                        mtime = datetime.fromtimestamp(file_stat.st_mtime)
                        if stats["oldestEntry"] is None or mtime < stats["oldestEntry"]:
                            stats["oldestEntry"] = mtime
                        if stats["newestEntry"] is None or mtime > stats["newestEntry"]:
                            stats["newestEntry"] = mtime

                        if verbose:
                            entries.append({
                                "category": category_name,
                                "file": cache_file.name,
                                "size": file_stat.st_size,
                                "modified": mtime.isoformat(),
                            })

                stats["categories"][category_name] = category_stats
                stats["totalEntries"] += category_stats["entries"]
                stats["totalSize"] += category_stats["size"]

    # Convert datetime to strings for JSON
    if stats["oldestEntry"]:
        stats["oldestEntry"] = stats["oldestEntry"].isoformat()
    if stats["newestEntry"]:
        stats["newestEntry"] = stats["newestEntry"].isoformat()

    if output == "json":
        result = stats.copy()
        if verbose:
            result["entries"] = entries
        click.echo(format_json(result))
    else:
        click.echo("\nCache Status")
        click.echo(f"{'=' * 60}\n")

        click.echo(f"Status:         {'Enabled' if cache_enabled else 'Disabled'}")
        click.echo(f"Cache Dir:      {cache_dir}")
        click.echo(f"Dir Exists:     {'Yes' if stats['exists'] else 'No'}")
        click.echo(f"Total Entries:  {stats['totalEntries']:,}")
        click.echo(f"Total Size:     {_format_bytes(stats['totalSize'])}")

        if stats["categories"]:
            click.echo("\nBy Category:")
            for cat_name, cat_stats in sorted(stats["categories"].items()):
                click.echo(
                    f"  {cat_name:15} {cat_stats['entries']:5} entries "
                    f"({_format_bytes(cat_stats['size'])})"
                )

        if stats["oldestEntry"]:
            click.echo(f"\nOldest Entry:   {stats['oldestEntry'][:19]}")
        if stats["newestEntry"]:
            click.echo(f"Newest Entry:   {stats['newestEntry'][:19]}")

        if verbose and entries:
            click.echo(f"\nCache Entries ({len(entries)} total):")
            data = []
            for e in entries[:20]:
                data.append({
                    "category": e["category"][:12],
                    "file": e["file"][:30],
                    "size": _format_bytes(e["size"]),
                    "modified": e["modified"][:19],
                })
            click.echo(format_table(
                data,
                columns=["category", "file", "size", "modified"],
                headers=["Category", "File", "Size", "Modified"],
            ))
            if len(entries) > 20:
                click.echo(f"  ... and {len(entries) - 20} more")

    print_success("Cache status retrieved")


# ============================================================================
# Cache Clear
# ============================================================================

@ops.command(name="cache-clear")
@click.option("--category", help="Clear only specific category (spaces, pages, users, etc.)")
@click.option("--pattern", help="Clear keys matching pattern")
@click.option("--older-than", type=int, help="Clear entries older than N days")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
@click.option("--dry-run", is_flag=True, help="Preview what would be cleared")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def cache_clear(
    category: str | None,
    pattern: str | None,
    older_than: int | None,
    force: bool,
    dry_run: bool,
    output: str,
) -> None:
    """Clear cache entries."""
    cache_dir = _get_cache_dir()

    if not cache_dir.exists():
        if output == "json":
            click.echo(format_json({"cleared": 0, "error": "Cache directory does not exist"}))
        else:
            print_warning("Cache directory does not exist")
        return

    # Collect files to clear
    files_to_clear: list[dict[str, Any]] = []
    cutoff_time = None
    if older_than:
        cutoff_time = time.time() - (older_than * 24 * 60 * 60)

    for category_dir in cache_dir.iterdir():
        if not category_dir.is_dir():
            continue

        # Filter by category if specified
        if category and category_dir.name != category:
            continue

        for cache_file in category_dir.glob("**/*"):
            if not cache_file.is_file():
                continue

            # Filter by pattern if specified
            if pattern and pattern not in cache_file.name:
                continue

            # Filter by age if specified
            if cutoff_time:
                file_stat = cache_file.stat()
                if file_stat.st_mtime >= cutoff_time:
                    continue

            files_to_clear.append({
                "path": cache_file,
                "category": category_dir.name,
                "size": cache_file.stat().st_size,
            })

    if not files_to_clear:
        if output == "json":
            click.echo(format_json({"cleared": 0, "message": "No matching cache entries"}))
        else:
            click.echo("No matching cache entries to clear.")
        return

    total_size = sum(f["size"] for f in files_to_clear)

    if dry_run:
        if output == "json":
            click.echo(format_json({
                "dryRun": True,
                "wouldClear": len(files_to_clear),
                "totalSize": total_size,
                "files": [
                    {"category": f["category"], "file": f["path"].name}
                    for f in files_to_clear[:50]
                ],
            }))
        else:
            click.echo(f"\n[DRY RUN] Would clear {len(files_to_clear)} cache entries "
                       f"({_format_bytes(total_size)}):\n")
            for f in files_to_clear[:10]:
                click.echo(f"  - [{f['category']}] {f['path'].name}")
            if len(files_to_clear) > 10:
                click.echo(f"  ... and {len(files_to_clear) - 10} more")
        return

    if not force:
        click.echo(f"\nAbout to clear {len(files_to_clear)} cache entries "
                   f"({_format_bytes(total_size)})")
        print_warning("This may slow down subsequent API calls until cache is rebuilt.")

        if not click.confirm("Continue?", default=True):
            click.echo("Cancelled.")
            return

    # Clear the files
    cleared = 0
    errors = []

    for f in files_to_clear:
        try:
            f["path"].unlink()
            cleared += 1
        except Exception as e:
            errors.append({"file": str(f["path"]), "error": str(e)})

    # Clean up empty directories
    for category_dir in cache_dir.iterdir():
        if category_dir.is_dir():
            try:
                # Remove if empty
                if not any(category_dir.iterdir()):
                    category_dir.rmdir()
            except Exception:  # nosec B110
                pass

    if output == "json":
        click.echo(format_json({
            "cleared": cleared,
            "totalSize": total_size,
            "errors": errors if errors else None,
        }))
    else:
        click.echo("\nCache cleared")
        click.echo(f"  Entries removed: {cleared}")
        click.echo(f"  Space freed: {_format_bytes(total_size)}")

        if errors:
            click.echo(f"\nErrors ({len(errors)}):")
            for err in errors[:5]:
                click.echo(f"  - {err['file']}: {err['error']}")

    print_success(f"Cleared {cleared} cache entries")


# ============================================================================
# Cache Warm
# ============================================================================

@ops.command(name="cache-warm")
@click.option("--spaces", is_flag=True, help="Warm cache with space list")
@click.option("--space", "-s", help="Warm cache with specific space metadata")
@click.option("--all", "warm_all", is_flag=True, help="Warm all available metadata")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed progress")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def cache_warm(
    spaces: bool,
    space: str | None,
    warm_all: bool,
    verbose: bool,
    output: str,
) -> None:
    """Pre-warm cache with commonly accessed data."""
    if not spaces and not space and not warm_all:
        raise ValidationError(
            "At least one of --spaces, --space, or --all is required"
        )

    client = get_confluence_client()

    warmed = []
    errors = []

    # Warm space list
    if spaces or warm_all:
        try:
            if verbose and output == "text":
                click.echo("  Warming: space list...")

            space_list = list(client.paginate(
                "/api/v2/spaces",
                params={"limit": 100},
                operation="warm space list",
            ))
            warmed.append({
                "type": "space_list",
                "count": len(space_list),
            })
        except Exception as e:
            errors.append({"type": "space_list", "error": str(e)})

    # Warm specific space
    if space:
        space = validate_space_key(space)
        try:
            if verbose and output == "text":
                click.echo(f"  Warming: space {space}...")

            space_info = list(client.paginate(
                "/api/v2/spaces",
                params={"keys": space},
                operation=f"warm space {space}",
            ))

            if space_info:
                space_id = space_info[0].get("id")

                # Get space homepage
                with contextlib.suppress(Exception):
                    client.get(
                        f"/api/v2/spaces/{space_id}/homepage",
                        operation=f"warm space {space} homepage",
                    )

                # Get recent pages
                try:
                    pages = list(client.paginate(
                        "/api/v2/pages",
                        params={"space-id": space_id, "limit": 25},
                        operation=f"warm space {space} pages",
                    ))
                    warmed.append({
                        "type": f"space_{space}",
                        "pages": len(pages),
                    })
                except Exception:  # nosec B110
                    pass

        except Exception as e:
            errors.append({"type": f"space_{space}", "error": str(e)})

    # Warm all available data
    if warm_all:
        try:
            # Warm current user
            if verbose and output == "text":
                click.echo("  Warming: current user...")
            client.get("/rest/api/user/current", operation="warm current user")
            warmed.append({"type": "current_user"})
        except Exception as e:
            errors.append({"type": "current_user", "error": str(e)})

        try:
            # Warm groups
            if verbose and output == "text":
                click.echo("  Warming: groups...")
            groups = list(client.paginate(
                "/rest/api/group",
                params={"limit": 50},
                operation="warm groups",
            ))
            warmed.append({"type": "groups", "count": len(groups)})
        except Exception as e:
            errors.append({"type": "groups", "error": str(e)})

    if output == "json":
        click.echo(format_json({
            "warmed": warmed,
            "errors": errors if errors else None,
        }))
    else:
        click.echo("\nCache Warm Complete")
        click.echo(f"{'=' * 60}\n")

        click.echo("Warmed:")
        for w in warmed:
            details = ", ".join(f"{k}={v}" for k, v in w.items() if k != "type")
            click.echo(f"  + {w['type']}" + (f" ({details})" if details else ""))

        if errors:
            click.echo("\nErrors:")
            for err in errors:
                click.echo(f"  - {err['type']}: {err['error']}")

    print_success(f"Warmed {len(warmed)} cache categories")


# ============================================================================
# Health Check
# ============================================================================

@ops.command(name="health-check")
@click.option("--endpoint", help="Test specific endpoint")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed timing")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def health_check(
    endpoint: str | None,
    verbose: bool,
    output: str,
) -> None:
    """Test API connectivity and health."""
    client = get_confluence_client()

    results: dict[str, Any] = {
        "siteUrl": os.environ.get("CONFLUENCE_SITE_URL", "Not configured"),
        "connected": False,
        "apiVersion": None,
        "user": None,
        "endpoints": [],
    }

    # Test authentication
    auth_start = time.time()
    try:
        user = client.get("/rest/api/user/current", operation="health check - auth")
        auth_time = (time.time() - auth_start) * 1000

        results["connected"] = True
        results["user"] = user.get("displayName", "Unknown")
        results["authTime"] = round(auth_time, 0)
    except Exception as e:
        results["authError"] = str(e)

    # Test specific endpoint if provided
    if endpoint:
        ep_start = time.time()
        try:
            client.get(endpoint, operation=f"health check - {endpoint}")
            ep_time = (time.time() - ep_start) * 1000
            results["endpoints"].append({
                "path": endpoint,
                "status": "ok",
                "time": round(ep_time, 0),
            })
        except Exception as e:
            results["endpoints"].append({
                "path": endpoint,
                "status": "error",
                "error": str(e),
            })
    else:
        # Test standard endpoints
        test_endpoints = [
            ("/api/v2/spaces", "v2"),
            ("/api/v2/pages", "v2"),
            ("/rest/api/search", "v1"),
        ]

        for ep_path, api_ver in test_endpoints:
            ep_start = time.time()
            try:
                client.get(ep_path, params={"limit": 1}, operation=f"health check - {ep_path}")
                ep_time = (time.time() - ep_start) * 1000
                results["endpoints"].append({
                    "path": ep_path,
                    "api": api_ver,
                    "status": "ok",
                    "time": round(ep_time, 0),
                })
                if results["apiVersion"] is None:
                    results["apiVersion"] = api_ver
            except Exception as e:
                results["endpoints"].append({
                    "path": ep_path,
                    "api": api_ver,
                    "status": "error",
                    "error": str(e),
                })

    if output == "json":
        click.echo(format_json(results))
    else:
        click.echo("\nConfluence Health Check")
        click.echo(f"{'=' * 60}\n")

        click.echo(f"Site URL:       {results['siteUrl']}")

        if results["connected"]:
            click.echo("Status:         + Connected")
            click.echo(f"API Version:    {results.get('apiVersion', 'Unknown')}")
            click.echo(f"Response Time:  {results.get('authTime', 'N/A')}ms")
        else:
            click.echo("Status:         - Disconnected")
            if results.get("authError"):
                click.echo(f"Error:          {results['authError']}")

        click.echo("\nEndpoint Tests:")
        for ep in results["endpoints"]:
            if ep["status"] == "ok":
                icon = "+"
                detail = f"{ep.get('time', 'N/A')}ms"
            else:
                icon = "-"
                detail = ep.get("error", "Failed")[:40]

            click.echo(f"  [{icon}] {ep['path']:25} {detail}")

        if results["connected"]:
            click.echo("\nAuthentication: + Valid")
            click.echo(f"User:           {results.get('user', 'Unknown')}")
        else:
            click.echo("\nAuthentication: - Failed")

    print_success("Health check complete")


# ============================================================================
# Rate Limit Status
# ============================================================================

@ops.command(name="rate-limit-status")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def rate_limit_status(
    output: str,
) -> None:
    """Check current rate limit status."""
    client = get_confluence_client()

    # Make a request and check response headers for rate limit info
    # Atlassian APIs include rate limit headers in responses
    try:
        # Use a lightweight endpoint
        client.get("/rest/api/user/current", operation="rate limit check")

        # Note: Rate limit headers vary by Atlassian product/tier
        # Common headers: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
        # For now, provide general guidance since headers may not be exposed

        results = {
            "status": "ok",
            "note": "Rate limit headers may not be exposed in all Atlassian tiers",
            "recommendations": [
                "Confluence Cloud has rate limits of ~100-500 requests/minute",
                "Use --batch-size option in bulk operations to stay within limits",
                "429 errors indicate rate limit exceeded - wait and retry",
            ],
        }

    except Exception as e:
        error_str = str(e)
        if "429" in error_str:
            results = {
                "status": "limited",
                "error": "Rate limit exceeded (429)",
                "recommendation": "Wait before making more requests",
            }
        else:
            results = {
                "status": "error",
                "error": error_str,
            }

    if output == "json":
        click.echo(format_json(results))
    else:
        click.echo("\nRate Limit Status")
        click.echo(f"{'=' * 60}\n")

        if results["status"] == "ok":
            click.echo("Status:         + OK")
            click.echo("")
            print_info("Rate limit information:")
            for rec in results.get("recommendations", []):
                click.echo(f"  - {rec}")
        elif results["status"] == "limited":
            click.echo("Status:         - Rate Limited")
            click.echo(f"Error:          {results.get('error', 'Unknown')}")
            click.echo(f"\nRecommendation: {results.get('recommendation', 'Wait and retry')}")
        else:
            click.echo("Status:         - Error")
            click.echo(f"Error:          {results.get('error', 'Unknown')}")

    print_success("Rate limit status retrieved")


# ============================================================================
# API Diagnostics
# ============================================================================

@ops.command(name="api-diagnostics")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed diagnostics")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def api_diagnostics(
    verbose: bool,
    output: str,
) -> None:
    """Run API diagnostics."""
    client = get_confluence_client()

    diagnostics: dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "environment": {
            "siteUrl": os.environ.get("CONFLUENCE_SITE_URL", "Not set"),
            "emailConfigured": bool(os.environ.get("CONFLUENCE_EMAIL")),
            "tokenConfigured": bool(os.environ.get("CONFLUENCE_API_TOKEN")),
            "cacheEnabled": os.environ.get("CONFLUENCE_CACHE_ENABLED", "true"),
            "cacheDir": str(_get_cache_dir()),
        },
        "connectivity": {},
        "permissions": {},
    }

    # Test connectivity
    try:
        start = time.time()
        user = client.get("/rest/api/user/current", operation="diagnostics - auth")
        diagnostics["connectivity"]["auth"] = {
            "status": "ok",
            "time": round((time.time() - start) * 1000),
            "user": user.get("displayName"),
        }
    except Exception as e:
        diagnostics["connectivity"]["auth"] = {
            "status": "error",
            "error": str(e),
        }

    # Test v2 API
    try:
        start = time.time()
        client.get("/api/v2/spaces", params={"limit": 1}, operation="diagnostics - v2")
        diagnostics["connectivity"]["v2Api"] = {
            "status": "ok",
            "time": round((time.time() - start) * 1000),
        }
    except Exception as e:
        diagnostics["connectivity"]["v2Api"] = {
            "status": "error",
            "error": str(e),
        }

    # Test v1 API
    try:
        start = time.time()
        client.get("/rest/api/space", params={"limit": 1}, operation="diagnostics - v1")
        diagnostics["connectivity"]["v1Api"] = {
            "status": "ok",
            "time": round((time.time() - start) * 1000),
        }
    except Exception as e:
        diagnostics["connectivity"]["v1Api"] = {
            "status": "error",
            "error": str(e),
        }

    # Test search API
    try:
        start = time.time()
        client.get("/rest/api/search", params={"cql": "type=page", "limit": 1},
                   operation="diagnostics - search")
        diagnostics["connectivity"]["search"] = {
            "status": "ok",
            "time": round((time.time() - start) * 1000),
        }
    except Exception as e:
        diagnostics["connectivity"]["search"] = {
            "status": "error",
            "error": str(e),
        }

    # Check permissions (simplified)
    try:
        spaces = list(client.paginate(
            "/api/v2/spaces",
            params={"limit": 5},
            operation="diagnostics - spaces",
        ))
        diagnostics["permissions"]["canListSpaces"] = True
        diagnostics["permissions"]["spacesAccessible"] = len(spaces)
    except Exception:
        diagnostics["permissions"]["canListSpaces"] = False

    if output == "json":
        click.echo(format_json(diagnostics))
    else:
        click.echo("\nAPI Diagnostics")
        click.echo(f"{'=' * 60}\n")

        click.echo("Environment:")
        env = diagnostics["environment"]
        click.echo(f"  Site URL:       {env['siteUrl']}")
        click.echo(f"  Email:          {'Configured' if env['emailConfigured'] else 'Not set'}")
        click.echo(f"  Token:          {'Configured' if env['tokenConfigured'] else 'Not set'}")
        click.echo(f"  Cache:          {env['cacheEnabled']}")

        click.echo("\nConnectivity:")
        for name, result in diagnostics["connectivity"].items():
            if result["status"] == "ok":
                click.echo(f"  [+] {name:15} OK ({result.get('time', 'N/A')}ms)")
            else:
                click.echo(f"  [-] {name:15} FAILED: {result.get('error', 'Unknown')[:40]}")

        click.echo("\nPermissions:")
        perms = diagnostics["permissions"]
        if perms.get("canListSpaces"):
            click.echo(f"  [+] Can list spaces ({perms.get('spacesAccessible', 0)} accessible)")
        else:
            click.echo("  [-] Cannot list spaces")

        if verbose:
            click.echo(f"\nDiagnostic Timestamp: {diagnostics['timestamp']}")

    print_success("Diagnostics complete")
