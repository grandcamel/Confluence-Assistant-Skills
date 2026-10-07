# Confluence Assistant Skills

A Claude Code plugin that teaches Claude to drive Confluence Cloud through the [`confluence-as`](https://pypi.org/project/confluence-as/) CLI (2.x).

[![Release](https://img.shields.io/github/v/release/grandcamel/Confluence-Assistant-Skills?color=36B37E)](https://github.com/grandcamel/Confluence-Assistant-Skills/releases)
[![PyPI](https://img.shields.io/pypi/v/confluence-as?color=36B37E)](https://pypi.org/project/confluence-as/)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

## What this is

The plugin ships one skill, `confluence`, holding a short Entry-Point Hint. It points a model at the CLI's own `help`, `api search`, `api describe`, `api topics` and `api call` commands rather than restating what they do -- the CLI's own help is the source of truth, and this repository never duplicates it.

## Install

**Claude Code plugin marketplace:**

```bash
claude plugin marketplace add grandcamel/as-plugins
claude plugin install confluence-assistant-skills@as-plugins --scope user
```

**Manual:**

```bash
git clone https://github.com/grandcamel/Confluence-Assistant-Skills.git
pip install "confluence-as>=2,<3"
```

For a release candidate, use the exact wheel and SHA256 from its reviewed product packet. Final installation requires the published 2.x release.

## Use

Once the plugin is installed, ask Claude to do something with Confluence Cloud and it will load the `confluence` skill, which tells it to run:

```bash
confluence-as help                       # surface map, discovery commands, topics, auth/sandbox modes
confluence-as api search WORDS           # find an operation
confluence-as api describe OPERATION     # read what it needs
confluence-as api call OPERATION ...     # run it
confluence-as api topics                 # deep-dive topics (credentials, scope, risk, paging, errors)
```

## Testing

The offline suite runs with no credentials, no network, and no `claude`/`confluence-as` binary; it needs only `git` and a git checkout:

```bash
python -m pytest -q --deselect skills/confluence/tests/test_routing.py --deselect tests/e2e/test_plugin_e2e.py
```

Two additional harnesses launch the real Claude Code CLI and are host-triggered only, never in CI:

- **Help-only sufficiency arm** (`tests/e2e/`) -- is the Entry-Point Hint alone enough for a model to complete representative tasks? See `tests/e2e/README.md` for prerequisites, thresholds, and how a trial is judged.
- **Two-skill routing check** (`skills/confluence/tests/test_routing.py`) -- given a prompt, does Claude Code load this skill, a sibling plugin's, or neither?

See [CLAUDE.md](CLAUDE.md) for repository layout, the release process, and CI.

## Release validation

Landing on `main` runs CI only. Release and marketplace workflows require
separate manual dispatches bound to the full reviewed main commit SHA;
marketplace updates create a PR for review and never merge it automatically.
The release workflow defaults to validation only.

CI and release validation require repository variables
`CONFLUENCE_CLI_WHEEL_URL` and `CONFLUENCE_CLI_WHEEL_SHA256` from the reviewed
product build packet. Missing or mismatched bindings fail validation; the
product wheel is installed directly, with no editable product dependency.
The plugin archive includes the adopted skill and excludes the test harnesses.

## License

MIT -- see [LICENSE](LICENSE).
