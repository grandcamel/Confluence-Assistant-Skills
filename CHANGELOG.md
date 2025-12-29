# Changelog

All notable changes to the Confluence Assistant Skills project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
