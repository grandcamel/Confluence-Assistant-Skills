---
description: "Get detailed information about a specific Confluence skill"
arguments:
  - name: skill_name
    description: "Name of the skill to get info about (e.g., confluence-page, confluence-search)"
    required: true
---

# Skill Info: $ARGUMENTS

Get detailed information about the **$ARGUMENTS** skill.

## Instructions

1. Read the SKILL.md file for the requested skill from `.claude/skills/$ARGUMENTS/SKILL.md`
2. Present a summary including:
   - Full description
   - When to use this skill
   - Available scripts/commands
   - Example usage
   - Configuration requirements

## Skill Locations

Skills are located at:
- `.claude/skills/confluence-page/SKILL.md`
- `.claude/skills/confluence-space/SKILL.md`
- `.claude/skills/confluence-search/SKILL.md`
- `.claude/skills/confluence-comment/SKILL.md`
- `.claude/skills/confluence-attachment/SKILL.md`
- `.claude/skills/confluence-label/SKILL.md`
- `.claude/skills/confluence-template/SKILL.md`
- `.claude/skills/confluence-property/SKILL.md`
- `.claude/skills/confluence-permission/SKILL.md`
- `.claude/skills/confluence-analytics/SKILL.md`
- `.claude/skills/confluence-watch/SKILL.md`
- `.claude/skills/confluence-hierarchy/SKILL.md`
- `.claude/skills/confluence-jira/SKILL.md`
- `.claude/skills/confluence-assistant/SKILL.md`

## Output

Present the skill information in a clear, readable format with sections for:
- **Description**: What this skill does
- **When to Use**: Trigger conditions
- **Key Features**: Main capabilities
- **Example Commands**: How to use it
- **Related Skills**: Other skills that work well together
