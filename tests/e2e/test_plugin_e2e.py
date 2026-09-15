"""
Help-only sufficiency arm.

Is the Entry-Point Hint (skills/confluence/SKILL.md) alone enough for a
model to complete representative confluence-as tasks? The model gets the
shipped plugin, the Bash and Skill tools (Skill is required to load the
hint at all), no MCP servers, and a `confluence-as` forced into
simulation transport with CONFLUENCE_ALLOWED_SPACES=DOCS and no
credentials, so nothing it runs can reach a live site. Each task's
prompt gets a fixed trailer (runner.PROMPT_TRAILER) telling the model to
act now rather than ask a clarifying question. A trial passes when any
confluence-as invocation in its transcript matches the task's `accept`
list (see test_cases.yaml and runner.command_matches_accept) and that
invocation's replay classifies well-formed (runner.classify_replay) --
and fails outright if the model loaded any skill other than
`confluence` (see runner.extract_skill_invocations).

Thresholds: five cold trials per task; a task passes at four or more
well-formed trials; the arm passes only when all seven tasks pass.
Model: claude-sonnet-5.

Run with: pytest tests/e2e/ -v
Not run in CI: this launches the `claude` binary. See
.github/workflows/ci.yml, which deselects this file.
"""

import pytest
import yaml

pytestmark = [pytest.mark.e2e, pytest.mark.slow]

TRIALS_PER_TASK = 5
MIN_PASSING_TRIALS = 4


def _load_tasks(test_cases_path):
    with test_cases_path.open() as f:
        data = yaml.safe_load(f)
    return data.get("tasks", [])


class TestSufficiencyArm:
    """One test per representative task; each runs its own cold trials."""

    @pytest.fixture(autouse=True)
    def _tasks(self, test_cases_path):
        self.tasks = {
            t["id"]: (t["prompt"], t["accept"]) for t in _load_tasks(test_cases_path)
        }

    def _run_task(self, sufficiency_runner, task_id):
        prompt, accept = self.tasks[task_id]
        results = sufficiency_runner.run_task(task_id, prompt, accept, TRIALS_PER_TASK)
        well_formed = sum(1 for r in results if r.well_formed)
        evidence_dir = results[0].evidence_dir if results else ""

        # Always visible (pytest shows captured stdout for a failing
        # test regardless of -s; for a passing one it needs -s or -rP),
        # and always in the failure message below: every trial's full
        # transcript and command detail is on disk here, so a scoring
        # question never requires re-running the live arm.
        print(f"[{task_id}] evidence: {evidence_dir}")

        if well_formed < MIN_PASSING_TRIALS:
            trial_reports = []
            for i, r in enumerate(results, 1):
                if r.replay_outcomes:
                    outcomes = "; ".join(
                        f"{o.command!r} -> exit {o.exit_code}, "
                        + ("ok" if o.ok else f"FAIL ({o.reason})")
                        for o in r.replay_outcomes
                    )
                else:
                    outcomes = "(no matching invocation replayed)"
                trial_reports.append(
                    f"  trial {i}: well_formed={r.well_formed} passed={r.command!r}\n"
                    f"    all commands run: {r.commands}\n"
                    f"    matching-command replays: {outcomes}\n"
                    f"    transcript_error: {r.transcript_error}"
                )
            pytest.fail(
                f"[{task_id}] expected >= {MIN_PASSING_TRIALS}/{TRIALS_PER_TASK} "
                f"well-formed trials, got {well_formed}/{TRIALS_PER_TASK}\n"
                f"Evidence directory: {evidence_dir}\n"
                f"Prompt: {prompt}\nAccept: {accept}\n" + "\n".join(trial_reports)
            )

    def test_read_page(self, sufficiency_runner):
        self._run_task(sufficiency_runner, "read-page")

    def test_search_cql(self, sufficiency_runner):
        self._run_task(sufficiency_runner, "search-cql")

    def test_create_page_property(self, sufficiency_runner):
        self._run_task(sufficiency_runner, "create-page-property")

    def test_read_page_labels(self, sufficiency_runner):
        self._run_task(sufficiency_runner, "read-page-labels")

    def test_update_page_property(self, sufficiency_runner):
        self._run_task(sufficiency_runner, "update-page-property")

    def test_delete_page(self, sufficiency_runner):
        self._run_task(sufficiency_runner, "delete-page")

    def test_find_attachments_operation(self, sufficiency_runner):
        self._run_task(sufficiency_runner, "find-attachments-operation")
