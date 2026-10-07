"""Pytest configuration for routing tests.

Copied from the jira sibling plugin's skills/jira/tests/conftest.py:
only the model-config plumbing (get_test_model), nothing product- or
telemetry-specific.
"""

import pytest


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--model",
        action="store",
        default=None,
        help="Claude model to use (e.g., 'haiku' for fast iteration, 'sonnet' for production)",
    )


# Module-level config storage for access from test_routing.py
_test_config: dict[str, str | None] = {}


@pytest.fixture(scope="session", autouse=True)
def _store_test_config(request):
    """Store test config for module-level access."""
    _test_config["model"] = request.config.getoption("--model")
    yield
    _test_config.clear()


def get_test_model() -> str | None:
    """Get the configured model for tests. Called from test_routing.py."""
    return _test_config.get("model")
