"""Third recovery/resumption fixtures: no canonical copy, provider or credential."""

import json
import os
import sqlite3
import subprocess
import sys
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from tests import (
    evaluation_budget as D,
    joint_evaluation as J,
    test_joint_evaluation as T,
)
from tests.test_charged_recovery import (
    recovery as recovery,
    rewrite_plan,
    run_recovery,
    sha,
)
from tests.test_joint_evaluation import reg as reg
from tests.test_second_recovery import second as second, sql_state


@pytest.fixture
def third(second, monkeypatch):
    f = second
    run_recovery(f)
    prior = f.new

    class ProbeProvider(T.FakeProvider):
        def message(self, request, **kwargs):
            value = super().message(request, **kwargs)
            value["usage"]["input_tokens"] = 6492
            return value

    original = T.claude_report

    def probe_report(binding):
        report = original(binding)
        report["usage"]["input_tokens"] = 6492
        report["modelUsage"][binding.model]["inputTokens"] = 6492
        report["total_cost_usd"] = report["modelUsage"][binding.model]["costUSD"] = (
            0.006502
        )
        return report

    monkeypatch.setattr(T, "claude_report", probe_report)
    transport = J.ProductionTransport(
        {"files": {}, "evidence_root": str(f.path.parent / "probe-evidence")},
        prior,
        T.FakeOAuthCLI(prior),
        ProbeProvider(),
    )
    probe = D.Call("probe-v3", "probe", "oauth-equivalent-accounting-v3", 1, "a" * 40)
    outcome = J.JointLauncher(
        f.ledger, prior.binding("floor-haiku45-api"), transport
    ).run(
        [
            "claude",
            "--print",
            "--model",
            prior.binding("floor-haiku45-api").model,
        ],
        "Reply OK.",
        call=probe,
        timeout=5,
    )
    assert outcome.receipt.actual_usd == "0.006502"
    monkeypatch.setattr(T, "claude_report", original)
    bad = D.Call("failed-plugin", "sufficiency", "read-page", 1, "a" * 40)
    f.ledger.reserve(bad, prior.binding("plugin-sonnet5-api"))
    f.ledger.uncertain(bad.call_id, "interrupted", halt=True)
    before = sql_state(f.ledger)
    with sqlite3.connect(f.ledger.path) as db:
        raw_meta = db.execute("SELECT payload FROM metadata").fetchone()[0]
    proof = f.path.parent / "proof-v4.json"
    proof.write_text('{"fixture_v4":true}')
    f.new = replace(
        prior,
        evidence_path=str(proof),
        evidence_sha256=sha(proof),
        bindings=tuple(
            replace(b, evidence_path=str(proof), evidence_sha256=sha(proof))
            for b in prior.bindings
        ),
    )
    folder = f.path.parent / "evidence-plugin"
    folder.mkdir()
    (folder / "stop.json").write_text('{"upstream_status":400}')
    inventory = []
    for i, identity, payload in before["calls"]:
        row = json.loads(payload)
        inventory.append(
            {
                "call_id": i,
                "identity_sha256": D._raw_sha(identity),
                "payload_sha256": D._raw_sha(payload),
                "reservation_microdollars": row["reservation"],
                "accounting_status": "charged-uncertain"
                if i in {"probe-v1", "probe-v2"}
                else row["status"],
                "actual_microdollars": row["actual"],
            }
        )
    target = next(i for i in inventory if i["call_id"] == bad.call_id)
    seq, pay, digest = before["registry_transitions"][-1]
    f.second_plan = f.path
    f.path = f.path.parent / "plan-v3.json"
    f.plan = {
        **f.plan,
        "schema_version": 3,
        "transition_id": "third-commissioned-fixture",
        "expected_ledger_sha256": sha(f.ledger.path),
        "expected_metadata_sha256": D._raw_sha(raw_meta),
        "old_registry_sha256": prior.digest,
        "new_registry_sha256": f.new.digest,
        "call": {
            k: v
            for k, v in target.items()
            if k not in {"accounting_status", "actual_microdollars"}
        },
        "evidence_directory": str(folder),
        "evidence": [
            {"path": str(folder / "stop.json"), "sha256": sha(folder / "stop.json")}
        ],
        "previous_transition": {
            "sequence": seq,
            "record_sha256": digest,
            "payload_sha256": D._raw_sha(pay),
        },
        "expected_calls": inventory,
        "expected_charges": [
            dict(
                zip(
                    ("call_id", "payload_sha256", "amount", "transition_sha256"),
                    r,
                    strict=True,
                )
            )
            for r in before["charged_uncertain"]
        ],
        "expected_exposure_microdollars": 3447464,
        "retry": {
            "binding_id": "plugin-sonnet5-api",
            "phase": "sufficiency",
            "task": "read-page",
            "trial": 1,
            "from_attempt": 1,
            "to_attempt": 2,
        },
    }
    rewrite_plan(f)
    f.third_before = before
    f.probe = probe
    f.probe_receipt = outcome.receipt
    f.prior_third = prior
    return f


def test_third_link_preserves_all_four_rows_history_and_trusted_settlement(third):
    f = third
    result = run_recovery(f)
    assert (
        result["newly_consumed_microdollars"] == 3020480
        and result["cumulative_consumed_microdollars"] == 3440962
        and result["exposure_microdollars"] == 3447464
    )
    now = sql_state(f.ledger)
    assert (
        now["calls"] == f.third_before["calls"]
        and now["registry_transitions"][:2] == f.third_before["registry_transitions"]
    )
    snapshot = f.ledger.snapshot()
    assert snapshot["exposure"] == 3447464
    settled = next(r for r in snapshot["calls"] if r["call"]["call_id"] == "probe-v3")
    assert (
        settled["status"] == "settled"
        and settled["actual"] == 6502
        and settled["receipt"] == asdict(f.probe_receipt)
    )
    before = sha(f.ledger.path)
    f.ledger.reconcile(f.probe_receipt)
    assert sha(f.ledger.path) == before
    assert J.reconcile_existing(f.ledger)["exposure"] == 3447464
    assert run_recovery(f)["already_applied"] is True and sha(f.ledger.path) == before
    assert sha(f.marker) == f.marker_sha


def test_plan_bound_attempt2_replays_without_reserve_dispatch_or_recharge(third):
    f = third
    run_recovery(f)
    provider = T.FakeProvider()
    transport = J.ProductionTransport(
        {"files": {}, "evidence_root": str(f.path.parent / "resumed")},
        f.new,
        T.FakeOAuthCLI(f.new),
        provider,
    )
    launcher = J.JointLauncher(f.ledger, f.new.binding("plugin-sonnet5-api"), transport)

    def request(identifier, task="read-page", trial=1):
        return launcher.run(
            ["claude", "--print", "--model", launcher.binding.model],
            "fixture prompt",
            call=D.Call(identifier, "sufficiency", task, trial, "b" * 40),
            timeout=5,
        )

    first = request("fresh-uuid")
    assert len(provider.calls) == 1
    attempt = next(r for r in f.ledger.snapshot()["calls"] if r["call"]["attempt"] == 2)
    assert (
        attempt["call"]["call_id"] == first.receipt.call_id
        and attempt["call"]["call_id"] != "failed-plugin"
    )
    state = sql_state(f.ledger)
    exposure = f.ledger.snapshot()["exposure"]
    before = sha(f.ledger.path)
    # Same packet process restart: fresh launcher/UUID, same exact paid request.
    fresh = J.JointLauncher(f.ledger, launcher.binding, transport)
    replay = fresh.run(
        ["claude", "--print", "--model", launcher.binding.model],
        "fixture prompt",
        call=D.Call("another-uuid", "sufficiency", "read-page", 1, "b" * 40),
        timeout=5,
    )
    assert replay == first and len(provider.calls) == 1 and sha(f.ledger.path) == before
    assert sql_state(f.ledger) == state and f.ledger.snapshot()["exposure"] == exposure
    request("second-task", "read-page", 2)
    assert len(provider.calls) == 2
    with pytest.raises(D.BudgetStop, match="unreviewed retry"):
        launcher.run(
            ["claude", "--print", "--model", launcher.binding.model],
            "fixture prompt",
            call=D.Call("forbidden3", "sufficiency", "read-page", 1, "b" * 40, 3),
            timeout=5,
        )
    with pytest.raises(D.BudgetStop, match="resume source or request mismatch"):
        launcher.run(
            ["claude", "--print", "--model", launcher.binding.model],
            "DIFFERENT",
            call=D.Call("changed-prompt", "sufficiency", "read-page", 2, "b" * 40),
            timeout=5,
        )
    assert len(provider.calls) == 2


@pytest.mark.parametrize(
    "kind",
    [
        "prior-link",
        "inventory",
        "settled-actual",
        "charge",
        "retry3",
        "retry-other",
        "evidence",
        "root",
        "exposure",
        "review",
    ],
)
def test_third_plan_mismatches_refuse_without_writes(third, kind):
    f = third
    if kind == "prior-link":
        f.plan["previous_transition"]["payload_sha256"] = "0" * 64
    elif kind == "inventory":
        f.plan["expected_calls"][0]["payload_sha256"] = "0" * 64
    elif kind == "settled-actual":
        next(
            i for i in f.plan["expected_calls"] if i["accounting_status"] == "settled"
        )["actual_microdollars"] = 0
    elif kind == "charge":
        f.plan["expected_charges"][0]["amount"] = 0
    elif kind == "retry3":
        f.plan["retry"]["to_attempt"] = 3
    elif kind == "retry-other":
        f.plan["retry"]["task"] = "search-cql"
    elif kind == "evidence":
        Path(f.plan["evidence"][0]["path"]).write_text("tamper")
    elif kind == "root":
        f.plan["original_registry_sha256"] = "0" * 64
    elif kind == "exposure":
        f.plan["expected_exposure_microdollars"] = 3440962
    elif kind == "review":
        Path(f.plan["provenance"]["reviews"][0]["path"]).write_text("Verdict: REVISE")
    rewrite_plan(f)
    before = sha(f.ledger.path)
    with pytest.raises(D.BudgetStop):
        run_recovery(f)
    assert sha(f.ledger.path) == before


@pytest.mark.parametrize(
    "kind",
    [
        "historical-settled",
        "old-row",
        "first-link",
        "second-link",
        "third-link",
        "old-map",
        "new-map",
        "evidence",
    ],
)
def test_third_state_tampering_is_detected(third, kind):
    f = third
    run_recovery(f)
    if kind == "evidence":
        Path(f.plan["evidence"][0]["path"]).write_text("tamper")
    else:
        with sqlite3.connect(f.ledger.path) as db:
            for name in D.RECOVERY_TRIGGERS | D.SETTLED_TRIGGERS:
                db.execute(f"DROP TRIGGER {name}")
            if kind in {"historical-settled", "old-row"}:
                identity = "probe-v3" if kind == "historical-settled" else "probe-v1"
                raw = db.execute(
                    "SELECT payload FROM calls WHERE id=?", (identity,)
                ).fetchone()[0]
                data = json.loads(raw)
                data["actual"] = 0
                db.execute(
                    "UPDATE calls SET payload=? WHERE id=?",
                    (json.dumps(data), identity),
                )
            elif kind.endswith("link"):
                db.execute(
                    "UPDATE registry_transitions SET sha256=? WHERE seq=?",
                    (
                        "0" * 64,
                        {"first-link": 1, "second-link": 2, "third-link": 3}[kind],
                    ),
                )
            else:
                db.execute(
                    "DELETE FROM charged_uncertain WHERE call_id=?",
                    ("probe-v1" if kind == "old-map" else "failed-plugin",),
                )
            for sql in (D.RECOVERY_TRIGGERS | D.SETTLED_TRIGGERS).values():
                db.execute(sql)
    with pytest.raises(D.BudgetStop):
        f.ledger.snapshot()
    with pytest.raises(D.BudgetStop):
        run_recovery(f)


@pytest.mark.parametrize("point", ["mid-charge", "mid-metadata", "after-commit"])
def test_third_transition_process_death_restarts_atomically(third, point):
    f = third
    code = r"""
import os,sys,sqlite3,json
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from tests import evaluation_budget as D
from tests.test_joint_evaluation import reg as reg
ledger=D.Ledger(Path(sys.argv[2]));plan=Path(sys.argv[3]);registry=D.Registry.from_dict(json.loads(Path(sys.argv[4]).read_text()));point=sys.argv[5]
original=sqlite3.connect
class Proxy:
 def __init__(self,db):self.db=db
 def execute(self,sql,*args):
  result=self.db.execute(sql,*args)
  if (point=='mid-charge' and sql.startswith('INSERT INTO charged_uncertain')) or (point=='mid-metadata' and sql.startswith('UPDATE metadata')):os._exit(73)
  return result
 def commit(self):
  self.db.commit()
  if point=='after-commit':os._exit(73)
 def __getattr__(self,key):return getattr(self.db,key)
D.sqlite3.connect=lambda *a,**kw:Proxy(original(*a,**kw))
ledger.recover_and_transition(plan,D.hashlib.sha256(plan.read_bytes()).hexdigest(),registry)
"""
    registry_file = f.path.parent / "fixture-registry.json"
    registry_file.write_text(json.dumps(asdict(f.new)))
    env = {
        k: os.environ[k]
        for k in os.environ
        if not k.startswith(("ANTHROPIC_", "CLAUDE_", "DEMO_"))
        and k not in ("PYTHONPATH", "PYTEST_ADDOPTS")
    }
    child = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-X",
            "pycache_prefix=/dev/null",
            "-c",
            code,
            str(Path(D.__file__).parents[1]),
            str(f.ledger.path),
            str(f.path),
            str(registry_file),
            point,
        ],
        env=env,
        capture_output=True,
        text=True,
    )
    assert child.returncode == 73, child.stderr
    result = run_recovery(f)
    assert result["already_applied"] == (point == "after-commit")
    assert f.ledger.snapshot()["exposure"] == 3447464
    now = sql_state(f.ledger)
    assert (
        now["calls"] == f.third_before["calls"]
        and now["registry_transitions"][:2] == f.third_before["registry_transitions"]
    )


def test_duplicate_third_recovery_preserves_later_halt_and_refuses_fourth(third):
    f = third
    run_recovery(f)
    new = D.Call("later", "floor-trial", "later", 1, "b" * 40)
    f.ledger.reserve(new, f.new.binding("floor-haiku45-api"))
    f.ledger.uncertain("later", "interrupted", halt=True)
    before = sha(f.ledger.path)
    result = run_recovery(f)
    assert (
        result["already_applied"]
        and result["halted"]
        and result["newly_consumed_microdollars"] == 0
    )
    assert (
        result["cumulative_consumed_microdollars"] == 3440962
        and result["exposure_microdollars"] == 3657705
        and sha(f.ledger.path) == before
    )
    f.plan["schema_version"] = 4
    rewrite_plan(f)
    with pytest.raises(D.BudgetStop):
        run_recovery(f)
    assert sha(f.ledger.path) == before


def test_resumed_partial_run_order_and_replay_bound(third):
    f = third
    run_recovery(f)
    provider = T.FakeProvider()
    transport = J.ProductionTransport(
        {"files": {}, "evidence_root": str(f.path.parent / "order")},
        f.new,
        T.FakeOAuthCLI(f.new),
        provider,
    )

    def run_items(count):
        launcher = J.JointLauncher(
            f.ledger, f.new.binding("plugin-sonnet5-api"), transport
        )
        result = []
        for trial in range(1, count + 1):
            call = D.Call(
                f"uuid-{count}-{trial}", "sufficiency", "read-page", trial, "b" * 40
            )
            outcome = launcher.run(
                ["claude", "--print", "--model", launcher.binding.model],
                f"prompt-{trial}",
                call=call,
                timeout=5,
            )
            result.append(outcome.receipt.call_id)
        return result

    first = run_items(2)
    assert len(provider.calls) == 2
    exposure = f.ledger.snapshot()["exposure"]
    resumed = run_items(5)
    assert resumed[:2] == first and len(provider.calls) == 5
    assert f.ledger.snapshot()["exposure"] == exposure + 3 * 34
    before = sha(f.ledger.path)
    assert (
        run_items(5) == resumed
        and sha(f.ledger.path) == before
        and len(provider.calls) == 5
    )
    # No caller source/prompt drift or unknown retry may silently reuse history.
    with pytest.raises(D.BudgetStop):
        J.JointLauncher(f.ledger, f.new.binding("plugin-sonnet5-api"), transport).run(
            ["claude", "--print", "--model", "claude-sonnet-5"],
            "prompt-2",
            call=D.Call("source-drift", "sufficiency", "read-page", 2, "d" * 40),
            timeout=5,
        )
    assert len(provider.calls) == 5


def test_exact_logical_plugin_coverage_excludes_only_reviewed_predecessor():
    import yaml

    root = Path(J.__file__).parents[1]
    items = []
    for phase, path, key in [
        ("sufficiency", root / "tests/e2e/test_cases.yaml", "tasks"),
        ("routing", root / "skills/confluence/tests/routing_golden.yaml", "tests"),
    ]:
        for task in yaml.safe_load(path.read_text())[key]:
            for trial in range(1, 6):
                items.append(
                    {
                        "call": {
                            "phase": phase,
                            "task": task["id"],
                            "trial": trial,
                            "attempt": 2
                            if (phase, task["id"], trial)
                            == ("sufficiency", "read-page", 1)
                            else 1,
                        },
                        "binding_id": "plugin-sonnet5-api",
                        "status": "settled",
                        "receipt": {"fixture": True},
                        "outcome": {"fixture": True},
                    }
                )
    predecessor = {
        "call": {"phase": "sufficiency", "task": "read-page", "trial": 1, "attempt": 1},
        "binding_id": "plugin-sonnet5-api",
        "status": "charged-uncertain",
    }
    J.check_plugin_completion([predecessor, *items])
    for bad in [
        items,
        [predecessor, *items[:-1]],
        [predecessor, *items, items[-1]],
        [predecessor, {**items[0], "status": "uncertain"}, *items[1:]],
    ]:
        with pytest.raises(D.BudgetStop):
            J.check_plugin_completion(bad)


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM calls WHERE id='probe-v3'",
        "UPDATE calls SET payload='{}' WHERE id='probe-v3'",
        "UPDATE calls SET id='changed-id' WHERE id='probe-v3'",
        "INSERT OR REPLACE INTO calls SELECT id,identity,'{}' FROM calls WHERE id='probe-v3'",
        "INSERT OR REPLACE INTO calls SELECT 'changed-id',identity,'{}' FROM calls WHERE id='probe-v3'",
        "UPDATE OR REPLACE calls SET id='probe-v3' WHERE id='ordinary'",
        "UPDATE OR REPLACE calls SET identity=(SELECT identity FROM calls WHERE id='probe-v3') WHERE id='ordinary'",
    ],
)
def test_historical_settled_sql_collision_and_mutation_guards(third, sql):
    f = third
    run_recovery(f)
    if sql.startswith("UPDATE OR REPLACE"):
        f.ledger.reserve(
            D.Call("ordinary", "floor-trial", "ordinary", 1, "b" * 40),
            f.new.binding("floor-haiku45-api"),
        )
    before = sql_state(f.ledger)
    exposure = f.ledger.snapshot()["exposure"]
    with sqlite3.connect(f.ledger.path) as db, pytest.raises(sqlite3.IntegrityError):
        db.execute(sql)
    assert sql_state(f.ledger) == before and f.ledger.snapshot()["exposure"] == exposure


def test_uncertain_with_valid_outcome_is_never_replayed_as_success(tmp_path, reg):
    launch, provider = T.launcher(tmp_path, reg)
    first = T.call()
    launch.run(
        ["claude", "--print", "--model", launch.binding.model],
        "fixture prompt",
        call=first,
        timeout=5,
    )
    # Synthetic otherwise valid interrupted row, not production evidence.
    with sqlite3.connect(launch.ledger.path) as db:
        row = json.loads(
            db.execute(
                "SELECT payload FROM calls WHERE id=?", (first.call_id,)
            ).fetchone()[0]
        )
        row.update(
            status="uncertain", actual=None, receipt=None, stop_reason="interrupted"
        )
        db.execute(
            "UPDATE calls SET payload=? WHERE id=?", (json.dumps(row), first.call_id)
        )
    before = sha(launch.ledger.path)
    with pytest.raises(D.BudgetStop, match="incomplete prior call"):
        launch.run(
            ["claude", "--print", "--model", launch.binding.model],
            "fixture prompt",
            call=replace(first, call_id="new-uuid"),
            timeout=5,
        )
    assert len(provider.calls) == 1 and sha(launch.ledger.path) == before
