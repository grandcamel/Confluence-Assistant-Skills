# Help-Only Sufficiency Arm

The end-to-end harness for Confluence-Assistant-Skills is the **help-only
sufficiency arm**: a task-level test of whether the Entry-Point Hint
(`skills/confluence/SKILL.md`) alone is enough for a model to complete
representative confluence-as tasks.

This replaced the old plugin-installation / per-skill-discovery E2E suite
when the hub and sixteen domain skills were retired: there is nothing
left to "discover" across skills, so the arm now asks a narrower
question -- is `confluence-as help` (as pointed to by the one shipped
skill) sufficient on its own?

## What the model gets, and nothing else

- The shipped plugin only: the plugin manifest plus
  `skills/confluence/SKILL.md`, installed via an **absolute**
  `--plugin-dir` path.
- Exactly two tools, via **`--tools Bash,Skill`** -- not `--allowedTools`
  alone, which only pre-approves permission for tools that would
  otherwise still be available. `Skill` is included, and is the only
  tool besides `Bash`, because a plugin's `SKILL.md` reaches the model
  only through the built-in `Skill` tool -- with `--tools Bash` alone the
  model could never load the Entry-Point Hint at all. `--allowedTools
  "Bash,Skill"` is also passed: under `--permission-mode dontAsk`, the
  Skill tool call is otherwise denied ("Permission to use Skill has been
  denied because Claude Code is running in don't ask mode"). See
  [cli-reference](https://code.claude.com/docs/en/cli-reference) and
  [tools-reference](https://code.claude.com/docs/en/tools-reference).
- **No MCP servers.** `--strict-mcp-config --mcp-config
  tests/e2e/empty-mcp.json` (an absolute path to `{"mcpServers": {}}`)
  keeps the operator's own configured MCP servers out of the session.
- **No project context from this repository.** Each trial runs with `cwd`
  set to a fresh, empty temporary directory, so Claude Code does not load
  this repository's own `CLAUDE.md`, its files, or any other ambient
  project context -- only the plugin passed via `--plugin-dir` is
  present.
- A `confluence-as` binary on `PATH`, forced into its `simulation`
  transport via `CONFLUENCE_AS_TRANSPORT=simulation`, with
  `CONFLUENCE_ALLOWED_SPACES=DOCS` also forced. Unlike the jira sibling
  harness, this second variable is required: every identity-scoped
  confluence-as operation (a read, a create, a delete preview, ...)
  fails with exit 4 ("empty allowlist") without it, even against a page
  that genuinely exists in the simulation store's default seed.
- **An allowlisted subprocess environment, not a denylisted one.** Built
  by `tests/harness_env.py`'s `build_harness_env()` (shared with the
  routing check): only `PATH` (with `HARNESS_CLI_BIN`'s value prepended
  when set), `HOME`, `USER`, `LOGNAME`, and `TERM`/`LANG` (if present)
  are ever copied from the operator's own environment, plus
  `CONFLUENCE_AS_TRANSPORT=simulation` and
  `CONFLUENCE_ALLOWED_SPACES=DOCS`. `CONFLUENCE_SITE_URL`,
  `CONFLUENCE_EMAIL`, `CONFLUENCE_API_TOKEN`, `ANTHROPIC_API_KEY`, and any
  other variable starting with `CONFLUENCE_` or `ANTHROPIC_` never reach
  the subprocess. Nothing the model runs can reach a live Confluence
  site.

### Known limitation: user-level skills and the operator's global CLAUDE.md

- **User-level skills.** Skills installed at the user level on the host
  remain visible to the model regardless of `--tools`/`--plugin-dir`/
  `--strict-mcp-config`. `--bare` would remove them, but it requires an
  `ANTHROPIC_API_KEY` this harness deliberately does not use. The
  mitigation is detection, not prevention: `runner.extract_skill_invocations`
  records **every** `Skill` tool_use in a trial's transcript, and
  `run_trial` **fails the trial outright if any loaded skill is not
  `confluence`**. Loading `confluence` itself is recorded as evidence the
  hint worked, but is not required for a trial to pass -- the model can
  complete a task by running `confluence-as` directly once it knows to.
- **The operator's global CLAUDE.md.** `HOME` is preserved (needed for
  the OAuth login), so the operator's **global** `~/.claude/CLAUDE.md`,
  if they have one, is still loaded as context -- the empty-cwd
  confinement only rules out a *project* `CLAUDE.md`. Run the arm on a
  host with no global `~/.claude/CLAUDE.md` (or one known to carry no
  Confluence-specific guidance) if this matters for a given measurement.

## How a trial is judged

For each cold trial:

1. Append a **fixed trailer** (`runner.PROMPT_TRAILER`) to the task's
   prompt: "Do this now with the confluence-as CLI in this shell. Do not
   ask me questions. The CLI is in simulation mode: use space DOCS and
   page 1 where an id is needed; a scope or not-found response is
   expected and fine. When finished, reply with the exact command you
   ran."
2. Send the combined prompt to Claude Code, from the fresh empty temp
   directory described above, and capture its full tool-use transcript
   (`--output-format stream-json --verbose`).
3. Extract **every** Bash command the model ran, verbatim, read from
   each Bash tool_use block's `input.command` field -- never inferred
   from the model's answer text (see `runner.extract_bash_commands`).
4. For MATCHING only, join any backslash-newline continuation in a
   command back into one logical line (`runner.join_line_continuations`)
   -- replay always uses the original, unjoined string -- then split
   each command into segments on newlines, `;`, `&&`, `||` and `|`, and
   find every segment that -- after stripping any redirection and a
   leading environment-assignment/`time` prefix -- is a `confluence-as`
   invocation matching the task's `accept` list in `test_cases.yaml`
   (`runner.command_matches_accept`): a bare operationId matches ONLY
   `api call OPERATIONID` (an `api describe` of the same operation is a
   discovery step, not the action being performed, and does not count);
   `"describe:OPERATIONID"` matches ONLY `api describe OPERATIONID`. A
   segment containing `--help`/`-h`, or a bare `\` token, never matches.
   Matching against ANY invocation, not just the last command, closes a
   gaming path: a trial that runs the right command and then a trailing
   `confluence-as help` must still be able to pass.
5. Fail the trial outright if the model loaded any **Skill** other than
   `confluence` (see the known-limitation note above) before reaching
   step 6.
6. Re-run **every matching command's ORIGINAL, verbatim string** (not a
   re-parsed or reassembled segment) through a **real shell**
   (`bash -o pipefail -c`), from a fresh empty temp directory, under the
   same simulation environment, and classify each well-formed or not
   with `runner.classify_replay` (see below) -- **not simply "exit 0"**.
   The trial passes if ANY matching command's replay is well-formed;
   `TrialResult` records every command the model ran and the replay
   outcome of every matching one, naming whichever one passed.

### Well-formedness against the simulation store's default seed

Probes of the simulation transport against the scratch confluence-as
2.0.0rc1 binary established:

| Exit code | Condition | Well-formed? |
|---|---|---|
| `0` | any (a real read, a dry-run preview, or a create/update that succeeds) | Yes |
| `4` | message matches `scope resolution could not establish membership` (simulation) or `requires exactly one matching identity` (responder) | Yes -- a real, well-formed operation and identity, just not resolvable against the store/allowlist (confluence's not-found analogue) |
| `4` | message matches `...allowlist=[]: empty allowlist` | **Not a classification** -- raises `HarnessConfigurationError`; `CONFLUENCE_ALLOWED_SPACES` was not set in the replay's own environment, a harness defect, and the trial is not scored |
| `5` | JSON has `"status": 404` and a message starting `"Unknown operation"` | No -- the operation name itself does not exist |
| `5` | JSON has `"status": 404` and no `"Unknown operation"` message | Yes -- a real operation, just not found (e.g. `updatePagePropertyById` against a property that does not exist) |
| `2` | usage error (missing/invalid parameter, unknown flag, or a legacy wrapper-verb migration stub) | No |
| anything else | | No |

This differs from the jira sibling harness's table in exactly one
structural way: where jira's not-found case is exit 5 (with a `(HTTP
404)` or `"status": 404` marker), confluence's is **exit 4** with a
scope-resolution message, and exit 4 additionally carries the
harness-bug-signaling "empty allowlist" variant that jira's rule set has
no equivalent for, since jira-as has no allowlist-shaped scope gate at
all.

One CLI quirk noted along the way, not a harness matter: `confluence-as
api call OPERATION --transport responder` is genuinely invalid on the
pinned CLI (`--transport` is only accepted when positioned on the `api`
group itself, before the subcommand, and only for `http`/`responder` --
`simulation` and `cassette` are environment-variable-only) -- exit 2,
correctly classified as a real failure, not a harness defect to work
around.

There is **no assertion on business content** -- the arm does not check
that the created property looks right or that the search returns the
page you meant. It only checks that the shape of the call the model
produced names a real confluence-as operation.

## Evidence

Every run writes a directory `${TMPDIR:-/tmp}/jas54-sufficiency-<UTC
timestamp>/` (one per pytest session). Per trial, it contains:

- `<task>-<n>.transcript.jsonl` -- the raw `--output-format stream-json`
  transcript, exactly as captured.
- `<task>-<n>.commands.json` -- every Bash command the model ran that
  trial, its segments, whether it matched the task's accept list, and
  (for matching commands) the replay's exit code, stdout, stderr, and
  classification; plus `skills_loaded`, every Skill tool_use name
  observed that trial, namespaced as the CLI reports it (e.g.
  `confluence-assistant-skills:confluence`).

and the directory also holds a `summary.json`, updated after every
trial, recording each trial's outcome (including `skills_loaded`) across
the whole session. The directory path is printed for every task, in
`pytest`'s output and in the failure message when a task does not reach
threshold. The routing check
(`skills/confluence/tests/test_routing.py`) does the same, in a sibling
`jas54-routing-<UTC timestamp>/` directory holding each trial's
transcript and the observed skill.

## The seven tasks

`test_cases.yaml` holds seven representative, concrete tasks, each with
an `accept` list of what counts as a matching invocation. Three of the
seven substitute for an originally-sketched operation that verification
found cannot succeed under this harness's simulation transport at all
(see `test_cases.yaml`'s header comment for the full justification):

1. Read the details of Confluence page 1 in space DOCS (`getPageById`).
2. Search Confluence for content of type page (`searchByCQL`).
3. Create a property on Confluence page 1 in space DOCS
   (`createPageProperty` -- substitutes for "add a label or comment",
   which no confluence-as operation can complete under simulation).
4. Find out whether Confluence page 1 in space DOCS has any labels
   (`getPageLabels` -- takes the slot of "create a page in space DOCS":
   `createPage` cannot succeed under simulation by any scope route, so no
   page-create operation is exercisable here).
5. Update a property on Confluence page 1 in space DOCS
   (`updatePagePropertyById` -- substitutes for "update page 1's
   title": `updatePageTitle` itself exits 6, "simulation does not
   support operation").
6. Delete Confluence page 2 in space DOCS (a preview is enough, never
   confirmed) (`deletePage`).
7. Find and describe the confluence-as API operation that lists a
   page's attachments (`describe:getPageAttachments`).

## Thresholds and provenance

Reused from the jira sibling plugin's own ruling, for consistency across
both plugins:

- **Five cold trials per task** (five independent, fresh `claude`
  invocations -- no session reuse).
- **A task passes at four or more well-formed trials** out of five.
- **The arm passes only when all seven tasks pass.**
- **Model: `claude-sonnet-5`.**

## Running it

This harness launches the `claude` binary directly and is **not run in
CI** (see `.github/workflows/ci.yml`, which deselects
`tests/e2e/test_plugin_e2e.py`). It is host-triggered, the same way the
routing check (`skills/confluence/tests/test_routing.py`) and the floor
eval (`tests/floor_eval/`) are.

### Prerequisites

- Claude Code CLI installed and authenticated with **`claude auth
  login`** (OAuth credentials live under `~/.claude/`, reachable via the
  preserved `HOME`). An `ANTHROPIC_API_KEY` exported in your shell will
  NOT reach the trial subprocess.
- `confluence-as>=2,<3` and its `simulation` transport available on
  `PATH` -- set `HARNESS_CLI_BIN` to a scratch venv's `bin/` (e.g.
  `~/.venvs/confluence-as-2.0.0rc1/bin`) if a compatible version is not
  installed globally; only `2.0.0rc1` is on PyPI as a pre-release until
  confluence-as 2.0.0 final ships (see the repository's `README.md`).
- `pytest` and `pyyaml`.

### Explicit opt-in: `E2E_SUFFICIENCY=1`

Because this arm launches the real `claude` binary and spends real
tokens, it never runs silently. Without `E2E_SUFFICIENCY=1` set, every
test in this directory is **skipped with a loud reason naming the
variable**. With the variable set, collection itself probes `claude
--version` and `confluence-as --version` (on the same built PATH the
trials use); either binary missing, erroring, or (for confluence-as) not
reporting a 2.x version **fails** the run rather than skipping it.

### Quick start

```bash
# Explicit opt-in is required -- this arm never runs silently
export E2E_SUFFICIENCY=1
export HARNESS_CLI_BIN=~/.venvs/confluence-as-2.0.0rc1/bin

# Run the full sufficiency arm (five cold trials per task)
pytest tests/e2e/ -v

# Override the model or per-trial timeout
pytest tests/e2e/ -v --sufficiency-model claude-sonnet-5 --sufficiency-timeout 180
```

## Test structure

```
tests/
├── harness_env.py            # Shared allowlist env builder (also used
│                              # by skills/confluence/tests/test_routing.py)
├── evidence.py                # Shared run-dir/transcript/summary writer
│                              # (also used by test_routing.py)
├── stream_observe.py         # Shared incremental subprocess reader
│                              # (used by test_routing.py)
├── test_harness_env.py       # Offline unit tests for harness_env.py
├── test_stream_observe.py    # Offline unit tests for stream_observe.py
├── test_e2e_matching.py      # Offline unit tests for classify_replay,
│                              # segment splitting, and accept-list
│                              # matching
└── e2e/
    ├── __init__.py
    ├── conftest.py          # Gate + runner fixtures (uses harness_env)
    ├── empty-mcp.json       # {"mcpServers": {}} -- passed with
    │                         # --strict-mcp-config
    ├── runner.py            # SufficiencyRunner: run + replay + judge
    ├── test_cases.yaml      # The seven tasks, each with an accept list
    └── test_plugin_e2e.py   # One pytest test per task
```
