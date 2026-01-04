"""Utility functions for Confluence Assistant Skills CLI."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import click.exceptions


def get_skills_root_dir() -> Path:
    """Get the root directory for skill scripts.

    Resolution order:
    1. CONFLUENCE_SKILLS_ROOT environment variable
    2. Plugin directory (.claude-plugin/.claude/skills)
    3. Current working directory plugin location
    """
    # Check environment variable first
    env_root = os.environ.get("CONFLUENCE_SKILLS_ROOT")
    if env_root:
        return Path(env_root)

    # Default: relative to this package - look in plugin directory
    # src/confluence_assistant_skills/utils.py -> ../../.claude-plugin/.claude/skills
    package_dir = Path(__file__).resolve().parent
    project_root = package_dir.parent.parent.parent
    skills_dir = project_root / ".claude-plugin" / ".claude" / "skills"

    if skills_dir.exists():
        return skills_dir

    # Fallback for installed package - check current working directory
    cwd_skills = Path.cwd() / ".claude-plugin" / ".claude" / "skills"
    if cwd_skills.exists():
        return cwd_skills

    raise RuntimeError(
        f"Could not locate skills directory. "
        f"Set CONFLUENCE_SKILLS_ROOT environment variable or ensure "
        f".claude-plugin/.claude/skills exists in the current directory."
    )


# Lazy initialization of SKILLS_ROOT_DIR
_skills_root_dir: Path | None = None


def get_skills_root() -> Path:
    """Get cached skills root directory."""
    global _skills_root_dir
    if _skills_root_dir is None:
        _skills_root_dir = get_skills_root_dir()
    return _skills_root_dir


def run_skill_script_subprocess(
    skill_name: str,
    script_name: str,
    argv: list[str],
    timeout: int = 300,
) -> int:
    """Run a skill script as a subprocess.

    Args:
        skill_name: Name of the skill (e.g., 'confluence-page')
        script_name: Name of the script file (e.g., 'get_page.py')
        argv: Arguments to pass to the script
        timeout: Timeout in seconds (default: 5 minutes)

    Returns:
        Exit code from the subprocess
    """
    skills_root = get_skills_root()
    script_path = skills_root / skill_name / "scripts" / script_name

    if not script_path.exists():
        raise FileNotFoundError(f"Script not found: {script_path}")

    command = [sys.executable, str(script_path)] + argv

    try:
        result = subprocess.run(
            command,
            check=False,
            timeout=timeout,
        )
        return result.returncode
    except subprocess.TimeoutExpired:
        print(f"Command timed out after {timeout} seconds", file=sys.stderr)
        return 124  # Standard timeout exit code


def import_skill_module(skill_name: str, script_name: str) -> Any:
    """Dynamically import a skill script module.

    Args:
        skill_name: Name of the skill (e.g., 'confluence-page')
        script_name: Name of the script file without .py (e.g., 'get_page')

    Returns:
        The imported module
    """
    import importlib.util

    skills_root = get_skills_root()
    script_path = skills_root / skill_name / "scripts" / f"{script_name}.py"

    if not script_path.exists():
        raise FileNotFoundError(f"Script not found: {script_path}")

    spec = importlib.util.spec_from_file_location(script_name, script_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load spec for {script_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    return module


def call_skill_main(
    skill_name: str,
    script_name: str,
    argv: list[str],
) -> int:
    """Call a skill script's main function directly.

    This is the preferred method as it's faster than subprocess.
    Falls back to subprocess if direct call fails.

    Args:
        skill_name: Name of the skill (e.g., 'confluence-page')
        script_name: Name of the script file without .py (e.g., 'get_page')
        argv: Arguments to pass to the script's main function

    Returns:
        Exit code (0 for success)
    """
    try:
        module = import_skill_module(skill_name, script_name)

        # Try execute_skill() first (preferred callable API)
        if hasattr(module, "execute_skill"):
            result = module.execute_skill(argv)
            return 0 if result is None else int(result)

        # Fall back to main(argv)
        if hasattr(module, "main"):
            result = module.main(argv)
            return 0 if result is None else int(result)

        raise AttributeError(f"Module {script_name} has no 'main' or 'execute_skill' function")

    except click.exceptions.Exit as e:
        # Script exited via Click - return the exit code (don't treat as error)
        return e.exit_code

    except Exception as e:
        # Fall back to subprocess
        print(f"Direct call failed ({e}), falling back to subprocess", file=sys.stderr)
        return run_skill_script_subprocess(
            skill_name,
            f"{script_name}.py",
            argv,
        )
