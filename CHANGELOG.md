# Changelog

All notable changes to the Confluence Assistant Skills project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] - 2026-10-07

### ⚠ BREAKING CHANGES

* The `confluence-assistant` hub skill and the sixteen domain skills
  (`confluence-admin`, `confluence-analytics`, `confluence-attachment`,
  `confluence-bulk`, `confluence-comment`, `confluence-hierarchy`,
  `confluence-jira`, `confluence-label`, `confluence-ops`,
  `confluence-page`, `confluence-permission`, `confluence-property`,
  `confluence-search`, `confluence-space`, `confluence-template`,
  `confluence-watch`), their references and shared hub-era docs and
  config, are removed.
* The `browse-skills` and `skill-info` commands, premised on browsing
  many skills, are removed; `confluence-assistant-setup` is removed too
  (nothing was left of it once every confluence-as flag and environment
  variable name it walked through was scrubbed).
* One `confluence` skill now carries the Entry-Point Hint: run
  `confluence-as help` first; find operations with `confluence-as api
  search`/`api describe`; the CLI's own help is the source of truth.
* Requires `confluence-as>=2,<3`. confluence-as 1.x is not supported:
  the plugin declares that range, the skill names it, and CI and release
  validation install only the reviewed 2.x wheel whose SHA-256 is bound
  in repository variables.
* The end-to-end harness is now the help-only sufficiency arm
  (`tests/e2e/`), and the routing test is now the two-skill routing check
  (`skills/confluence/tests/test_routing.py`); both are host-run, not CI.
* The dormant `e2e-tests.yml` GitHub Actions workflow, and the Docker
  image it built, are removed.
* The `docker-publish.yml` workflow, which pushed that image to GHCR on
  every published release, on manual dispatch, and on main pushes that
  changed `docker/e2e/`, `requirements-e2e.txt` or the workflow itself,
  is removed, along with `requirements-e2e.txt`.
* The old developer scripts under `scripts/` (`run-e2e-tests.sh`,
  `run_live_tests.sh`, `run_single_test.sh`, `run_tests.sh`,
  `setup-env.sh`, `sync-version.sh`, `update_skill_md.py`), the sample
  `.claude/settings.json` profile file, the root `conftest.py` and the
  archived hub-era notes under `docs/archived/` are removed.

### Release process

* Releases are manual and bound to a reviewed commit. release-please no
  longer runs on pushes to main. `release.yml` runs only by dispatch on
  main, with the full reviewed `candidate_sha`, which must equal the
  dispatched commit. The default `publish=false` only validates;
  `publish=true` plus approval of the `plugin-release` environment
  creates the `v3.0.0` tag atomically and publishes the validated
  archive, and never replaces an existing tag or release.
* The release archive is reproducible and holds only
  `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`,
  `skills/confluence/SKILL.md`, `README.md`, `VERSION` and `LICENSE`.
  The validation job writes the archive's SHA-256 and every member's
  SHA-256 to its job summary for the approver, and the GitHub release
  notes are this changelog section.
* `release-please-config.json` and `.release-please-manifest.json` stay
  as history (the manifest is still a checked version site), but no
  workflow uses them.
* `sync-marketplace.yml` no longer runs when `plugin.json` changes on
  main. It runs only by dispatch with the reviewed `candidate_sha`,
  behind the `marketplace-review` environment, and opens a pull request
  in the marketplace repository for review.
* CI and release validation pin ruff to 0.16.10 and install the pinned
  Anthropic SDK that the offline evaluation-controller tests import.

### Features

* **confluence:** one skill holding the Entry-Point Hint replaces the
  hub and sixteen domain skills (JAS-54, JAS-31)

### Safety

* **confluence:** before any write, the skill has the agent read the
  Risk line in `confluence-as api describe OPERATION`. In confluence-as
  2.0.0 only operations marked destructive or irreversible preview
  first; any other write sends at once, so the agent confirms it with
  the user before sending.
* **confluence:** the skill declares no `allowed-tools`, so loading it
  pre-approves no tool and Bash calls keep their normal permission
  prompts.

### Tests

* **confluence:** add a two-skill (confluence vs. a non-shipped
  jira-stub fixture) inter-plugin routing check
* **e2e:** rewrite the end-to-end harness as the help-only sufficiency
  arm: the model gets only the Entry-Point Hint, the Bash tool, and
  `confluence-as` in simulation transport with no credentials

## [2.0.1] - 2026-08-19

### Changed

- **Skill docs aligned with the confluence-as CLI**: every command example
  in the 16 domain SKILL.md files, the shared references (QUICK_REFERENCE,
  ERROR_HANDLING, SAFEGUARDS), README, and the setup command was verified
  against the confluence-as 1.1.1 `--help` tree, with mock-mode runs and
  library source as the authority for behavior claims
  - Binary name corrected everywhere: `confluence` → `confluence-as`
  - Nonexistent commands/flags removed or remapped to real equivalents
  - Exit-code documentation corrected to actual behavior (all API errors
    exit 1; malformed command lines exit 2; Ctrl+C exits 130)
  - Wrong behavior claims fixed (retry timings, v2-only property API,
    `jira link` page marker, bulk partial-failure exit code, ops cache
    reality, display-only hierarchy reorder)
  - Documented the global `-o/--output` propagation added in
    confluence-as 1.1.1
- **Dependency floor raised to `confluence-as>=1.1.1`** in pyproject and
  install docs, matching the CLI behavior the docs now describe

### Notes

- The planned `search scale-search` HTTP 400 caveat was intentionally
  omitted: no such command exists in the public confluence-as CLI

## [2.0.0] - 2026-01-20

### Changed

- **BREAKING**: Library dependency renamed from
  `confluence-assistant-skills-lib` to [confluence-as](https://pypi.org/project/confluence-as/);
  all scripts and docs now import/install `confluence-as`
- Unit and live-integration tests migrated to the confluence-as
  repository; this repo keeps plugin docs, routing tests, and e2e tests
- CI workflows updated for the post-migration layout

## [1.1.0] - 2025-12-31

### Added

- **CLI Framework**: Unified `confluence` command-line interface using Click
  - 13 command groups: page, space, search, comment, label, attachment, hierarchy, permission, analytics, watch, template, property, jira
  - Global options: `--output`, `--verbose`, `--quiet`
  - Shell completion support for bash and zsh
- **Package Installation**: Install via `pip install -e .` with `confluence` entry point
- **Hybrid Dispatch**: CLI calls skill scripts directly with subprocess fallback
- **Comprehensive CLI Tests**: 31 tests covering all command groups

### Changed

- All 75 skill scripts now accept `argv` parameter for testability and CLI integration
- SKILL.md files updated to use new `confluence <group> <command>` syntax
- Documentation updated with CLI installation, usage, and examples
- Script template pattern now includes `argv: list[str] | None = None` parameter

### Documentation

- Added CLI Interface section to CLAUDE.md
- Updated README.md Quick Start with CLI installation
- All code examples converted from `python script.py` to `confluence` CLI syntax

## 1.0.0 (2025-12-29)


### Features

* add Claude Code plugin manifest and marketplace ([e7a0cfd](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/e7a0cfd0837e098ad62fc2ebc2d07b8afc58c237))
* **confluence-analytics:** implement analytics scripts and tests ([b4ca6b6](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/b4ca6b62bc686d61c341cfd4f4dd46796a0acf56))
* **confluence-attachment:** implement attachment scripts and tests ([31df8e6](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/31df8e6caf817785ca9466cf6cab7bd5833089dc))
* **confluence-comment:** implement comment scripts and tests ([d38b99b](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/d38b99b394a3e7ae4b8c2087ab532bc5f82c3995))
* **confluence-hierarchy:** implement hierarchy scripts and tests ([5bac182](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/5bac182acbd624d6db842c944e2babb51663f7e5))
* **confluence-jira:** implement JIRA integration scripts and tests ([129d442](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/129d442031c0aa7c7f5f64b24548f9ce659581c3))
* **confluence-label:** implement label scripts and tests ([5a40a23](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/5a40a238396267216fd18daaa8209b604a5a8261))
* **confluence-permission:** implement permission scripts and tests ([f0bc9e3](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/f0bc9e37ad773a78a55f3a2a0150d072aadfa124))
* **confluence-property:** implement property scripts and tests ([5da7a86](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/5da7a869920bc96f14eb4e8e423241ff87809973))
* **confluence-search:** add advanced search scripts and tests ([2094956](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/2094956a76b381e467f1ad35ba17696c1348e5fa))
* **confluence-template:** implement template scripts and tests ([a194437](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/a194437816d2f84002917f8582074bd750649a29))
* **confluence-watch:** implement watch scripts and tests ([968b5be](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/968b5be9b1ce5983335283ea6b58bba7f24e377c))
* **shared:** add configuration schema and example ([23fc4fe](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/23fc4fe96ddb68eac3286487aa661bd849e52ac2))
* **shared:** add core Python library for Confluence API ([a8038ae](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/a8038aeb661f17ba5e8e20a7c1d80ea8948549dd))
* **shared:** add JIRA validators to shared library ([4b51a97](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/4b51a978896b6faa31ef17a42a1ffc140ed2217d))
* **skill:** add confluence-analytics and confluence-watch skills ([7dbc30f](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/7dbc30f37990abe1939cbfb4b3cfc011b5d61000))
* **skill:** add confluence-assistant hub skill ([4851a28](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/4851a280f317db9a886badffc68d19a99d9efd85))
* **skill:** add confluence-attachment skill for file management ([b6791b4](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/b6791b43cbf28959e90201441f3d83ef20aced92))
* **skill:** add confluence-comment and confluence-label skills ([07b179a](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/07b179ab3a95e4cabce3ba8d029edf0ee58679ee))
* **skill:** add confluence-hierarchy skill for page tree navigation ([cc7ff63](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/cc7ff637986b77575cb78c06415a146ac1c429fe))
* **skill:** add confluence-jira skill for JIRA integration ([0196929](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/01969294fdc65c63be2af5774479a5b7b61c77f4))
* **skill:** add confluence-page skill for page and blog post CRUD ([e069489](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/e0694897a7d6748c288aead9a9ca764bad96f3e1))
* **skill:** add confluence-permission skill for access control ([42233de](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/42233de87a400a52aed3366d538a6d4fe6b8c4a6))
* **skill:** add confluence-property and confluence-template skills ([6b0b6a9](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/6b0b6a921489026ecc6a417307c32b10cd8e5a55))
* **skill:** add confluence-search skill for CQL queries ([a3c6e21](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/a3c6e212c192c0d483f66c21171ed432471f8395))
* **skill:** add confluence-space skill for space management ([138c248](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/138c24850da04d68ab20265dae4af5021000d21c))


### Bug Fixes

* exclude Python lib/ but allow shared scripts lib/ ([586fd26](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/586fd2619d270a3d131352715aa81be8d7506b7a))
* **tests:** resolve pytest option conflicts and add missing fixtures ([2b5329a](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/2b5329a64973fc721c3c1f75b076a06de361d7f2))
* **validators:** add single quote validation for CQL queries ([071ae4d](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/071ae4d4ffd9c93cc5f22a02c886e917ec01bc1b))

## [1.0.0] - 2024-01-01

### Added

- Initial release of Confluence Assistant Skills
- **confluence-assistant**: Central hub/router skill
- **confluence-page**: Page and blog post CRUD operations
- **confluence-space**: Space management
- **confluence-search**: CQL queries and search export
- **confluence-comment**: Page and inline comments
- **confluence-attachment**: File attachment management
- **confluence-label**: Content labeling
- **confluence-template**: Page templates and blueprints
- **confluence-property**: Content properties (metadata)
- **confluence-permission**: Space and page permissions
- **confluence-analytics**: Content analytics
- **confluence-watch**: Content watching and notifications
- **confluence-hierarchy**: Content tree navigation
- **confluence-jira**: Cross-product JIRA integration
- Shared library with:
  - ConfluenceClient with retry logic
  - Multi-source configuration management
  - Exception hierarchy and error handling
  - Input validation utilities
  - Output formatting utilities
  - ADF (Atlassian Document Format) conversion
  - XHTML storage format conversion
  - Response caching
- CI/CD workflow with Release Please
- Comprehensive documentation
