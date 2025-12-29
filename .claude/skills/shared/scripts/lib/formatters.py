"""
Output Formatters for Confluence Assistant Skills

Provides formatting functions for:
- Pages and blog posts
- Spaces
- Comments
- Search results
- Tables
- JSON output
- CSV export

Usage:
    from formatters import format_page, format_table, print_success

    print(format_page(page_data))
    print_success("Page created successfully")
"""

import sys
import json
import csv
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pathlib import Path


# ANSI color codes for terminal output
class Colors:
    """ANSI color codes for terminal formatting."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Foreground colors
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Check if colors are supported
    @classmethod
    def enabled(cls) -> bool:
        """Check if terminal supports colors."""
        return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()


def _colorize(text: str, color: str) -> str:
    """Apply color to text if terminal supports it."""
    if Colors.enabled():
        return f"{color}{text}{Colors.RESET}"
    return text


def print_success(message: str) -> None:
    """Print a success message in green."""
    print(_colorize(f"[OK] {message}", Colors.GREEN))


def print_warning(message: str) -> None:
    """Print a warning message in yellow."""
    print(_colorize(f"[WARN] {message}", Colors.YELLOW), file=sys.stderr)


def print_info(message: str) -> None:
    """Print an info message in cyan."""
    print(_colorize(f"[INFO] {message}", Colors.CYAN))


def format_json(data: Any, pretty: bool = True, indent: int = 2) -> str:
    """
    Format data as JSON.

    Args:
        data: Data to format
        pretty: If True, format with indentation
        indent: Indentation level for pretty printing

    Returns:
        JSON string
    """
    if pretty:
        return json.dumps(data, indent=indent, ensure_ascii=False, default=str)
    return json.dumps(data, ensure_ascii=False, default=str)


def format_timestamp(timestamp: Optional[str], format_str: str = "%Y-%m-%d %H:%M") -> str:
    """
    Format an ISO timestamp for display.

    Args:
        timestamp: ISO format timestamp string
        format_str: Output format string

    Returns:
        Formatted date/time string
    """
    if not timestamp:
        return "N/A"

    try:
        # Handle various ISO formats
        if 'T' in timestamp:
            # Remove timezone info for simple parsing
            clean = timestamp.split('+')[0].split('Z')[0]
            dt = datetime.fromisoformat(clean)
        else:
            dt = datetime.fromisoformat(timestamp)

        return dt.strftime(format_str)
    except (ValueError, TypeError):
        return timestamp[:16] if len(timestamp) > 16 else timestamp


def format_page(page: Dict[str, Any], detailed: bool = False) -> str:
    """
    Format a Confluence page for display.

    Args:
        page: Page data from API
        detailed: If True, include extended information

    Returns:
        Formatted string
    """
    lines = []

    # Title and ID
    title = page.get('title', 'Untitled')
    page_id = page.get('id', 'Unknown')
    status = page.get('status', 'current')

    lines.append(_colorize(f"Page: {title}", Colors.BOLD))
    lines.append(f"  ID: {page_id}")
    lines.append(f"  Status: {status}")

    # Space info
    space_id = page.get('spaceId')
    if space_id:
        lines.append(f"  Space ID: {space_id}")

    # Parent page
    parent_id = page.get('parentId')
    if parent_id:
        lines.append(f"  Parent ID: {parent_id}")

    # Version
    version = page.get('version', {})
    if version:
        version_num = version.get('number', 1)
        version_msg = version.get('message', '')
        lines.append(f"  Version: {version_num}")
        if version_msg:
            lines.append(f"  Version Message: {version_msg}")

    # Dates
    created = page.get('createdAt')
    if created:
        lines.append(f"  Created: {format_timestamp(created)}")

    # Author info (if available)
    author_id = page.get('authorId')
    if author_id:
        lines.append(f"  Author ID: {author_id}")

    # URL (v2 API format)
    links = page.get('_links', {})
    web_ui = links.get('webui', '')
    if web_ui:
        lines.append(f"  URL: {web_ui}")

    if detailed:
        # Labels
        labels = page.get('labels', {}).get('results', [])
        if labels:
            label_names = [l.get('name', l.get('label', '')) for l in labels]
            lines.append(f"  Labels: {', '.join(label_names)}")

        # Body preview (if present)
        body = page.get('body', {})
        if body:
            storage = body.get('storage', {}).get('value', '')
            if storage:
                preview = storage[:200].replace('\n', ' ')
                if len(storage) > 200:
                    preview += '...'
                lines.append(f"  Content Preview: {preview}")

    return '\n'.join(lines)


def format_blogpost(blogpost: Dict[str, Any], detailed: bool = False) -> str:
    """
    Format a Confluence blog post for display.

    Args:
        blogpost: Blog post data from API
        detailed: If True, include extended information

    Returns:
        Formatted string
    """
    lines = []

    title = blogpost.get('title', 'Untitled')
    post_id = blogpost.get('id', 'Unknown')
    status = blogpost.get('status', 'current')

    lines.append(_colorize(f"Blog Post: {title}", Colors.BOLD))
    lines.append(f"  ID: {post_id}")
    lines.append(f"  Status: {status}")

    # Space info
    space_id = blogpost.get('spaceId')
    if space_id:
        lines.append(f"  Space ID: {space_id}")

    # Created date
    created = blogpost.get('createdAt')
    if created:
        lines.append(f"  Created: {format_timestamp(created)}")

    # URL
    links = blogpost.get('_links', {})
    web_ui = links.get('webui', '')
    if web_ui:
        lines.append(f"  URL: {web_ui}")

    return '\n'.join(lines)


def format_space(space: Dict[str, Any], detailed: bool = False) -> str:
    """
    Format a Confluence space for display.

    Args:
        space: Space data from API
        detailed: If True, include extended information

    Returns:
        Formatted string
    """
    lines = []

    name = space.get('name', 'Unnamed')
    key = space.get('key', space.get('id', 'Unknown'))
    space_type = space.get('type', 'global')
    status = space.get('status', 'current')

    lines.append(_colorize(f"Space: {name}", Colors.BOLD))
    lines.append(f"  Key: {key}")
    lines.append(f"  Type: {space_type}")
    lines.append(f"  Status: {status}")

    # Description
    description = space.get('description', {})
    if isinstance(description, dict):
        desc_text = description.get('plain', {}).get('value', '')
    else:
        desc_text = str(description)

    if desc_text:
        lines.append(f"  Description: {desc_text[:100]}")

    # Homepage
    homepage_id = space.get('homepageId')
    if homepage_id:
        lines.append(f"  Homepage ID: {homepage_id}")

    if detailed:
        # URL
        links = space.get('_links', {})
        web_ui = links.get('webui', '')
        if web_ui:
            lines.append(f"  URL: {web_ui}")

    return '\n'.join(lines)


def format_comment(comment: Dict[str, Any], show_body: bool = True) -> str:
    """
    Format a Confluence comment for display.

    Args:
        comment: Comment data from API
        show_body: If True, include comment body

    Returns:
        Formatted string
    """
    lines = []

    comment_id = comment.get('id', 'Unknown')
    created = comment.get('createdAt', '')
    author_id = comment.get('authorId', 'Unknown')

    lines.append(_colorize(f"Comment {comment_id}", Colors.BOLD))
    lines.append(f"  Author ID: {author_id}")
    lines.append(f"  Created: {format_timestamp(created)}")

    if show_body:
        body = comment.get('body', {})
        if body:
            # Try to get plain text representation
            storage = body.get('storage', {}).get('value', '')
            # Simple HTML stripping for preview
            import re
            text = re.sub(r'<[^>]+>', '', storage)
            text = text[:200].strip()
            if len(storage) > 200:
                text += '...'
            lines.append(f"  Content: {text}")

    return '\n'.join(lines)


def format_comments(
    comments: List[Dict[str, Any]],
    limit: Optional[int] = None,
    show_body: bool = True,
) -> str:
    """
    Format multiple comments for display.

    Args:
        comments: List of comment data
        limit: Maximum number to display
        show_body: If True, include comment bodies

    Returns:
        Formatted string
    """
    if limit:
        comments = comments[:limit]

    if not comments:
        return "No comments found."

    formatted = []
    for i, comment in enumerate(comments, 1):
        formatted.append(f"{i}. {format_comment(comment, show_body=show_body)}")

    return '\n\n'.join(formatted)


def format_search_results(
    results: List[Dict[str, Any]],
    show_labels: bool = False,
    show_ancestors: bool = False,
    show_excerpt: bool = True,
) -> str:
    """
    Format search results for display.

    Args:
        results: List of search result items
        show_labels: If True, include labels
        show_ancestors: If True, include parent pages
        show_excerpt: If True, include content excerpt

    Returns:
        Formatted string
    """
    if not results:
        return "No results found."

    lines = []
    lines.append(_colorize(f"Found {len(results)} result(s)", Colors.BOLD))
    lines.append("")

    for i, result in enumerate(results, 1):
        # Handle both v1 and v2 API result formats
        content = result.get('content', result)

        title = content.get('title', 'Untitled')
        content_id = content.get('id', 'Unknown')
        content_type = content.get('type', 'page')
        space = content.get('space', {})
        space_key = space.get('key', content.get('spaceId', 'Unknown'))

        lines.append(f"{i}. {_colorize(title, Colors.CYAN)}")
        lines.append(f"   ID: {content_id} | Type: {content_type} | Space: {space_key}")

        if show_excerpt:
            excerpt = result.get('excerpt', '')
            if excerpt:
                # Clean HTML from excerpt
                import re
                clean = re.sub(r'<[^>]+>', '', excerpt)[:150].strip()
                if clean:
                    lines.append(f"   Excerpt: {clean}...")

        if show_ancestors:
            ancestors = content.get('ancestors', [])
            if ancestors:
                ancestor_titles = [a.get('title', '') for a in ancestors]
                lines.append(f"   Path: {' > '.join(ancestor_titles)}")

        if show_labels:
            labels = content.get('metadata', {}).get('labels', {}).get('results', [])
            if labels:
                label_names = [l.get('name', '') for l in labels if l.get('name')]
                if label_names:
                    lines.append(f"   Labels: {', '.join(label_names)}")

        # URL
        links = content.get('_links', {})
        web_ui = links.get('webui', '')
        if web_ui:
            lines.append(f"   URL: {web_ui}")

        lines.append("")

    return '\n'.join(lines)


def format_table(
    data: List[Dict[str, Any]],
    columns: List[str],
    headers: Optional[List[str]] = None,
    max_width: int = 40,
) -> str:
    """
    Format data as an ASCII table.

    Args:
        data: List of dictionaries
        columns: List of keys to include
        headers: Optional custom headers (defaults to column names)
        max_width: Maximum column width

    Returns:
        Formatted table string
    """
    if not data:
        return "No data to display."

    headers = headers or columns

    # Calculate column widths
    widths = []
    for i, col in enumerate(columns):
        header_width = len(str(headers[i]))
        data_width = max(len(str(row.get(col, ''))[:max_width]) for row in data)
        widths.append(max(header_width, data_width, 3))

    # Build table
    lines = []

    # Header
    header_line = " | ".join(
        str(h).ljust(widths[i]) for i, h in enumerate(headers)
    )
    lines.append(header_line)

    # Separator
    separator = "-+-".join("-" * w for w in widths)
    lines.append(separator)

    # Data rows
    for row in data:
        values = []
        for i, col in enumerate(columns):
            val = str(row.get(col, ''))[:max_width]
            values.append(val.ljust(widths[i]))
        lines.append(" | ".join(values))

    return '\n'.join(lines)


def export_csv(
    data: List[Dict[str, Any]],
    file_path: Union[str, Path],
    columns: Optional[List[str]] = None,
    headers: Optional[List[str]] = None,
) -> Path:
    """
    Export data to a CSV file.

    Args:
        data: List of dictionaries
        file_path: Output file path
        columns: Keys to include (defaults to all keys from first row)
        headers: Custom headers (defaults to column names)

    Returns:
        Path to the created file
    """
    file_path = Path(file_path)

    if not data:
        file_path.write_text("")
        return file_path

    # Determine columns
    if columns is None:
        columns = list(data[0].keys())

    headers = headers or columns

    # Write CSV
    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        for row in data:
            values = [row.get(col, '') for col in columns]
            writer.writerow(values)

    return file_path


def format_attachment(attachment: Dict[str, Any]) -> str:
    """
    Format an attachment for display.

    Args:
        attachment: Attachment data from API

    Returns:
        Formatted string
    """
    lines = []

    title = attachment.get('title', 'Unnamed')
    att_id = attachment.get('id', 'Unknown')
    media_type = attachment.get('mediaType', 'unknown')
    file_size = attachment.get('fileSize', 0)

    # Format file size
    if file_size > 1024 * 1024:
        size_str = f"{file_size / (1024 * 1024):.1f} MB"
    elif file_size > 1024:
        size_str = f"{file_size / 1024:.1f} KB"
    else:
        size_str = f"{file_size} bytes"

    lines.append(_colorize(f"Attachment: {title}", Colors.BOLD))
    lines.append(f"  ID: {att_id}")
    lines.append(f"  Type: {media_type}")
    lines.append(f"  Size: {size_str}")

    # Download link
    links = attachment.get('_links', {})
    download = links.get('download', '')
    if download:
        lines.append(f"  Download: {download}")

    return '\n'.join(lines)


def format_label(label: Dict[str, Any]) -> str:
    """
    Format a label for display.

    Args:
        label: Label data from API

    Returns:
        Formatted string
    """
    name = label.get('name', label.get('label', 'Unknown'))
    prefix = label.get('prefix', '')
    label_id = label.get('id', '')

    if prefix:
        return f"{prefix}:{name} (ID: {label_id})"
    return f"{name} (ID: {label_id})"


def format_version(version: Dict[str, Any]) -> str:
    """
    Format a version for display.

    Args:
        version: Version data from API

    Returns:
        Formatted string
    """
    number = version.get('number', 'Unknown')
    message = version.get('message', '')
    when = version.get('when', version.get('createdAt', ''))
    author = version.get('by', {}).get('displayName', version.get('authorId', 'Unknown'))

    line = f"v{number}"
    if when:
        line += f" ({format_timestamp(when)})"
    if author:
        line += f" by {author}"
    if message:
        line += f" - {message}"

    return line


def truncate(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length.

    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to add when truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix
