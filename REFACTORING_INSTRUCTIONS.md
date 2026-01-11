# Refactoring Instructions: `Confluence-Assistant-Skills` (Phase 2)

**Engineer:** Confluence Team

This document outlines the specific steps to refactor the `Confluence-Assistant-Skills` project to use the new CLI framework.

## P2a: Foundation

### P2a.1: Plugin Project Formalization

1.  **Create `pyproject.toml`**: Create a `pyproject.toml` file at the project root with a `[project]` table.
    ```toml
    [project]
    name = "confluence-assistant-skills"
    version = "1.0.0"
    description = "A collection of CLI-based assistant skills for interacting with Confluence."
    readme = "README.md"
    requires-python = ">=3.9"
    dependencies = [
        "click>=8.0"
    ]

    [project.scripts]
    confluence = "confluence_assistant_skills.cli.main:cli"
    ```
2.  **Create `src/` Layout**: Create the directory `src/confluence_assistant_skills`.
3.  **Add `__init__.py` Files**:
    -   `src/confluence_assistant_skills/__init__.py`
    -   `src/confluence_assistant_skills/cli/__init__.py`
    -   `src/confluence_assistant_skills/cli/commands/__init__.py`
    -   Recursively add `__init__.py` to all subdirectories under `skills/`.
4.  **Verify Installation**: Run `pip install -e .` from the `Confluence-Assistant-Skills` root to confirm it installs successfully.

### P2a.2: Script Audit & Refactoring

Audit all scripts in `skills/`. For each script:

1.  **Modify `main()`**: Change the signature from `def main():` to `def main(argv: list[str] | None = None):`.
2.  **Update `parse_args()`**: Change `parser.parse_args()` to `parser.parse_args(argv)`.
3.  **(Optional but Recommended)** Extract core logic into a separate, callable function (e.g., `execute_skill()`) if it's not already structured that way.

### P2a.3: Sandbox Compatibility Test

This step will be performed once for all projects. The results confirm that `pip`-installed entry points are viable.

## P2b: CLI Implementation

### P2b.1: CLI Framework Setup

1.  **Create `src/confluence_assistant_skills/utils.py`**: Add the `SKILLS_ROOT_DIR` path resolution logic and the `run_skill_script_subprocess` helper function.
2.  **Create `src/confluence_assistant_skills/cli/main.py`**:
    -   Define the root `cli` command using `@click.group()`.
    -   Define global options: `--output`, `--verbose`, `--quiet`.
    -   Import and add command groups from the `commands` directory.

### P2b.2: Command Group Implementation

For each skill directory (e.g., `confluence-page`, `confluence-space`):

1.  **Create `src/confluence_assistant_skills/cli/commands/<skill_name>_cmds.py`**.
2.  **Define a `click.group()`** that corresponds to the skill (e.g., `@click.group() def page():`).
3.  For each script in the skill, **create a `@click.command()`**.
4.  Map the `click` options and arguments to the arguments expected by the script's `main()` function.
5.  Implement the hybrid dispatch logic:
    -   **Primary:** Attempt to dynamically import the script and call its `execute_skill()` function directly (if it exists).
    -   **Fallback:** If the direct call fails, use the `run_skill_script_subprocess` helper to execute the script's `main(argv=...)` function.

### P2b.3: CLI Test Suite

1.  **Create `tests/test_cli.py`** at the project root.
2.  For each command, write tests using `click.testing.CliRunner`.
3.  Use `unittest.mock.patch` to mock the `execute_skill()` and `run_skill_script_subprocess` calls to prevent actual script execution.
4.  Assert that the correct arguments are being passed to the mocked functions.

### P2b.4: Update `SKILL.md` Files

1.  Create an automated script to parse all `SKILL.md` files.
2.  Replace `python <script_name>.py ...` examples with the new `confluence <group> <command> ...` syntax.
3.  Add a "Shell Completion" section to the main `CLAUDE.md` or a central `README.md`.

### P2b.5: E2E Validation

1.  Ensure the E2E test environment (local or Docker) installs the new `confluence-assistant-skills` package via `pip install -e .`.
2.  Run the existing E2E tests and validate that Claude can successfully use the new CLI-based commands.
