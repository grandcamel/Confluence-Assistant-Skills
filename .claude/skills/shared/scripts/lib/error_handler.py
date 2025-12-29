"""
Error Handling for Confluence Assistant Skills

Provides:
- Exception hierarchy for Confluence API errors
- Error handling decorator
- Error sanitization for sensitive data
- Formatted error output

Usage:
    from error_handler import handle_errors, ConfluenceError, print_error

    @handle_errors
    def main():
        # Your code here
        pass
"""

import sys
import re
import functools
import traceback
from typing import Optional, Callable, Any

import requests


class ConfluenceError(Exception):
    """Base exception for all Confluence-related errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response: Optional[requests.Response] = None,
        operation: Optional[str] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.response = response
        self.operation = operation
        super().__init__(self.message)

    def __str__(self) -> str:
        parts = []
        if self.operation:
            parts.append(f"[{self.operation}]")
        if self.status_code:
            parts.append(f"({self.status_code})")
        parts.append(self.message)
        return " ".join(parts)


class AuthenticationError(ConfluenceError):
    """Raised when authentication fails (401)."""
    pass


class PermissionError(ConfluenceError):
    """Raised when user lacks permission (403)."""
    pass


class ValidationError(ConfluenceError):
    """Raised for invalid input or bad requests (400)."""
    pass


class NotFoundError(ConfluenceError):
    """Raised when resource is not found (404)."""
    pass


class RateLimitError(ConfluenceError):
    """Raised when rate limit is exceeded (429)."""

    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class ConflictError(ConfluenceError):
    """Raised on resource conflicts (409)."""
    pass


class ServerError(ConfluenceError):
    """Raised for server-side errors (5xx)."""
    pass


def sanitize_error_message(message: str) -> str:
    """
    Remove sensitive information from error messages.

    Args:
        message: The error message to sanitize

    Returns:
        Sanitized message with sensitive data removed
    """
    # Patterns to sanitize
    patterns = [
        # API tokens (various formats)
        (r'(?i)(api[_-]?token|token|apikey|api[_-]?key)["\s:=]+[A-Za-z0-9_\-]{10,}', r'\1=[REDACTED]'),
        # Email addresses in auth context
        (r'(?i)(auth|email|user)["\s:=]+[\w.+-]+@[\w.-]+', r'\1=[REDACTED]'),
        # Bearer tokens
        (r'Bearer\s+[A-Za-z0-9_\-\.]+', 'Bearer [REDACTED]'),
        # Basic auth base64
        (r'Basic\s+[A-Za-z0-9+/=]+', 'Basic [REDACTED]'),
        # URLs with credentials
        (r'https?://[^:]+:[^@]+@', 'https://[REDACTED]@'),
        # Session IDs
        (r'(?i)(session[_-]?id|jsessionid)["\s:=]+[A-Za-z0-9_\-]+', r'\1=[REDACTED]'),
    ]

    sanitized = message
    for pattern, replacement in patterns:
        sanitized = re.sub(pattern, replacement, sanitized)

    return sanitized


def extract_error_message(response: requests.Response) -> str:
    """
    Extract a meaningful error message from a Confluence API response.

    Args:
        response: The HTTP response object

    Returns:
        Extracted error message
    """
    try:
        data = response.json()

        # V2 API error format
        if "errors" in data:
            errors = data["errors"]
            if isinstance(errors, list) and errors:
                error = errors[0]
                return error.get("title", error.get("detail", str(error)))
            return str(errors)

        # V1 API error format
        if "message" in data:
            return data["message"]

        # Alternative format
        if "errorMessage" in data:
            return data["errorMessage"]

        # Status message
        if "statusMessage" in data:
            return data["statusMessage"]

        return str(data)

    except (ValueError, KeyError):
        return response.text[:500] if response.text else f"HTTP {response.status_code}"


def handle_confluence_error(
    response: requests.Response,
    operation: str = "API request",
) -> None:
    """
    Handle an error response from the Confluence API.

    Args:
        response: The HTTP response object
        operation: Description of the operation for error context

    Raises:
        Appropriate ConfluenceError subclass based on status code
    """
    status_code = response.status_code
    message = extract_error_message(response)
    message = sanitize_error_message(message)

    error_kwargs = {
        "message": message,
        "status_code": status_code,
        "response": response,
        "operation": operation,
    }

    if status_code == 400:
        raise ValidationError(**error_kwargs)
    elif status_code == 401:
        raise AuthenticationError(
            message="Authentication failed. Check your email and API token.",
            **{k: v for k, v in error_kwargs.items() if k != "message"}
        )
    elif status_code == 403:
        raise PermissionError(
            message=f"Permission denied: {message}",
            **{k: v for k, v in error_kwargs.items() if k != "message"}
        )
    elif status_code == 404:
        raise NotFoundError(**error_kwargs)
    elif status_code == 409:
        raise ConflictError(**error_kwargs)
    elif status_code == 429:
        retry_after = response.headers.get("Retry-After")
        raise RateLimitError(
            message=f"Rate limit exceeded. Retry after {retry_after or 'unknown'} seconds.",
            retry_after=int(retry_after) if retry_after and retry_after.isdigit() else None,
            **{k: v for k, v in error_kwargs.items() if k != "message"}
        )
    elif 500 <= status_code < 600:
        raise ServerError(
            message=f"Confluence server error: {message}",
            **{k: v for k, v in error_kwargs.items() if k != "message"}
        )
    else:
        raise ConfluenceError(**error_kwargs)


def print_error(
    message: str,
    error: Optional[Exception] = None,
    suggestion: Optional[str] = None,
    show_traceback: bool = False,
) -> None:
    """
    Print a formatted error message to stderr.

    Args:
        message: The main error message
        error: Optional exception object
        suggestion: Optional suggestion for resolution
        show_traceback: Whether to print the full traceback
    """
    print(f"\n[ERROR] {message}", file=sys.stderr)

    if error:
        error_str = sanitize_error_message(str(error))
        print(f"  Details: {error_str}", file=sys.stderr)

        if isinstance(error, AuthenticationError):
            print("  Hint: Check your CONFLUENCE_EMAIL and CONFLUENCE_API_TOKEN", file=sys.stderr)
            print("  Token URL: https://id.atlassian.com/manage-profile/security/api-tokens", file=sys.stderr)
        elif isinstance(error, PermissionError):
            print("  Hint: Verify you have access to this resource", file=sys.stderr)
        elif isinstance(error, RateLimitError) and error.retry_after:
            print(f"  Hint: Wait {error.retry_after} seconds before retrying", file=sys.stderr)
        elif isinstance(error, NotFoundError):
            print("  Hint: Check that the resource ID/key is correct", file=sys.stderr)

    if suggestion:
        print(f"  Suggestion: {suggestion}", file=sys.stderr)

    if show_traceback and error:
        print("\n  Traceback:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

    print("", file=sys.stderr)


def handle_errors(func: Callable) -> Callable:
    """
    Decorator to handle errors in main functions.

    Catches exceptions and prints formatted error messages,
    then exits with appropriate status code.

    Usage:
        @handle_errors
        def main():
            # Your code here
            pass

    Args:
        func: The function to wrap

    Returns:
        Wrapped function with error handling
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            print("\n\nOperation cancelled by user.", file=sys.stderr)
            sys.exit(130)
        except AuthenticationError as e:
            print_error("Authentication failed", e)
            sys.exit(1)
        except PermissionError as e:
            print_error("Permission denied", e)
            sys.exit(1)
        except ValidationError as e:
            print_error("Invalid input", e)
            sys.exit(1)
        except NotFoundError as e:
            print_error("Resource not found", e)
            sys.exit(1)
        except RateLimitError as e:
            print_error("Rate limit exceeded", e)
            sys.exit(1)
        except ConflictError as e:
            print_error("Conflict error", e)
            sys.exit(1)
        except ServerError as e:
            print_error("Server error", e)
            sys.exit(1)
        except ConfluenceError as e:
            print_error("Confluence API error", e)
            sys.exit(1)
        except requests.exceptions.ConnectionError as e:
            print_error(
                "Connection failed",
                e,
                suggestion="Check your network connection and Confluence URL"
            )
            sys.exit(1)
        except requests.exceptions.Timeout as e:
            print_error(
                "Request timed out",
                e,
                suggestion="The server took too long to respond. Try again later."
            )
            sys.exit(1)
        except Exception as e:
            print_error(
                "Unexpected error",
                e,
                show_traceback=True
            )
            sys.exit(1)

    return wrapper


class ErrorContext:
    """
    Context manager for error handling with custom messages.

    Usage:
        with ErrorContext("creating page", page_title=title):
            client.post("/api/v2/pages", data=page_data)
    """

    def __init__(self, operation: str, **context):
        self.operation = operation
        self.context = context

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None and issubclass(exc_type, ConfluenceError):
            # Enhance error message with context
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            exc_val.operation = f"{self.operation} ({context_str})" if context_str else self.operation
        return False  # Don't suppress the exception
