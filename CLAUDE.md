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

## The scratch confluence-as CLI

`confluence-as` 2.0.0 final is not on PyPI yet -- only the `2.0.0rc1`
pre-release is. Until it ships:

```bash
python3 -m venv ~/.venvs/confluence-as-2.0.0rc1
~/.venvs/confluence-as-2.0.0rc1/bin/pip install --pre "confluence-as==2.0.0rc1" pytest pytest-asyncio pytest-cov pyyaml
export HARNESS_CLI_BIN=~/.venvs/confluence-as-2.0.0rc1/bin
```

The offline suite itself does not need the CLI installed at all -- no
test in it imports or shells out to `confluence-as`.

## CI

`.github/workflows/ci.yml`'s `test` job installs `confluence-as` with
`--pre` (for the same reason as above) and runs:

```bash
python -m pytest -q --deselect skills/confluence/tests/test_routing.py --deselect tests/e2e/test_plugin_e2e.py
```

`lint`, `type-check`, `security`, `dependency-scan`, `pre-commit` and
`docker-lint` run as separate jobs; `ci-success` gates on `lint` and
`test`. No workflow in this repository invokes the `claude` binary.

## Release policy

Versions are hand-bumped across five sites: `VERSION`,
`.release-please-manifest.json`, `pyproject.toml`,
`.claude-plugin/plugin.json`, and the skill's own frontmatter `version`
(`.claude-plugin/marketplace.json`'s two version fields too, since that
file exists in this repository). `tests/test_consistency.py` asserts
they all agree. Conventional commits carry no `!` suffix and no
`BREAKING CHANGE:` footer -- a breaking release is recorded by hand in
`CHANGELOG.md` under a `### ⚠ BREAKING CHANGES` heading instead. Because the manifest is hand-bumped, `release-please`
proposes its own next minor on `main`; the release itself is a manual
`vX.Y.Z` tag after merge, and the `release-please` proposal is closed.

`.github/workflows/sync-marketplace.yml` pushes this repository's
`.claude-plugin/plugin.json` version to the separate `as-plugins`
marketplace repository automatically on every push to `main`; it does
not update that repository's own `description` field, which needs a
manual follow-up PR after a version bump that changes it.

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
