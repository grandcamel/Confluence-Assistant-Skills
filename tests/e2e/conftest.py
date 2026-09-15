"""Pytest configuration and fixtures for the help-only sufficiency arm.

The sufficiency arm answers: is the Entry-Point Hint alone
(skills/confluence/SKILL.md, shipped via the plugin manifest) enough for
a model to complete representative confluence-as tasks? The model under
test gets nothing else: no other skill, no tool besides Bash and Skill
(Skill is required to load the plugin's SKILL.md at all -- see
runner.py), no project context from this repository, and a
`confluence-as` on PATH forced into its `simulation` transport with
`CONFLUENCE_ALLOWED_SPACES=DOCS` and no credentials in the environment,
so nothing it runs can reach a live site.

This arm launches the real `claude` binary and spends real tokens, so it
never runs silently: it requires the explicit E2E_SUFFICIENCY=1 opt-in
(see `_sufficiency_gate` below), rather than inferring "enabled" from
whatever credentials happen to be present. Adapted from the jira
plugin's own tests/e2e/conftest.py.
"""

import os
import re
import subprocess
import tempfile
from pathlib import Path

import pytest

from tests.harness_env import build_harness_env

from .runner import EMPTY_MCP_CONFIG, SufficiencyRunner

DEFAULT_MODEL = "claude-sonnet-5"

# Explicit opt-in required to run this arm at all. Do NOT infer "enabled"
# from ANTHROPIC_API_KEY or ~/.claude/credentials.json: a `claude auth
# login` keeps OAuth credentials in the system keychain, which would
# otherwise make the arm look "enabled" and skip silently through some
# other path, with no visible signal in a test run.
E2E_SUFFICIENCY_VAR = "E2E_SUFFICIENCY"

# The scratch confluence-as this harness requires: only the 2.0.0rc1
# pre-release is on PyPI as of this writing (2.0.0 final has not
# shipped), so this checks the major version only, not an exact match.
_VERSION_RE = re.compile(r"\bversion\s+2\.")


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--sufficiency-timeout",
        action="store",
        default=os.environ.get("SUFFICIENCY_TEST_TIMEOUT", "120"),
        help="Timeout per trial in seconds",
    )
    parser.addoption(
        "--sufficiency-model",
        action="store",
        default=os.environ.get("SUFFICIENCY_TEST_MODEL", DEFAULT_MODEL),
        help="Claude model to use for the sufficiency arm",
    )


@pytest.fixture(scope="session")
def e2e_enabled():
    """
    Whether the sufficiency arm should run for real -- gated on the
    explicit E2E_SUFFICIENCY=1 opt-in only. See the module docstring for
    why this is not inferred from ambient credentials.
    """
    return os.environ.get(E2E_SUFFICIENCY_VAR) == "1"


@pytest.fixture(scope="session")
def harness_env():
    """
    The environment the model's Claude Code process (and every
    confluence-as invocation re-run from its transcript) executes under.
    Built once per session so the gate below and the runner fixture
    share exactly the same PATH (including any HARNESS_CLI_BIN prefix).
    """
    return build_harness_env()


@pytest.fixture(scope="session", autouse=True)
def _sufficiency_gate(request, e2e_enabled, harness_env):
    """
    Never let the arm run silently, and never let it run against a
    broken or wrong-version toolchain.

    Without E2E_SUFFICIENCY=1, every test in this directory is skipped
    with a loud reason naming the variable -- not a quiet pass. With the
    variable set, this probes `claude --version` and `confluence-as
    --version` once per session (on the SAME built environment/PATH the
    trials themselves use, so HARNESS_CLI_BIN is honored) and FAILS (not
    skips) if either binary is missing, times out, errors, or --for
    confluence-as-- does not report a 2.x version: an operator who
    explicitly opted in asked for a real run, and a missing, broken, or
    mismatched-version CLI is a setup defect, not something to quietly
    skip past. Auth absence is likewise never silently skipped: one
    authenticated one-turn `claude --print` probe runs here, on the same
    built environment, and FAILS on a nonzero exit, so an unauthenticated
    host is reported before any trial is scored.
    """
    if not e2e_enabled:
        pytest.skip(
            f"Sufficiency arm disabled: set {E2E_SUFFICIENCY_VAR}=1 to run "
            "it (it launches the real `claude` binary and spends real "
            "tokens)."
        )

    try:
        probe = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=30,
            env=harness_env,
        )
    except FileNotFoundError:
        pytest.fail(
            f"{E2E_SUFFICIENCY_VAR}=1 was set but the `claude` binary is "
            "not on PATH; install/authenticate Claude Code before running "
            "the sufficiency arm."
        )
    except subprocess.TimeoutExpired:
        pytest.fail(
            f"{E2E_SUFFICIENCY_VAR}=1 was set but `claude --version` did "
            "not respond within 30s."
        )

    if probe.returncode != 0:
        pytest.fail(
            f"{E2E_SUFFICIENCY_VAR}=1 was set but `claude --version` "
            f"exited {probe.returncode}: {probe.stderr.strip()[:500]}"
        )

    model = request.config.getoption("--sufficiency-model")
    with tempfile.TemporaryDirectory(prefix="sufficiency-auth-probe-") as probe_cwd:
        try:
            auth_probe = subprocess.run(
                [
                    "claude",
                    "--print",
                    "--model",
                    model,
                    "--max-turns",
                    "1",
                    "--strict-mcp-config",
                    "--mcp-config",
                    str(EMPTY_MCP_CONFIG),
                    "Reply with the single word OK.",
                ],
                capture_output=True,
                text=True,
                timeout=120,
                env=harness_env,
                cwd=probe_cwd,
            )
        except subprocess.TimeoutExpired:
            pytest.fail(
                f"{E2E_SUFFICIENCY_VAR}=1 was set but the authenticated "
                "`claude --print` probe did not respond within 120s."
            )
    if auth_probe.returncode != 0:
        detail = (auth_probe.stderr or auth_probe.stdout).strip()[:500]
        pytest.fail(
            f"{E2E_SUFFICIENCY_VAR}=1 was set but `claude` cannot complete an "
            f"authenticated request (exit {auth_probe.returncode}): {detail} "
            "-- log in to Claude Code on this host (the harness passes only "
            "PATH, HOME, USER and LOGNAME through) before running the "
            "sufficiency arm."
        )

    try:
        cas_probe = subprocess.run(
            ["confluence-as", "--version"],
            capture_output=True,
            text=True,
            timeout=30,
            env=harness_env,
        )
    except FileNotFoundError:
        pytest.fail(
            f"{E2E_SUFFICIENCY_VAR}=1 was set but `confluence-as` is not "
            "on the harness PATH; set HARNESS_CLI_BIN to a scratch venv's "
            "bin/ (see tests/harness_env.py) or install confluence-as>=2,<3."
        )
    except subprocess.TimeoutExpired:
        pytest.fail(
            f"{E2E_SUFFICIENCY_VAR}=1 was set but `confluence-as "
            "--version` did not respond within 30s."
        )

    if cas_probe.returncode != 0:
        pytest.fail(
            f"{E2E_SUFFICIENCY_VAR}=1 was set but `confluence-as "
            f"--version` exited {cas_probe.returncode}: "
            f"{cas_probe.stderr.strip()[:500]}"
        )

    version_output = cas_probe.stdout + cas_probe.stderr
    if not _VERSION_RE.search(version_output):
        pytest.fail(
            f"{E2E_SUFFICIENCY_VAR}=1 was set but confluence-as on the "
            "harness PATH did not report a 2.x version (only 2.0.0rc1 "
            f"is on PyPI as a pre-release until 2.0.0 final ships): "
            f"{version_output!r}"
        )


@pytest.fixture(scope="session")
def repo_root():
    """The shipped plugin's own directory: manifest + skills/confluence/SKILL.md."""
    return Path(__file__).parent.parent.parent


@pytest.fixture(scope="session")
def test_cases_path(repo_root):
    """Path to the seven representative tasks."""
    return repo_root / "tests" / "e2e" / "test_cases.yaml"


@pytest.fixture(scope="session")
def sufficiency_timeout(request):
    return int(request.config.getoption("--sufficiency-timeout"))


@pytest.fixture(scope="session")
def sufficiency_model(request):
    return request.config.getoption("--sufficiency-model")


@pytest.fixture(scope="session")
def simulation_env(harness_env):
    """
    The environment the model's Claude Code process (and every
    confluence-as invocation re-run from its transcript) executes under.
    Built by the shared tests/harness_env.py allowlist (also used by the
    routing check), not by denylisting a copy of the whole environment:
    only PATH (with HARNESS_CLI_BIN prepended when set), HOME, USER,
    LOGNAME, TERM and LANG (the last two if present) are ever copied,
    plus CONFLUENCE_AS_TRANSPORT forced to simulation and
    CONFLUENCE_ALLOWED_SPACES forced to DOCS, so confluence-as never
    dials out to a live site regardless of what it's told, and every
    identity-scoped operation can actually resolve against the
    simulation store's default seed.
    """
    return harness_env


@pytest.fixture(scope="session")
def sufficiency_runner(
    repo_root,
    sufficiency_timeout,
    sufficiency_model,
    simulation_env,
    _sufficiency_gate,
):
    """
    Build the runner that drives Claude Code with ONLY the shipped plugin
    (skills/confluence/SKILL.md) and the Bash and Skill tools installed.
    Depending on `_sufficiency_gate` guarantees the opt-in/probes run
    first.
    """
    return SufficiencyRunner(
        plugin_dir=repo_root,
        timeout=sufficiency_timeout,
        model=sufficiency_model,
        env=simulation_env,
    )
