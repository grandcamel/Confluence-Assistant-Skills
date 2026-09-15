"""
Offline unit tests for tests/harness_env.py's build_harness_env(). No
subprocess is launched anywhere in this file.
"""

from tests.harness_env import build_harness_env


def test_present_keys_are_copied_and_transport_and_scope_are_forced(monkeypatch):
    """PATH, HOME, USER, LOGNAME, TERM and LANG, when present, are copied
    verbatim, and CONFLUENCE_AS_TRANSPORT/CONFLUENCE_ALLOWED_SPACES are
    always forced."""
    monkeypatch.delenv("HARNESS_CLI_BIN", raising=False)
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    monkeypatch.setenv("HOME", "/home/operator")
    monkeypatch.setenv("USER", "operator")
    monkeypatch.setenv("LOGNAME", "operator")
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.setenv("LANG", "en_US.UTF-8")

    env = build_harness_env()

    assert env["PATH"] == "/usr/bin:/bin"
    assert env["HOME"] == "/home/operator"
    assert env["USER"] == "operator"
    assert env["LOGNAME"] == "operator"
    assert env["TERM"] == "xterm-256color"
    assert env["LANG"] == "en_US.UTF-8"
    assert env["CONFLUENCE_AS_TRANSPORT"] == "simulation"
    assert env["CONFLUENCE_ALLOWED_SPACES"] == "DOCS"
    assert len(env) == 8, f"unexpected extra keys leaked through: {env}"


def test_absent_optional_keys_are_omitted_and_credentials_never_pass_through(
    monkeypatch,
):
    """
    TERM/LANG are simply omitted when absent (no KeyError). Credential
    variables -- named ones, and anything else starting with
    CONFLUENCE_ or ANTHROPIC_ -- never appear in the built environment
    even when set in the calling process's own environment.
    """
    monkeypatch.delenv("HARNESS_CLI_BIN", raising=False)
    monkeypatch.setenv("PATH", "/usr/bin")
    monkeypatch.setenv("HOME", "/home/operator")
    monkeypatch.setenv("USER", "operator")
    monkeypatch.setenv("LOGNAME", "operator")
    monkeypatch.delenv("TERM", raising=False)
    monkeypatch.delenv("LANG", raising=False)

    # Credentials and lookalikes that must never leak through -- including
    # the exact three names the operator's own shell carries in this
    # repository's environment (CONFLUENCE_SITE_URL, CONFLUENCE_EMAIL,
    # CONFLUENCE_API_TOKEN).
    monkeypatch.setenv("CONFLUENCE_SITE_URL", "https://example.atlassian.net")
    monkeypatch.setenv("CONFLUENCE_EMAIL", "operator@example.com")
    monkeypatch.setenv("CONFLUENCE_API_TOKEN", "secret-token")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-secret")
    monkeypatch.setenv("CONFLUENCE_SOME_FUTURE_VAR", "should-never-appear")
    monkeypatch.setenv("ANTHROPIC_SOME_FUTURE_VAR", "should-never-appear")

    env = build_harness_env()

    assert "TERM" not in env
    assert "LANG" not in env
    assert env["PATH"] == "/usr/bin"
    assert env["HOME"] == "/home/operator"
    assert env["USER"] == "operator"
    assert env["LOGNAME"] == "operator"
    assert env["CONFLUENCE_AS_TRANSPORT"] == "simulation"
    assert env["CONFLUENCE_ALLOWED_SPACES"] == "DOCS"

    for leaked in (
        "CONFLUENCE_SITE_URL",
        "CONFLUENCE_EMAIL",
        "CONFLUENCE_API_TOKEN",
        "ANTHROPIC_API_KEY",
        "CONFLUENCE_SOME_FUTURE_VAR",
        "ANTHROPIC_SOME_FUTURE_VAR",
    ):
        assert leaked not in env, f"{leaked} leaked into the harness environment"

    assert len(env) == 6, f"unexpected extra keys leaked through: {env}"


def test_harness_cli_bin_prepends_path(monkeypatch):
    """When HARNESS_CLI_BIN is set, its value is prepended to the built
    PATH, so a scratch confluence-as (e.g. a pre-release venv's bin/)
    is what both the model's `claude` invocation and the harness's own
    replay resolve to first."""
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    monkeypatch.setenv("HOME", "/home/operator")
    monkeypatch.setenv("USER", "operator")
    monkeypatch.setenv("LOGNAME", "operator")
    monkeypatch.setenv("HARNESS_CLI_BIN", "/scratch/venv/bin")

    env = build_harness_env()

    assert env["PATH"] == "/scratch/venv/bin:/usr/bin:/bin"


def test_no_credential_shaped_variable_ever_appears_even_with_harness_cli_bin(
    monkeypatch,
):
    """The operator's shell for this repository always exports
    CONFLUENCE_SITE_URL, CONFLUENCE_EMAIL and CONFLUENCE_API_TOKEN; this
    proves the built environment lacks all three even when
    HARNESS_CLI_BIN is also set (the two features are independent)."""
    monkeypatch.setenv("PATH", "/usr/bin")
    monkeypatch.setenv("HOME", "/home/operator")
    monkeypatch.setenv("USER", "operator")
    monkeypatch.setenv("LOGNAME", "operator")
    monkeypatch.setenv("HARNESS_CLI_BIN", "/scratch/venv/bin")
    monkeypatch.setenv("CONFLUENCE_SITE_URL", "https://example.atlassian.net")
    monkeypatch.setenv("CONFLUENCE_EMAIL", "operator@example.com")
    monkeypatch.setenv("CONFLUENCE_API_TOKEN", "secret-token")

    env = build_harness_env()

    assert "CONFLUENCE_SITE_URL" not in env
    assert "CONFLUENCE_EMAIL" not in env
    assert "CONFLUENCE_API_TOKEN" not in env
    assert env["PATH"] == "/scratch/venv/bin:/usr/bin"
