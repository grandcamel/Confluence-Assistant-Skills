"""Analytics commands - CLI-only implementation."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import click

from confluence_assistant_skills_lib import (
    format_json,
    format_table,
    get_confluence_client,
    handle_errors,
    print_info,
    print_success,
    validate_limit,
    validate_page_id,
    validate_space_key,
)

from confluence_assistant_skills.cli.helpers import get_space_by_key


@click.group()
def analytics() -> None:
    """View content analytics."""
    pass


@analytics.command(name="views")
@click.argument("page_id")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def get_page_views(
    page_id: str,
    output: str,
) -> None:
    """Get view statistics for a page."""
    page_id = validate_page_id(page_id)

    client = get_confluence_client()

    # Get page info
    page = client.get(f"/api/v2/pages/{page_id}", operation="get page")
    page_title = page.get("title", "Unknown")

    # Get views using v1 API (v2 doesn't have analytics)
    # Note: This endpoint may require Analytics for Confluence
    try:
        views_data = client.get(
            f"/rest/api/content/{page_id}/history",
            params={"expand": "lastUpdated,contributors.publishers"},
            operation="get page history",
        )

        # Extract contributor info as proxy for engagement
        contributors = views_data.get("contributors", {}).get("publishers", {}).get("users", [])
        last_updated = views_data.get("lastUpdated", {})

        if output == "json":
            click.echo(format_json({
                "page": {"id": page_id, "title": page_title},
                "history": views_data,
                "contributorCount": len(contributors),
            }))
        else:
            click.echo(f"\nPage Statistics: {page_title} ({page_id})")
            click.echo(f"{'=' * 60}\n")

            click.echo("History Information:")
            click.echo(f"  Created: {views_data.get('createdDate', 'N/A')[:10]}")
            if last_updated:
                click.echo(f"  Last Updated: {last_updated.get('when', 'N/A')[:10]}")
                click.echo(f"  Updated By: {last_updated.get('by', {}).get('displayName', 'Unknown')}")

            click.echo(f"\nContributors: {len(contributors)}")
            if contributors:
                for contributor in contributors[:5]:  # Show top 5
                    click.echo(f"  - {contributor.get('displayName', 'Unknown')}")
                if len(contributors) > 5:
                    click.echo(f"  ... and {len(contributors) - 5} more")

    except Exception as e:
        # Analytics may not be available
        if output == "json":
            click.echo(format_json({
                "page": {"id": page_id, "title": page_title},
                "error": str(e),
                "note": "Analytics data may require Confluence Premium",
            }))
        else:
            click.echo(f"\nPage: {page_title} ({page_id})")
            click.echo(f"{'=' * 60}\n")
            print_info("Detailed view analytics may require Confluence Premium.")
            click.echo("Basic page information retrieved.")

    print_success("Retrieved page statistics")


@analytics.command(name="watchers")
@click.argument("page_id")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def get_content_watchers(
    page_id: str,
    output: str,
) -> None:
    """Get users watching a page."""
    page_id = validate_page_id(page_id)

    client = get_confluence_client()

    # Get page info
    page = client.get(f"/api/v2/pages/{page_id}", operation="get page")
    page_title = page.get("title", "Unknown")

    # Get watchers using v1 API
    watchers_response = client.get(
        f"/rest/api/content/{page_id}/notification/child-created",
        operation="get watchers",
    )

    watchers = watchers_response.get("results", [])

    if output == "json":
        click.echo(format_json({
            "page": {"id": page_id, "title": page_title},
            "watchers": watchers,
            "count": len(watchers),
        }))
    else:
        click.echo(f"\nWatchers of: {page_title} ({page_id})")
        click.echo(f"{'=' * 60}\n")

        if not watchers:
            click.echo("No watchers found.")
        else:
            data = []
            for watcher in watchers:
                user = watcher.get("user", watcher)
                data.append({
                    "name": user.get("displayName", "Unknown"),
                    "type": user.get("type", "user"),
                    "email": user.get("email", "N/A")[:30] if user.get("email") else "N/A",
                })

            click.echo(format_table(
                data,
                columns=["name", "type", "email"],
                headers=["Name", "Type", "Email"],
            ))

    print_success(f"Found {len(watchers)} watcher(s)")


@analytics.command(name="popular")
@click.option("--space", "-s", help="Limit to specific space")
@click.option("--label", help="Filter by label")
@click.option(
    "--type",
    "content_type",
    type=click.Choice(["page", "blogpost", "all"]),
    default="all",
    help="Content type (default: all)",
)
@click.option(
    "--sort",
    type=click.Choice(["created", "modified"]),
    default="modified",
    help="Sort by created or modified date (default: modified)",
)
@click.option(
    "--limit", "-l", type=int, default=10, help="Maximum results (default: 10)"
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def get_popular_content(
    space: str | None,
    label: str | None,
    content_type: str,
    sort: str,
    limit: int,
    output: str,
) -> None:
    """Get popular content.

    Shows recently modified/created content as a proxy for popularity.
    For full view-count analytics, Confluence Premium may be required.
    """
    if space:
        space = validate_space_key(space)

    limit = validate_limit(limit, max_value=100)

    client = get_confluence_client()

    # Build CQL query for popular content
    cql_parts = []

    if space:
        cql_parts.append(f'space = "{space}"')

    if content_type != "all":
        cql_parts.append(f"type = {content_type}")
    else:
        cql_parts.append("type in (page, blogpost)")

    if label:
        cql_parts.append(f'label = "{label}"')

    cql = " AND ".join(cql_parts) if cql_parts else "type in (page, blogpost)"

    # Sort order
    sort_order = "created desc" if sort == "created" else "lastmodified desc"
    cql += f" ORDER BY {sort_order}"

    # Search for content
    params: dict[str, Any] = {
        "cql": cql,
        "limit": min(limit, 25),
    }

    results = []
    for result in client.paginate(
        "/rest/api/search",
        params=params,
        operation="search popular content",
    ):
        results.append(result)
        if len(results) >= limit:
            break

    if output == "json":
        click.echo(format_json({
            "cql": cql,
            "space": space,
            "label": label,
            "contentType": content_type,
            "sort": sort,
            "results": results,
            "count": len(results),
        }))
    else:
        click.echo(f"\nPopular Content")
        if space:
            click.echo(f"Space: {space}")
        if label:
            click.echo(f"Label: {label}")
        click.echo(f"Sort: {sort}")
        click.echo(f"{'=' * 60}\n")

        if not results:
            click.echo("No content found.")
        else:
            data = []
            for r in results:
                content = r.get("content", r)
                data.append({
                    "id": content.get("id", ""),
                    "title": content.get("title", "")[:35],
                    "type": content.get("type", ""),
                    "space": content.get("space", {}).get("key", ""),
                    "modified": content.get("lastModified", {}).get("when", "")[:10]
                    if isinstance(content.get("lastModified"), dict)
                    else str(content.get("lastModified", ""))[:10],
                })

            click.echo(format_table(
                data,
                columns=["id", "title", "type", "space", "modified"],
                headers=["ID", "Title", "Type", "Space", "Modified"],
            ))

    print_success(f"Found {len(results)} content item(s)")


@analytics.command(name="space")
@click.argument("space_key")
@click.option("--days", type=int, help="Limit to content from last N days")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@handle_errors
def get_space_analytics(
    space_key: str,
    days: int | None,
    output: str,
) -> None:
    """Get analytics for a space.

    Shows space statistics including page count, recent activity,
    and contributor information.
    """
    space_key = validate_space_key(space_key)

    client = get_confluence_client()

    # Get space info
    space = get_space_by_key(client, space_key)
    space_name = space.get("name", space_key)
    space_id = space.get("id")

    # Build date filter
    date_filter = ""
    if days:
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        date_filter = f" AND lastmodified >= {cutoff_date}"

    # Get content counts
    page_cql = f'space = "{space_key}" AND type = page{date_filter}'
    blog_cql = f'space = "{space_key}" AND type = blogpost{date_filter}'

    # Count pages
    pages = list(client.paginate(
        "/rest/api/search",
        params={"cql": page_cql, "limit": 1},
        operation="count pages",
    ))

    # We need to get the total from the search response differently
    # Let's collect samples to estimate
    page_results = []
    for p in client.paginate(
        "/rest/api/search",
        params={"cql": page_cql, "limit": 25},
        operation="get pages",
    ):
        page_results.append(p)
        if len(page_results) >= 200:  # Cap for performance
            break

    blog_results = []
    for b in client.paginate(
        "/rest/api/search",
        params={"cql": blog_cql, "limit": 25},
        operation="get blogposts",
    ):
        blog_results.append(b)
        if len(blog_results) >= 100:
            break

    # Get recent activity (last 10 modified items)
    recent_cql = f'space = "{space_key}" ORDER BY lastmodified desc'
    recent_items = []
    for item in client.paginate(
        "/rest/api/search",
        params={"cql": recent_cql, "limit": 10},
        operation="get recent",
    ):
        recent_items.append(item)
        if len(recent_items) >= 10:
            break

    # Collect unique contributors
    contributors: set[str] = set()
    for item in page_results + blog_results:
        content = item.get("content", item)
        by = content.get("lastModified", {})
        if isinstance(by, dict) and "by" in by:
            contributors.add(by["by"].get("displayName", "Unknown"))

    analytics_data = {
        "space": {"key": space_key, "name": space_name, "id": space_id},
        "pageCount": len(page_results),
        "blogCount": len(blog_results),
        "totalContent": len(page_results) + len(blog_results),
        "contributorCount": len(contributors),
        "recentItems": recent_items[:10],
    }

    if days:
        analytics_data["dateRange"] = f"Last {days} days"

    if output == "json":
        click.echo(format_json(analytics_data))
    else:
        click.echo(f"\nSpace Analytics: {space_name} ({space_key})")
        if days:
            click.echo(f"Date Range: Last {days} days")
        click.echo(f"{'=' * 60}\n")

        click.echo("Content Summary:")
        click.echo(f"  Pages: {len(page_results)}+")
        click.echo(f"  Blog Posts: {len(blog_results)}+")
        click.echo(f"  Total: {len(page_results) + len(blog_results)}+")
        click.echo(f"  Contributors: {len(contributors)}")

        if recent_items:
            click.echo("\nRecent Activity:")
            for item in recent_items[:5]:
                content = item.get("content", item)
                title = content.get("title", "Untitled")[:40]
                content_type = content.get("type", "page")
                click.echo(f"  - [{content_type}] {title}")

    print_success(f"Retrieved analytics for space {space_key}")
