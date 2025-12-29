"""
Confluence Cloud API Client

HTTP client for Confluence Cloud REST API with:
- HTTP Basic Auth (email + API token)
- Automatic retry with exponential backoff on 429/5xx
- Configurable timeout
- Support for v2 (primary) and v1 (legacy) API endpoints

Usage:
    from confluence_client import ConfluenceClient

    client = ConfluenceClient(
        base_url="https://your-site.atlassian.net",
        email="your-email@example.com",
        api_token="your-api-token"
    )

    # Get a page
    page = client.get("/api/v2/pages/12345", operation="get page")

    # Create a page
    result = client.post("/api/v2/pages", data={...}, operation="create page")
"""

import time
import logging
from typing import Optional, Any, Dict, Union
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class ConfluenceClient:
    """HTTP client for Confluence Cloud REST API."""

    # API version paths
    API_V2_PREFIX = "/api/v2"
    API_V1_PREFIX = "/rest/api"
    WIKI_PATH = "/wiki"

    def __init__(
        self,
        base_url: str,
        email: str,
        api_token: str,
        timeout: int = 30,
        max_retries: int = 3,
        retry_backoff: float = 2.0,
        verify_ssl: bool = True,
    ):
        """
        Initialize the Confluence client.

        Args:
            base_url: Confluence Cloud URL (e.g., https://your-site.atlassian.net)
            email: User email for authentication
            api_token: API token from https://id.atlassian.com/manage-profile/security/api-tokens
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_backoff: Backoff multiplier for retries
            verify_ssl: Whether to verify SSL certificates
        """
        # Normalize base URL - remove trailing slash and /wiki if present
        self.base_url = base_url.rstrip("/")
        if self.base_url.endswith("/wiki"):
            self.base_url = self.base_url[:-5]

        self.email = email
        self.api_token = api_token
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self.verify_ssl = verify_ssl

        # Create session with retry strategy
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create a requests session with retry strategy."""
        session = requests.Session()

        # Configure retry strategy for 429 and 5xx errors
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=self.retry_backoff,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"],
            raise_on_status=False,
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set auth and default headers
        session.auth = (self.email, self.api_token)
        session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Confluence-Assistant-Skills/1.0",
        })

        return session

    def _build_url(self, endpoint: str) -> str:
        """
        Build the full URL for an API endpoint.

        Args:
            endpoint: API endpoint path (e.g., /api/v2/pages/12345)

        Returns:
            Full URL including base URL and /wiki prefix
        """
        # Normalize endpoint
        endpoint = endpoint.lstrip("/")

        # Determine if this is a v1 or v2 endpoint
        if endpoint.startswith("api/v2") or endpoint.startswith("rest/api"):
            return f"{self.base_url}{self.WIKI_PATH}/{endpoint}"
        elif endpoint.startswith("wiki/"):
            return f"{self.base_url}/{endpoint}"
        else:
            # Default to v2 API
            return f"{self.base_url}{self.WIKI_PATH}/{endpoint}"

    def _handle_response(
        self,
        response: requests.Response,
        operation: str = "API request",
    ) -> Dict[str, Any]:
        """
        Handle API response, raising appropriate errors.

        Args:
            response: The requests Response object
            operation: Description of the operation for error messages

        Returns:
            Parsed JSON response

        Raises:
            ConfluenceError subclass based on status code
        """
        # Import here to avoid circular import
        from error_handler import handle_confluence_error

        # Check for rate limiting with Retry-After header
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "60")
            logger.warning(f"Rate limited. Retry after {retry_after} seconds")
            # Let the error handler deal with it
            handle_confluence_error(response, operation)

        # Handle error responses
        if not response.ok:
            handle_confluence_error(response, operation)

        # Parse successful response
        if response.status_code == 204:
            return {}

        try:
            return response.json()
        except ValueError:
            # Some endpoints return empty response on success
            if response.status_code in (200, 201, 202):
                return {"success": True, "status_code": response.status_code}
            return {"raw": response.text}

    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        operation: str = "GET request",
    ) -> Dict[str, Any]:
        """
        Perform a GET request.

        Args:
            endpoint: API endpoint path
            params: Query parameters
            operation: Description for error messages

        Returns:
            Parsed JSON response
        """
        url = self._build_url(endpoint)
        logger.debug(f"GET {url} params={params}")

        response = self.session.get(
            url,
            params=params,
            timeout=self.timeout,
            verify=self.verify_ssl,
        )

        return self._handle_response(response, operation)

    def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        operation: str = "POST request",
    ) -> Dict[str, Any]:
        """
        Perform a POST request.

        Args:
            endpoint: API endpoint path
            data: Form data (mutually exclusive with json_data)
            json_data: JSON data to send
            params: Query parameters
            operation: Description for error messages

        Returns:
            Parsed JSON response
        """
        url = self._build_url(endpoint)
        logger.debug(f"POST {url}")

        # Use json_data if provided, otherwise data
        payload = json_data if json_data is not None else data

        response = self.session.post(
            url,
            json=payload,
            params=params,
            timeout=self.timeout,
            verify=self.verify_ssl,
        )

        return self._handle_response(response, operation)

    def put(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        operation: str = "PUT request",
    ) -> Dict[str, Any]:
        """
        Perform a PUT request.

        Args:
            endpoint: API endpoint path
            data: Form data (mutually exclusive with json_data)
            json_data: JSON data to send
            params: Query parameters
            operation: Description for error messages

        Returns:
            Parsed JSON response
        """
        url = self._build_url(endpoint)
        logger.debug(f"PUT {url}")

        payload = json_data if json_data is not None else data

        response = self.session.put(
            url,
            json=payload,
            params=params,
            timeout=self.timeout,
            verify=self.verify_ssl,
        )

        return self._handle_response(response, operation)

    def delete(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        operation: str = "DELETE request",
    ) -> Dict[str, Any]:
        """
        Perform a DELETE request.

        Args:
            endpoint: API endpoint path
            params: Query parameters
            operation: Description for error messages

        Returns:
            Parsed JSON response (usually empty)
        """
        url = self._build_url(endpoint)
        logger.debug(f"DELETE {url}")

        response = self.session.delete(
            url,
            params=params,
            timeout=self.timeout,
            verify=self.verify_ssl,
        )

        return self._handle_response(response, operation)

    def upload_file(
        self,
        endpoint: str,
        file_path: Union[str, Path],
        params: Optional[Dict[str, Any]] = None,
        additional_data: Optional[Dict[str, str]] = None,
        operation: str = "upload file",
    ) -> Dict[str, Any]:
        """
        Upload a file to Confluence.

        Args:
            endpoint: API endpoint path (e.g., /api/v2/pages/12345/attachments)
            file_path: Path to the file to upload
            params: Query parameters
            additional_data: Additional form data to include
            operation: Description for error messages

        Returns:
            Parsed JSON response
        """
        url = self._build_url(endpoint)
        file_path = Path(file_path)

        if not file_path.exists():
            from error_handler import ValidationError
            raise ValidationError(f"File not found: {file_path}")

        logger.debug(f"Uploading file {file_path.name} to {url}")

        # Create multipart form data
        # Need to temporarily remove Content-Type header for file upload
        headers = dict(self.session.headers)
        headers.pop("Content-Type", None)
        headers["X-Atlassian-Token"] = "nocheck"  # Required for file uploads

        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f)}
            data = additional_data or {}

            response = self.session.post(
                url,
                files=files,
                data=data,
                params=params,
                headers=headers,
                timeout=self.timeout * 3,  # Longer timeout for uploads
                verify=self.verify_ssl,
            )

        return self._handle_response(response, operation)

    def download_file(
        self,
        download_url: str,
        output_path: Union[str, Path],
        operation: str = "download file",
    ) -> Path:
        """
        Download a file from Confluence.

        Args:
            download_url: Full URL or relative path to download
            output_path: Local path to save the file
            operation: Description for error messages

        Returns:
            Path to the downloaded file
        """
        # Handle both full URLs and relative paths
        if download_url.startswith("http"):
            url = download_url
        else:
            url = self._build_url(download_url)

        output_path = Path(output_path)
        logger.debug(f"Downloading from {url} to {output_path}")

        response = self.session.get(
            url,
            stream=True,
            timeout=self.timeout * 3,  # Longer timeout for downloads
            verify=self.verify_ssl,
        )

        if not response.ok:
            from error_handler import handle_confluence_error
            handle_confluence_error(response, operation)

        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file in chunks
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return output_path

    def paginate(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        operation: str = "paginated request",
        limit: Optional[int] = None,
        results_key: str = "results",
    ):
        """
        Generator that handles pagination automatically.

        Args:
            endpoint: API endpoint path
            params: Query parameters
            operation: Description for error messages
            limit: Maximum total results to fetch (None for all)
            results_key: Key in response containing results list

        Yields:
            Individual result items
        """
        params = params or {}
        fetched = 0
        cursor = None

        while True:
            if cursor:
                params["cursor"] = cursor

            response = self.get(endpoint, params=params, operation=operation)

            results = response.get(results_key, [])
            for item in results:
                yield item
                fetched += 1

                if limit and fetched >= limit:
                    return

            # Check for next page
            links = response.get("_links", {})
            next_link = links.get("next")

            if not next_link or not results:
                break

            # Extract cursor from next link
            # Next link format: /api/v2/pages?cursor=xxx
            if "cursor=" in next_link:
                cursor = next_link.split("cursor=")[1].split("&")[0]
            else:
                break

    def test_connection(self) -> Dict[str, Any]:
        """
        Test the connection to Confluence.

        Returns:
            Current user information if successful
        """
        try:
            # Try to get current user via v1 API (more reliable for auth test)
            result = self.get(
                "/rest/api/user/current",
                operation="test connection"
            )
            return {
                "success": True,
                "user": result.get("displayName", result.get("username", "Unknown")),
                "email": result.get("email", ""),
                "type": result.get("type", ""),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }


# Convenience function for quick client creation
def create_client(
    base_url: str,
    email: str,
    api_token: str,
    **kwargs
) -> ConfluenceClient:
    """
    Create a Confluence client with the given credentials.

    Args:
        base_url: Confluence Cloud URL
        email: User email
        api_token: API token
        **kwargs: Additional client options

    Returns:
        Configured ConfluenceClient instance
    """
    return ConfluenceClient(
        base_url=base_url,
        email=email,
        api_token=api_token,
        **kwargs
    )
