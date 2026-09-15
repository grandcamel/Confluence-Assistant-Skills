"""
Offline unit tests for tests/e2e/runner.py's pure functions: well-
formedness classification (classify_replay), segment splitting/cleaning
(split_into_segments, clean_segment and friends), and accept-list
matching (command_matches_accept, extract_bash_commands,
find_matching_commands). No subprocess and no `claude`/`confluence-as`
binary is launched anywhere in this file -- every sample below is a
literal, hand-written stand-in for output the scratch confluence-as
2.0.0rc1 binary actually produced.
"""

import json

import pytest

from tests.e2e.runner import (
    HarnessConfigurationError,
    classify_replay,
    clean_segment,
    command_matches_accept,
    extract_bash_commands,
    find_matching_commands,
    segment_matches_accept,
    split_into_segments,
)

# ---------------------------------------------------------------------------
# classify_replay: well-formedness against the simulation transport's
# default-seeded store, per exact probe outputs against the scratch
# 2.0.0rc1 binary.
# ---------------------------------------------------------------------------


def test_exit_0_is_well_formed():
    """`api call getPageById --id 1` exits 0 with the real seeded page."""
    stdout = json.dumps({"id": "1", "spaceId": "55", "title": "First"})
    ok, reason = classify_replay(0, stdout, "")
    assert ok is True
    assert reason == ""


def test_exit_0_describe_is_well_formed():
    """`api describe getPageAttachments` exits 0."""
    ok, reason = classify_replay(0, "# getPageAttachments\n...", "")
    assert ok is True
    assert reason == ""


def test_exit_0_dry_run_preview_is_well_formed():
    """`api call deletePage --id 2` (no --confirm) exits 0 with a dry-run
    preview payload."""
    stdout = json.dumps(
        {"dry_run": True, "operationId": "deletePage", "risk": "irreversible"}
    )
    ok, reason = classify_replay(0, stdout, "")
    assert ok is True
    assert reason == ""


def test_exit_4_scope_not_found_under_simulation_is_well_formed():
    """`api call getPageById --id 999999999` with CONFLUENCE_ALLOWED_SPACES=DOCS
    exits 4 -- a real, well-formed identity, just not resolvable against
    the store."""
    stderr = json.dumps(
        {
            "status": None,
            "messages": [
                'getPageById: scope identity 999999999; allowlist=["DOCS"]: '
                "scope resolution could not establish membership"
            ],
        }
    )
    ok, reason = classify_replay(4, "", stderr)
    assert ok is True
    assert reason == ""


def test_exit_4_scope_not_found_under_responder_is_well_formed():
    """The responder transport's distinct wording for the same underlying
    condition -- also well-formed."""
    stderr = json.dumps(
        {
            "status": None,
            "messages": [
                'getPageById: scope identity 1; allowlist=["DOCS"]: scope '
                "resolution requires exactly one matching identity"
            ],
        }
    )
    ok, reason = classify_replay(4, "", stderr)
    assert ok is True
    assert reason == ""


def test_exit_4_empty_allowlist_raises_harness_configuration_error():
    """An exit 4 with 'empty allowlist' means CONFLUENCE_ALLOWED_SPACES
    was never set in the replay's own environment -- a harness defect,
    not a model failure. This must raise, not return a classification,
    so the trial is never silently scored as a miss."""
    stderr = json.dumps(
        {
            "status": None,
            "messages": [
                "getPageById: scope identity 1; allowlist=[]: empty allowlist"
            ],
        }
    )
    with pytest.raises(HarnessConfigurationError):
        classify_replay(4, "", stderr)


def test_exit_4_unrecognized_scope_message_is_not_well_formed():
    """An exit 4 whose message matches neither the not-found nor the
    empty-allowlist pattern is treated conservatively as not well-formed,
    not guessed at."""
    ok, reason = classify_replay(4, "", '{"messages": ["something else entirely"]}')
    assert ok is False
    assert "unrecognized scope message" in reason


def test_exit_5_unknown_operation_on_stdout_is_not_well_formed():
    """An unknown operation exits 5, with a message starting 'Unknown
    operation' -- this is the operation name being wrong, not a
    not-found result, so it must NOT be classified well-formed."""
    stdout = json.dumps({"status": 404, "messages": ["Unknown operation: bogusOp"]})
    ok, reason = classify_replay(5, stdout, "")
    assert ok is False
    assert "unknown operation" in reason.lower()


def test_exit_5_unknown_operation_on_stderr_is_not_well_formed():
    """The same 'Unknown operation' check must fire when the payload is
    on stderr instead of stdout."""
    stderr = json.dumps({"status": 404, "messages": ["Unknown operation: bogusOp"]})
    ok, reason = classify_replay(5, "", stderr)
    assert ok is False
    assert "unknown operation" in reason.lower()


def test_exit_5_status_404_without_unknown_operation_is_well_formed():
    """`api call updatePagePropertyById` against a property id that does
    not exist exits 5 with `{"status": 404, "messages": ["Property not
    found"]}` -- a real operation and identity, just not found."""
    stdout = json.dumps({"status": 404, "messages": ["Property not found"]})
    ok, reason = classify_replay(5, stdout, "")
    assert ok is True
    assert reason == ""


def test_exit_2_usage_error_is_not_well_formed():
    """`api call getPageById` (missing --id) exits 2 with a usage error."""
    stderr = json.dumps({"messages": ["missing required parameter: id"]})
    ok, reason = classify_replay(2, "", stderr)
    assert ok is False
    assert "usage" in reason.lower()


def test_exit_2_wrapper_verb_stub_is_not_well_formed():
    """`confluence-as page get --id 1` (a legacy wrapper-verb migration
    stub) exits 2, correctly classified as NOT well-formed."""
    stderr = json.dumps(
        {"messages": ["Use api call getPageById --id PAGE_ID --body-format storage"]}
    )
    ok, _reason = classify_replay(2, "", stderr)
    assert ok is False


def test_other_exit_code_is_not_well_formed():
    ok, reason = classify_replay(17, "", "")
    assert ok is False
    assert "17" in reason


# ---------------------------------------------------------------------------
# split_into_segments / clean_segment: MATCHING uses a shell-aware
# tokenizer, quote-safe splitting on newlines/;/&&/||/|, then strips
# redirections and a leading env-assignment/`time` prefix. The actual
# REPLAY always uses the original, verbatim command via a real shell
# (bash -o pipefail -c) -- these functions are for MATCHING only.
# ---------------------------------------------------------------------------


def test_split_into_segments_on_each_separator():
    assert split_into_segments("confluence-as help; echo done") == [
        ["confluence-as", "help"],
        ["echo", "done"],
    ]
    assert split_into_segments("cmd1 && confluence-as help") == [
        ["cmd1"],
        ["confluence-as", "help"],
    ]
    assert split_into_segments("cmd1 || confluence-as help") == [
        ["cmd1"],
        ["confluence-as", "help"],
    ]
    assert split_into_segments("echo x | confluence-as help") == [
        ["echo", "x"],
        ["confluence-as", "help"],
    ]
    assert split_into_segments(
        "confluence-as help\nconfluence-as api call getPageById"
    ) == [
        ["confluence-as", "help"],
        ["confluence-as", "api", "call", "getPageById"],
    ]


def test_split_into_segments_never_splits_on_a_lone_ampersand_from_redirection():
    """`2>&1` is one redirection token (fused `>&`), not a background
    `&` that would otherwise start a new (empty) segment."""
    assert split_into_segments("confluence-as help 2>&1") == [
        ["confluence-as", "help", "2", ">&", "1"]
    ]


def test_clean_segment_strips_redirections():
    tokens = [
        "confluence-as",
        "api",
        "describe",
        "getPageById",
        "--examples",
        "2",
        ">&",
        "1",
    ]
    assert clean_segment(tokens) == [
        "confluence-as",
        "api",
        "describe",
        "getPageById",
        "--examples",
    ]


def test_clean_segment_strips_redirection_with_space_before_target():
    tokens = ["confluence-as", "help", "risk", "2", ">", "/dev/null"]
    assert clean_segment(tokens) == ["confluence-as", "help", "risk"]


def test_clean_segment_strips_leading_env_assignment():
    tokens = ["CONFLUENCE_AS_TRANSPORT=simulation", "confluence-as", "help"]
    assert clean_segment(tokens) == ["confluence-as", "help"]


def test_clean_segment_strips_leading_time_and_env():
    tokens = [
        "time",
        "CONFLUENCE_AS_TRANSPORT=simulation",
        "confluence-as",
        "help",
    ]
    assert clean_segment(tokens) == ["confluence-as", "help"]


# ---------------------------------------------------------------------------
# command_matches_accept: accept-list matching for the read-page and
# find-attachments-operation tasks' exact accept lists, operating on the
# RAW (possibly env-prefixed, piped, chained, or redirected) command.
# ---------------------------------------------------------------------------

READ_PAGE_ACCEPT = ["getPageById"]
ATTACHMENTS_ACCEPT = ["describe:getPageAttachments"]
DELETE_PAGE_ACCEPT = ["deletePage"]


def test_api_call_matches_bare_operation_id():
    command = "confluence-as api call getPageById --id 1"
    assert command_matches_accept(command, READ_PAGE_ACCEPT) is True


def test_env_prefixed_command_matches():
    command = (
        "CONFLUENCE_AS_TRANSPORT=simulation CONFLUENCE_ALLOWED_SPACES=DOCS "
        "confluence-as api call getPageById --id 1"
    )
    assert command_matches_accept(command, READ_PAGE_ACCEPT) is True


def test_env_prefixed_command_with_quoted_field_value_matches():
    command = (
        "CONFLUENCE_AS_TRANSPORT=simulation confluence-as api call "
        "createPageProperty --page-id 1 --field 'key=\"harness-probe\"' "
        "--field value=1"
    )
    assert command_matches_accept(command, ["createPageProperty"]) is True


def test_redirection_does_not_break_matching():
    command = "confluence-as api call getPageById --id 1 2>&1"
    assert command_matches_accept(command, READ_PAGE_ACCEPT) is True


def test_bare_operation_id_does_not_match_api_describe():
    """A discovery step (`api describe X`) for an action task must NOT
    count as the action having been performed -- a bare operationId entry
    matches ONLY `api call`."""
    command = "confluence-as api describe getPageById"
    assert command_matches_accept(command, READ_PAGE_ACCEPT) is False


def test_describe_prefixed_entry_requires_describe_verb():
    """A bare `api call getPageAttachments` must NOT satisfy a
    "describe:getPageAttachments" entry -- only `api describe` does."""
    call_command = "confluence-as api call getPageAttachments --id 1"
    describe_command = "confluence-as api describe getPageAttachments"
    assert command_matches_accept(call_command, ATTACHMENTS_ACCEPT) is False
    assert command_matches_accept(describe_command, ATTACHMENTS_ACCEPT) is True


def test_kebab_case_operation_id_matches_camel_case_accept_entry():
    """The pinned CLI resolves `get-page-by-id` to the same operation as
    `getPageById` (verified: both return the same seeded page for id 1)
    -- kebab-case is an accepted alias, not a different operation."""
    command = "confluence-as api call get-page-by-id --id 1"
    assert command_matches_accept(command, READ_PAGE_ACCEPT) is True


def test_kebab_case_operation_id_matches_describe_entry():
    command = "confluence-as api describe get-page-attachments"
    assert command_matches_accept(command, ATTACHMENTS_ACCEPT) is True


def test_unrelated_operation_id_does_not_match():
    command = "confluence-as api call searchByCQL --cql 'type=page'"
    assert command_matches_accept(command, READ_PAGE_ACCEPT) is False


def test_help_never_matches():
    assert command_matches_accept("confluence-as help", READ_PAGE_ACCEPT) is False
    assert command_matches_accept("confluence-as help", ATTACHMENTS_ACCEPT) is False
    assert (
        command_matches_accept(
            "confluence-as api call getPageById --id 1 --help", READ_PAGE_ACCEPT
        )
        is False
    )
    assert (
        command_matches_accept(
            "confluence-as api call deletePage --id 2 -h", DELETE_PAGE_ACCEPT
        )
        is False
    )


def test_messy_piped_command_matches_via_its_confluence_as_segment():
    raw = "cd /tmp && confluence-as api describe getPageAttachments | head -20"
    assert command_matches_accept(raw, ATTACHMENTS_ACCEPT) is True


def test_stdin_fed_body_pipeline_yields_a_matching_segment():
    raw = "echo '{}' | confluence-as api call deletePage --id 2 --body -"
    assert command_matches_accept(raw, DELETE_PAGE_ACCEPT) is True


def _bash_tool_use_event(command: str) -> str:
    """Build one stream-json transcript line for a Bash tool_use block,
    matching the shape a real `claude --output-format stream-json
    --verbose` transcript carries."""
    return json.dumps(
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "tool_use", "name": "Bash", "input": {"command": command}}
                ]
            },
        }
    )


def test_a_trailing_help_command_cannot_game_a_real_match():
    transcript = [
        _bash_tool_use_event("confluence-as api call getPageById --id 1"),
        _bash_tool_use_event("confluence-as help"),
    ]
    commands = extract_bash_commands(transcript)
    assert commands == [
        "confluence-as api call getPageById --id 1",
        "confluence-as help",
    ]
    matching = find_matching_commands(commands, READ_PAGE_ACCEPT)
    assert matching == ["confluence-as api call getPageById --id 1"]


def test_a_lone_trailing_help_command_never_matches_on_its_own():
    transcript = [_bash_tool_use_event("confluence-as help")]
    commands = extract_bash_commands(transcript)
    assert commands == ["confluence-as help"]
    assert find_matching_commands(commands, READ_PAGE_ACCEPT) == []


def test_multiple_matching_commands_are_all_returned():
    transcript = [
        _bash_tool_use_event("confluence-as api describe getPageById"),
        _bash_tool_use_event("confluence-as api call getPageById --id 1"),
        _bash_tool_use_event("confluence-as api call get-page-by-id --id 1"),
    ]
    commands = extract_bash_commands(transcript)
    matching = find_matching_commands(commands, READ_PAGE_ACCEPT)
    assert matching == [
        "confluence-as api call getPageById --id 1",
        "confluence-as api call get-page-by-id --id 1",
    ]


def test_line_continued_command_is_joined_and_then_matched():
    raw = (
        "confluence-as api call createPageProperty \\\n"
        "  --page-id 1 \\\n"
        "  --field 'key=\"harness-probe\"'"
    )
    commands = extract_bash_commands([_bash_tool_use_event(raw)])
    assert commands == [raw]
    assert command_matches_accept(raw, ["createPageProperty"]) is True


def test_dangling_backslash_does_not_crash_and_is_not_matched():
    raw = "confluence-as api call createPageProperty --page-id 1 \\"
    commands = extract_bash_commands([_bash_tool_use_event(raw)])
    assert commands == [raw]
    assert command_matches_accept(raw, ["createPageProperty"]) is False


def test_segment_matches_accept_directly():
    tokens = ["confluence-as", "api", "call", "getPageById", "--id", "1"]
    assert segment_matches_accept(tokens, READ_PAGE_ACCEPT) is True
    assert segment_matches_accept(["echo", "hello"], READ_PAGE_ACCEPT) is False


# ---------------------------------------------------------------------------
# strip_redirection_tokens (via clean_segment): the run-1-style shell
# redirection stripping the jira sibling harness needed, re-verified here
# with confluence-as sample commands.
# ---------------------------------------------------------------------------


def test_clean_segment_strips_bare_redirect_with_no_space():
    tokens = ["confluence-as", "help", "risk", "2", ">&", "1"]
    assert clean_segment(tokens) == ["confluence-as", "help", "risk"]


def test_clean_segment_strips_stdout_redirect_no_space():
    tokens = ["confluence-as", "help", ">", "out.txt"]
    assert clean_segment(tokens) == ["confluence-as", "help"]


def test_clean_segment_strips_append_redirect():
    tokens = ["confluence-as", "help", ">>", "out.txt"]
    assert clean_segment(tokens) == ["confluence-as", "help"]
