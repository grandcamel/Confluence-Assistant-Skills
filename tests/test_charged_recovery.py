"""Conservative recovery fixtures only; never touch the canonical ledger."""

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests import evaluation_budget as D, joint_evaluation as J
from tests.test_joint_evaluation import FakeOAuthCLI, FakeProvider, reg as reg


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def original_sql(ledger):
    with sqlite3.connect(ledger.path) as db:
        return db.execute(
            "SELECT id, identity, payload FROM calls WHERE id='probe-v1'"
        ).fetchone()


@pytest.fixture
def recovery(tmp_path, reg):
    ledger = D.Ledger.create(tmp_path / "fixture.sqlite3", reg)
    old_call = D.Call("probe-v1", "probe", "oauth-equivalent-accounting", 1, "a" * 40)
    binding = reg.binding("floor-haiku45-api")
    ledger.reserve(old_call, binding)
    ledger.uncertain(old_call.call_id, "interrupted", halt=True)
    # Construct the exact schema2 legacy fixture; no production file is copied.
    with sqlite3.connect(ledger.path) as db:
        meta = json.loads(db.execute("SELECT payload FROM metadata").fetchone()[0])
        meta["version"] = 2
        meta.pop("transition_head")
        db.execute("UPDATE metadata SET payload=?", (json.dumps(meta),))
        for name in D.RECOVERY_TRIGGERS:
            db.execute(f"DROP TRIGGER {name}")
        db.execute("DROP TABLE registry_transitions")
        db.execute("DROP TABLE charged_uncertain")
    marker = ledger.path.with_suffix(".init.json")
    marker.write_text(
        json.dumps({"registry_sha256": reg.digest, "prior_sha256": "d" * 64})
    )
    proof = tmp_path / "new-proof.json"
    proof.write_text('{"reviewed_offline_fixture":true}')
    new = D.Registry(
        "repaired-fixture",
        tuple(
            replace(b, evidence_path=str(proof), evidence_sha256=sha(proof))
            for b in reg.bindings
        ),
        str(proof),
        sha(proof),
    )
    folder = tmp_path / "old-evidence"
    folder.mkdir()
    (folder / "intent.json").write_text('{"fixture_intent":true}')
    (folder / "child.jsonl").write_text(
        '{"type":"system","subtype":"api_retry","error":"authentication_failed"}\n'
    )
    reviews = []
    heads = {"plugin": "b" * 40, "floor": "c" * 40}
    for index, lens in enumerate(("Spec", "Standards/privacy", "RISK")):
        path = tmp_path / f"review-{index}.md"
        path.write_text(
            f"Verdict: PASS\nPlugin head: {heads['plugin']}\nFloor head: {heads['floor']}\nSynthetic offline fixture only\n"
        )
        reviews.append({"lens": lens, "path": str(path), "sha256": sha(path)})
    sql = original_sql(ledger)
    with sqlite3.connect(ledger.path) as db:
        raw_meta = db.execute("SELECT payload FROM metadata").fetchone()[0]
    plan = {
        "schema_version": 1,
        "transition_id": "fixture-conservative-recovery-v1",
        "ledger_path": str(ledger.path),
        "expected_ledger_sha256": sha(ledger.path),
        "expected_metadata_sha256": D._raw_sha(raw_meta),
        "old_registry_sha256": reg.digest,
        "new_registry_sha256": new.digest,
        "call": {
            "call_id": sql[0],
            "identity_sha256": D._raw_sha(sql[1]),
            "payload_sha256": D._raw_sha(sql[2]),
            "reservation_microdollars": 210241,
        },
        "initialization_marker": {"path": str(marker), "sha256": sha(marker)},
        "evidence_directory": str(folder),
        "evidence": [
            {"path": str(p), "sha256": sha(p)} for p in sorted(folder.iterdir())
        ],
        "provenance": {
            "owner_authority": "c-i conservative charged recovery commissioned by dispatch owner 2026-10-05",
            "source_heads": heads,
            "reviews": reviews,
        },
    }
    path = tmp_path / "recovery-plan.json"
    path.write_text(json.dumps(plan))
    return SimpleNamespace(
        ledger=ledger,
        old=reg,
        new=new,
        plan=plan,
        path=path,
        sql=sql,
        marker=marker,
        marker_sha=sha(marker),
        folder=folder,
    )


def run_recovery(f):
    with f.ledger.controller():
        return f.ledger.recover_and_transition(f.path, sha(f.path), f.new)


def rewrite_plan(f):
    f.path.write_text(json.dumps(f.plan))


def test_exact_charge_atomic_transition_and_original_bytes_immutable(recovery):
    f = recovery
    result = run_recovery(f)
    assert (
        result["already_applied"] is False and result["exposure_microdollars"] == 210241
    )
    assert original_sql(f.ledger) == f.sql and sha(f.marker) == f.marker_sha
    state = f.ledger.snapshot()
    assert state["metadata"]["version"] == 3
    assert state["metadata"]["registry_sha256"] == f.new.digest
    assert not state["metadata"]["halted"]
    row = state["calls"][0]
    assert (
        row["status"] == "charged-uncertain"
        and row["actual"] is None
        and row["receipt"] is None
    )
    assert row["consumed_exposure_microdollars"] == row["reservation"] == 210241
    assert J.reconcile_existing(f.ledger)["exposure"] == 210241
    J.check_ledger_eligibility({"ledger_path": str(f.ledger.path)}, f.new)
    with sqlite3.connect(f.ledger.path) as db:
        payload, digest = db.execute(
            "SELECT payload, sha256 FROM registry_transitions"
        ).fetchone()
    record = json.loads(payload)
    assert D._digest(record) == digest == state["metadata"]["transition_head"]
    assert record["previous_hash"] == f.plan["expected_metadata_sha256"]
    assert (
        record["from_registry_sha256"] == f.old.digest
        and record["to_registry_sha256"] == f.new.digest
    )
    assert record["provenance"] == f.plan["provenance"]


def test_duplicate_no_write_even_after_legitimate_new_uncertainty(recovery):
    f = recovery
    run_recovery(f)
    before = sha(f.ledger.path)
    assert run_recovery(f)["already_applied"] is True
    assert sha(f.ledger.path) == before
    call = D.Call("probe-v2", "probe", "oauth-equivalent-accounting-v2", 1, "b" * 40)
    f.ledger.reserve(call, f.new.binding("floor-haiku45-api"))
    f.ledger.uncertain(call.call_id, "interrupted", halt=True)
    before = sha(f.ledger.path)
    result = run_recovery(f)
    assert (
        result["already_applied"]
        and result["halted"]
        and result["exposure_microdollars"] == 420482
    )
    assert sha(f.ledger.path) == before and original_sql(f.ledger) == f.sql


def test_new_provider_settlement_preserves_consumed_old_charge(recovery, tmp_path):
    f = recovery
    run_recovery(f)
    provider = FakeProvider()
    transport = J.ProductionTransport(
        {"files": {}, "evidence_root": str(tmp_path / "new-evidence")},
        f.new,
        FakeOAuthCLI(f.new),
        provider,
    )
    binding = f.new.binding("floor-haiku45-api")
    call = D.Call("probe-v2", "probe", "oauth-equivalent-accounting-v2", 1, "b" * 40)
    result = J.JointLauncher(f.ledger, binding, transport).run(
        ["claude", "--print", "--model", binding.model], "OK?", call=call, timeout=5
    )
    assert result.receipt.actual_usd == "0.000017"
    assert f.ledger.snapshot()["exposure"] == 210258
    assert original_sql(f.ledger) == f.sql and len(provider.calls) == 1
    assert run_recovery(f)["already_applied"]


def test_cap_exhaustion_counts_old_charge_exactly_once(recovery):
    f = recovery
    run_recovery(f)
    binding = f.new.binding("floor-opus55-api")
    count = 0
    while True:
        call = D.Call(f"call-{count}", "floor", f"fixture-{count}", 1, "b" * 40)
        try:
            f.ledger.reserve(call, binding)
        except D.BudgetStop as error:
            assert "headroom" in str(error)
            break
        count += 1
    state = f.ledger.snapshot()
    assert state["exposure"] == 210241 + count * binding.validate() <= D.CAP
    assert state["exposure"] + binding.validate() > D.CAP


@pytest.mark.parametrize("point", ["mid-charge", "mid-metadata", "after-commit"])
def test_process_crash_has_only_original_or_complete_transition(
    recovery, tmp_path, point
):
    f = recovery
    registry_file = tmp_path / "new-registry.json"
    registry_file.write_text(json.dumps(asdict(f.new)))
    script = """
import json,os,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from tests import evaluation_budget as D
original=D.sqlite3.connect
class Connection:
 def __init__(self,db): self.db=db
 def __getattr__(self,key): return getattr(self.db,key)
 def execute(self,sql,*args):
  result=self.db.execute(sql,*args)
  if (sys.argv[5]=='mid-charge' and sql.startswith('INSERT INTO charged_uncertain')) or (sys.argv[5]=='mid-metadata' and sql.startswith('UPDATE metadata')): os._exit(73)
  return result
 def commit(self):
  self.db.commit()
  if sys.argv[5]=='after-commit': os._exit(73)
D.sqlite3.connect=lambda *a,**kw:Connection(original(*a,**kw))
path=Path(sys.argv[2]); plan=json.loads(path.read_text())
D.Ledger(Path(plan['ledger_path'])).recover_and_transition(path,sys.argv[3],D.Registry.from_dict(json.loads(Path(sys.argv[4]).read_text())))
"""
    child = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            script,
            str(Path(D.__file__).parents[1]),
            str(f.path),
            sha(f.path),
            str(registry_file),
            point,
        ],
        env={"PATH": os.defpath},
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert child.returncode == 73, child.stderr
    state = f.ledger.snapshot()
    assert original_sql(f.ledger) == f.sql and state["exposure"] == 210241
    if point == "after-commit":
        assert (
            state["calls"][0]["status"] == "charged-uncertain"
            and not state["metadata"]["halted"]
        )
    else:
        assert state["metadata"]["version"] == 2 and state["metadata"]["halted"]
        assert state["calls"][0]["status"] == "uncertain"
    result = run_recovery(f)
    assert result["already_applied"] is (point == "after-commit")


@pytest.mark.parametrize(
    "kind",
    [
        "evidence",
        "extra-evidence",
        "review",
        "marker",
        "amount",
        "dbhash",
        "rowhash",
        "oldregistry",
        "newregistry",
        "sourcehead",
        "missingreview",
        "schema",
        "wal",
    ],
)
def test_mismatch_refuses_without_any_ledger_write(recovery, kind):
    f = recovery
    if kind == "evidence":
        (f.folder / "intent.json").write_text("tampered")
    elif kind == "extra-evidence":
        (f.folder / "extra.json").write_text("unreviewed")
    elif kind == "review":
        Path(f.plan["provenance"]["reviews"][0]["path"]).write_text("REVISE")
    elif kind == "marker":
        f.marker.write_text("{}")
    elif kind == "amount":
        f.plan["call"]["reservation_microdollars"] = 210240
    elif kind == "dbhash":
        f.plan["expected_ledger_sha256"] = "0" * 64
    elif kind == "rowhash":
        f.plan["call"]["payload_sha256"] = "0" * 64
    elif kind == "oldregistry":
        f.plan["old_registry_sha256"] = "0" * 64
    elif kind == "newregistry":
        f.plan["new_registry_sha256"] = "0" * 64
    elif kind == "sourcehead":
        f.plan["provenance"]["source_heads"]["plugin"] = "e" * 40
    elif kind == "missingreview":
        f.plan["provenance"]["reviews"].pop()
    elif kind == "schema":
        f.plan["schema_version"] = True
    elif kind == "wal":
        Path(str(f.ledger.path) + "-wal").write_bytes(b"")
    rewrite_plan(f)
    before = sha(f.ledger.path)
    with pytest.raises(D.BudgetStop):
        run_recovery(f)
    assert sha(f.ledger.path) == before and original_sql(f.ledger) == f.sql


def test_financial_terms_cannot_change_even_with_resealed_plan(recovery):
    f = recovery
    f.new = replace(
        f.new,
        bindings=(
            replace(f.new.bindings[0], session_cap_usd="1.5"),
            *f.new.bindings[1:],
        ),
    )
    f.plan["new_registry_sha256"] = f.new.digest
    rewrite_plan(f)
    with pytest.raises(D.BudgetStop, match="financial"):
        run_recovery(f)


@pytest.mark.parametrize(
    "kind", ["evidence", "chain", "active-registry", "orphan", "row", "guards"]
)
def test_post_transition_tamper_fails_closed(recovery, kind):
    f = recovery
    run_recovery(f)
    if kind == "evidence":
        (f.folder / "intent.json").write_text("tampered")
    else:
        with sqlite3.connect(f.ledger.path) as db:
            if kind == "chain":
                db.execute("DROP TRIGGER registry_transitions_update")
                db.execute("UPDATE registry_transitions SET sha256=?", ("0" * 64,))
                db.execute(D.RECOVERY_TRIGGERS["registry_transitions_update"])
            elif kind == "active-registry":
                meta = json.loads(
                    db.execute("SELECT payload FROM metadata").fetchone()[0]
                )
                meta["registry"] = asdict(f.old)
                meta["registry_sha256"] = f.old.digest
                db.execute("UPDATE metadata SET payload=?", (json.dumps(meta),))
            elif kind == "orphan":
                db.execute("DROP TRIGGER charged_uncertain_delete")
                db.execute("DELETE FROM charged_uncertain")
                db.execute(D.RECOVERY_TRIGGERS["charged_uncertain_delete"])
            elif kind == "row":
                db.execute("DROP TRIGGER protected_call_update")
                raw = json.loads(f.sql[2])
                raw["actual"] = 0
                db.execute(
                    "UPDATE calls SET payload=? WHERE id=?", (json.dumps(raw), f.sql[0])
                )
                db.execute(D.RECOVERY_TRIGGERS["protected_call_update"])
            elif kind == "guards":
                db.execute("DROP TRIGGER protected_call_update")
    with pytest.raises(D.BudgetStop):
        f.ledger.snapshot()
    with pytest.raises(D.BudgetStop):
        run_recovery(f)


def test_permanent_charge_refuses_all_mutators_and_sql_edits(recovery):
    f = recovery
    run_recovery(f)
    before = sha(f.ledger.path)
    binding = f.new.binding("floor-haiku45-api")
    old_call = D.Call(**json.loads(f.sql[2])["call"])
    for mutation in (
        lambda: f.ledger.uncertain("probe-v1", "interrupted"),
        lambda: f.ledger.reconcile(SimpleNamespace(call_id="probe-v1")),
        lambda: f.ledger.record_outcome("probe-v1", D.Outcome()),
        lambda: f.ledger.cached(old_call, binding, ""),
        lambda: f.ledger.reserve(old_call, binding),
    ):
        with pytest.raises(D.BudgetStop):
            mutation()
    assert original_sql(f.ledger) == f.sql and sha(f.ledger.path) == before
    with sqlite3.connect(f.ledger.path) as db:
        for sql in (
            "UPDATE calls SET payload=payload WHERE id='probe-v1'",
            "DELETE FROM calls WHERE id='probe-v1'",
            "UPDATE charged_uncertain SET amount=0",
            "DELETE FROM registry_transitions",
        ):
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(sql)
    assert f.ledger.snapshot()["exposure"] == 210241


def test_recovery_main_never_reads_token_or_constructs_provider(
    recovery, monkeypatch, capsys
):
    f = recovery

    def forbidden(*args, **kwargs):
        raise AssertionError("recovery crossed a credential/model boundary")

    monkeypatch.delenv("DEMO_CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    monkeypatch.setattr(J, "Provider", forbidden)
    monkeypatch.setattr(J, "oauth_presence", forbidden)
    monkeypatch.setattr(J, "CANONICAL", f.ledger.path)
    config = {"files": {"recovery_plan": {"path": str(f.path), "sha256": sha(f.path)}}}

    def checked(*args, recovery=False):
        assert recovery is True
        return config, f.new, None

    monkeypatch.setattr(J, "checked_config", checked)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "joint",
            "--config",
            "fixture",
            "--config-sha256",
            "0" * 64,
            "recover-and-transition",
        ],
    )
    assert J.main() == 0
    report = json.loads(capsys.readouterr().out)
    assert report["api_calls"] == 0 and report["exposure_microdollars"] == 210241
    assert original_sql(f.ledger) == f.sql


def test_resealed_revise_report_mentioning_pass_is_not_admission(recovery):
    f = recovery
    item = f.plan["provenance"]["reviews"][0]
    heads = f.plan["provenance"]["source_heads"]
    Path(item["path"]).write_text(
        f"Verdict: REVISE — prior PASS superseded; fix before PASS\nPlugin head: {heads['plugin']}\nFloor head: {heads['floor']}\n"
    )
    item["sha256"] = sha(item["path"])
    rewrite_plan(f)
    with pytest.raises(D.BudgetStop, match="review"):
        run_recovery(f)


def test_sql_replace_cannot_overwrite_protected_call_or_chain(recovery):
    f = recovery
    run_recovery(f)
    with sqlite3.connect(f.ledger.path) as db:
        for table in ("calls", "charged_uncertain", "registry_transitions"):
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(f"INSERT OR REPLACE INTO {table} SELECT * FROM {table}")
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT OR REPLACE INTO calls VALUES (?, ?, ?)",
                ("foreign-id", f.sql[1], f.sql[2]),
            )
    assert original_sql(f.ledger) == f.sql


def test_rejected_protected_outcome_creates_no_evidence(recovery):
    f = recovery
    run_recovery(f)
    with pytest.raises(D.BudgetStop):
        f.ledger.record_outcome("probe-v1", D.Outcome())
    assert not f.ledger.path.with_suffix(f.ledger.path.suffix + ".evidence").exists()


@pytest.mark.parametrize(
    "kind",
    [
        "extra-call",
        "wrong-cap",
        "malformed-evidence",
        "changed-identity",
        "non-delete-journal",
    ],
)
def test_exact_exclusive_legacy_state_required(recovery, kind, monkeypatch):
    f = recovery
    if kind == "malformed-evidence":
        f.plan["evidence"] = None
    elif kind == "non-delete-journal":

        @contextmanager
        def unsupported_transaction():
            db = sqlite3.connect(f.ledger.path)
            try:
                db.execute("PRAGMA journal_mode=PERSIST")
                db.execute("BEGIN IMMEDIATE")
                yield db
            finally:
                db.rollback()
                db.close()

        monkeypatch.setattr(f.ledger, "_transaction", unsupported_transaction)
    else:
        with sqlite3.connect(f.ledger.path) as db:
            if kind == "extra-call":
                payload = json.loads(f.sql[2])
                payload["call"]["call_id"] = "extra-call"
                payload["call"]["task"] = "extra"
                identity = D.Ledger._identity(
                    D.Call(**payload["call"]), payload["binding_id"]
                )
                db.execute(
                    "INSERT INTO calls VALUES (?, ?, ?)",
                    ("extra-call", identity, json.dumps(payload)),
                )
            elif kind == "wrong-cap":
                meta = json.loads(
                    db.execute("SELECT payload FROM metadata").fetchone()[0]
                )
                meta["cap"] = 50000001
                db.execute("UPDATE metadata SET payload=?", (json.dumps(meta),))
            elif kind == "changed-identity":
                db.execute("UPDATE calls SET identity=?", ('["edited"]',))
    # A newly sealed file fingerprint cannot grant a broader logical recovery.
    f.plan["expected_ledger_sha256"] = sha(f.ledger.path)
    rewrite_plan(f)
    before = sha(f.ledger.path)
    with pytest.raises(D.BudgetStop):
        run_recovery(f)
    assert sha(f.ledger.path) == before


@pytest.mark.parametrize("collision", ["id", "identity"])
def test_update_replace_cannot_overwrite_protected_call(recovery, collision):
    f = recovery
    run_recovery(f)
    binding = f.new.binding("floor-haiku45-api")
    f.ledger.reserve(D.Call("new-call", "probe", "probe-v2", 1, "a" * 40), binding)
    with sqlite3.connect(f.ledger.path) as db:
        value = f.sql[0 if collision == "id" else 1]
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                f"UPDATE OR REPLACE calls SET {collision}=? WHERE id='new-call'",
                (value,),
            )
    assert original_sql(f.ledger) == f.sql
    assert f.ledger.snapshot()["exposure"] == 420482
