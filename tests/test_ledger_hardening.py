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
from tests.evaluation_api import ProviderStop
from tests.evaluation_sandbox import SandboxStop
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


EAGAIN_TEXT = os.strerror(errno.EAGAIN)


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (
            BlockingIOError(errno.EAGAIN, "fork: retry: /private/fixture-path"),
            {
                "exception_type": "BlockingIOError",
                "errno": "EAGAIN",
                "message": EAGAIN_TEXT,
                "cause": "process-or-thread-limit",
            },
        ),
        (
            RuntimeError("can't start new thread"),
            {
                "exception_type": "RuntimeError",
                "message": "can't start new thread",
                "cause": "process-or-thread-limit",
            },
        ),
        (
            D.BudgetStop("sandbox child unavailable"),
            {"exception_type": "BudgetStop", "message": "sandbox child unavailable"},
        ),
        (
            KeyboardInterrupt(),
            {
                "exception_type": "KeyboardInterrupt",
                "message": "",
                "cause": "interrupt-signal",
            },
        ),
        (
            ValueError("an unreviewed dependency message"),
            {"exception_type": "ValueError", "message": D.SUPPRESSED_MESSAGE},
        ),
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
    assert detail == {**expected, "evidence": detail["evidence"]}
    evidence = Path(detail["evidence"])
    assert (
        evidence
        == (tmp_path / "evidence/calls" / call.call_id).resolve() / "launcher-stop.json"
    )
    sealed = json.loads(evidence.read_text())
    assert sealed["call"]["call_id"] == call.call_id
    assert {k: sealed[k] for k in expected} == expected
    assert not provider.calls


# Synthetic credential fragments only (codex risk r1 finding 2 and standards r1
# finding 5): none may reach any durable or printed sink, whatever the format.
FRAGMENTS = (
    "ZmFrZXVzZXI6ZmFrZXBhc3M",
    "fixture-user",
    "fixture-pass",
    "hunter2",
    "abc123xyz",
    "abcd1234",
    "abcdef123",
    "fixture-token",
)


class EchoingError(Exception):
    def __str__(self):
        return "Bearer fixture-token"


ADVERSARIAL = (
    ValueError("headers [('Authorization', 'Basic ZmFrZXVzZXI6ZmFrZXBhc3M=')]"),
    ValueError("cannot connect to https://fixture-user:fixture-pass@example.invalid/"),
    RuntimeError(
        "ANTHROPIC_API_KEY=abc123xyz client_secret=abcd1234 db_password=hunter2"
    ),
    TypeError("GET /v1?access_token=abcdef123"),
    OSError(errno.EACCES, "Permission denied", "/tmp/fixture-pass/abc123xyz"),
    FileNotFoundError(errno.ENOENT, "fixture-pass", "/fixture-user/hunter2"),
    OSError("fixture-user:fixture-pass"),
    KeyError("fixture-pass"),
    EchoingError(),
    # A reviewed class misused with a credential still never persists it.
    D.BudgetStop("Basic ZmFrZXVzZXI6ZmFrZXBhc3M="),
    D.BudgetStop("see https://fixture-user:fixture-pass@example.invalid/"),
    D.BudgetStop("db_password=hunter2 [abcd1234]"),
    SandboxStop("timeout", "Bearer fixture-token", "fixture-pass"),
)


def sinks(launch, row):
    """Every byte stop_detail reached: ledger, journal, launcher stop sidecars.

    (child-stop.json is the transport's bounded child-output evidence, which
    by design holds the sandboxed child's own output, never a parent secret.)
    """
    data = launch.ledger.path.read_bytes()
    journal = Path(str(launch.ledger.path) + "-journal")
    if journal.exists():
        data += journal.read_bytes()
    evidence = Path(launch.transport.config["evidence_root"])
    for path in evidence.rglob("launcher-stop*.json"):
        data += path.read_bytes()
    return data + json.dumps(row).encode()


@pytest.mark.parametrize("error", ADVERSARIAL, ids=lambda e: type(e).__name__)
def test_no_exception_text_format_reaches_a_durable_sink(tmp_path, reg, error):
    launch, provider = failing_launch(tmp_path, reg, error)
    with pytest.raises(type(error)):
        T.invoke(launch, T.call())
    (row,) = launch.ledger.snapshot()["calls"]
    data = sinks(launch, row)
    for fragment in FRAGMENTS:
        assert fragment.encode() not in data, fragment
    detail = row["stop_detail"]
    assert detail["exception_type"] == type(error).__name__
    assert Path(detail["evidence"]).is_file() and not provider.calls
    if isinstance(error, SandboxStop):
        assert detail["message"] == "sandbox child timeout; reservation retained"
    elif isinstance(error, OSError) and error.errno is not None:
        assert detail["message"] == os.strerror(error.errno)
    else:
        assert detail["message"] == D.SUPPRESSED_MESSAGE


def test_stop_detail_keeps_only_bounded_plain_reviewed_text():
    assert D.stop_detail(D.BudgetStop("ledger halted"))["message"] == "ledger halted"
    for text in ("a\nb", "x" * 301, 'quoted "value"', "x\x00y", "key: [list]"):
        assert D.stop_detail(D.BudgetStop(text))["message"] == D.SUPPRESSED_MESSAGE
    plain = D.stop_detail(OSError("no errno, free text"))
    assert plain == {"exception_type": "OSError", "message": D.SUPPRESSED_MESSAGE}
    assert D.stop_detail(MemoryError()) == {
        "exception_type": "MemoryError",
        "message": "",
        "cause": "memory-exhaustion",
    }
    # Only the exact interpreter text is a trusted classification.
    near = D.stop_detail(RuntimeError("can't start new thread: fixture-pass"))
    assert near["message"] == D.SUPPRESSED_MESSAGE and "cause" not in near


def test_stop_detail_never_masks_a_broken_exception():
    class Broken(Exception):
        def __str__(self):
            raise ValueError("broken __str__")

    class BrokenStop(D.BudgetStop):
        def __str__(self):
            raise ValueError("broken __str__")

    for error in (Broken(), BrokenStop("x")):
        assert D.stop_detail(error) == {
            "exception_type": type(error).__name__,
            "message": D.SUPPRESSED_MESSAGE,
        }


STOP_CLASSES = {"BudgetStop", "SandboxStop", "RateLimitStop", "ProviderStop"}
REVIEWED_MODULES = (
    "tests/evaluation_budget.py",
    "tests/joint_evaluation.py",
    "tests/evaluation_sandbox.py",
    "tests/evaluation_api.py",
    "tests/harness_env.py",
    "tests/evidence.py",
    "tests/stream_observe.py",
    "scripts/joint_evaluation.py",
)


def test_every_stop_message_is_reviewed_literal_text():
    """stop_detail trusts BudgetStop-family text, so every construction in the
    controller's modules must be literal plain prose. The four non-literal
    sites are enumerated and their rendered messages checked."""
    import ast

    root = Path(D.__file__).resolve().parents[1]
    dynamic = []
    for relative in REVIEWED_MODULES:
        tree = ast.parse((root / relative).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and any(
                getattr(base, "attr", getattr(base, "id", None)) in STOP_CLASSES
                for base in node.bases
            ):
                assert not any(
                    isinstance(item, ast.FunctionDef) and item.name == "__str__"
                    for item in node.body
                ), node.name
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = getattr(func, "attr", getattr(func, "id", None))
            if name not in STOP_CLASSES | {"stopped"}:
                continue
            arg = node.args[0] if node.args else None
            if (
                len(node.args) == 1
                and not node.keywords
                and isinstance(arg, ast.Constant)
                and isinstance(arg.value, str)
            ):
                text = arg.value
                if name == "stopped":  # SandboxStop(reason, ...)'s message
                    text = f"sandbox child {text}; reservation retained"
                assert D._reviewed_text(text), (relative, node.lineno, text)
            else:
                dynamic.append((relative, ast.unparse(node).split("(")[0]))
    assert sorted(dynamic) == sorted(
        [
            ("tests/evaluation_budget.py", "BudgetStop"),  # host guard: ints only
            ("tests/evaluation_budget.py", "BudgetStop"),  # one of two literals
            ("tests/evaluation_sandbox.py", "SandboxStop"),  # literal reasons
            ("tests/evaluation_api.py", "ProviderStop"),  # fixed message
        ]
    )
    guard = (
        "host process headroom guard: 2000 user processes exceed 1670 "
        "(60% of the per-user limit 2784); no reservation made"
    )
    rendered = (
        guard,
        "only commissioned read-page attempt2 allowed",
        "only the commissioned Floor G042/sonnet/4 attempt2 allowed",
        str(ProviderStop("sdk-failure", 500, {"fixture-pass": 1})),
        str(SandboxStop("output-limit", "Bearer fixture-token", "")),
    )
    assert all(D._reviewed_text(text) for text in rendered)
    with pytest.raises(D.BudgetStop) as raised:
        D.check_host_headroom(lambda: (2000, 2784))
    assert D.stop_detail(raised.value)["message"] == guard


def test_uncertain_refuses_a_malformed_stop_detail(tmp_path, reg):
    launch, _ = T.launcher(tmp_path, reg)
    call = T.call()
    launch.ledger.reserve(call, launch.binding)
    for bad in ({}, {"bad key!": "x"}, {"k": 1}, {"k": "x" * 1000}, ["x"]):
        with pytest.raises(D.BudgetStop, match="invalid stop detail"):
            launch.ledger.uncertain(call.call_id, "interrupted", detail=bad)
    assert launch.ledger.snapshot()["calls"][0]["status"] == "reserved"


def assert_plain_interrupted_halt(launch, raised, error):
    assert raised.value is error  # the original exception, never the detail's
    snapshot = launch.ledger.snapshot()
    (row,) = snapshot["calls"]
    assert snapshot["metadata"]["halted"]
    assert (row["status"], row["stop_reason"]) == ("uncertain", "interrupted")
    assert snapshot["exposure"] == launch.binding.validate()
    return row


def test_an_overlong_evidence_path_is_left_out_of_the_ledger_detail(tmp_path, reg):
    """Standards r1 finding 4: an evidence path over the detail bound used to
    make uncertain() refuse, leaving the row reserved and the ledger unhalted."""
    deep = tmp_path / "/".join(["d" * 60] * 11)
    launch, _ = failing_launch(tmp_path, reg, BlockingIOError(errno.EAGAIN, "x"))
    launch.transport.config["evidence_root"] = str(deep / "evidence")
    with pytest.raises(BlockingIOError) as raised:
        T.invoke(launch, T.call())
    row = assert_plain_interrupted_halt(launch, raised, raised.value)
    assert "evidence" not in row["stop_detail"]
    assert row["stop_detail"]["errno"] == "EAGAIN"
    (sidecar,) = (deep / "evidence/calls").rglob("launcher-stop.json")
    assert len(str(sidecar.resolve())) > 2 * D.STOP_MESSAGE_LIMIT


def test_a_refused_detail_falls_back_to_the_plain_interrupted_halt(
    tmp_path, reg, monkeypatch
):
    error = BlockingIOError(errno.EAGAIN, "x")
    launch, _ = failing_launch(tmp_path, reg, error)
    monkeypatch.setattr(D, "stop_detail", lambda error: {"bad key!": "x"})
    with pytest.raises(BlockingIOError) as raised:
        T.invoke(launch, T.call())
    row = assert_plain_interrupted_halt(launch, raised, error)
    assert "stop_detail" not in row


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


@pytest.mark.real_host_guard
def test_production_guard_is_the_reviewed_function():
    assert D.BudgetLauncher.host_guard is D.check_host_headroom
    assert SimpleNamespace(**vars(D)).HOST_PROCESS_FRACTION == (3, 5)


def test_offline_tests_see_a_quiet_host_but_paid_processes_keep_the_guard(
    tmp_path, reg, monkeypatch
):
    """Standards r1 finding 2: results never depend on the host's process
    count; the autouse fixture (tests/conftest.py) stays inert in a process
    that admitted a paid launcher, and for tests marked real_host_guard."""
    quiet = D.BudgetLauncher.host_guard
    assert quiet is not D.check_host_headroom and quiet() is None
    applies = quiet.__globals__["quiet_host_applies"]  # tests/conftest.py
    assert applies(None, {})
    assert not applies(object(), {})
    assert not applies(None, {"real_host_guard": True})
    # A saturated default probe no longer reaches an ordinary offline launch.
    monkeypatch.setattr(
        D.check_host_headroom, "__defaults__", ((lambda: (2783, 2784)),)
    )
    with pytest.raises(D.BudgetStop, match="host process headroom guard"):
        D.check_host_headroom()
    launch, provider = T.launcher(tmp_path, reg)
    assert T.invoke(launch, T.call()).stdout == "OK" and len(provider.calls) == 1
