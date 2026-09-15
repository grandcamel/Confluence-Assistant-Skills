"""
Shared subprocess-environment builder for the two live harnesses: the
help-only sufficiency arm (tests/e2e/) and the two-skill routing check
(skills/confluence/tests/test_routing.py).

Both harnesses launch the real `claude` binary as a subprocess, and the
sufficiency arm also replays `confluence-as` commands directly. The
environment is built from an ALLOWLIST, not a denylist: copying
os.environ and removing a handful of named credential variables would
still let anything else through unexamined -- another CONFLUENCE_*/
ANTHROPIC_* variable, or an unrelated secret the operator happens to
have exported. Adapted from the jira plugin's own tests/harness_env.py:
see USER/LOGNAME below for a login-lookup finding this module reuses
unchanged.
"""

import os

# The only variables ever copied from the operator's own environment.
# PATH is required to find the `claude` and `confluence-as` binaries at
# all. HOME is required for Claude Code's own authentication, whose
# OAuth credentials live under ~/.claude/ -- without it the subprocess
# cannot authenticate even though nothing Confluence-related is at
# stake. USER and LOGNAME are required for that same authentication: the
# jira sibling harness's live probe found that with only
# PATH/HOME/TERM/LANG set, the CLI reports "Not logged in" -- its
# Keychain-backed login lookup needs USER/LOGNAME to identify the
# account, not just HOME to locate the credentials file.
_REQUIRED_PASSTHROUGH_VARS = ("PATH", "HOME", "USER", "LOGNAME")

# Copied only when present; terminal/locale-sensitive output only, no
# secrets.
_OPTIONAL_PASSTHROUGH_VARS = ("TERM", "LANG")

CONFLUENCE_AS_TRANSPORT_VALUE = "simulation"

# The default simulation seed's one space (`_default_seed()` in
# as-engine's simulation transport ships space DOCS/id 55 with pages 1
# and 2 baked in). Every identity-scoped confluence-as operation (a
# read, a create, a
# delete preview, ...) fails with exit 4 "empty allowlist" unless
# CONFLUENCE_ALLOWED_SPACES is set, even against a page that genuinely
# exists in the store -- this is a required addition the jira sibling
# harness never needed (jira-as has no allowlist-shaped scope gate at
# all), not a rename of anything jira-as's harness already had.
CONFLUENCE_ALLOWED_SPACES_VALUE = "DOCS"

# When set by the operator, its value is prepended to the built PATH
# ahead of everything else, so a scratch confluence-as (e.g. a
# 2.0.0rc1 pre-release venv's bin/, needed until confluence-as 2.0.0
# final ships to PyPI) is what both the model's `claude` invocation and
# the harness's own same-transport replay resolve to -- never whatever
# confluence-as happens to be installed globally on the operator's PATH,
# if any.
HARNESS_CLI_BIN_VAR = "HARNESS_CLI_BIN"


def build_harness_env() -> dict[str, str]:
    """
    Build the environment for a harness subprocess: the model's `claude`
    invocation, and the same-transport replay of any confluence-as
    command it produced.

    Contains exactly: PATH (with HARNESS_CLI_BIN's directory prepended,
    when that variable is set), HOME, USER and LOGNAME (copied from the
    operator's own environment), TERM and LANG (copied only if present),
    CONFLUENCE_AS_TRANSPORT=simulation, and
    CONFLUENCE_ALLOWED_SPACES=DOCS. Never CONFLUENCE_SITE_URL,
    CONFLUENCE_EMAIL, CONFLUENCE_API_TOKEN, ANTHROPIC_API_KEY, or any
    other variable whose name starts with CONFLUENCE_ or ANTHROPIC_ --
    including ones this function does not yet know the name of, which is
    why the allowlist copies only named variables instead of filtering a
    copy of the whole environment.
    """
    env: dict[str, str] = {}

    for name in _REQUIRED_PASSTHROUGH_VARS:
        if name in os.environ:
            env[name] = os.environ[name]

    for name in _OPTIONAL_PASSTHROUGH_VARS:
        if name in os.environ:
            env[name] = os.environ[name]

    cli_bin = os.environ.get(HARNESS_CLI_BIN_VAR)
    if cli_bin:
        env["PATH"] = f"{cli_bin}:{env.get('PATH', '')}"

    env["CONFLUENCE_AS_TRANSPORT"] = CONFLUENCE_AS_TRANSPORT_VALUE
    env["CONFLUENCE_ALLOWED_SPACES"] = CONFLUENCE_ALLOWED_SPACES_VALUE

    # Defense in depth: even though only a fixed allowlist was copied
    # above, assert no credential-shaped variable ever ends up in the
    # built environment, in case a future edit widens the allowlist by
    # mistake. CONFLUENCE_AS_TRANSPORT and CONFLUENCE_ALLOWED_SPACES both
    # start with "CONFLUENCE_" too, so they are named exceptions here --
    # neither is a credential.
    for name in env:
        if name in ("CONFLUENCE_AS_TRANSPORT", "CONFLUENCE_ALLOWED_SPACES"):
            continue
        assert not name.startswith("CONFLUENCE_") and not name.startswith(
            "ANTHROPIC_"
        ), f"build_harness_env leaked a credential-shaped variable: {name}"

    return env
