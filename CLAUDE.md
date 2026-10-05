# Confluence Assistant Skills -- Development Guide

This repository ships a single Claude Code plugin: one skill
(`skills/confluence/SKILL.md`) holding the Entry-Point Hint for the
`confluence-as` CLI (2.x), plus the manifests and tests that back it.
There is no application code here -- the CLI itself lives in the
separate `confluence-as` PyPI package.

## Layout

```
.claude-plugin/
  plugin.json           # Plugin manifest (name, version, description)
  marketplace.json       # This repo's own copy of the marketplace entry
skills/
  confluence/
    SKILL.md             # The Entry-Point Hint (the whole shipped skill)
    tests/                # The two-skill routing check (host-run only)
tests/
  harness_env.py          # Shared allowlist env builder for both live harnesses
  evidence.py              # Shared run-dir/transcript/summary writer
  stream_observe.py        # Shared incremental subprocess reader
  test_*.py                 # Offline unit tests for the harness code above
  e2e/                       # The help-only sufficiency arm (host-run only)
  fixtures/jira-stub/        # Non-shipped fixture plugin for the routing check
  floor_eval/                 # Pointer to the shared floor-eval job (see below)
VERSION, .release-please-manifest.json, pyproject.toml,
.claude-plugin/plugin.json, .claude-plugin/marketplace.json
                                # Five version sites; a consistency test
                                # asserts they all agree
CHANGELOG.md                    # Release history (the only file where a
                                 # ticket key from this organization's
                                 # tracker may appear)
```

## The two live harnesses

Both launch the real Claude Code CLI, spend real tokens, and are never
run in CI (`.github/workflows/ci.yml` deselects both test modules). They
are host-triggered, the same way a release check would be:

- **Help-only sufficiency arm** (`tests/e2e/`, opt-in via
  `E2E_SUFFICIENCY=1`): drives Claude Code with only the shipped plugin,
  the Bash and Skill tools, and `confluence-as` on `PATH` forced into
  its `simulation` transport with no credentials. See
  `tests/e2e/README.md`.
- **Two-skill routing check** (`skills/confluence/tests/test_routing.py`,
  marked `live`): drives Claude Code with this plugin and a non-shipped
  fixture plugin both installed, and observes which skill (if either)
  loads for a set of prompts.

Both share `tests/harness_env.py`'s allowlist-based environment builder
(never a denylist) and `tests/evidence.py`'s run-directory/transcript
writer. Set `HARNESS_CLI_BIN` to a scratch venv's `bin/` directory to
point either harness at a `confluence-as` build other than whatever is
on the operator's own `PATH` -- see the next section for why that
scratch venv currently has to exist.

## The reviewed confluence-as CLI

Host harnesses must use the exact product wheel from the reviewed build
packet. Install it into a scratch venv after checking its SHA256 and set
`HARNESS_CLI_BIN` to that venv's `bin/` directory. The offline suite does
not need the CLI installed: it uses local fixtures only.

## CI

CI and release validation require repository variables
`CONFLUENCE_CLI_WHEEL_URL` and `CONFLUENCE_CLI_WHEEL_SHA256` from the reviewed
product build packet. `tests/release_checks.py` rejects missing bindings,
wrong digests, wrong product names and wrong major versions before installation.
Validation installs the verified product wheel directly, checks dependencies,
collects both paid modules without executing them, inspects packaging, and runs:

```bash
python -m pytest -q --deselect skills/confluence/tests/test_routing.py --deselect tests/e2e/test_plugin_e2e.py
ruff check .
ruff format --check .
```

The remaining CI jobs retain their existing advisory role. `ci-success`
requires successful lint and test jobs, including refusing skipped jobs.
No workflow invokes the `claude` binary.

## Release policy

Every present version field must equal `3.0.0`: `VERSION`,
`.release-please-manifest.json`, `pyproject.toml`,
`.claude-plugin/plugin.json`, the adopted skill's frontmatter, and both
`.claude-plugin/marketplace.json` fields. The dependency remains
`confluence-as>=2,<3`. Preserve the adopted skill when preparing packaging.

Main pushes cannot start release-please, create a release, or update the
marketplace. Close the superseded release-please proposal separately after
review; its historical configuration is retained but no workflow runs it.

Before any dispatch, configure required reviewers and main-only restrictions
for the separate `plugin-release` and `marketplace-review` environments.
These settings are an operator prerequisite; YAML cannot configure reviewers.
Complete product, paid sufficiency/routing, and Knowledge Floor acceptance
before approving publication. Offline validation alone does not satisfy them.

Dispatch `release.yml` on `main` with the full reviewed `candidate_sha`.
Its default `publish=false` validates only. Explicit `publish=true` and the
`plugin-release` environment approval permit the validated archive to be
released as `v3.0.0`; an existing tag or release must not be replaced.
`tests/release_checks.py` creates a reproducible archive containing only the
manifests, adopted skill, README, VERSION and license, never the harnesses.

Dispatch `sync-marketplace.yml` separately with the full reviewed
`candidate_sha` and approve the `marketplace-review` environment. It creates
an update PR in `as-plugins` for human review and never auto-merges it.
A changed product description still needs a separately reviewed update.
Release and marketplace dispatches do not authorize promotion.

### Before each plugin release

Run the shared Knowledge Floor job on a host with authenticated headless
`claude` and `codex` CLIs, and again whenever a fleet-wide model-policy
change alters the floor models or judge. The driver and its full fact
inventory live in a sibling `JIRA-Assistant-Skills` checkout's
`tests/floor_eval/`; see [the job pointer](tests/floor_eval/README.md)
for the exact invocation. This is host-run, never in GitHub Actions:
runners do not have the required CLIs or model credentials, and no
Atlassian site credentials are used by the evaluator.

## Instance-fact discipline

Nothing in this plugin -- the skill, the manifests, `README.md`, or this
file -- names a ticket key, an internal host name, or any other fact
specific to this organization, with one exception: `CHANGELOG.md` may
cite the ticket that produced a release, as release history.
`tests/test_consistency.py` enforces this, along with the "no
confluence-as flag or concept word outside the harness code and test
fixtures" rule the skill and these two files are also held to.
