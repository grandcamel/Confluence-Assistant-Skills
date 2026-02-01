# Changelog

All notable changes to the Confluence Assistant Skills project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0](https://github.com/grandcamel/Confluence-Assistant-Skills/compare/v1.1.0...v2.0.0) (2026-02-01)


### ⚠ BREAKING CHANGES

* The PyPI package has been renamed from `confluence-assistant-skills-lib` to `confluence-as` for brevity.
* CLI removed, now plugin-only package. Install confluence-assistant-skills-lib for CLI functionality.
* The `confluence` CLI command is no longer provided by this package. Install confluence-assistant-skills-lib instead.
* Remove multi-profile support in favor of environment variables only. This simplifies configuration and improves security boundaries for containerized deployments.

### Features

* add __init__.py to export PageBuilder and test utilities ([8676bf7](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/8676bf739a10b2cfe8621aa6ef1b75ef2c4ae4c7))
* add confluence-bulk, confluence-ops, and confluence-admin skills ([f344b2f](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/f344b2f09c671d45a01e1b393a9ff251ffa112fd))
* add skill_count metadata to plugin.json ([a405d4b](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/a405d4b1e1a7599bfc299904239a7662e1656a72))
* **commands:** add slash commands for skill discovery and setup ([91b4fed](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/91b4fed20a1249d917b4a87f9c7094a0281ade17))
* implement assistant-skills alignment (phases 1-4) ([bb20ccb](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/bb20ccbaf1b05d0708d91efa39bf24799caaf373))
* **safeguards:** add permission block for claude-safe integration ([70f5f90](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/70f5f9006dea5a85261c7b5aa209f606f99aca6f))
* **scripts:** add test runner scripts for TDD workflow ([fd2bc1c](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/fd2bc1c3c8cb4df24f848cf9c69ee05f4912bab6))
* **scripts:** add version sync script for release management ([6bf9fab](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/6bf9fabb56cf0e24f22e63f5c1ed9bc171ec58c5))
* **testing:** add run_live_tests.sh and document test scripts ([730e79d](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/730e79d52b9cded1fa319fee64862a7000202fe6))
* **testing:** add run_live_tests.sh and document test scripts ([ef8f4b3](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/ef8f4b3693c54ec4850fb608aaebe51bbb4859fc))


### Bug Fixes

* add ConfluenceContainer alias and export reset_confluence_connection ([fd2616e](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/fd2616e9885b5903efe00fac6a3db6bdc7b9de8f))
* **ci:** update workflows for post-migration testing ([283d0c1](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/283d0c1ea909108249da2bd66cd8c47de128e7f7))
* **confluence-analytics:** align CLI wrapper with script interfaces ([92ccb61](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/92ccb619af8c2142f39f4db77998cd5d82328267))
* **confluence-attachment:** align CLI wrapper with script interfaces ([db976d6](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/db976d6d2dffd12839df2fe7fb8b6a47f8460070))
* **confluence-comment:** align CLI wrapper with script interfaces ([6826b79](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/6826b79289d2ce2c8d51649b9ac3223497ef3613))
* **confluence-hierarchy:** align CLI wrapper with script interfaces ([860335f](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/860335f94a2935505da61752a4b8300bac4b89de))
* **confluence-jira:** align CLI wrapper with script interfaces ([aedcce7](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/aedcce7d38cff7e49ad24729e8ea1d0cb384e0ee))
* **confluence-label:** align CLI wrapper with script interfaces ([a278250](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/a2782506d9c3ad9fcfa9fae3cb769c2863901c50))
* **confluence-page:** align CLI wrapper with script interfaces ([de47658](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/de47658e133b154c3f227d89a3c8692d86b75c0c))
* **confluence-permission:** align CLI wrapper with script interfaces ([524a0ce](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/524a0ce91f60fca4946dd1c58b7cfffcf3646fa7))
* **confluence-property:** align CLI wrapper with script interfaces ([3eb493c](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/3eb493c65f4d53679f2da15c461b483fe5544a26))
* **confluence-search:** align CLI wrapper with script interfaces ([bc3cdc6](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/bc3cdc64401d1d6ef12be667ac507235fe1ae79e))
* **confluence-space:** align CLI wrapper with script interfaces ([ab9dac5](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/ab9dac54f43c2679ec6f013225de76f04336062c))
* **confluence-template:** align CLI wrapper with script interfaces ([f24ebbb](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/f24ebbb8525334a04d43c0b9aeaf090e77db872f))
* **confluence-watch:** add missing --output option to unwatch-page ([63736f8](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/63736f8cb3a25d082dd2965c58374811045aa7d6))
* **e2e:** use direct prompts for skill mention tests ([ef05652](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/ef05652351fc5c643bd62db512dc53a092f1b0b9))
* remove invalid plugin.json field and sync versions/counts ([769bbba](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/769bbbabbd00b22f602ae02d59c5b61168dd3a9c))
* remove unrecognized assistant_skills key from plugin.json ([98075ba](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/98075ba0f904a62a5fae69aaed53c6705d5c83c3))
* resolve all mypy type errors (61 → 0) ([b5d58a8](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/b5d58a854a5c73ef95c007777cc6cb72a28376e9))
* **scripts:** use --ignore instead of --ignore-glob for live_integration ([6435579](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/64355792a2d03806dddc566262c7d75614634f83))
* **test:** add retry logic for page version race condition ([8dc73b8](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/8dc73b87a14ce80f259e35e390769a27b68e9eef))
* update mock client fixtures to match ConfluenceClient implementation ([5c58cca](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/5c58ccab25842f3565cc3c0f0a3aa6b6fe9af9d7))
* update pyproject.toml for plugin-only package ([7cba618](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/7cba6187f54f5a2242093fc3e11a018c12371f0b))
* use plugin-root-relative paths in plugin.json ([ee00cc9](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/ee00cc96bc64f8c37a097a3190d0d49a0d0d59e9))


### Miscellaneous Chores

* bump version to 2.0.0 ([5512178](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/5512178936e45c89bb356a2e8d34df78f37f63d3))


### Code Refactoring

* remove CLI, convert to plugin-only package ([403d54d](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/403d54dc9e0d7629dd36bb3f56f9b86ecaf0eb79))
* remove profile feature from configuration ([c013293](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/c013293d0d4f9751e242d764f9abecdc221314e6))
* update dependency from confluence-assistant-skills-lib to confluence-as ([9c23702](https://github.com/grandcamel/Confluence-Assistant-Skills/commit/9c23702bc669a80ea66f7d370b12b3f92e6da9af))

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
