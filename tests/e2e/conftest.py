"""Pytest configuration and fixtures for E2E tests."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pytest

from .runner import ClaudeCodeRunner, E2ETestRunner


class ResponseLogger:
    """Logs Claude responses for debugging failed tests."""

    def __init__(self, output_dir: Path, enabled: bool = True):
        self.output_dir = output_dir
        self.enabled = enabled
        self.responses: List[Dict[str, Any]] = []
        if enabled:
            self.output_dir.mkdir(parents=True, exist_ok=True)

    def log(self, test_name: str, prompt: str, result: Dict[str, Any]) -> None:
        """Log a response for later analysis."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "test_name": test_name,
            "prompt": prompt,
            "output": result.get("output", ""),
            "error": result.get("error", ""),
            "success": result.get("success", False),
            "exit_code": result.get("exit_code"),
            "duration": result.get("duration"),
        }
        self.responses.append(entry)

        if self.enabled:
            # Write individual response file
            safe_name = test_name.replace("::", "_").replace(" ", "_")[:50]
            response_file = self.output_dir / f"{safe_name}.json"
            with open(response_file, "w") as f:
                json.dump(entry, f, indent=2)

    def save_all(self) -> None:
        """Save all responses to a single file."""
        if self.enabled and self.responses:
            all_responses_file = self.output_dir / "all_responses.json"
            with open(all_responses_file, "w") as f:
                json.dump(self.responses, f, indent=2)


def assert_response_contains(
    result: Dict[str, Any],
    terms: List[str],
    message: str,
    match_any: bool = True
) -> None:
    """
    Assert that response contains expected terms, with helpful error message.

    Args:
        result: The response dict from claude_runner.send_prompt()
        terms: List of terms to search for
        message: Error message prefix
        match_any: If True, pass if ANY term found. If False, ALL must be found.
    """
    output = result.get("output", "").lower()
    error = result.get("error", "").lower()
    combined = f"{output}\n{error}"

    if match_any:
        found = any(term.lower() in combined for term in terms)
    else:
        found = all(term.lower() in combined for term in terms)

    if not found:
        # Build detailed error message
        error_details = [
            f"\n{message}",
            f"\nExpected {'any of' if match_any else 'all of'}: {terms}",
            f"\n\n--- ACTUAL RESPONSE ({len(output)} chars) ---",
            output[:2000] if output else "(empty)",
        ]
        if error:
            error_details.extend([
                "\n\n--- STDERR ---",
                error[:500]
            ])
        error_details.append("\n--- END RESPONSE ---\n")

        assert False, "".join(error_details)


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--e2e-timeout",
        action="store",
        default=os.environ.get("E2E_TEST_TIMEOUT", "120"),
        help="Timeout per test in seconds",
    )
    parser.addoption(
        "--e2e-model",
        action="store",
        default=os.environ.get("E2E_TEST_MODEL", "claude-sonnet-4-20250514"),
        help="Claude model to use",
    )
    parser.addoption(
        "--e2e-verbose",
        action="store_true",
        default=os.environ.get("E2E_VERBOSE", "").lower() == "true",
        help="Enable verbose output",
    )
    parser.addoption(
        "--e2e-save-responses",
        action="store_true",
        default=os.environ.get("E2E_SAVE_RESPONSES", "").lower() == "true",
        help="Save all responses to files for debugging",
    )


@pytest.fixture(scope="session")
def e2e_enabled():
    """Check if E2E tests should run."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    claude_dir = Path.home() / ".claude"

    if api_key:
        return True
    if claude_dir.exists() and (claude_dir / "credentials.json").exists():
        return True
    return False


@pytest.fixture(scope="session")
def project_root():
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent


@pytest.fixture(scope="session")
def test_cases_path(project_root):
    """Get path to test cases YAML."""
    return project_root / "tests" / "e2e" / "test_cases.yaml"


@pytest.fixture(scope="session")
def e2e_timeout(request):
    """Get E2E test timeout."""
    return int(request.config.getoption("--e2e-timeout"))


@pytest.fixture(scope="session")
def e2e_model(request):
    """Get E2E test model."""
    return request.config.getoption("--e2e-model")


@pytest.fixture(scope="session")
def e2e_verbose(request):
    """Get E2E verbosity setting."""
    return request.config.getoption("--e2e-verbose")


@pytest.fixture(scope="session")
def e2e_save_responses(request):
    """Get E2E save responses setting."""
    return request.config.getoption("--e2e-save-responses")


@pytest.fixture(scope="session")
def response_logger(project_root, e2e_save_responses, request):
    """Create response logger for debugging."""
    output_dir = project_root / "tests" / "e2e" / "responses"
    logger = ResponseLogger(output_dir, enabled=e2e_save_responses)

    yield logger

    # Save all responses at end of session
    logger.save_all()


@pytest.fixture(scope="session")
def claude_runner(project_root, e2e_timeout, e2e_model, e2e_verbose, e2e_enabled):
    """Create Claude Code runner."""
    if not e2e_enabled:
        pytest.skip("E2E tests disabled (no API key or OAuth credentials)")

    return ClaudeCodeRunner(
        working_dir=project_root,
        timeout=e2e_timeout,
        model=e2e_model,
        verbose=e2e_verbose,
    )


@pytest.fixture(scope="session")
def e2e_runner(test_cases_path, project_root, e2e_timeout, e2e_model, e2e_verbose, e2e_enabled):
    """Create E2E test runner."""
    if not e2e_enabled:
        pytest.skip("E2E tests disabled (no API key or OAuth credentials)")

    return E2ETestRunner(
        test_cases_path=test_cases_path,
        working_dir=project_root,
        timeout=e2e_timeout,
        model=e2e_model,
        verbose=e2e_verbose,
    )


@pytest.fixture(scope="session")
def installed_plugin(claude_runner, e2e_enabled):
    """Install the plugin once for all tests."""
    if not e2e_enabled:
        pytest.skip("E2E tests disabled")

    result = claude_runner.install_plugin(".")
    if not result["success"] and "already installed" not in result.get("output", "").lower():
        pytest.fail(f"Failed to install plugin: {result.get('error', 'Unknown error')}")

    return result
