"""
Confluence Container Management for Live Integration Tests

Thread-safe singleton pattern for sharing Docker containers across test sessions.
Supports both Docker-based testing and external Confluence instances.

Environment Variables:
    CONFLUENCE_TEST_URL: External Confluence URL (skips Docker)
    CONFLUENCE_TEST_EMAIL: Email for external Confluence
    CONFLUENCE_TEST_TOKEN: API token for external Confluence
    CONFLUENCE_TEST_IMAGE: Docker image (default: atlassian/confluence)
    CONFLUENCE_TEST_LICENSE: Confluence license key (required for Docker)
    CONFLUENCE_TEST_ADMIN_USER: Admin username (default: admin)
    CONFLUENCE_TEST_ADMIN_PASSWORD: Admin password (default: admin)
    CONFLUENCE_TEST_STARTUP_TIMEOUT: Startup timeout in seconds (default: 300)
    CONFLUENCE_TEST_MEM_LIMIT: Container memory limit (default: 4g)

Usage:
    from confluence_container import get_confluence_connection

    connection = get_confluence_connection()
    connection.start()

    client = connection.get_client()
    # ... run tests ...

    connection.stop()
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from confluence_assistant_skills_lib import ConfluenceClient

logger = logging.getLogger(__name__)

# =============================================================================
# Singleton Pattern with Double-Checked Locking
# =============================================================================

_shared_container: Optional["ConfluenceConnection"] = None
_container_lock = threading.Lock()


def get_confluence_connection() -> "ConfluenceConnection":
    """
    Get the shared Confluence connection (singleton).

    Uses double-checked locking for thread safety with pytest-xdist.

    Returns:
        ConfluenceConnection instance (either Docker or external)
    """
    global _shared_container

    if _shared_container is None:
        with _container_lock:
            if _shared_container is None:  # Double-check inside lock
                # Check for external Confluence configuration
                if os.environ.get("CONFLUENCE_TEST_URL"):
                    _shared_container = ExternalConfluenceConnection()
                else:
                    _shared_container = DockerConfluenceContainer()

    return _shared_container


def reset_confluence_connection() -> None:
    """Reset the shared connection (for testing purposes)."""
    global _shared_container
    with _container_lock:
        if _shared_container is not None:
            _shared_container.stop()
            _shared_container = None


# =============================================================================
# Connection Info Data Class
# =============================================================================

@dataclass
class ConnectionInfo:
    """Information about a Confluence connection."""
    base_url: str
    email: str
    api_token: str
    is_docker: bool
    container_id: Optional[str] = None

    def as_dict(self) -> dict[str, Any]:
        """Convert to dictionary for client initialization."""
        return {
            "base_url": self.base_url,
            "email": self.email,
            "api_token": self.api_token,
        }


# =============================================================================
# Base Connection Class
# =============================================================================

class ConfluenceConnection:
    """Base class for Confluence connections."""

    def __init__(self):
        self._lock = threading.Lock()
        self._ref_count = 0
        self._is_started = False
        self._connection_info: Optional[ConnectionInfo] = None
        self._client: Optional["ConfluenceClient"] = None

    def start(self) -> "ConfluenceConnection":
        """Start the connection (thread-safe with reference counting)."""
        with self._lock:
            self._ref_count += 1
            if self._is_started:
                logger.debug(f"Reusing existing connection (ref_count={self._ref_count})")
                return self

            logger.info("Starting Confluence connection...")
            self._do_start()
            self._is_started = True
            logger.info("Confluence connection started")
            return self

    def stop(self) -> None:
        """Stop the connection (thread-safe with reference counting)."""
        with self._lock:
            if self._ref_count > 0:
                self._ref_count -= 1

            if self._ref_count > 0:
                logger.debug(f"Connection still in use (ref_count={self._ref_count})")
                return

            if not self._is_started:
                return

            logger.info("Stopping Confluence connection...")
            self._do_stop()
            self._is_started = False
            self._client = None
            logger.info("Confluence connection stopped")

    def _do_start(self) -> None:
        """Implementation-specific start logic."""
        raise NotImplementedError

    def _do_stop(self) -> None:
        """Implementation-specific stop logic."""
        raise NotImplementedError

    def get_connection_info(self) -> ConnectionInfo:
        """Get connection information."""
        if not self._is_started or self._connection_info is None:
            raise RuntimeError("Connection not started")
        return self._connection_info

    def get_client(self) -> "ConfluenceClient":
        """Get a configured ConfluenceClient."""
        if not self._is_started:
            raise RuntimeError("Connection not started")

        if self._client is None:
            from confluence_assistant_skills_lib import ConfluenceClient
            info = self.get_connection_info()
            self._client = ConfluenceClient(**info.as_dict())

        return self._client

    @property
    def is_started(self) -> bool:
        """Check if connection is started."""
        return self._is_started

    @property
    def ref_count(self) -> int:
        """Get current reference count."""
        return self._ref_count


# =============================================================================
# External Confluence Connection
# =============================================================================

class ExternalConfluenceConnection(ConfluenceConnection):
    """Connection to an external Confluence instance (Cloud or Server)."""

    def _do_start(self) -> None:
        """Configure connection from environment variables."""
        base_url = os.environ.get("CONFLUENCE_TEST_URL")
        email = os.environ.get("CONFLUENCE_TEST_EMAIL")
        api_token = os.environ.get("CONFLUENCE_TEST_TOKEN")

        if not all([base_url, email, api_token]):
            missing = []
            if not base_url:
                missing.append("CONFLUENCE_TEST_URL")
            if not email:
                missing.append("CONFLUENCE_TEST_EMAIL")
            if not api_token:
                missing.append("CONFLUENCE_TEST_TOKEN")
            raise ValueError(f"Missing environment variables: {', '.join(missing)}")

        self._connection_info = ConnectionInfo(
            base_url=base_url,
            email=email,
            api_token=api_token,
            is_docker=False,
        )

        # Verify connection
        self._verify_connection()
        logger.info(f"Connected to external Confluence: {base_url}")

    def _do_stop(self) -> None:
        """No cleanup needed for external connection."""
        pass

    def _verify_connection(self) -> None:
        """Verify the connection works."""
        client = self.get_client()
        result = client.test_connection()
        if not result.get("success"):
            raise RuntimeError(f"Failed to connect to Confluence: {result.get('error')}")


# =============================================================================
# Docker Container Connection
# =============================================================================

class DockerConfluenceContainer(ConfluenceConnection):
    """
    Docker-based Confluence container for testing.

    Uses reference counting to share a single container across multiple test sessions.
    Implements dual-phase health check for reliable startup detection.
    """

    # Default configuration
    DEFAULT_IMAGE = "atlassian/confluence"
    DEFAULT_ADMIN_USER = "admin"
    DEFAULT_ADMIN_PASSWORD = "admin"
    DEFAULT_STARTUP_TIMEOUT = 300
    DEFAULT_HEALTH_INTERVAL = 5
    DEFAULT_MEM_LIMIT = "4g"

    def __init__(self):
        super().__init__()
        self._container = None
        self._container_id: Optional[str] = None

    def _do_start(self) -> None:
        """Start the Docker container."""
        try:
            from testcontainers.core.container import DockerContainer
            from testcontainers.core.waiting_utils import wait_for_logs
        except ImportError as e:
            raise ImportError(
                "testcontainers package required for Docker-based testing. "
                "Install with: pip install testcontainers[docker]"
            ) from e

        # Get configuration from environment
        image = os.environ.get("CONFLUENCE_TEST_IMAGE", self.DEFAULT_IMAGE)
        license_key = os.environ.get("CONFLUENCE_TEST_LICENSE")
        admin_user = os.environ.get("CONFLUENCE_TEST_ADMIN_USER", self.DEFAULT_ADMIN_USER)
        admin_password = os.environ.get("CONFLUENCE_TEST_ADMIN_PASSWORD", self.DEFAULT_ADMIN_PASSWORD)
        startup_timeout = int(os.environ.get("CONFLUENCE_TEST_STARTUP_TIMEOUT", self.DEFAULT_STARTUP_TIMEOUT))
        mem_limit = os.environ.get("CONFLUENCE_TEST_MEM_LIMIT", self.DEFAULT_MEM_LIMIT)

        if not license_key:
            raise ValueError(
                "CONFLUENCE_TEST_LICENSE environment variable required for Docker testing. "
                "Get a free developer license at: https://my.atlassian.com/license/evaluation"
            )

        logger.info(f"Starting Confluence container with image: {image}")

        # Create and configure container
        self._container = (
            DockerContainer(image)
            .with_exposed_ports(8090, 8091)
            .with_env("ATL_LICENSE_KEY", license_key)
            .with_env("ATL_ADMIN_USER", admin_user)
            .with_env("ATL_ADMIN_PASSWORD", admin_password)
            .with_env("JVM_MINIMUM_MEMORY", "1024m")
            .with_env("JVM_MAXIMUM_MEMORY", "2048m")
            .with_kwargs(mem_limit=mem_limit)
        )

        # Start container
        self._container.start()
        self._container_id = self._container.get_wrapped_container().id

        logger.info(f"Container started: {self._container_id[:12]}")

        # Dual-phase health check
        self._wait_for_startup(startup_timeout)

        # Get connection details
        host = self._container.get_container_host_ip()
        port = self._container.get_exposed_port(8090)

        self._connection_info = ConnectionInfo(
            base_url=f"http://{host}:{port}",
            email=admin_user,
            api_token=admin_password,
            is_docker=True,
            container_id=self._container_id,
        )

        logger.info(f"Confluence ready at: http://{host}:{port}")

    def _do_stop(self) -> None:
        """Stop and remove the Docker container."""
        if self._container is not None:
            try:
                self._container.stop()
                logger.info(f"Container stopped: {self._container_id[:12] if self._container_id else 'unknown'}")
            except Exception as e:
                logger.warning(f"Error stopping container: {e}")
            finally:
                self._container = None
                self._container_id = None

    def _wait_for_startup(self, timeout: int) -> None:
        """
        Dual-phase health check for container startup.

        Phase 1: Wait for Ansible playbook completion in logs
        Phase 2: Verify REST API responds
        """
        health_interval = int(os.environ.get("CONFLUENCE_TEST_HEALTH_INTERVAL", self.DEFAULT_HEALTH_INTERVAL))
        start_time = time.time()

        logger.info("Phase 1: Waiting for Ansible playbook completion...")

        # Phase 1: Wait for log message indicating startup
        # Atlassian containers use Ansible for setup
        startup_markers = [
            "Ansible playbook complete",
            "Confluence started",
            "Server startup in",
            "Application ready",
        ]

        while time.time() - start_time < timeout:
            try:
                logs = self._container.get_logs()[0].decode("utf-8", errors="replace")

                for marker in startup_markers:
                    if marker.lower() in logs.lower():
                        logger.info(f"Found startup marker: '{marker}'")
                        break
                else:
                    time.sleep(health_interval)
                    continue
                break
            except Exception as e:
                logger.debug(f"Error reading logs: {e}")
                time.sleep(health_interval)
        else:
            raise TimeoutError(f"Container startup timeout after {timeout}s (Phase 1)")

        # Phase 2: Verify REST API responds
        logger.info("Phase 2: Verifying REST API...")

        host = self._container.get_container_host_ip()
        port = self._container.get_exposed_port(8090)
        admin_user = os.environ.get("CONFLUENCE_TEST_ADMIN_USER", self.DEFAULT_ADMIN_USER)
        admin_password = os.environ.get("CONFLUENCE_TEST_ADMIN_PASSWORD", self.DEFAULT_ADMIN_PASSWORD)

        import requests

        api_url = f"http://{host}:{port}/wiki/rest/api/user/current"

        while time.time() - start_time < timeout:
            try:
                response = requests.get(
                    api_url,
                    auth=(admin_user, admin_password),
                    timeout=10,
                )

                if response.status_code == 200:
                    logger.info("REST API responding successfully")
                    return
                elif response.status_code == 401:
                    logger.debug("API returned 401, waiting for auth setup...")
                else:
                    logger.debug(f"API returned {response.status_code}, waiting...")
            except requests.exceptions.ConnectionError:
                logger.debug("Connection refused, waiting...")
            except requests.exceptions.Timeout:
                logger.debug("Request timeout, waiting...")
            except Exception as e:
                logger.debug(f"Health check error: {e}")

            time.sleep(health_interval)

        raise TimeoutError(f"Container startup timeout after {timeout}s (Phase 2)")

    def get_logs(self, tail: int = 100) -> str:
        """Get container logs."""
        if self._container is None:
            return ""
        try:
            stdout, stderr = self._container.get_logs()
            combined = stdout.decode("utf-8", errors="replace")
            lines = combined.split("\n")
            return "\n".join(lines[-tail:])
        except Exception as e:
            return f"Error retrieving logs: {e}"


# =============================================================================
# Pytest Integration
# =============================================================================

def pytest_configure_confluence_container(config) -> None:
    """
    Configure pytest for Confluence container testing.

    Call this from conftest.py pytest_configure hook.
    """
    # Register markers
    config.addinivalue_line("markers", "docker_required: mark test as requiring Docker")
    config.addinivalue_line("markers", "external_confluence: mark test as requiring external Confluence")
    config.addinivalue_line("markers", "skip_on_docker: skip test when using Docker container")
    config.addinivalue_line("markers", "skip_on_external: skip test when using external Confluence")


def should_skip_test(connection: ConfluenceConnection, marker: str) -> tuple[bool, str]:
    """
    Check if a test should be skipped based on connection type.

    Args:
        connection: The active Confluence connection
        marker: The marker to check (docker_required, external_confluence, etc.)

    Returns:
        Tuple of (should_skip, reason)
    """
    info = connection.get_connection_info()

    if marker == "docker_required" and not info.is_docker:
        return True, "Test requires Docker container (CONFLUENCE_TEST_URL is set)"

    if marker == "external_confluence" and info.is_docker:
        return True, "Test requires external Confluence (using Docker container)"

    if marker == "skip_on_docker" and info.is_docker:
        return True, "Test skipped on Docker container"

    if marker == "skip_on_external" and not info.is_docker:
        return True, "Test skipped on external Confluence"

    return False, ""


# Alias for backward compatibility with __init__.py exports
ConfluenceContainer = DockerConfluenceContainer
