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
pip install --pre "confluence-as>=2,<3"
```

`--pre` is needed until `confluence-as` 2.0.0 final ships to PyPI (only the `2.0.0rc1` pre-release is published there today).

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

The offline suite runs with no credentials, no network, and no `claude`/`confluence-as` binary:

```bash
python -m pytest -q --deselect skills/confluence/tests/test_routing.py --deselect tests/e2e/test_plugin_e2e.py
```

Two additional harnesses launch the real Claude Code CLI and are host-triggered only, never in CI:

- **Help-only sufficiency arm** (`tests/e2e/`) -- is the Entry-Point Hint alone enough for a model to complete representative tasks? See `tests/e2e/README.md` for prerequisites, thresholds, and how a trial is judged.
- **Two-skill routing check** (`skills/confluence/tests/test_routing.py`) -- given a prompt, does Claude Code load this skill, a sibling plugin's, or neither?

See [CLAUDE.md](CLAUDE.md) for repository layout, the release process, and CI.

## License

MIT -- see [LICENSE](LICENSE).
