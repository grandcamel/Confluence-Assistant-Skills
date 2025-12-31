# Changelog

All notable changes to the Confluence Assistant Skills project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-12-31

### Added

- **CLI Framework**: Unified `confluence` command-line interface using Click
  - 13 command groups: page, space, search, comment, label, attachment, hierarchy, permission, analytics, watch, template, property, jira
  - Global options: `--profile`, `--output`, `--verbose`, `--quiet`
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
