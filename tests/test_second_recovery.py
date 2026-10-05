"""Second charged recovery against locally constructed fixtures only."""

import json
import os
import sqlite3
import subprocess
import sys
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from tests import evaluation_budget as D
from tests.test_charged_recovery import (
    recovery as recovery,
    rewrite_plan,
    run_recovery,
    sha,
)
from tests.test_joint_evaluation import reg as reg


def sql_state(ledger):
    with sqlite3.connect(ledger.path) as db:
        return {
            table: db.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()
            for table in ("calls", "registry_transitions", "charged_uncertain")
        }


@pytest.fixture
def second(recovery):
    f = recovery
    run_recovery(f)
    first_state = sql_state(f.ledger)
    first_plan = f.path
    binding = f.new.binding("floor-haiku45-api")
    call = D.Call("probe-v2", "probe", "oauth-equivalent-accounting-v2", 1, "a" * 40)
    f.ledger.reserve(call, binding)
    f.ledger.uncertain(call.call_id, "interrupted", halt=True)
    prior = f.new
    proof = f.path.parent / "proof-v3.json"
    proof.write_text('{"reviewed_fixture_v3":true}')
    f.new = replace(
        prior,
        evidence_path=str(proof),
        evidence_sha256=sha(proof),
        bindings=tuple(
            replace(b, evidence_path=str(proof), evidence_sha256=sha(proof))
            for b in prior.bindings
        ),
    )
    folder = f.path.parent / "evidence-v2"
    folder.mkdir()
    (folder / "stop.json").write_text('{"upstream_status":400}')
    state = sql_state(f.ledger)
    rows = {i: json.loads(payload) for i, identity, payload in state["calls"]}
    with sqlite3.connect(f.ledger.path) as db:
        raw_meta = db.execute("SELECT payload FROM metadata").fetchone()[0]
    target = next(
        (i, identity, payload)
        for i, identity, payload in state["calls"]
        if i == call.call_id
    )

    def entry(i, identity, payload, status):
        return {
            "call_id": i,
            "identity_sha256": D._raw_sha(identity),
            "payload_sha256": D._raw_sha(payload),
            "reservation_microdollars": rows[i]["reservation"],
            "accounting_status": status,
        }

    first_record = first_state["registry_transitions"][0]
    f.path = f.path.parent / "plan-v2.json"
    f.plan = {
        **f.plan,
        "schema_version": 2,
        "transition_id": "fixture-second-charged-recovery",
        "expected_ledger_sha256": sha(f.ledger.path),
        "expected_metadata_sha256": D._raw_sha(raw_meta),
        "old_registry_sha256": prior.digest,
        "new_registry_sha256": f.new.digest,
        "call": {
            k: v
            for k, v in entry(*target, "uncertain").items()
            if k != "accounting_status"
        },
        "evidence_directory": str(folder),
        "evidence": [
            {"path": str(folder / "stop.json"), "sha256": sha(folder / "stop.json")}
        ],
        "original_registry_sha256": f.old.digest,
        "previous_transition": {
            "sequence": 1,
            "record_sha256": first_record[2],
            "payload_sha256": D._raw_sha(first_record[1]),
        },
        "expected_calls": [
            entry(
                i,
                identity,
                payload,
                "charged-uncertain" if i == "probe-v1" else "uncertain",
            )
            for i, identity, payload in state["calls"]
        ],
        "expected_charges": [
            dict(
                zip(
                    ("call_id", "payload_sha256", "amount", "transition_sha256"),
                    first_state["charged_uncertain"][0],
                    strict=False,
                )
            )
        ],
        "expected_exposure_microdollars": 420482,
    }
    rewrite_plan(f)
    f.first_plan = first_plan
    f.prior = prior
    f.first_state = first_state
    f.before_state = state
    return f


def test_second_transition_preserves_all_old_rows_maps_and_chain(second):
    f = second
    marker = sha(f.ledger.path.with_suffix(".init.json"))
    result = run_recovery(f)
    assert result["newly_consumed_microdollars"] == 210241
    assert (
        result["cumulative_consumed_microdollars"]
        == result["exposure_microdollars"]
        == 420482
    )
    now = sql_state(f.ledger)
    assert now["calls"] == f.before_state["calls"]
    assert now["registry_transitions"][0] == f.first_state["registry_transitions"][0]
    assert now["charged_uncertain"][0] == f.first_state["charged_uncertain"][0]
    link = json.loads(now["registry_transitions"][1][1])
    assert (
        link["previous_hash"] == now["registry_transitions"][0][2]
        and link["sequence"] == 2
    )
    assert (
        link["from_registry_sha256"] == f.prior.digest
        and link["to_registry_sha256"] == f.new.digest
    )
    assert marker == sha(f.ledger.path.with_suffix(".init.json"))
    assert not f.ledger.snapshot()["metadata"]["halted"]
    assert {r["status"] for r in f.ledger.snapshot()["calls"]} == {"charged-uncertain"}
    before = sha(f.ledger.path)
    assert (
        run_recovery(f)["already_applied"]
        and run_recovery(f)["newly_consumed_microdollars"] == 0
    )
    assert sha(f.ledger.path) == before
    with pytest.raises(D.BudgetStop):
        f.ledger.recover_and_transition(f.first_plan, sha(f.first_plan), f.prior)


def test_second_recovery_duplicate_preserves_later_halt_and_cap(second):
    f = second
    run_recovery(f)
    binding = f.new.binding("floor-haiku45-api")
    f.ledger.reserve(D.Call("probe-v3", "probe", "v3", 1, "a" * 40), binding)
    f.ledger.uncertain("probe-v3", "interrupted", halt=True)
    before = sha(f.ledger.path)
    result = run_recovery(f)
    assert result["halted"] and result["exposure_microdollars"] == 630723
    assert (
        result["cumulative_consumed_microdollars"] == 420482
        and sha(f.ledger.path) == before
    )
    for call_id in ("probe-v1", "probe-v2"):
        with pytest.raises(D.BudgetStop):
            f.ledger.uncertain(call_id, "interrupted")
    with pytest.raises(D.BudgetStop):
        f.ledger.reserve(
            D.Call("too-large", "probe", "cap", 1, "a" * 40),
            replace(binding, session_cap_usd="49.6"),
        )


@pytest.mark.parametrize(
    "kind",
    [
        "prior-payload",
        "prior-hash",
        "root-marker",
        "inventory",
        "mapping",
        "exposure",
        "target-evidence",
        "review",
        "third-link",
    ],
)
def test_second_transition_refuses_every_mismatch_without_writes(second, kind):
    f = second
    if kind == "prior-payload":
        f.plan["previous_transition"]["payload_sha256"] = "0" * 64
    elif kind == "prior-hash":
        f.plan["previous_transition"]["record_sha256"] = "0" * 64
    elif kind == "root-marker":
        f.plan["original_registry_sha256"] = f.prior.digest
    elif kind == "inventory":
        f.plan["expected_calls"][0]["identity_sha256"] = "0" * 64
    elif kind == "mapping":
        f.plan["expected_charges"][0]["amount"] = 0
    elif kind == "exposure":
        f.plan["expected_exposure_microdollars"] = 210241
    elif kind == "target-evidence":
        Path(f.plan["evidence"][0]["path"]).write_text("tamper")
    elif kind == "review":
        Path(f.plan["provenance"]["reviews"][0]["path"]).write_text("Verdict: REVISE")
    elif kind == "third-link":
        f.plan["previous_transition"]["sequence"] = 2
    rewrite_plan(f)
    before = sha(f.ledger.path)
    with pytest.raises(D.BudgetStop):
        run_recovery(f)
    assert sha(f.ledger.path) == before


@pytest.mark.parametrize("point", ["mid-charge", "mid-metadata", "after-commit"])
def test_second_transition_process_death_restarts_atomically(second, point):
    f = second
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
    assert f.ledger.snapshot()["exposure"] == 420482
    now = sql_state(f.ledger)
    assert (
        now["calls"] == f.before_state["calls"]
        and now["registry_transitions"][0] == f.first_state["registry_transitions"][0]
    )


def test_real_fifty_dollar_headroom_counts_both_charges_once(second):
    f = second
    run_recovery(f)
    binding = f.new.binding("floor-opus55-api")
    index = 0
    while f.ledger.snapshot()["exposure"] + binding.validate() <= D.CAP:
        f.ledger.reserve(
            D.Call(f"ordinary-{index}", "floor-trial", f"task-{index}", 1, "a" * 40),
            binding,
        )
        index += 1
    before = f.ledger.snapshot()["exposure"]
    with pytest.raises(D.BudgetStop, match="headroom"):
        f.ledger.reserve(
            D.Call("over-cap", "floor-trial", "over-cap", 1, "a" * 40), binding
        )
    assert f.ledger.snapshot()["exposure"] == before <= 50000000
    assert before == 420482 + index * binding.validate()


@pytest.mark.parametrize(
    "kind",
    [
        "first-record",
        "second-record",
        "first-evidence",
        "second-evidence",
        "first-row",
        "second-row",
        "active-registry",
        "mapping",
    ],
)
def test_two_link_read_refuses_any_tampered_history(second, kind):
    f = second
    run_recovery(f)
    if kind.endswith("evidence"):
        plan = json.loads(
            (f.first_plan if kind == "first-evidence" else f.path).read_text()
        )
        Path(plan["evidence"][0]["path"]).write_text("tamper")
    else:
        with sqlite3.connect(f.ledger.path) as db:
            if kind.endswith("record"):
                db.execute("DROP TRIGGER registry_transitions_update")
                db.execute(
                    "UPDATE registry_transitions SET payload='{}' WHERE seq=?",
                    (1 if kind == "first-record" else 2,),
                )
                db.execute(D.RECOVERY_TRIGGERS["registry_transitions_update"])
            elif kind.endswith("row"):
                db.execute("DROP TRIGGER protected_call_update")
                db.execute(
                    "UPDATE calls SET payload='{}' WHERE id=?",
                    ("probe-v1" if kind == "first-row" else "probe-v2",),
                )
                db.execute(D.RECOVERY_TRIGGERS["protected_call_update"])
            elif kind == "active-registry":
                meta = json.loads(
                    db.execute("SELECT payload FROM metadata").fetchone()[0]
                )
                meta["registry"] = asdict(f.prior)
                meta["registry_sha256"] = f.prior.digest
                db.execute("UPDATE metadata SET payload=?", (json.dumps(meta),))
            else:
                db.execute("DROP TRIGGER charged_uncertain_delete")
                db.execute("DELETE FROM charged_uncertain WHERE call_id='probe-v1'")
                db.execute(D.RECOVERY_TRIGGERS["charged_uncertain_delete"])
    with pytest.raises(D.BudgetStop):
        f.ledger.snapshot()
    with pytest.raises(D.BudgetStop):
        run_recovery(f)
