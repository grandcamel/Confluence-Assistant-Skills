# Refactoring Proposal: Centralizing Assistant-Skills Libraries and Scripts

**Author:** Gemini AI Agent
**Reviewed by:** Claude AI Agent
**Date:** December 30, 2025
**Status:** DRAFT - WITH FEEDBACK

---

## Revision History

| Date | Author | Changes |
|------|--------|---------|
| 2025-12-30 | Gemini | Initial draft |
| 2025-12-31 | Claude | Added technical review, Phase 0, test fixture consolidation, migration strategy |

---

## 1. Abstract

The `Assistant-Skills` ecosystem currently comprises several projects, each with its own Python library (`...-lib`). This has led to significant code duplication, particularly for common functionalities like configuration management, error handling, and input validation. Furthermore, the skill execution model relies on invoking Python scripts via their full file path, creating a brittle coupling to the filesystem layout.

This proposal outlines a **three-phase** refactoring plan to address these issues.

* **Phase 0** (NEW) will establish a baseline by fixing existing bugs, ensuring test coverage, and documenting current behavior.
* **Phase 1** will consolidate all duplicated, non-domain-specific code from the `jira-`, `confluence-`, and `splunk-assistant-skills-lib` projects into the central `assistant-skills-lib`. This phase now includes test fixture consolidation.
* **Phase 2** will transform the skill scripts into formal command-line entry points distributed by their respective Python packages, decoupling skill execution from the file system.

This effort will drastically reduce code duplication, improve long-term maintainability, and align the projects with standard Python packaging and distribution practices.

---

## 2. Background & Problem Statement

The `Assistant-Skills` architecture is a "factory" model where the `Assistant-Skills` project provides templates and tools to create service-specific plugins (e.g., `Jira-Assistant-Skills`). While this has successfully standardized the project structure, it has led to two significant technical debts.

### Problem A: Systemic Code Duplication Across Libraries

The service-specific libraries (`confluence-lib`, `jira-lib`, `splunk-lib`) were developed independently and contain large amounts of functionally identical boilerplate code.

**Evidence of Duplication:**

| Common Module | `assistant-skills-lib` | `confluence-lib` | `jira-lib` | `splunk-lib` |
| :--- | :---: | :---: | :---: | :---: |
| `error_handler.py` | ✅ | ✅ | ✅ | ✅ |
| `formatters.py` | ✅ | ✅ | ✅ | ✅ |
| `validators.py` | ✅ | ✅ | ✅ | ✅ |
| `config_manager.py`| ❌ | ✅ | ✅ | ✅ |

This duplication means that:
* Fixing a bug in the error handling logic for Jira requires manually porting the fix to Confluence and Splunk.
* The overall maintenance burden is 3x higher than it needs to be for common code.
* There is a high risk of divergence, where subtle differences can emerge over time, leading to inconsistent behavior across the different `Assistant-Skills` projects.

### Problem B: Brittle Filesystem-Coupled Skill Execution

Currently, `SKILL.md` files trigger functionality by invoking a Python script directly via its path:
```bash
# Example from a current SKILL.md
python .claude/skills/jira-issue/scripts/get_issue.py PROJ-123
```
This approach is problematic because:
* It is tightly coupled to the project's directory structure.
* It is not a standard or professional way to distribute and execute code within a Python package.
* It makes the scripts less portable and harder to test or execute outside the specific context of the Claude Code runner.

### Problem C: Test Fixture Duplication (NEW)

**Discovered during technical review:** Approximately 2,373 lines of duplicate test fixtures exist across skill-specific `conftest.py` files. Each of the 15 skill directories contains nearly identical:
- `mock_response()` fixture
- `mock_client()` fixture
- Sample data fixtures (`sample_page()`, `sample_space()`, etc.)

This duplication exists despite a shared fixtures file at `.claude/skills/shared/tests/conftest.py`.

---

## 3. Scope Quantification (NEW)

Understanding the full scope of this refactoring is critical for planning and risk assessment.

### Affected Files by Project

| Project | Scripts | SKILL.md Files | Test Files | conftest.py Files |
|---------|---------|----------------|------------|-------------------|
| Confluence | 75 | 14 | ~120 | 15 |
| Jira | ~60 (est.) | ~12 | ~100 | ~12 |
| Splunk | ~30 (est.) | ~6 | ~50 | ~6 |
| **Total** | **~165** | **~32** | **~270** | **~33** |

### Repositories Affected

1. `assistant-skills-lib` (base library)
2. `confluence-as`
3. `jira-assistant-skills-lib`
4. `splunk-assistant-skills-lib`
5. `Confluence-Assistant-Skills` (skills project)
6. `Jira-Assistant-Skills` (skills project)
7. `Splunk-Assistant-Skills` (skills project)

### Success Metrics

| Metric | Current State | Target State |
|--------|---------------|--------------|
| Duplicated library code (LOC) | ~3,000 | 0 |
| Duplicated test fixtures (LOC) | ~2,373 | 0 |
| Scripts using filesystem execution | 165 | 0 |
| Average script boilerplate (LOC) | ~25 | ~10 |

---

## 4. Proposed Solution

This refactoring will be executed in three distinct phases.

### Phase 0: Preparation & Baseline (NEW)

**Goal:** Establish a solid foundation before making architectural changes.

**Detailed Steps:**

1. **Fix Existing Bugs:**
   - `.claude/skills/confluence-page/scripts/create_page.py` - Add missing `from pathlib import Path` import (line 20 uses `Path` without import)
   - Audit all scripts for similar issues using static analysis

2. **Ensure Test Coverage:**
   - Run coverage analysis on all modules targeted for consolidation
   - Achieve minimum 80% coverage on `error_handler.py`, `validators.py`, `formatters.py`, `config_manager.py`
   - Document any untested edge cases

3. **Document Current Behavior:**
   - Create behavior specification for each module being moved
   - Capture current error messages and exit codes
   - Document all public API signatures

4. **Static Analysis Baseline:**
   - Run `mypy` on all service-specific libraries
   - Fix any type errors before consolidation
   - Establish lint baseline with `ruff` or `flake8`

**Exit Criteria:**
- All known bugs fixed
- Test coverage ≥80% on target modules
- Clean `mypy` run on all libraries
- Behavior documentation complete

---

### Phase 1: Library Consolidation & Centralization

**Goal:** Establish the base `assistant-skills-lib` as the single source of truth for all common, non-domain-specific code.

**Detailed Steps:**

#### 1.1 Enhance `assistant-skills-lib`

A new, generic `BaseConfigManager` will be created in the base library using a **service prefix pattern** to handle service-specific variations:

```python
class BaseConfigManager:
    """
    Base configuration manager supporting multiple services.

    Args:
        service_name: Service identifier ("confluence", "jira", "splunk")
                      Used for config keys and environment variable prefixes.
    """
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.env_prefix = service_name.upper()  # CONFLUENCE_, JIRA_, SPLUNK_
        self._config_key = service_name  # Key in settings.json

    def _get_env_var(self, name: str) -> Optional[str]:
        """Get environment variable with service prefix."""
        return os.environ.get(f"{self.env_prefix}_{name}")

    def get_site_url(self) -> str:
        """Get site URL from env or config."""
        return self._get_env_var("SITE_URL") or self._get_config("url")

    def get_default_context(self) -> str:
        """Get default space/project/index depending on service."""
        key_mapping = {
            "confluence": "default_space",
            "jira": "default_project",
            "splunk": "default_index",
        }
        return self._get_config(key_mapping.get(self.service_name, "default_context"))
```

**Additional base library enhancements:**
- Add `validate_profile()` utility function
- Add common CLI argument helpers (`add_profile_argument()`, `add_output_argument()`)
- Update `error_handler.py`, `validators.py`, and `formatters.py` to be the canonical versions

#### 1.2 Refactor Service-Specific Libraries

The `ConfigManager` within each service library will be refactored to inherit from `BaseConfigManager`:

```python
# In confluence_as/config_manager.py
from assistant_skills_lib import BaseConfigManager

class ConfigManager(BaseConfigManager):
    """Confluence-specific configuration manager."""

    def __init__(self):
        super().__init__(service_name="confluence")

    # Only Confluence-specific methods remain here
    def get_default_space(self) -> str:
        return self.get_default_context()
```

**Deletion targets:**
- `error_handler.py` - DELETE from all service libs
- `validators.py` - DELETE from all service libs (keep service-specific validators)
- `formatters.py` - DELETE from all service libs (keep service-specific formatters)

#### 1.3 Consolidate Test Fixtures (NEW)

Move all shared test fixtures to a single location and update imports:

**Target structure:**
```
assistant-skills-lib/
└── src/assistant_skills_lib/
    └── testing/
        ├── __init__.py
        ├── fixtures.py      # mock_response, mock_client, etc.
        └── factories.py     # sample_page, sample_space, etc.
```

**Migration for skill conftest.py files:**
```python
# Before (in each skill's conftest.py)
@pytest.fixture
def mock_response():
    # 20 lines of duplicate code...

# After
from assistant_skills_lib.testing import mock_response, mock_client, sample_page
# conftest.py now only contains skill-specific fixtures
```

#### 1.4 Update Dependencies

The `pyproject.toml` for service-specific libraries will declare formal dependencies:

```toml
[project]
dependencies = [
    "assistant-skills-lib>=1.0.0",
    # ... other deps
]
```

---

### Phase 2: Script-to-Entry-Point Refactoring

**Goal:** Decouple skill execution from the filesystem by converting skill scripts into standard Python package command-line entry points.

#### 2.1 Entry Point Naming Convention (RESOLVED)

**Decision:** Use `{service}-{verb}-{noun}` pattern for clarity and discoverability.

| Service | Examples |
|---------|----------|
| Confluence | `confluence-get-page`, `confluence-create-space`, `confluence-search` |
| Jira | `jira-get-issue`, `jira-create-issue`, `jira-search` |
| Splunk | `splunk-run-query`, `splunk-get-index` |

**Rationale:**
- Unambiguous service identification
- Tab-completion friendly (type `confluence-` and see all commands)
- Consistent with tools like `aws-`, `gcloud-`, `kubectl-`

#### 2.2 Move Scripts

Python script files will be moved from their current location into the library's source tree:

```
# Before
Confluence-Assistant-Skills/
└── .claude/skills/confluence-page/scripts/
    └── get_page.py

# After
confluence-as/
└── src/confluence_as/
    └── cli/
        ├── __init__.py
        └── page/
            ├── __init__.py
            └── get_page.py
```

#### 2.3 Define Entry Points

Update `pyproject.toml` to register CLI commands:

```toml
[project.scripts]
# Page operations
confluence-get-page = "confluence_as.cli.page.get_page:main"
confluence-create-page = "confluence_as.cli.page.create_page:main"
confluence-update-page = "confluence_as.cli.page.update_page:main"
confluence-delete-page = "confluence_as.cli.page.delete_page:main"

# Space operations
confluence-get-space = "confluence_as.cli.space.get_space:main"
confluence-create-space = "confluence_as.cli.space.create_space:main"
# ... etc
```

#### 2.4 Update SKILL.md Files

**Before:**
```bash
python .claude/skills/confluence-page/scripts/get_page.py 12345 --output json
```

**After:**
```bash
confluence-get-page 12345 --output json
```

#### 2.5 Migration & Deprecation Strategy (NEW)

To ensure smooth transition for existing installations:

**Step 1: Dual Support Period (2 releases)**

Keep scripts in original locations but add deprecation wrapper:

```python
#!/usr/bin/env python3
# .claude/skills/confluence-page/scripts/get_page.py
import sys
import warnings

warnings.warn(
    "Direct script execution is deprecated. "
    "Use 'confluence-get-page' command instead. "
    "This script will be removed in version 2.0.",
    DeprecationWarning,
    stacklevel=2
)

from confluence_as.cli.page.get_page import main
sys.exit(main())
```

**Step 2: Update Documentation**

- Update all SKILL.md files to use new entry points
- Add migration guide to README
- Update CLAUDE.md with new invocation patterns

**Step 3: Remove Deprecated Scripts**

After deprecation period, remove wrapper scripts entirely.

---

## 5. Benefits

* **Drastically Reduced Maintenance:** A bug fix in `error_handler.py` is made in one place and instantly benefits all three service projects.
* **Code Simplification:** The service-specific libraries will become significantly smaller and focused only on their core domain logic.
* **Improved Robustness & Consistency:** All projects will share the exact same implementation for configuration, validation, and error handling.
* **Professional Packaging:** Adopts the standard, modern Python practice for distributing command-line tools, making the projects easier to understand, install, and use.
* **Reduced Test Duplication:** Centralizing test fixtures eliminates ~2,373 lines of duplicate code.
* **Future-Proofing:** Establishes a clean, DRY (Don't Repeat Yourself) architecture that makes it trivial to create new, high-quality `*-Assistant-Skills` projects in the future.

---

## 6. Risks & Mitigation Strategy

### Risk 1: Regression from Scale of Changes

**Probability:** Medium
**Impact:** High

The refactoring affects 400+ files across 7 repositories.

**Mitigation:**
- Phase 0 establishes baseline with full test coverage
- Phased approach isolates changes
- Each phase has explicit exit criteria
- No phase begins until previous phase tests pass 100%

### Risk 2: Import Modification Errors

**Probability:** Medium
**Impact:** Medium

Modifying imports across hundreds of files is error-prone.

**Mitigation:**
- Use IDE refactoring tools (PyCharm, VS Code)
- Batch replacements via `grep`/`sed` with careful review
- Validate with `mypy` static analysis
- Run full test suite after each batch

### Risk 3: Breaking Existing Installations

**Probability:** Low
**Impact:** High

Phase 2 changes the invocation interface.

**Mitigation:**
- Deprecation period with dual support
- Clear migration documentation
- Semantic versioning with major version bump
- Rollback procedure documented

### Risk 4: BaseConfigManager Design Flaws

**Probability:** Medium
**Impact:** Medium

The service prefix pattern may not handle all edge cases.

**Mitigation:**
- Design review before implementation
- Prototype with Confluence first
- Comprehensive unit tests for all service variations
- Document extension points for future services

---

## 7. Testing & Validation

### Phase 0 Validation

- [ ] All existing bugs fixed
- [ ] `mypy` passes on all libraries
- [ ] Coverage report generated showing ≥80% on target modules
- [ ] Behavior documentation approved

### Phase 1 Validation

- [ ] `assistant-skills-lib` unit tests pass
- [ ] Each service-specific library's full test suite passes after refactoring
- [ ] Import changes verified via static analysis
- [ ] No new `mypy` errors introduced
- [ ] Test fixture imports updated and working

### Phase 2 Validation

- [ ] Entry points install correctly via `pip install -e .`
- [ ] All commands accessible from PATH
- [ ] SKILL.md files updated and tested
- [ ] End-to-End test suite (`run-e2e-tests.sh`) passes
- [ ] Deprecation warnings emit correctly for old invocation method

---

## 8. Implementation Timeline

| Phase | Description | Dependencies | Estimated Effort |
|-------|-------------|--------------|------------------|
| 0 | Preparation & Baseline | None | 1-2 days |
| 1a | BaseConfigManager design | Phase 0 | 1 day |
| 1b | Library consolidation | Phase 1a | 2-3 days |
| 1c | Test fixture consolidation | Phase 1a | 1 day |
| 2a | Entry point conversion (Confluence pilot) | Phase 1 | 2 days |
| 2b | Entry point conversion (Jira, Splunk) | Phase 2a | 2-3 days |
| 2c | Deprecation wrappers & documentation | Phase 2b | 1 day |

**Total estimated effort:** 10-13 days

---

## 9. Rollback Procedure (NEW)

If critical issues are discovered post-deployment:

### Phase 1 Rollback

1. Revert `pyproject.toml` dependency changes
2. Restore deleted module files from git history
3. Revert import changes via git
4. Publish patch version of service libraries

### Phase 2 Rollback

1. Keep entry points but restore original scripts
2. Update SKILL.md to use original invocation
3. Document issue and timeline for fix

---

## 10. Open Questions for Feedback

1. ~~Naming convention for entry points~~ **RESOLVED:** Using `{service}-{verb}-{noun}` pattern

2. Should `assistant-skills-lib` testing utilities be a separate package (`assistant-skills-lib-testing`) to avoid test dependencies in production?

3. What is the minimum supported Python version across all projects? This affects which language features can be used in the base library.

4. Should we consider a monorepo structure to simplify cross-repository changes?

---

## 11. Appendix

### A. Known Bugs to Fix in Phase 0

| File | Issue | Fix |
|------|-------|-----|
| `.claude/skills/confluence-page/scripts/create_page.py` | Missing `from pathlib import Path` import | Add import statement |

### B. Files to Delete in Phase 1

**From `confluence-as`:**
- `src/confluence_as/error_handler.py` (after migration)
- `src/confluence_as/validators.py` (keep Confluence-specific only)
- `src/confluence_as/formatters.py` (keep Confluence-specific only)

**From each skill's `tests/conftest.py`:**
- `mock_response()` fixture
- `mock_client()` fixture
- Duplicate sample data fixtures

### C. Entry Point Mapping (Confluence)

| Current Script | New Entry Point |
|----------------|-----------------|
| `get_page.py` | `confluence-get-page` |
| `create_page.py` | `confluence-create-page` |
| `update_page.py` | `confluence-update-page` |
| `delete_page.py` | `confluence-delete-page` |
| `get_space.py` | `confluence-get-space` |
| `create_space.py` | `confluence-create-space` |
| `search.py` | `confluence-search` |
| ... | ... |

*Full mapping to be generated during Phase 2 planning.*
