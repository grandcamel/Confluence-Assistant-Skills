"""Shared helper functions for CLI commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from confluence_assistant_skills_lib import ValidationError

if TYPE_CHECKING:
    from pathlib import Path


def get_space_by_key(client: Any, space_key: str) -> dict[str, Any]:
    """Get space details by space key.

    Args:
        client: Confluence API client
        space_key: Space key to look up

    Returns:
        Space data dictionary

    Raises:
        ValidationError: If space not found
    """
    spaces = list(
        client.paginate(
            "/api/v2/spaces", params={"keys": space_key}, operation="get space"
        )
    )
    if not spaces:
        raise ValidationError(f"Space not found: {space_key}")
    return spaces[0]


def get_space_id(client: Any, space_key: str) -> str:
    """Get space ID from space key.

    Args:
        client: Confluence API client
        space_key: Space key to look up

    Returns:
        Space ID string

    Raises:
        ValidationError: If space not found
    """
    return get_space_by_key(client, space_key)["id"]


def read_file_content(file_path: Path) -> str:
    """Read content from a file.

    Args:
        file_path: Path to the file

    Returns:
        File content as string

    Raises:
        ValidationError: If file not found
    """
    if not file_path.exists():
        raise ValidationError(f"File not found: {file_path}")
    return file_path.read_text(encoding="utf-8")


def is_markdown_file(file_path: Path) -> bool:
    """Check if file is a Markdown file.

    Args:
        file_path: Path to check

    Returns:
        True if file has .md or .markdown extension
    """
    return file_path.suffix.lower() in (".md", ".markdown")
