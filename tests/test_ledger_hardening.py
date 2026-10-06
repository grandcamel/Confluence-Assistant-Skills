"""Ledger read verification and launch hardening: temporary ledgers, fake CLI and
provider only. No canonical ledger, credential, provider or model call."""

import collections
import errno
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests import evaluation_budget as D, test_joint_evaluation as T
from tests.test_joint_evaluation import reg as reg


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def settled(tmp_path, reg):
    launch, provider = T.launcher(tmp_path, reg)
    outcome = T.invoke(launch, T.call())
    return launch, provider, outcome.receipt


def test_each_read_hashes_each_sealed_file_once_and_every_read_rehashes(
    tmp_path, reg, monkeypatch
):
    launch, _, receipt = settled(tmp_path, reg)
    reads = collections.Counter()
    original = Path.read_bytes

    def counting(self):
        reads[str(self)] += 1
        return original(self)

    monkeypatch.setattr(Path, "read_bytes", counting)
    launch.ledger.snapshot()
    # Receipt and partial receipt name the same transcript/proof, and every
    # binding names the same registry evidence: hashed once per read.
    assert reads[receipt.transcript_path] == reads[receipt.proof_path] == 1
    assert reads[reg.evidence_path] == 1
    launch.ledger.snapshot()
    assert reads[receipt.transcript_path] == reads[receipt.proof_path] == 2
    assert getattr(D._READ_PROOFS, "verified", None) is None
    Path(receipt.transcript_path).write_text("tampered after the first read")
    with pytest.raises(D.BudgetStop, match="evidence hash mismatch"):
        launch.ledger.snapshot()
    assert getattr(D._READ_PROOFS, "verified", None) is None


def test_outside_a_ledger_read_every_proof_hashes_again(tmp_path):
    path = tmp_path / "evidence.json"
    path.write_text("{}")
    digest = sha(path)
    D._proof(str(path), digest)
    path.write_text('{"changed": true}')
    with pytest.raises(D.BudgetStop, match="evidence hash mismatch"):
        D._proof(str(path), digest)


def test_settled_row_with_a_different_partial_receipt_is_still_validated(tmp_path, reg):
    launch, _, _ = settled(tmp_path, reg)
    with sqlite3.connect(launch.ledger.path) as db:
        row = json.loads(db.execute("SELECT payload FROM calls").fetchone()[0])
        assert row["partial_receipt"] == row["receipt"]
        row["partial_receipt"] = {**row["partial_receipt"], "proof_sha256": "0" * 64}
        db.execute("UPDATE calls SET payload=?", (json.dumps(row),))
    with pytest.raises(D.BudgetStop, match="evidence hash mismatch"):
        launch.ledger.snapshot()


class RaisingCLI(T.FakeOAuthCLI):
    def __init__(self, reg, error):
        super().__init__(reg)
        self.error = error

    def run(self, argv, **kwargs):
        raise self.error


def failing_launch(tmp_path, reg, error):
    launch, provider = T.launcher(tmp_path, reg)
    launch.transport.sandbox = RaisingCLI(reg, error)
    return launch, provider


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (
            BlockingIOError(errno.EAGAIN, os.strerror(errno.EAGAIN)),
            {"exception_type": "BlockingIOError", "errno": "EAGAIN"},
        ),
        (RuntimeError("can't start new thread"), {"exception_type": "RuntimeError"}),
        (
            D.BudgetStop("sandbox child unavailable"),
            {"exception_type": "BudgetStop", "message": "sandbox child unavailable"},
        ),
        (KeyboardInterrupt(), {"exception_type": "KeyboardInterrupt", "message": ""}),
    ],
)
def test_failed_execute_records_its_exception_in_evidence_and_ledger(
    tmp_path, reg, error, expected
):
    launch, provider = failing_launch(tmp_path, reg, error)
    call = T.call()
    with pytest.raises(type(error)) as raised:
        T.invoke(launch, call)
    assert raised.value is error  # re-raised, never replaced
    snapshot = launch.ledger.snapshot()
    (row,) = snapshot["calls"]
    assert snapshot["metadata"]["halted"]
    assert (row["status"], row["stop_reason"]) == ("uncertain", "interrupted")
    assert snapshot["exposure"] == launch.binding.validate()
    detail = row["stop_detail"]
    assert detail.items() >= {"message": str(error), **expected}.items()
    evidence = Path(detail["evidence"])
    assert (
        evidence
        == (tmp_path / "evidence/calls" / call.call_id).resolve() / "launcher-stop.json"
    )
    sealed = json.loads(evidence.read_text())
    assert sealed["call"]["call_id"] == call.call_id
    assert {k: sealed[k] for k in expected} == expected
    assert sealed["message"] == detail["message"] and not provider.calls


def test_stop_detail_redacts_credential_shaped_text_everywhere(tmp_path, reg):
    secrets = (
        "Bearer fixture-not-a-real-token-0123456789",
        "sk-ant-oat01-fixturefixturefixture",
        "eyJfixture.eyJpayload.signature",
        "Z" * 40,
    )
    launch, _ = failing_launch(tmp_path, reg, RuntimeError(" ".join(secrets)))
    with pytest.raises(RuntimeError):
        T.invoke(launch, T.call())
    (row,) = launch.ledger.snapshot()["calls"]
    stored = (
        launch.ledger.path.read_bytes()
        + Path(row["stop_detail"]["evidence"]).read_bytes()
    )
    for secret in secrets:
        assert secret.encode() not in stored
    assert row["stop_detail"]["message"].count("<REDACTED>") == 4
    echo = D.stop_detail(ValueError('{"x-api-key": "fixture", "messages": []}'))
    assert echo["message"] == "<REDACTED REQUEST OR CREDENTIAL-SHAPED CONTENT>"
    long = D.stop_detail(OSError("x " * 400))
    assert len(long["message"]) <= D.STOP_MESSAGE_LIMIT + len("<TRUNCATED>")
    assert "\n" not in D.stop_detail(OSError("a\nb\x00c"))["message"]


def test_stop_detail_never_masks_a_broken_exception():
    class Broken(Exception):
        def __str__(self):
            raise ValueError("broken __str__")

    assert D.stop_detail(Broken()) == {"exception_type": "Broken", "message": ""}


def test_uncertain_refuses_a_malformed_stop_detail(tmp_path, reg):
    launch, _ = T.launcher(tmp_path, reg)
    call = T.call()
    launch.ledger.reserve(call, launch.binding)
    for bad in ({}, {"bad key!": "x"}, {"k": 1}, {"k": "x" * 1000}, ["x"]):
        with pytest.raises(D.BudgetStop, match="invalid stop detail"):
            launch.ledger.uncertain(call.call_id, "interrupted", detail=bad)
    assert launch.ledger.snapshot()["calls"][0]["status"] == "reserved"


def guard(count, limit=2784):
    return staticmethod(lambda: D.check_host_headroom(lambda: (count, limit)))


def test_saturated_host_refuses_before_any_reservation(tmp_path, reg, monkeypatch):
    launch, provider = T.launcher(tmp_path, reg)
    before = sha(launch.ledger.path)
    monkeypatch.setattr(D.BudgetLauncher, "host_guard", guard(1671))
    with pytest.raises(D.BudgetStop, match="1671 user processes exceed 1670"):
        T.invoke(launch, T.call())
    snapshot = launch.ledger.snapshot()
    assert snapshot["calls"] == [] and not snapshot["metadata"]["halted"]
    assert sha(launch.ledger.path) == before and not provider.calls
    # The same call is admitted once the host is back under 60% of the limit.
    monkeypatch.setattr(D.BudgetLauncher, "host_guard", guard(1670))
    assert T.invoke(launch, T.call()).stdout == "OK" and len(provider.calls) == 1


def test_replay_of_a_settled_call_never_consults_the_guard(tmp_path, reg, monkeypatch):
    launch, provider, _ = settled(tmp_path, reg)

    def forbidden():
        raise AssertionError("a replay needs no host headroom")

    monkeypatch.setattr(D.BudgetLauncher, "host_guard", staticmethod(forbidden))
    assert T.invoke(launch, T.call()).stdout == "OK" and len(provider.calls) == 1


@pytest.mark.parametrize(
    "usage", [lambda: (_ for _ in ()).throw(OSError(5, "x")), lambda: (1, 0)]
)
def test_unknown_host_headroom_refuses(usage):
    with pytest.raises(D.BudgetStop, match="headroom unavailable"):
        D.check_host_headroom(usage)


def test_no_per_user_limit_means_no_guard():
    assert D.check_host_headroom(lambda: None) is None
    assert D.check_host_headroom(lambda: (10, 100)) == (10, 100)


def test_linux_usage_counts_this_users_processes(tmp_path, monkeypatch):
    import resource

    for name in ("1", "22", "self", "abc"):
        (tmp_path / name).mkdir()
    monkeypatch.setattr(resource, "getrlimit", lambda kind: (100, 200))
    assert D._linux_process_usage(tmp_path) == (2, 100)
    monkeypatch.setattr(
        resource, "getrlimit", lambda kind: (resource.RLIM_INFINITY,) * 2
    )
    assert D._linux_process_usage(tmp_path) is None


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS process table probe")
def test_darwin_usage_matches_the_process_table():
    count, limit = D.host_process_usage()
    listed = subprocess.run(
        ["/bin/ps", "-U", str(os.getuid()), "-o", "pid="],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    assert abs(count - len(listed)) <= 50
    maximum = int(
        subprocess.run(
            ["/usr/sbin/sysctl", "-n", "kern.maxprocperuid"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    )
    assert 0 < limit <= maximum


def test_production_guard_is_the_reviewed_function():
    assert D.BudgetLauncher.host_guard is D.check_host_headroom
    assert SimpleNamespace(**vars(D)).HOST_PROCESS_FRACTION == (3, 5)
