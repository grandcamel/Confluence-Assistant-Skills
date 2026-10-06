"""Fourth charged recovery against locally constructed fixtures only.

Builds on the three-link fixture: ordinary settled Floor traffic follows link 3,
then the commissioned Floor trial (G042/sonnet/4 attempt 1) is interrupted and
halts the ledger, as in run 2. No canonical ledger, credential or provider.
"""

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

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
from tests.test_third_recovery import third as third

FLOOR_HEAD, PLUGIN_HEAD = "c" * 40, "b" * 40
RUN = "confluence-floor-full-oauth-org-v4"
TARGET = D.COMMISSIONED_RETRIES[4]
LINK3_CUMULATIVE, TARGET_RESERVATION = 3440962, 2020481


def floor_launcher(f, binding_id):
    transport = J.ProductionTransport(
        {"files": {}, "evidence_root": str(f.path.parent / "floor-evidence")},
        f.new,
        T.FakeOAuthCLI(f.new),
        T.FakeProvider(),
    )
    return D.BudgetLauncher(f.ledger, f.new.binding(binding_id), transport)


def floor_call(model, fact, trial, attempt=1):
    task = f"{RUN}/{model}/{fact}"
    return D.Call(
        D._digest([RUN, "trial", task, trial, attempt]),
        "floor-trial",
        task,
        trial,
        FLOOR_HEAD,
        attempt,
    )


def floor_run(launcher, call):
    return launcher.run(
        ["claude", "-p", "--model", launcher.binding.model],
        "Answer from your own knowledge only.",
        call=call,
        evidence_destination=Path(launcher.transport.config["evidence_root"])
        / call.call_id,
        timeout=5,
    )


@pytest.fixture
def fourth(third):
    f = third
    run_recovery(f)  # link 3
    f.third_plan = f.path
    sonnet = floor_launcher(f, "floor-sonnet55-api")
    terra = floor_launcher(f, "floor-haiku45-api")
    floor_run(terra, floor_call("terra", "G001", 1))
    floor_run(sonnet, floor_call("sonnet", "G042", 3))
    # The commissioned trial stops inside execute, before the child writes.
    target = floor_call("sonnet", "G042", 4)

    def unavailable(*args, **kwargs):
        raise D.BudgetStop("sandbox child unavailable")

    sonnet.transport.execute = unavailable
    try:
        with pytest.raises(D.BudgetStop, match="sandbox child unavailable"):
            floor_run(sonnet, target)
    finally:
        del sonnet.transport.execute
    before = sql_state(f.ledger)
    with sqlite3.connect(f.ledger.path) as db:
        raw_meta = db.execute("SELECT payload FROM metadata").fetchone()[0]
    assert json.loads(raw_meta)["halted"] is True
    folder = f.path.parent / "floor-evidence-empty" / target.call_id
    folder.mkdir(parents=True)
    support = []
    for name, text in (("attempt.json", '{"budget_stop":true}'), ("run.log", "x\n")):
        path = f.path.parent / name
        path.write_text(text)
        support.append({"path": str(path), "sha256": sha(path)})
    charged = {row[0] for row in before["charged_uncertain"]}
    inventory = []
    for i, identity, payload in before["calls"]:
        row = json.loads(payload)
        status = "charged-uncertain" if i in charged else row["status"]
        inventory.append(
            {
                "call_id": i,
                "identity_sha256": D._raw_sha(identity),
                "payload_sha256": D._raw_sha(payload),
                "reservation_microdollars": row["reservation"],
                "accounting_status": status,
                "actual_microdollars": row["actual"] if status == "settled" else None,
            }
        )
    seq, payload3, sha3 = before["registry_transitions"][-1]
    snapshot = f.ledger.snapshot()
    # Link 4's own review receipts: earlier links keep sealing theirs.
    reviews = []
    for review in f.plan["provenance"]["reviews"]:
        copy = f.path.parent / ("v4-" + Path(review["path"]).name)
        copy.write_bytes(Path(review["path"]).read_bytes())
        reviews.append({**review, "path": str(copy)})
    f.path = f.path.parent / "plan-v4.json"
    f.plan = {
        "schema_version": 4,
        "transition_id": "fourth-commissioned-fixture",
        "ledger_path": str(f.ledger.path),
        "expected_ledger_sha256": sha(f.ledger.path),
        "expected_metadata_sha256": D._raw_sha(raw_meta),
        "old_registry_sha256": f.new.digest,
        "new_registry_sha256": f.new.digest,
        "original_registry_sha256": f.plan["original_registry_sha256"],
        "previous_transition": {
            "sequence": seq,
            "record_sha256": sha3,
            "payload_sha256": D._raw_sha(payload3),
        },
        "call": {
            k: v
            for k, v in next(
                i for i in inventory if i["call_id"] == target.call_id
            ).items()
            if k not in {"accounting_status", "actual_microdollars"}
        },
        "initialization_marker": f.plan["initialization_marker"],
        "evidence_directory": str(folder),
        "evidence": [],
        "supporting_evidence": support,
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
        "expected_exposure_microdollars": snapshot["exposure"],
        "retry": dict(TARGET),
        "provenance": {
            "owner_authority": D.RECOVERY_AUTHORITY[4],
            "source_heads": {"plugin": PLUGIN_HEAD, "floor": FLOOR_HEAD},
            "reviews": reviews,
        },
    }
    rewrite_plan(f)
    f.fourth_before = before
    f.target = target
    f.exposure = snapshot["exposure"]
    f.sonnet = sonnet
    return f


def test_fourth_link_charges_the_interrupted_floor_trial_and_conserves_all(fourth):
    f = fourth
    marker = sha(f.marker)
    result = run_recovery(f)
    assert result["already_applied"] is False and result["halted"] is False
    assert result["newly_consumed_microdollars"] == TARGET_RESERVATION
    assert (
        result["cumulative_consumed_microdollars"]
        == result["charged_uncertain_microdollars"]
        == LINK3_CUMULATIVE + TARGET_RESERVATION
    )
    assert result["exposure_microdollars"] == f.exposure
    assert result["registry_sha256"] == f.new.digest
    now = sql_state(f.ledger)
    assert now["calls"] == f.fourth_before["calls"]
    assert now["registry_transitions"][:3] == f.fourth_before["registry_transitions"]
    assert set(now["charged_uncertain"]) > set(f.fourth_before["charged_uncertain"])
    snapshot = f.ledger.snapshot()
    by_id = {r["call"]["call_id"]: r for r in snapshot["calls"]}
    charged = by_id[f.target.call_id]
    assert charged["status"] == "charged-uncertain"
    assert charged["consumed_exposure_microdollars"] == TARGET_RESERVATION
    assert charged["recovery_record_sha256"] == result["transition_sha256"]
    assert (
        by_id["probe-v3"]["status"] == "settled" and by_id["probe-v3"]["actual"] == 6502
    )
    assert snapshot["exposure"] == f.exposure and not snapshot["metadata"]["halted"]
    assert snapshot["metadata"]["transition_head"] == result["transition_sha256"]
    assert J.reconcile_existing(f.ledger)["exposure"] == f.exposure
    J.check_ledger_eligibility({"ledger_path": str(f.ledger.path)}, f.new)
    record = json.loads(now["registry_transitions"][3][1])
    assert D._digest(record) == result["transition_sha256"]
    assert record["previous_hash"] == f.fourth_before["registry_transitions"][2][2]
    assert record["from_registry_sha256"] == record["to_registry_sha256"]
    assert record["supporting_evidence"] == f.plan["supporting_evidence"]
    assert record["retry"] == TARGET and sha(f.marker) == marker


def test_exact_duplicate_writes_nothing_and_never_clears_a_later_halt(fourth):
    f = fourth
    run_recovery(f)
    before = sha(f.ledger.path)
    again = run_recovery(f)
    assert again["already_applied"] and again["newly_consumed_microdollars"] == 0
    assert sha(f.ledger.path) == before
    later = floor_call("terra", "G002", 1)
    f.ledger.reserve(later, f.new.binding("floor-haiku45-api"))
    f.ledger.uncertain(later.call_id, "interrupted", halt=True)
    before = sha(f.ledger.path)
    result = run_recovery(f)
    assert result["already_applied"] and result["halted"]
    assert result["exposure_microdollars"] == f.exposure + 210241
    assert sha(f.ledger.path) == before
    # No fifth link: the reader refuses any longer chain, and no plan schema 5.
    f.plan["schema_version"] = 5
    rewrite_plan(f)
    with pytest.raises(D.BudgetStop):
        run_recovery(f)
    assert sha(f.ledger.path) == before


@pytest.mark.parametrize(
    "kind",
    [
        "prior-link",
        "row-payload",
        "missing-row",
        "extra-row",
        "settled-actual",
        "charge",
        "retry-attempt3",
        "retry-other-trial",
        "registry-change",
        "evidence-not-empty",
        "supporting-tampered",
        "supporting-missing",
        "exposure",
        "review",
        "authority",
        "ledger-bytes",
    ],
)
def test_fourth_plan_mismatches_refuse_without_writes(fourth, kind):
    f = fourth
    plan = f.plan
    if kind == "prior-link":
        plan["previous_transition"]["payload_sha256"] = "0" * 64
    elif kind == "row-payload":
        next(i for i in plan["expected_calls"] if i["accounting_status"] == "settled")[
            "payload_sha256"
        ] = "0" * 64
    elif kind == "missing-row":
        plan["expected_calls"] = [
            i for i in plan["expected_calls"] if i["call_id"] != "probe-v3"
        ]
        plan["expected_exposure_microdollars"] -= 6502
    elif kind == "extra-row":
        plan["expected_calls"].append(
            {**plan["expected_calls"][-1], "call_id": "phantom-settled"}
        )
    elif kind == "settled-actual":
        next(i for i in plan["expected_calls"] if i["call_id"] == "probe-v3")[
            "actual_microdollars"
        ] = 0
    elif kind == "charge":
        plan["expected_charges"][0]["amount"] = 0
    elif kind == "retry-attempt3":
        plan["retry"]["to_attempt"] = 3
    elif kind == "retry-other-trial":
        plan["retry"]["trial"] = 5
    elif kind == "registry-change":
        plan["new_registry_sha256"] = f.old.digest
    elif kind == "evidence-not-empty":
        (Path(plan["evidence_directory"]) / "late.json").write_text("{}")
    elif kind == "supporting-tampered":
        Path(plan["supporting_evidence"][0]["path"]).write_text("tampered")
    elif kind == "supporting-missing":
        plan["supporting_evidence"] = []
    elif kind == "exposure":
        plan["expected_exposure_microdollars"] += 1
    elif kind == "review":
        Path(plan["provenance"]["reviews"][0]["path"]).write_text("Verdict: REVISE")
    elif kind == "authority":
        plan["provenance"]["owner_authority"] = D.RECOVERY_AUTHORITY[3]
    elif kind == "ledger-bytes":
        plan["expected_ledger_sha256"] = "0" * 64
    rewrite_plan(f)
    before = sha(f.ledger.path)
    with pytest.raises(D.BudgetStop):
        run_recovery(f)
    assert sha(f.ledger.path) == before
    assert f.ledger.snapshot()["metadata"]["halted"] is True


def test_fourth_link_refuses_a_target_that_is_not_the_commissioned_trial(fourth):
    f = fourth
    other = next(
        i
        for i in f.plan["expected_calls"]
        if i["accounting_status"] == "settled" and i["call_id"] != "probe-v3"
    )
    target = next(
        i for i in f.plan["expected_calls"] if i["accounting_status"] == "uncertain"
    )
    other["accounting_status"], target["accounting_status"] = "uncertain", "settled"
    other["actual_microdollars"], target["actual_microdollars"] = None, 0
    f.plan["expected_exposure_microdollars"] = sum(
        i["actual_microdollars"]
        if i["accounting_status"] == "settled"
        else i["reservation_microdollars"]
        for i in f.plan["expected_calls"]
    )
    f.plan["call"] = {
        k: v
        for k, v in other.items()
        if k not in {"accounting_status", "actual_microdollars"}
    }
    rewrite_plan(f)
    before = sha(f.ledger.path)
    with pytest.raises(D.BudgetStop):
        run_recovery(f)
    assert sha(f.ledger.path) == before


@pytest.mark.parametrize(
    "kind", ["fourth-link", "fourth-map", "target-row", "settled-row", "fifth-link"]
)
def test_four_link_read_refuses_any_tampered_history(fourth, kind):
    f = fourth
    run_recovery(f)
    guards = D.recovery_guards(4)
    with sqlite3.connect(f.ledger.path) as db:
        for name in guards:
            db.execute(f"DROP TRIGGER {name}")
        if kind == "fourth-link":
            db.execute(
                "UPDATE registry_transitions SET sha256=? WHERE seq=4", ("0" * 64,)
            )
        elif kind == "fourth-map":
            db.execute(
                "DELETE FROM charged_uncertain WHERE call_id=?", (f.target.call_id,)
            )
        elif kind in ("target-row", "settled-row"):
            identity = (
                f.target.call_id
                if kind == "target-row"
                else floor_call("sonnet", "G042", 3).call_id
            )
            raw = db.execute(
                "SELECT payload FROM calls WHERE id=?", (identity,)
            ).fetchone()[0]
            data = json.loads(raw)
            data["reservation" if kind == "target-row" else "actual"] = 1
            db.execute(
                "UPDATE calls SET payload=? WHERE id=?", (json.dumps(data), identity)
            )
        else:
            payload, _ = db.execute(
                "SELECT payload, sha256 FROM registry_transitions WHERE seq=4"
            ).fetchone()
            db.execute(
                "INSERT INTO registry_transitions VALUES (5, ?, ?)",
                (payload, "f" * 64),
            )
        for sql in guards.values():
            db.execute(sql)
    with pytest.raises(D.BudgetStop):
        f.ledger.snapshot()


def link4_settlement(f):
    """A row only link 4 seals: settled after link 3, before run 2's halt."""
    call = floor_call("sonnet", "G042", 3)
    with sqlite3.connect(f.ledger.path) as db:
        raw = db.execute(
            "SELECT id, identity, payload FROM calls WHERE id=?", (call.call_id,)
        ).fetchone()
    link3 = json.loads(f.fourth_before["registry_transitions"][2][1])
    assert call.call_id not in {i["call_id"] for i in link3["expected_calls"]}
    return call, raw


def test_link4_guards_refuse_deleting_or_rewriting_a_sealed_settlement(fourth):
    """Codex risk r1 finding 1: link 4's 498 additional settlements were not
    guarded. Its own additive SQL guards now refuse every write to them."""
    f = fourth
    run_recovery(f)
    _, (row_id, identity, payload) = link4_settlement(f)
    before = sha(f.ledger.path)
    rewritten = json.dumps({**json.loads(payload), "terminal_at_ns": 1})
    for sql, args in (
        ("DELETE FROM calls WHERE id=?", (row_id,)),
        ("UPDATE calls SET payload=? WHERE id=?", (rewritten, row_id)),
        ("INSERT OR REPLACE INTO calls VALUES (?, ?, ?)", (row_id, identity, payload)),
        ("INSERT INTO calls VALUES (?, ?, ?)", ("other-id", identity, payload)),
    ):
        with (
            sqlite3.connect(f.ledger.path) as db,
            pytest.raises(sqlite3.IntegrityError, match="historical settlement"),
        ):
            db.execute(sql, args)
    assert sha(f.ledger.path) == before
    with sqlite3.connect(f.ledger.path) as db:
        names = {
            n
            for (n,) in db.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger'"
            )
        }
    assert names == set(D.recovery_guards(4)) and len(names) == 15


@pytest.mark.parametrize("kind", ["delete", "valid-field"])
def test_link4_read_refuses_a_deleted_or_rewritten_sealed_settlement(fourth, kind):
    """With every guard bypassed, the read itself still enforces each sealed
    link-4 settlement's existence and exact bytes: no lower exposure, no cache
    miss and no new reservation for the erased identity."""
    f = fourth
    run_recovery(f)
    exposure = f.ledger.snapshot()["exposure"]
    call, (row_id, identity, payload) = link4_settlement(f)
    guards = D.recovery_guards(4)
    with sqlite3.connect(f.ledger.path) as db:
        for name in guards:
            db.execute(f"DROP TRIGGER {name}")
        if kind == "valid-field":
            data = json.loads(payload)
            data["terminal_at_ns"] += 1  # still a valid settled row
            db.execute(
                "UPDATE calls SET payload=? WHERE id=?", (json.dumps(data), row_id)
            )
        else:
            db.execute("DELETE FROM calls WHERE id=?", (row_id,))
        for sql in guards.values():
            db.execute(sql)
    before = sha(f.ledger.path)
    binding = f.new.binding("floor-sonnet55-api")
    message = (
        "protected original call bytes changed"
        if kind == "valid-field"
        else "sealed historical settlement missing"
    )
    for operation in (
        f.ledger.snapshot,
        lambda: f.ledger.cached(call, binding, "0" * 64),
        lambda: f.ledger.reserve(call, binding),
        lambda: floor_run(f.sonnet, call),
    ):
        with pytest.raises(D.BudgetStop, match=message):
            operation()
    assert sha(f.ledger.path) == before
    # Restoring the exact sealed row restores the exact conserved state.
    with sqlite3.connect(f.ledger.path) as db:
        for name in guards:
            db.execute(f"DROP TRIGGER {name}")
        db.execute("DELETE FROM calls WHERE id=?", (row_id,))
        db.execute("INSERT INTO calls VALUES (?, ?, ?)", (row_id, identity, payload))
        for sql in guards.values():
            db.execute(sql)
    assert f.ledger.snapshot()["exposure"] == exposure


@pytest.mark.parametrize("point", ["mid-charge", "mid-metadata", "after-commit"])
def test_fourth_transition_process_death_restarts_atomically(fourth, point):
    f = fourth
    code = r"""
import os,sys,sqlite3,json
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from tests import evaluation_budget as D
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
    registry_file = f.path.parent / "fixture-registry-v4.json"
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
    snapshot = f.ledger.snapshot()
    assert snapshot["exposure"] == f.exposure and not snapshot["metadata"]["halted"]
    assert sql_state(f.ledger)["calls"] == f.fourth_before["calls"]


def test_commissioned_retries_survive_the_fourth_link(fourth):
    f = fourth
    run_recovery(f)
    retries = f.ledger.commissioned_retries()
    links = sql_state(f.ledger)["registry_transitions"]
    assert [r["retry"] for r in retries] == [
        D.COMMISSIONED_RETRIES[3],
        D.COMMISSIONED_RETRIES[4],
    ]
    assert [r["record_sha256"] for r in retries] == [links[2][2], links[3][2]]
    assert [r["source_head"] for r in retries] == [PLUGIN_HEAD, FLOOR_HEAD]
    assert retries[1]["predecessor_call_id"] == f.target.call_id
    # Link 3's plugin replacement keeps the identity it had before link 4.
    plugin = f.new.binding("plugin-sonnet5-api")
    mapped = f.ledger.retry_call(
        D.Call("fresh-uuid", "sufficiency", "read-page", 1, PLUGIN_HEAD), plugin
    )
    assert (
        mapped.attempt == 2
        and mapped.call_id
        == D._digest(
            [links[2][2], plugin.binding_id, "sufficiency", "read-page", 1, 2]
        )[:32]
    )
    # The Floor replacement is reservable as attempt 2 of the charged trial.
    retry = floor_call("sonnet", "G042", 4, attempt=2)
    outcome = floor_run(f.sonnet, retry)
    assert outcome.receipt.call_id == retry.call_id
    rows = {r["call"]["call_id"]: r for r in f.ledger.snapshot()["calls"]}
    assert rows[retry.call_id]["status"] == "settled"
    assert rows[f.target.call_id]["status"] == "charged-uncertain"


@pytest.fixture
def recovery_packet(fourth, monkeypatch, tmp_path):
    """A schema-3 charged-recovery configuration around the fixture ledger."""
    f = fourth
    monkeypatch.setattr(J, "CANONICAL", f.ledger.path)
    monkeypatch.setattr(
        J,
        "sys",
        SimpleNamespace(
            flags=SimpleNamespace(isolated=1, dont_write_bytecode=1),
            pycache_prefix="/dev/null",
            base_prefix=sys.base_prefix,
            executable=sys.executable,
            argv=sys.argv,
        ),
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("recovery crossed a credential/model boundary")

    presence = []
    for name in ("Provider", "Sandbox", "check_floor_policy"):
        monkeypatch.setattr(J, name, forbidden)
    monkeypatch.setattr(J, "oauth_presence", lambda: presence.append(1))
    monkeypatch.setattr(J, "registry", lambda models, proof: f.new)
    monkeypatch.setattr(J, "check_source", lambda entry: None)
    monkeypatch.setattr(J, "runtime_manifest", lambda: {"files": ["fixture"]})
    manifest = tmp_path / "runtime.json"
    manifest.write_text(json.dumps({"files": ["fixture"]}))
    claude = tmp_path / "claude-fixture"
    claude.write_text("never executed\n")
    wrapper = Path(sys.executable).parent / "confluence-as"
    if not wrapper.is_file():
        pytest.skip("controller packet tests need the venv's confluence-as wrapper")
    root = Path(J.__file__).resolve().parents[1]

    def entry(path):
        return {"path": str(path), "sha256": sha(path)}

    files = {name: entry(root / rel) for name, rel in J.CODE_FILES.items()}
    files.update(
        models=entry(f.new.bindings[0].pricing.evidence_path),
        proof=entry(f.new.evidence_path),
        claude=entry(claude),
        runtime_manifest=entry(manifest),
        cli_wrapper=entry(wrapper),
        recovery_plan=entry(f.path),
    )
    config = {
        "schema_version": 3,
        "selection": {"kind": J.RECOVERY_KIND},
        "ledger_path": str(f.ledger.path),
        "serial": True,
        "budget_module_sha256": D.interface_manifest()["module_sha256"],
        "files": files,
        "sources": {
            "plugin": {"path": str(root), "head": PLUGIN_HEAD},
            "floor": {"path": str(tmp_path), "head": FLOOR_HEAD},
        },
        "registry_sha256": f.new.digest,
        "cli_bin": str(Path(sys.executable).parent),
        "runtime_read_paths": [str(Path(sys.base_prefix).resolve())],
        "evidence_root": str(tmp_path / "paid"),
    }

    def write(value):
        path = tmp_path / "recovery-config.json"
        path.write_text(json.dumps(value))
        return path, sha(path)

    return SimpleNamespace(f=f, config=config, write=write, presence=presence)


def test_recovery_configuration_runs_only_recover_and_transition(
    recovery_packet, monkeypatch, capsys
):
    p = recovery_packet
    path, digest = p.write(p.config)
    for mode in ("dry-admission", "run", "probe"):
        monkeypatch.setattr(
            sys,
            "argv",
            ["joint", "--config", str(path), "--config-sha256", digest, mode],
        )
        assert J.main() == 2
        assert json.loads(capsys.readouterr().out)["status"] == "STOPPED_INCOMPLETE"
    assert p.f.ledger.snapshot()["metadata"]["halted"] is True
    p.presence.clear()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "joint",
            "--config",
            str(path),
            "--config-sha256",
            digest,
            "recover-and-transition",
        ],
    )
    assert J.main() == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "RECOVERED_AND_TRANSITIONED" and report["api_calls"] == 0
    assert report["newly_consumed_microdollars"] == TARGET_RESERVATION
    assert report["exposure_microdollars"] == p.f.exposure and not report["halted"]
    assert p.presence == []  # recovery never even checks for a credential
    before = sha(p.f.ledger.path)
    assert J.main() == 0
    assert json.loads(capsys.readouterr().out)["already_applied"] is True
    assert sha(p.f.ledger.path) == before


@pytest.mark.parametrize(
    "mutate",
    [
        lambda c: c["selection"].update(extra=1),
        lambda c: c["files"].pop("recovery_plan"),
        lambda c: c["files"].update(floor_policy=c["files"]["models"]),
        lambda c: c["files"].update(prior_ledger=c["files"]["models"]),
        lambda c: c["sources"].pop("floor"),
        lambda c: c.update(schema_version=1),
        lambda c: c["sources"]["plugin"].update(head="d" * 40),
    ],
)
def test_recovery_configuration_refuses_unreviewed_shapes(
    recovery_packet, monkeypatch, mutate
):
    p = recovery_packet
    config = json.loads(json.dumps(p.config))
    mutate(config)
    before = sha(p.f.ledger.path)
    with pytest.raises((D.BudgetStop, KeyError)):
        J.checked_config(*p.write(config), recovery=True)
    assert sha(p.f.ledger.path) == before


def test_plan_digest_is_the_reviewed_bytes(fourth):
    f = fourth
    digest = hashlib.sha256(f.path.read_bytes()).hexdigest()
    with pytest.raises(D.BudgetStop), f.ledger.controller():
        f.ledger.recover_and_transition(f.path, "0" * 64, f.new)
    assert run_recovery(f)["transition_sha256"] and digest == sha(f.path)
