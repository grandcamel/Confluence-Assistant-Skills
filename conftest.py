"""
Shared pytest fixtures for all Confluence Assistant Skills tests.

Provides common fixtures used across multiple skill tests.
Skill-specific fixtures remain in their respective conftest.py files.

This root conftest.py centralizes:
- pytest hooks (addoption, configure, collection_modifyitems)
- Temporary directory fixtures
- Project structure fixtures
"""

import json
import pytest
import tempfile
from pathlib import Path


# =============================================================================
# PYTEST HOOKS
# =============================================================================

def pytest_addoption(parser):
    """Add custom command-line options."""
    parser.addoption(
        "--live",
        action="store_true",
        default=False,
        help="Run live integration tests"
    )


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks integration tests")
    config.addinivalue_line("markers", "live: marks tests requiring live API")
    config.addinivalue_line("markers", "destructive: mark test as making destructive changes")


def pytest_collection_modifyitems(config, items):
    """Skip live tests unless --live is provided."""
    if not config.getoption("--live"):
        skip_live = pytest.mark.skip(reason="Need --live to run")
        for item in items:
            if "live" in item.keywords:
                item.add_marker(skip_live)


# =============================================================================
# TEMPORARY DIRECTORY FIXTURES
# =============================================================================

@pytest.fixture
def temp_path():
    """Create a temporary directory as Path object.

    Preferred fixture for new tests. Automatically cleaned up.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_dir(temp_path):
    """Create a temporary directory as string.

    Legacy compatibility. Prefer temp_path for new tests.
    """
    return str(temp_path)


# =============================================================================
# PROJECT STRUCTURE FIXTURES
# =============================================================================

@pytest.fixture
def claude_project_structure(temp_path):
    """Create a standard .claude project structure."""
    project = temp_path / "Test-Project"
    project.mkdir()

    claude_dir = project / ".claude"
    skills_dir = claude_dir / "skills"
    shared_lib = skills_dir / "shared" / "scripts" / "lib"
    shared_lib.mkdir(parents=True)

    settings = claude_dir / "settings.json"
    settings.write_text('{}')

    return {
        "root": project,
        "claude_dir": claude_dir,
        "skills_dir": skills_dir,
        "shared_lib": shared_lib,
        "settings": settings,
    }


@pytest.fixture
def sample_skill_md():
    """Return sample SKILL.md content."""
    return '''---
name: sample-skill
description: A sample skill for testing.
---

# Sample Skill

## Quick Start

```bash
echo "Hello"
```
'''
