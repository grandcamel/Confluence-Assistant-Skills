"""Utility functions for Confluence Assistant Skills CLI.

This module previously contained script delegation functions that have been
removed as part of the CLI-only architecture refactoring. All command
implementations are now directly in the CLI command files.

Historical functions removed:
- get_skills_root_dir() - Located skill scripts directory
- get_skills_root() - Cached skills root directory
- run_skill_script_subprocess() - Ran scripts via subprocess
- import_skill_module() - Dynamically imported skill modules
- call_skill_main() - Called skill script main functions

These functions are no longer needed since all command logic is now
implemented directly in the CLI command modules under:
  src/confluence_assistant_skills/cli/commands/
"""

from __future__ import annotations

# This module is kept for backwards compatibility but no longer exports
# any functions. All functionality is now in the CLI command modules.
