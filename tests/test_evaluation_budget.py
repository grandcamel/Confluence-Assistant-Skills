"""Offline controller acceptance: synthetic receipts and fake processes only."""

import hashlib
import multiprocessing
import os
import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from tests.evaluation_budget import (
    CAP,
    Binding,
    BudgetLauncher,
    BudgetStop,
    Call,
    Ledger,
    Outcome,
    Settlement,
    harness_call,
    microdollars,
    require_launcher,
)

BASE = "386bb6a1e10cf9a057a1034fac59fb53df5b8bef"


def artifact(path, text):
    path.write_text(text)
    return str(path), hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def budget(tmp_path):
    path, sha = artifact(tmp_path / "binding.json", '{"fake": true}')
    binding = Binding(
        "fake-v1", "claude-sonnet-5", "fake", "synthetic-usd", "2", "1", path, sha
    )
    ledger = Ledger.create(tmp_path / "budget.db", binding)
    return ledger, binding


def call(name="call1", task="task1", trial=1, attempt=1, phase="sufficiency"):
    return Call(name, phase, task, trial, BASE, attempt)


def receipt(ledger, binding, invocation, amount="0.4"):
    path, sha = artifact(
        ledger.path.parent / f"{invocation.call_id}.jsonl", '{"type":"result"}\n'
    )
    proof, digest = artifact(
        ledger.path.parent / f"{invocation.call_id}.cost.json",
        '{"synthetic_charge": true}',
    )
    return Settlement(
        invocation.call_id,
        binding.binding_id,
        binding.model,
        binding.provider,
        binding.billing,
        binding.evidence_sha256,
        amount,
        amount,
        {
            "input_tokens": 1,
            "output_tokens": 2,
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0,
        },
        "success",
        0,
        path,
        sha,
        proof,
        digest,
    )


class FakeTransport:
    """No auth, network, real model command or subprocess execution."""

    offline_only = True

    def __init__(self, ledger, binding, mode="success"):
        self.ledger, self.binding, self.mode = ledger, binding, mode
        self.commands = []

    def validate(self, binding):
        assert binding == self.binding
        if self.mode == "uncontained":
            raise BudgetStop("secondary paid path not contained")

    def execute(self, cmd, prompt, *, call, **kwargs):
        assert (
            next(
                r
                for r in self.ledger.snapshot()["calls"]
                if r["call"]["call_id"] == call.call_id
            )["status"]
            == "reserved"
        )
        assert cmd[-2:] == ["--max-budget-usd", "2"]
        self.commands.append(cmd)
        if self.mode == "crash":
            raise RuntimeError("fake process crash")
        if self.mode == "timeout":
            return Outcome(lines=['{"type":"partial"}'], timed_out=True)
        if self.mode == "early":
            return Outcome(
                lines=['{"type":"assistant"}'], result="confluence", early_stop=True
            )
        if self.mode == "missing":
            # A bare CLI total is not a trusted settlement.
            return Outcome(lines=['{"type":"result","total_cost_usd":0}'])
        charge = receipt(self.ledger, self.binding, call)
        if self.mode == "mismatch":
            charge = replace(charge, model="another-model")
        return Outcome(receipt=charge)

    def replay(self, command, **kwargs):
        raise BudgetStop("fake replay denies secondary model launches")


def launch(budget, mode="success"):
    ledger, binding = budget
    transport = FakeTransport(ledger, binding, mode)
    return BudgetLauncher(ledger, binding, transport), transport


def command():
    return ["claude", "--print", "--model", "claude-sonnet-5"]


@pytest.mark.parametrize(
    "value", [0.1, True, "NaN", "Infinity", "-0.01", "50.01", "x", "1" * 65]
)
def test_money_rejects_invalid(value):
    with pytest.raises(BudgetStop):
        microdollars(value)


def test_rounding_never_releases_fractional_microdollar():
    assert microdollars("0.0000000001") == 1
    assert microdollars("49.9999991") == CAP
    assert microdollars("0") == 0


def test_cap_bound_and_price_proof_required(budget):
    ledger, binding = budget
    for changed in (
        replace(binding, inflight_usd="NaN"),
        replace(binding, session_cap_usd="0"),
        replace(binding, evidence_sha256="0" * 64),
        replace(binding, session_cap_usd="50"),
    ):
        with pytest.raises(BudgetStop):
            ledger.reserve(call(), changed)
    assert ledger.snapshot()["calls"] == []


def test_reservation_restart_and_idempotent_reconciliation(budget):
    ledger, binding = budget
    ledger.reserve(call(), binding)
    reopened = Ledger(ledger.path)
    assert reopened.snapshot()["exposure"] == 3_000_000
    charge = receipt(ledger, binding, call())
    reopened.reconcile(charge)
    before = reopened.snapshot()
    reopened.reconcile(charge)
    assert reopened.snapshot() == before
    assert before["exposure"] == 400_000


@pytest.mark.parametrize(
    "field,value",
    [
        ("model", "wrong"),
        ("provider", "wrong"),
        ("billing", "wrong"),
        ("binding_sha256", "0" * 64),
        ("actual_usd", "NaN"),
        ("actual_usd", "4"),
        ("reported_cost_usd", "bad"),
        ("usage", {}),
        ("usage", None),
        ("transcript_sha256", "0" * 64),
        ("proof_sha256", "0" * 64),
    ],
)
def test_bad_accounting_retains_reservation_and_halts(budget, field, value):
    ledger, binding = budget
    ledger.reserve(call(), binding)
    with pytest.raises(BudgetStop):
        ledger.reconcile(replace(receipt(ledger, binding, call()), **{field: value}))
    assert ledger.snapshot()["exposure"] == 3_000_000
    assert ledger.snapshot()["metadata"]["halted"]
    with pytest.raises(BudgetStop):
        ledger.reserve(call("call2", trial=2), binding)


def test_conflicting_reconciliation_cannot_reduce_spend(budget):
    ledger, binding = budget
    ledger.reserve(call(), binding)
    charge = receipt(ledger, binding, call())
    ledger.reconcile(charge)
    with pytest.raises(BudgetStop):
        ledger.reconcile(replace(charge, actual_usd="0"))
    assert ledger.snapshot()["exposure"] == 400_000
    assert ledger.snapshot()["metadata"]["halted"]


def test_duplicate_trial_cannot_relaunch_after_restart(budget):
    ledger, binding = budget
    ledger.reserve(call(), binding)
    for other in (call(), call("new-uuid")):
        with pytest.raises(BudgetStop):
            Ledger(ledger.path).reserve(other, binding)
    ledger.reserve(call("retry", attempt=2), binding)
    assert ledger.snapshot()["exposure"] == 6_000_000
    with pytest.raises(BudgetStop):
        ledger.reserve(call("skip-retry", attempt=4), binding)


def test_exhaustion_keeps_uncertain_early_stops(budget):
    launcher, _ = launch(budget, "early")
    for number in range(1, 17):
        outcome = launcher.run(
            command(), "prompt", call=call(f"c{number}", trial=number)
        )
        assert outcome.result == "confluence"
    assert launcher.ledger.snapshot()["headroom"] == 2_000_000
    with pytest.raises(BudgetStop, match="headroom"):
        launcher.run(command(), "prompt", call=call("c17", trial=17))


@pytest.mark.parametrize("mode", ["timeout", "early", "missing", "crash", "mismatch"])
def test_uncertain_and_failed_processes_never_free_reservations(budget, mode):
    launcher, transport = launch(budget, mode)
    if mode in {"missing", "crash", "mismatch"}:
        with pytest.raises((BudgetStop, RuntimeError)):
            launcher.run(command(), "prompt", call=call())
    else:
        launcher.run(command(), "prompt", call=call())
    assert len(transport.commands) == 1
    assert launcher.ledger.snapshot()["exposure"] == 3_000_000


def test_every_phase_and_probe_uses_one_aggregate(budget):
    launcher, _ = launch(budget)
    for i, phase in enumerate(
        ("probe", "sufficiency", "routing", "floor-model", "floor-judge")
    ):
        launcher.run(command(), "prompt", call=call(f"phase{i}", phase=phase))
    assert launcher.ledger.snapshot()["exposure"] == 2_000_000


@pytest.mark.parametrize(
    "extra",
    [
        ["--max-budget-usd", "50"],
        ["--resume", "old"],
        ["--continue"],
        ["--fallback-model=haiku"],
        ["--model", "haiku"],
    ],
)
def test_overrides_and_secondary_launch_paths_refused_before_spawn(budget, extra):
    launcher, transport = launch(budget)
    with pytest.raises(BudgetStop):
        launcher.run(command() + extra, "prompt", call=call())
    assert transport.commands == []
    assert launcher.ledger.snapshot()["calls"] == []


def test_uncontained_transport_and_replay_refused(budget):
    launcher, transport = launch(budget, "uncontained")
    with pytest.raises(BudgetStop):
        launcher.run(command(), "prompt", call=call())
    assert not transport.commands
    with pytest.raises(BudgetStop):
        launcher.replay("confluence-as --help; claude -p spend")


def test_missing_corrupt_and_reinitialized_ledger_fail_closed(budget, tmp_path):
    ledger, binding = budget
    with pytest.raises(FileExistsError):
        Ledger.create(ledger.path, binding)
    with pytest.raises(BudgetStop):
        Ledger(tmp_path / "absent").snapshot()
    ledger.path.write_bytes(b"not a sqlite database")
    with pytest.raises(BudgetStop):
        ledger.snapshot()


def test_evidence_loss_blocks_future_calls(budget):
    launcher, transport = launch(budget)
    launcher.run(command(), "prompt", call=call())
    row = launcher.ledger.snapshot()["calls"][0]
    Path(row["receipt"]["transcript_path"]).unlink()
    with pytest.raises(BudgetStop):
        launcher.run(command(), "prompt", call=call("next", trial=2))
    assert len(transport.commands) == 1


def test_malformed_ledger_is_not_zero_balance(budget):
    ledger, _ = budget
    with sqlite3.connect(ledger.path) as db:
        db.execute("UPDATE metadata SET payload='{}'")
    with pytest.raises(BudgetStop):
        ledger.snapshot()


def reserve_in_process(path, binding, number, queue):
    try:
        Ledger(Path(path)).reserve(call(f"process{number}", trial=number + 1), binding)
        queue.put("reserved")
    except BudgetStop:
        queue.put("stopped")


def crash_after_reserve(path, binding):
    Ledger(Path(path)).reserve(call("crash-process"), binding)
    os._exit(9)


def test_competing_processes_cannot_overbook(budget):
    ledger, binding = budget
    for i in range(15):
        ledger.reserve(call(f"prior{i}", task="prior", trial=i + 1), binding)
    context = multiprocessing.get_context("spawn")
    queue = context.Queue()
    children = [
        context.Process(
            target=reserve_in_process, args=(str(ledger.path), binding, n, queue)
        )
        for n in range(2)
    ]
    for child in children:
        child.start()
    for child in children:
        child.join(15)
        assert child.exitcode == 0
    assert sorted(queue.get(timeout=2) for _ in children) == ["reserved", "stopped"]
    assert ledger.snapshot()["exposure"] == 48_000_000


def test_abrupt_process_death_preserves_durable_reservation(budget):
    ledger, binding = budget
    child = multiprocessing.get_context("spawn").Process(
        target=crash_after_reserve, args=(str(ledger.path), binding)
    )
    child.start()
    child.join(15)
    assert child.exitcode == 9
    assert Ledger(ledger.path).snapshot()["exposure"] == 3_000_000


def test_exclusive_controller_and_secondary_controller_refused(budget):
    ledger, _ = budget
    launcher, transport = launch(budget)
    with ledger.controller(), pytest.raises(BudgetStop, match="controller"):
        launcher.run(command(), "prompt", call=call())
    assert not transport.commands
    launcher.run(command(), "prompt", call=call())


def test_default_production_entry_point_cannot_be_enabled_by_env(monkeypatch):
    monkeypatch.setenv("E2E_SUFFICIENCY", "1")
    monkeypatch.setenv("EVALUATION_BUDGET_APPROVED", "true")
    with pytest.raises(BudgetStop, match="no reviewed"):
        require_launcher()


def test_harness_call_requires_source_pin(monkeypatch):
    monkeypatch.delenv("EVALUATION_SOURCE_COMMIT", raising=False)
    with pytest.raises(BudgetStop):
        harness_call("routing", "confluence-01", 1)
    monkeypatch.setenv("EVALUATION_SOURCE_COMMIT", BASE)
    assert harness_call("routing", "confluence-01", 1).source_commit == BASE


def test_direct_runner_and_replay_cannot_bypass_boundary(tmp_path, monkeypatch):
    from tests.e2e.runner import SufficiencyRunner

    monkeypatch.setenv("EVALUATION_SOURCE_COMMIT", BASE)
    runner = SufficiencyRunner(tmp_path)
    with pytest.raises(BudgetStop):
        runner.run_trial("task1", "prompt", ["confluence-as --help"])
    with pytest.raises(BudgetStop):
        runner._replay_command("confluence-as --help; claude -p spend")


def test_routing_uses_boundary_without_altering_golden_trials():
    # Static guard for the two live modules that must never execute in CI.
    root = Path(__file__).parents[1]
    routing = (root / "skills/confluence/tests/test_routing.py").read_text()
    probe = (root / "tests/e2e/conftest.py").read_text()
    assert "observation = require_launcher().run(" in routing
    assert "auth_probe = launcher.run(" in probe
    assert "launcher = require_launcher()" in probe
    assert '"--max-turns"' in probe


@pytest.mark.parametrize("amount", ["1e-1000085", "0e-1000085", "1e-65", "1e1000000"])
def test_extreme_exponents_fail_closed(budget, amount):
    ledger, binding = budget
    with pytest.raises(BudgetStop):
        microdollars(amount)
    with pytest.raises(BudgetStop):
        ledger.reserve(call(), replace(binding, inflight_usd=amount))
    ledger.reserve(call(), binding)
    with pytest.raises(BudgetStop):
        ledger.reconcile(replace(receipt(ledger, binding, call()), actual_usd=amount))
    assert ledger.snapshot()["exposure"] == 3_000_000
    assert ledger.snapshot()["metadata"]["halted"]


def test_stale_receipt_cannot_reconcile_active_call(budget):
    launcher, transport = launch(budget)
    previous = launcher.run(command(), "prompt", call=call()).receipt

    def stale(*args, **kwargs):
        return Outcome(receipt=previous)

    transport.execute = stale
    with pytest.raises(BudgetStop, match="active call"):
        launcher.run(command(), "prompt", call=call("second", trial=2))
    state = launcher.ledger.snapshot()
    assert state["exposure"] == 3_400_000
    assert state["metadata"]["halted"]
    assert (
        next(r for r in state["calls"] if r["call"]["call_id"] == "second")["status"]
        == "uncertain"
    )


@pytest.mark.parametrize("mode", ["early", "timeout"])
@pytest.mark.parametrize("damage", ["delete", "tamper"])
def test_uncertain_outcome_evidence_loss_stops_next_launch(budget, mode, damage):
    launcher, transport = launch(budget, mode)
    launcher.run(command(), "prompt", call=call())
    evidence = Path(launcher.ledger.snapshot()["calls"][0]["outcome"]["path"])
    if damage == "delete":
        evidence.unlink()
    else:
        evidence.write_text("changed")
    with pytest.raises(BudgetStop, match="evidence"):
        launcher.run(command(), "prompt", call=call("next", trial=2))
    assert len(transport.commands) == 1


def test_restart_restores_observation_without_new_charge(budget):
    launcher, transport = launch(budget, "early")
    initial = launcher.run(command(), "prompt", call=call())
    restored = BudgetLauncher(Ledger(launcher.ledger.path), launcher.binding, transport)
    result = restored.run(command(), "prompt", call=call("new-process-uuid"))
    assert result == initial
    assert len(transport.commands) == 1
    assert restored.ledger.snapshot()["exposure"] == 3_000_000
    for changed_call, prompt in [
        (call("new", trial=1), "changed prompt"),
        (replace(call("new"), source_commit="a" * 40), "prompt"),
    ]:
        with pytest.raises(BudgetStop, match="resume"):
            restored.run(command(), prompt, call=changed_call)


def test_partial_sufficiency_run_resumes_five_identities(budget, tmp_path, monkeypatch):
    from tests.e2e.runner import SufficiencyRunner

    monkeypatch.setenv("EVALUATION_SOURCE_COMMIT", BASE)
    launcher, transport = launch(budget)
    first = SufficiencyRunner(tmp_path, launcher=launcher)
    first.run_task("adopted-task", "prompt", ["confluence-as --help"], 2)
    restarted = SufficiencyRunner(
        tmp_path,
        launcher=BudgetLauncher(
            Ledger(launcher.ledger.path), launcher.binding, transport
        ),
    )
    results = restarted.run_task("adopted-task", "prompt", ["confluence-as --help"], 5)
    assert len(results) == 5
    assert len(transport.commands) == 5
    assert sorted(r["call"]["trial"] for r in launcher.ledger.snapshot()["calls"]) == [
        1,
        2,
        3,
        4,
        5,
    ]


@pytest.mark.parametrize("outcome", [Outcome(timed_out=True), Outcome(early_stop=True)])
def test_auth_probe_fixture_rejects_incomplete_outcome(monkeypatch, outcome):
    from types import SimpleNamespace

    from tests.e2e import conftest as fixtures

    monkeypatch.setenv("EVALUATION_SOURCE_COMMIT", BASE)
    monkeypatch.setattr(
        fixtures,
        "require_launcher",
        lambda: SimpleNamespace(run=lambda *a, **k: outcome),
    )
    probes = []

    def version_probe(argv, **kwargs):
        probes.append(argv)
        return SimpleNamespace(returncode=0, stdout="version 2.0.0", stderr="")

    monkeypatch.setattr(fixtures.subprocess, "run", version_probe)
    request = SimpleNamespace(
        config=SimpleNamespace(getoption=lambda name: "claude-sonnet-5")
    )
    with pytest.raises(pytest.fail.Exception, match="probe incomplete"):
        fixtures._sufficiency_gate.__wrapped__(request, True, {})
    assert probes == [["claude", "--version"]]


def test_routing_restart_preserves_first_skill_and_trial_count(budget, monkeypatch):
    from skills.confluence.tests import test_routing as routing

    monkeypatch.setenv("EVALUATION_SOURCE_COMMIT", BASE)
    launcher, transport = launch(budget, "early")
    monkeypatch.setattr(routing, "require_launcher", lambda: launcher)
    monkeypatch.setattr(routing, "get_test_model", lambda: "claude-sonnet-5")
    # Use a task-local evidence directory, not the import-time shared directory.
    monkeypatch.setattr(routing, "_ROUTING_RUN_DIR", launcher.ledger.path.parent)
    monkeypatch.setattr(routing, "_ROUTING_TRIAL_COUNTERS", {})
    monkeypatch.setattr(routing, "_ROUTING_SUMMARY", {"prompts": {}})
    first = routing.run_claude_routing("confluence-01", "prompt")
    assert first.skill_loaded == "confluence"
    monkeypatch.setattr(routing, "_ROUTING_TRIAL_COUNTERS", {})
    second = routing.run_claude_routing("confluence-01", "prompt")
    assert second.skill_loaded == first.skill_loaded
    assert len(transport.commands) == 1

    restored_transcript = (
        launcher.ledger.path.parent / "confluence-01-1.transcript.jsonl"
    )
    assert restored_transcript.read_text().splitlines() == ['{"type":"assistant"}']


@pytest.mark.parametrize("mode", ["early", "timeout"])
@pytest.mark.parametrize(
    "field,value",
    [
        ("model", "wrong"),
        ("provider", "wrong"),
        ("billing", "wrong"),
        ("binding_sha256", "0" * 64),
        ("actual_usd", "4"),
        ("actual_usd", "NaN"),
        ("reported_cost_usd", "bad"),
        ("usage", {}),
        ("proof_sha256", "0" * 64),
    ],
)
def test_partial_receipt_invalidity_halts_later_launches(budget, mode, field, value):
    launcher, transport = launch(budget, mode)
    executions = []

    def partial(cmd, prompt, *, call, **kwargs):
        executions.append(call.call_id)
        charge = replace(
            receipt(launcher.ledger, launcher.binding, call), **{field: value}
        )
        return Outcome(
            timed_out=mode == "timeout", early_stop=mode == "early", receipt=charge
        )

    transport.execute = partial
    with pytest.raises(BudgetStop):
        launcher.run(command(), "prompt", call=call())
    state = launcher.ledger.snapshot()
    assert state["metadata"]["halted"]
    assert state["exposure"] == 3_000_000
    assert state["calls"][0]["outcome"] is not None
    with pytest.raises(BudgetStop, match="halted"):
        launcher.run(command(), "prompt", call=call("second", trial=2))
    assert executions == ["call1"]


@pytest.mark.parametrize("mode", ["early", "timeout"])
def test_valid_partial_receipt_still_retains_full_reservation(budget, mode):
    launcher, transport = launch(budget, mode)

    def partial(cmd, prompt, *, call, **kwargs):
        return Outcome(
            timed_out=mode == "timeout",
            early_stop=mode == "early",
            receipt=receipt(launcher.ledger, launcher.binding, call),
        )

    transport.execute = partial
    launcher.run(command(), "prompt", call=call())
    state = launcher.ledger.snapshot()
    assert not state["metadata"]["halted"]
    assert state["exposure"] == 3_000_000
    launcher.run(command(), "prompt", call=call("second", trial=2))
    assert launcher.ledger.snapshot()["exposure"] == 6_000_000


@pytest.mark.parametrize("mode", ["early", "timeout"])
@pytest.mark.parametrize("field", ["transcript_path", "proof_path"])
@pytest.mark.parametrize("damage", ["delete", "tamper"])
def test_partial_receipt_evidence_loss_blocks_restart_and_next_call(
    budget, mode, field, damage
):
    launcher, transport = launch(budget, mode)
    executions = []

    def partial(cmd, prompt, *, call, **kwargs):
        executions.append(call.call_id)
        return Outcome(
            timed_out=mode == "timeout",
            early_stop=mode == "early",
            receipt=receipt(launcher.ledger, launcher.binding, call),
        )

    transport.execute = partial
    launcher.run(command(), "prompt", call=call())
    row = launcher.ledger.snapshot()["calls"][0]
    assert row["partial_receipt"] is not None
    assert row["actual"] is None
    assert row["reservation"] == 3_000_000
    evidence = Path(row["partial_receipt"][field])
    if damage == "delete":
        evidence.unlink()
    else:
        evidence.write_text("tampered")
    restarted = BudgetLauncher(
        Ledger(launcher.ledger.path), launcher.binding, transport
    )
    for invocation in (call("restart-uuid"), call("next", trial=2)):
        with pytest.raises(BudgetStop, match="evidence"):
            restarted.run(command(), "prompt", call=invocation)
    assert executions == ["call1"]


@pytest.mark.parametrize("field", ["transcript_path", "proof_path"])
@pytest.mark.parametrize("damage", ["delete", "tamper"])
def test_crash_after_outcome_before_reconciliation_checks_receipt_evidence(
    budget, field, damage
):
    ledger, binding = budget
    invocation = call()
    ledger.reserve(invocation, binding, "a" * 64)
    charge = receipt(ledger, binding, invocation)
    ledger.record_outcome(invocation.call_id, Outcome(receipt=charge))
    state = ledger.snapshot()
    assert state["calls"][0]["status"] == "reserved"
    assert state["calls"][0]["partial_receipt"] is not None
    assert state["exposure"] == 3_000_000
    path = Path(getattr(charge, field))
    if damage == "delete":
        path.unlink()
    else:
        path.write_text("tampered")
    reopened = Ledger(ledger.path)
    with pytest.raises(BudgetStop, match="evidence"):
        reopened.snapshot()
    with pytest.raises(BudgetStop, match="evidence"):
        reopened.reserve(call("next", trial=2), binding)
    with pytest.raises(BudgetStop, match="evidence"):
        reopened.cached(call("new-uuid"), binding, "a" * 64)


def test_missing_terminal_cost_halt_is_atomic_with_outcome(budget):
    ledger, binding = budget
    invocation = call()
    ledger.reserve(invocation, binding, "a" * 64)
    with pytest.raises(BudgetStop, match="terminal accounting missing"):
        ledger.record_outcome(invocation.call_id, Outcome(lines=['{"type":"result"}']))
    reopened = Ledger(ledger.path)
    state = reopened.snapshot()
    assert state["metadata"]["halted"]
    assert state["calls"][0]["status"] == "uncertain"
    assert state["calls"][0]["stop_reason"] == "missing-cost"
    assert state["calls"][0]["outcome"] is not None
    assert state["exposure"] == 3_000_000
    with pytest.raises(BudgetStop, match="halted"):
        reopened.reserve(call("next", trial=2), binding)
    with pytest.raises(BudgetStop, match="halted"):
        reopened.cached(call("new-uuid"), binding, "a" * 64)


@pytest.mark.parametrize("flag", ["timed_out", "early_stop"])
def test_malformed_stop_flags_cannot_disguise_terminal_missing_cost(budget, flag):
    ledger, binding = budget
    invocation = call()
    ledger.reserve(invocation, binding)
    outcome = Outcome(**{flag: "false"})
    with pytest.raises(BudgetStop, match="stop flags"):
        ledger.record_outcome(invocation.call_id, outcome)
    assert ledger.snapshot()["metadata"]["halted"]
    assert ledger.snapshot()["exposure"] == 3_000_000
