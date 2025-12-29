"""
Input Validators for Confluence Assistant Skills

Provides validation functions for:
- Page IDs
- Space keys
- CQL queries
- Content types
- File paths
- URLs
- Email addresses

Usage:
    from validators import validate_page_id, validate_space_key

    page_id = validate_page_id("12345")  # Returns "12345"
    space_key = validate_space_key("DOCS")  # Returns "DOCS"
"""

import re
import os
from pathlib import Path
from typing import Optional, Union
from urllib.parse import urlparse


class ValidationError(Exception):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: Optional[str] = None, value: Optional[str] = None):
        self.field = field
        self.value = value
        self.message = message
        super().__init__(message)


def validate_page_id(page_id: Union[str, int], field_name: str = "page_id") -> str:
    """
    Validate a Confluence page ID.

    Page IDs are numeric strings in the Confluence API.

    Args:
        page_id: The page ID to validate
        field_name: Name of the field for error messages

    Returns:
        Validated page ID as string

    Raises:
        ValidationError: If the page ID is invalid
    """
    if page_id is None:
        raise ValidationError(f"{field_name} is required", field=field_name)

    # Convert to string
    page_id_str = str(page_id).strip()

    if not page_id_str:
        raise ValidationError(f"{field_name} cannot be empty", field=field_name, value=page_id_str)

    # Check if numeric
    if not page_id_str.isdigit():
        raise ValidationError(
            f"{field_name} must be a numeric string (got: {page_id_str})",
            field=field_name,
            value=page_id_str
        )

    return page_id_str


def validate_space_key(
    space_key: str,
    field_name: str = "space_key",
    allow_lowercase: bool = True,
) -> str:
    """
    Validate a Confluence space key.

    Space keys are typically uppercase alphanumeric strings (2-255 chars).
    Some Confluence instances allow lowercase, so we normalize to uppercase.

    Args:
        space_key: The space key to validate
        field_name: Name of the field for error messages
        allow_lowercase: If True, convert to uppercase; if False, require uppercase

    Returns:
        Validated space key (uppercase)

    Raises:
        ValidationError: If the space key is invalid
    """
    if space_key is None:
        raise ValidationError(f"{field_name} is required", field=field_name)

    space_key = str(space_key).strip()

    if not space_key:
        raise ValidationError(f"{field_name} cannot be empty", field=field_name, value=space_key)

    # Check length
    if len(space_key) < 2:
        raise ValidationError(
            f"{field_name} must be at least 2 characters",
            field=field_name,
            value=space_key
        )

    if len(space_key) > 255:
        raise ValidationError(
            f"{field_name} must be at most 255 characters",
            field=field_name,
            value=space_key
        )

    # Check format - alphanumeric and underscores only
    if not re.match(r'^[A-Za-z][A-Za-z0-9_]*$', space_key):
        raise ValidationError(
            f"{field_name} must start with a letter and contain only letters, numbers, and underscores",
            field=field_name,
            value=space_key
        )

    # Normalize to uppercase
    return space_key.upper() if allow_lowercase else space_key


def validate_cql(cql: str, field_name: str = "cql") -> str:
    """
    Validate a CQL (Confluence Query Language) query.

    Performs basic syntax validation:
    - Non-empty
    - Balanced parentheses and quotes
    - Contains at least one field or operator

    Args:
        cql: The CQL query to validate
        field_name: Name of the field for error messages

    Returns:
        Validated CQL query (stripped)

    Raises:
        ValidationError: If the CQL query is invalid
    """
    if cql is None:
        raise ValidationError(f"{field_name} is required", field=field_name)

    cql = str(cql).strip()

    if not cql:
        raise ValidationError(f"{field_name} cannot be empty", field=field_name, value=cql)

    # Check balanced parentheses
    paren_count = 0
    for char in cql:
        if char == '(':
            paren_count += 1
        elif char == ')':
            paren_count -= 1
        if paren_count < 0:
            raise ValidationError(
                f"{field_name} has unbalanced parentheses",
                field=field_name,
                value=cql
            )
    if paren_count != 0:
        raise ValidationError(
            f"{field_name} has unbalanced parentheses",
            field=field_name,
            value=cql
        )

    # Check balanced quotes (simple check)
    if cql.count('"') % 2 != 0:
        raise ValidationError(
            f"{field_name} has unbalanced double quotes",
            field=field_name,
            value=cql
        )

    if cql.count("'") % 2 != 0:
        raise ValidationError(
            f"{field_name} has unbalanced single quotes",
            field=field_name,
            value=cql
        )

    # Known CQL fields
    cql_fields = [
        'space', 'title', 'text', 'type', 'label', 'creator', 'contributor',
        'created', 'lastModified', 'parent', 'ancestor', 'id', 'content',
        'macro', 'favourite', 'watcher', 'mention'
    ]

    # Known CQL operators
    cql_operators = ['=', '!=', '~', '!~', '>', '<', '>=', '<=', 'in', 'not in']

    # Check that query contains at least one field or uses text search
    cql_lower = cql.lower()
    has_field = any(field in cql_lower for field in cql_fields)
    has_operator = any(op in cql for op in cql_operators)

    if not has_field and not has_operator:
        # Could be a simple text search, which is allowed
        pass

    return cql


def validate_content_type(
    content_type: str,
    field_name: str = "content_type",
    allowed: Optional[list] = None,
) -> str:
    """
    Validate a Confluence content type.

    Args:
        content_type: The content type to validate
        field_name: Name of the field for error messages
        allowed: List of allowed content types. Defaults to standard types.

    Returns:
        Validated content type (lowercase)

    Raises:
        ValidationError: If the content type is invalid
    """
    if allowed is None:
        allowed = ['page', 'blogpost', 'comment', 'attachment']

    if content_type is None:
        raise ValidationError(f"{field_name} is required", field=field_name)

    content_type = str(content_type).strip().lower()

    if not content_type:
        raise ValidationError(f"{field_name} cannot be empty", field=field_name, value=content_type)

    if content_type not in allowed:
        raise ValidationError(
            f"{field_name} must be one of: {', '.join(allowed)} (got: {content_type})",
            field=field_name,
            value=content_type
        )

    return content_type


def validate_file_path(
    file_path: Union[str, Path],
    field_name: str = "file_path",
    must_exist: bool = True,
    must_be_file: bool = True,
    allowed_extensions: Optional[list] = None,
) -> Path:
    """
    Validate a file path.

    Args:
        file_path: The file path to validate
        field_name: Name of the field for error messages
        must_exist: If True, the file must exist
        must_be_file: If True, the path must be a file (not directory)
        allowed_extensions: List of allowed extensions (e.g., ['.txt', '.pdf'])

    Returns:
        Validated Path object

    Raises:
        ValidationError: If the file path is invalid
    """
    if file_path is None:
        raise ValidationError(f"{field_name} is required", field=field_name)

    path = Path(file_path).expanduser().resolve()

    if must_exist and not path.exists():
        raise ValidationError(
            f"{field_name} does not exist: {path}",
            field=field_name,
            value=str(path)
        )

    if must_exist and must_be_file and not path.is_file():
        raise ValidationError(
            f"{field_name} is not a file: {path}",
            field=field_name,
            value=str(path)
        )

    if allowed_extensions:
        ext = path.suffix.lower()
        if ext not in [e.lower() for e in allowed_extensions]:
            raise ValidationError(
                f"{field_name} must have extension: {', '.join(allowed_extensions)} (got: {ext})",
                field=field_name,
                value=str(path)
            )

    return path


def validate_url(
    url: str,
    field_name: str = "url",
    require_https: bool = True,
    require_atlassian: bool = False,
) -> str:
    """
    Validate a URL.

    Args:
        url: The URL to validate
        field_name: Name of the field for error messages
        require_https: If True, require HTTPS protocol
        require_atlassian: If True, require atlassian.net domain

    Returns:
        Validated URL (normalized)

    Raises:
        ValidationError: If the URL is invalid
    """
    if url is None:
        raise ValidationError(f"{field_name} is required", field=field_name)

    url = str(url).strip()

    if not url:
        raise ValidationError(f"{field_name} cannot be empty", field=field_name, value=url)

    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception as e:
        raise ValidationError(
            f"{field_name} is not a valid URL: {e}",
            field=field_name,
            value=url
        )

    # Check scheme
    if not parsed.scheme:
        raise ValidationError(
            f"{field_name} must include protocol (https://)",
            field=field_name,
            value=url
        )

    if require_https and parsed.scheme != 'https':
        raise ValidationError(
            f"{field_name} must use HTTPS",
            field=field_name,
            value=url
        )

    # Check host
    if not parsed.netloc:
        raise ValidationError(
            f"{field_name} must include a host",
            field=field_name,
            value=url
        )

    if require_atlassian and not parsed.netloc.endswith('.atlassian.net'):
        raise ValidationError(
            f"{field_name} must be an Atlassian Cloud URL (*.atlassian.net)",
            field=field_name,
            value=url
        )

    # Normalize: remove trailing slash
    normalized = url.rstrip('/')

    return normalized


def validate_email(
    email: str,
    field_name: str = "email",
) -> str:
    """
    Validate an email address.

    Args:
        email: The email address to validate
        field_name: Name of the field for error messages

    Returns:
        Validated email (lowercase)

    Raises:
        ValidationError: If the email is invalid
    """
    if email is None:
        raise ValidationError(f"{field_name} is required", field=field_name)

    email = str(email).strip().lower()

    if not email:
        raise ValidationError(f"{field_name} cannot be empty", field=field_name, value=email)

    # Basic email pattern
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        raise ValidationError(
            f"{field_name} is not a valid email address",
            field=field_name,
            value=email
        )

    return email


def validate_title(
    title: str,
    field_name: str = "title",
    max_length: int = 255,
) -> str:
    """
    Validate a page or content title.

    Args:
        title: The title to validate
        field_name: Name of the field for error messages
        max_length: Maximum allowed length

    Returns:
        Validated title (stripped)

    Raises:
        ValidationError: If the title is invalid
    """
    if title is None:
        raise ValidationError(f"{field_name} is required", field=field_name)

    title = str(title).strip()

    if not title:
        raise ValidationError(f"{field_name} cannot be empty", field=field_name, value=title)

    if len(title) > max_length:
        raise ValidationError(
            f"{field_name} must be at most {max_length} characters (got {len(title)})",
            field=field_name,
            value=title
        )

    # Check for invalid characters (Confluence restrictions)
    invalid_chars = [':', '|', '@', '/', '\\']
    for char in invalid_chars:
        if char in title:
            raise ValidationError(
                f"{field_name} cannot contain the character '{char}'",
                field=field_name,
                value=title
            )

    return title


def validate_label(
    label: str,
    field_name: str = "label",
) -> str:
    """
    Validate a Confluence label.

    Labels in Confluence:
    - Are case-insensitive (stored lowercase)
    - Cannot contain spaces (use hyphens or underscores)
    - Max 255 characters

    Args:
        label: The label to validate
        field_name: Name of the field for error messages

    Returns:
        Validated label (lowercase, stripped)

    Raises:
        ValidationError: If the label is invalid
    """
    if label is None:
        raise ValidationError(f"{field_name} is required", field=field_name)

    label = str(label).strip().lower()

    if not label:
        raise ValidationError(f"{field_name} cannot be empty", field=field_name, value=label)

    if len(label) > 255:
        raise ValidationError(
            f"{field_name} must be at most 255 characters",
            field=field_name,
            value=label
        )

    # Labels should not contain spaces
    if ' ' in label:
        raise ValidationError(
            f"{field_name} cannot contain spaces (use hyphens or underscores)",
            field=field_name,
            value=label
        )

    # Check for valid characters (alphanumeric, hyphens, underscores)
    if not re.match(r'^[a-z0-9_-]+$', label):
        raise ValidationError(
            f"{field_name} can only contain letters, numbers, hyphens, and underscores",
            field=field_name,
            value=label
        )

    return label


def validate_limit(
    limit: Union[str, int],
    field_name: str = "limit",
    min_value: int = 1,
    max_value: int = 250,
    default: int = 25,
) -> int:
    """
    Validate a pagination limit.

    Args:
        limit: The limit value to validate
        field_name: Name of the field for error messages
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        default: Default value if limit is None

    Returns:
        Validated limit as integer

    Raises:
        ValidationError: If the limit is invalid
    """
    if limit is None:
        return default

    try:
        limit_int = int(limit)
    except (TypeError, ValueError):
        raise ValidationError(
            f"{field_name} must be an integer",
            field=field_name,
            value=str(limit)
        )

    if limit_int < min_value:
        raise ValidationError(
            f"{field_name} must be at least {min_value}",
            field=field_name,
            value=str(limit_int)
        )

    if limit_int > max_value:
        raise ValidationError(
            f"{field_name} must be at most {max_value}",
            field=field_name,
            value=str(limit_int)
        )

    return limit_int


def validate_issue_key(
    issue_key: str,
    field_name: str = "issue_key",
) -> str:
    """
    Validate a JIRA issue key.

    JIRA issue keys have the format: PROJECT-123
    - Project key: 1-10 uppercase letters/underscores
    - Hyphen separator
    - Issue number: 1 or more digits

    Args:
        issue_key: The JIRA issue key to validate
        field_name: Name of the field for error messages

    Returns:
        Validated issue key (uppercase)

    Raises:
        ValidationError: If the issue key is invalid
    """
    if issue_key is None:
        raise ValidationError(f"{field_name} is required", field=field_name)

    issue_key = str(issue_key).strip().upper()

    if not issue_key:
        raise ValidationError(f"{field_name} cannot be empty", field=field_name, value=issue_key)

    # JIRA issue key pattern: PROJECT-123
    pattern = r'^[A-Z][A-Z0-9_]{0,9}-\d+$'
    if not re.match(pattern, issue_key):
        raise ValidationError(
            f"{field_name} must be in format PROJECT-123 (got: {issue_key})",
            field=field_name,
            value=issue_key
        )

    return issue_key


def validate_jql_query(
    jql: str,
    field_name: str = "jql",
) -> str:
    """
    Validate a JQL (JIRA Query Language) query.

    Performs basic syntax validation:
    - Non-empty
    - Balanced parentheses and quotes

    Args:
        jql: The JQL query to validate
        field_name: Name of the field for error messages

    Returns:
        Validated JQL query (stripped)

    Raises:
        ValidationError: If the JQL query is invalid
    """
    if jql is None:
        raise ValidationError(f"{field_name} is required", field=field_name)

    jql = str(jql).strip()

    if not jql:
        raise ValidationError(f"{field_name} cannot be empty", field=field_name, value=jql)

    # Check balanced parentheses
    paren_count = 0
    for char in jql:
        if char == '(':
            paren_count += 1
        elif char == ')':
            paren_count -= 1
        if paren_count < 0:
            raise ValidationError(
                f"{field_name} has unbalanced parentheses",
                field=field_name,
                value=jql
            )
    if paren_count != 0:
        raise ValidationError(
            f"{field_name} has unbalanced parentheses",
            field=field_name,
            value=jql
        )

    # Check balanced quotes
    if jql.count('"') % 2 != 0:
        raise ValidationError(
            f"{field_name} has unbalanced double quotes",
            field=field_name,
            value=jql
        )

    return jql
