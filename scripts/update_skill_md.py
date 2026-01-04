#!/usr/bin/env python3
"""Update SKILL.md files to use new CLI syntax."""

import re
from pathlib import Path

# Mapping from skill/script to CLI command
SCRIPT_TO_CLI = {
    # confluence-page
    "confluence-page/get_page.py": "confluence page get",
    "confluence-page/create_page.py": "confluence page create",
    "confluence-page/update_page.py": "confluence page update",
    "confluence-page/delete_page.py": "confluence page delete",
    "confluence-page/copy_page.py": "confluence page copy",
    "confluence-page/move_page.py": "confluence page move",
    "confluence-page/get_page_versions.py": "confluence page versions",
    "confluence-page/restore_version.py": "confluence page restore",
    "confluence-page/create_blogpost.py": "confluence page blog create",
    "confluence-page/get_blogpost.py": "confluence page blog get",
    # confluence-space
    "confluence-space/list_spaces.py": "confluence space list",
    "confluence-space/get_space.py": "confluence space get",
    "confluence-space/create_space.py": "confluence space create",
    "confluence-space/update_space.py": "confluence space update",
    "confluence-space/delete_space.py": "confluence space delete",
    "confluence-space/get_space_content.py": "confluence space content",
    "confluence-space/get_space_settings.py": "confluence space settings",
    # confluence-search
    "confluence-search/cql_search.py": "confluence search cql",
    "confluence-search/search_content.py": "confluence search content",
    "confluence-search/cql_validate.py": "confluence search validate",
    "confluence-search/cql_suggest.py": "confluence search suggest",
    "confluence-search/export_results.py": "confluence search export",
    "confluence-search/streaming_export.py": "confluence search stream-export",
    "confluence-search/cql_history.py": "confluence search history",
    "confluence-search/cql_interactive.py": "confluence search interactive",
    # confluence-comment
    "confluence-comment/get_comments.py": "confluence comment list",
    "confluence-comment/add_comment.py": "confluence comment add",
    "confluence-comment/add_inline_comment.py": "confluence comment add-inline",
    "confluence-comment/update_comment.py": "confluence comment update",
    "confluence-comment/delete_comment.py": "confluence comment delete",
    "confluence-comment/resolve_comment.py": "confluence comment resolve",
    # confluence-label
    "confluence-label/get_labels.py": "confluence label list",
    "confluence-label/add_label.py": "confluence label add",
    "confluence-label/remove_label.py": "confluence label remove",
    "confluence-label/search_by_label.py": "confluence label search",
    "confluence-label/list_popular_labels.py": "confluence label popular",
    # confluence-attachment
    "confluence-attachment/list_attachments.py": "confluence attachment list",
    "confluence-attachment/upload_attachment.py": "confluence attachment upload",
    "confluence-attachment/download_attachment.py": "confluence attachment download",
    "confluence-attachment/update_attachment.py": "confluence attachment update",
    "confluence-attachment/delete_attachment.py": "confluence attachment delete",
    # confluence-hierarchy
    "confluence-hierarchy/get_children.py": "confluence hierarchy children",
    "confluence-hierarchy/get_ancestors.py": "confluence hierarchy ancestors",
    "confluence-hierarchy/get_descendants.py": "confluence hierarchy descendants",
    "confluence-hierarchy/get_page_tree.py": "confluence hierarchy tree",
    "confluence-hierarchy/reorder_children.py": "confluence hierarchy reorder",
    # confluence-permission
    "confluence-permission/get_page_restrictions.py": "confluence permission page get",
    "confluence-permission/add_page_restriction.py": "confluence permission page add",
    "confluence-permission/remove_page_restriction.py": "confluence permission page remove",
    "confluence-permission/get_space_permissions.py": "confluence permission space get",
    "confluence-permission/add_space_permission.py": "confluence permission space add",
    "confluence-permission/remove_space_permission.py": "confluence permission space remove",
    # confluence-analytics
    "confluence-analytics/get_page_views.py": "confluence analytics views",
    "confluence-analytics/get_content_watchers.py": "confluence analytics watchers",
    "confluence-analytics/get_popular_content.py": "confluence analytics popular",
    "confluence-analytics/get_space_analytics.py": "confluence analytics space",
    # confluence-watch
    "confluence-watch/watch_page.py": "confluence watch page",
    "confluence-watch/unwatch_page.py": "confluence watch unwatch-page",
    "confluence-watch/watch_space.py": "confluence watch space",
    "confluence-watch/am_i_watching.py": "confluence watch status",
    "confluence-watch/get_watchers.py": "confluence watch list",
    # confluence-template
    "confluence-template/list_templates.py": "confluence template list",
    "confluence-template/get_template.py": "confluence template get",
    "confluence-template/create_template.py": "confluence template create",
    "confluence-template/update_template.py": "confluence template update",
    "confluence-template/create_from_template.py": "confluence template create-from",
    # confluence-property
    "confluence-property/list_properties.py": "confluence property list",
    "confluence-property/get_properties.py": "confluence property get",
    "confluence-property/set_property.py": "confluence property set",
    "confluence-property/delete_property.py": "confluence property delete",
    # confluence-jira
    "confluence-jira/link_to_jira.py": "confluence jira link",
    "confluence-jira/get_linked_issues.py": "confluence jira linked",
    "confluence-jira/embed_jira_issues.py": "confluence jira embed",
    "confluence-jira/create_jira_from_page.py": "confluence jira create-from-page",
    "confluence-jira/sync_jira_macro.py": "confluence jira sync-macro",
}


def update_skill_md(skill_path: Path) -> tuple[int, int]:
    """Update a SKILL.md file to use new CLI syntax.

    Returns:
        Tuple of (lines_changed, files_changed)
    """
    skill_name = skill_path.parent.name
    content = skill_path.read_text()
    original_content = content
    changes = 0

    # Pattern to match python script invocations
    # Matches: python script_name.py [args]
    for script_key, cli_cmd in SCRIPT_TO_CLI.items():
        skill_prefix, script_name = script_key.split("/")

        if skill_prefix != skill_name:
            continue

        # Replace python script.py with CLI command
        # Pattern: python script_name.py (followed by args or newline)
        pattern = rf'python\s+{re.escape(script_name)}'
        if re.search(pattern, content):
            content = re.sub(pattern, cli_cmd, content)
            changes += 1

    if content != original_content:
        skill_path.write_text(content)
        print(f"Updated: {skill_path} ({changes} replacements)")
        return changes, 1

    return 0, 0


def main():
    """Update all SKILL.md files."""
    skills_dir = Path(".claude-plugin/.claude/skills")

    total_changes = 0
    total_files = 0

    for skill_path in skills_dir.glob("*/SKILL.md"):
        changes, files = update_skill_md(skill_path)
        total_changes += changes
        total_files += files

    print(f"\nTotal: {total_changes} replacements in {total_files} files")


if __name__ == "__main__":
    main()
