"""
Confluence Assistant Skills - Shared Library

This module provides common utilities for all Confluence skills:
- ConfluenceClient: HTTP client with retry logic
- ConfigManager: Multi-source configuration
- Error handling: Exception hierarchy and decorators
- Validators: Input validation utilities
- Formatters: Output formatting utilities
- ADF Helper: Atlassian Document Format utilities
- XHTML Helper: Legacy storage format utilities
- Cache: Response caching
"""

from confluence_client import ConfluenceClient
from config_manager import (
    ConfigManager,
    get_confluence_client,
    get_config,
)
from error_handler import (
    ConfluenceError,
    AuthenticationError,
    PermissionError,
    ValidationError,
    NotFoundError,
    RateLimitError,
    ConflictError,
    ServerError,
    handle_confluence_error,
    handle_errors,
    print_error,
    sanitize_error_message,
)
from validators import (
    validate_page_id,
    validate_space_key,
    validate_cql,
    validate_content_type,
    validate_file_path,
    validate_url,
    validate_email,
)
from formatters import (
    format_page,
    format_space,
    format_table,
    format_json,
    format_search_results,
    format_comments,
    export_csv,
    print_success,
    print_warning,
    print_info,
)

__version__ = "1.0.0"

__all__ = [
    # Client
    "ConfluenceClient",
    # Config
    "ConfigManager",
    "get_confluence_client",
    "get_config",
    # Errors
    "ConfluenceError",
    "AuthenticationError",
    "PermissionError",
    "ValidationError",
    "NotFoundError",
    "RateLimitError",
    "ConflictError",
    "ServerError",
    "handle_confluence_error",
    "handle_errors",
    "print_error",
    "sanitize_error_message",
    # Validators
    "validate_page_id",
    "validate_space_key",
    "validate_cql",
    "validate_content_type",
    "validate_file_path",
    "validate_url",
    "validate_email",
    # Formatters
    "format_page",
    "format_space",
    "format_table",
    "format_json",
    "format_search_results",
    "format_comments",
    "export_csv",
    "print_success",
    "print_warning",
    "print_info",
]
