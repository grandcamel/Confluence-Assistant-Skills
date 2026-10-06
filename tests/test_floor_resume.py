"""Floor-only resume selection: temporary ledgers, fake CLI/provider, fake Floor.

The pinned Floor evaluator lives in another checkout, so main() here drives a
small stand-in with the same contract the controller relies on: the
FloorBudget.call(request, command, attempt, evidence, timeout) seam, run_eval's
deterministic call identity, and its "any RuntimeError is a budget stop" rule.
The real evaluator against run 2's ledger copy is the packet's offline proof.
No canonical ledger, credential, provider or model call.
"""

import errno
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests import (
    evaluation_budget as D,
    joint_evaluation as J,
    test_joint_evaluation as T,
)
from tests.test_charged_recovery import recovery as recovery, run_recovery, sha
from tests.test_fourth_recovery import (
    FLOOR_HEAD,
    PLUGIN_HEAD,
    RUN,
    floor_call,
    fourth as fourth,
)
from tests.test_joint_evaluation import reg as reg
from tests.test_second_recovery import second as second
from tests.test_third_recovery import third as third

FACTS = ("G001", "G042")
TRIALS = {(m, f, t) for m in ("sonnet", "terra") for f in FACTS for t in range(1, 6)}
JUDGES = {(m, f) for m in ("sonnet", "terra") for f in FACTS}


class IsolatedSys(SimpleNamespace):
    """The controller's view of an isolated interpreter (flags cannot be set
    on the real sys); argv stays the real one, which the evaluator reads."""

    def __init__(self):
        super().__init__(
            flags=SimpleNamespace(isolated=1, dont_write_bytecode=1),
            pycache_prefix="/dev/null",
            base_prefix=sys.base_prefix,
            executable=sys.executable,
        )

    @property
    def argv(self):
        return sys.argv

    @argv.setter
    def argv(self, value):
        sys.argv = value


FAKE_EVALUATOR = '''\
"""Stand-in for the pinned Floor evaluator (contract only)."""
import hashlib
import json
import sys
from pathlib import Path

from tests import evaluation_budget as D

APPROVED_BUDGET_SHA256 = "0" * 64
APPROVED_INTERFACE_SHA256 = "0" * 64
FACTS = %(facts)r
PROMPT = "Answer from your own knowledge only."


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class FloorBudget:
    def __init__(self, policy, transport):
        self.policy = policy
        ledger = D.Ledger(Path(policy["ledger_path"]))
        self.launchers = {
            role: D.BudgetLauncher(
                ledger,
                ledger.approved_binding(route["binding_id"], policy["registry_sha256"]),
                transport,
            )
            for role, route in policy["roles"].items()
        }

    def call(self, request, command, attempt, evidence, timeout):
        role = "judge" if request["kind"] == "judge" else request["model"]
        task = f"{self.policy['run_id']}/{request['model']}/{request['fact_id']}"
        call = D.Call(
            digest([self.policy["run_id"], request["kind"], task, request["trial"], attempt]),
            "floor-" + request["kind"],
            task,
            max(1, request["trial"]),
            self.policy["source_commit"],
            attempt,
        )
        launcher = self.launchers[role]
        outcome = launcher.run(
            ["claude", "-p", "--model", launcher.binding.model],
            request["prompt"],
            call=call,
            evidence_destination=evidence / call.call_id,
            timeout=timeout,
        )
        row = next(
            r for r in launcher.ledger.snapshot()["calls"]
            if r["call"]["call_id"] == call.call_id
        )
        return outcome, {"settled": row["status"] == "settled", "call": call}


def main(*, transport=None):
    argv = sys.argv[1:]
    policy = json.loads(Path(argv[argv.index("--policy") + 1]).read_text())
    if (policy["module_sha256"], policy["interface_sha256"]) != (
        APPROVED_BUDGET_SHA256,
        APPROVED_INTERFACE_SHA256,
    ):
        raise ValueError("unreviewed D module/interface")
    output = Path(argv[argv.index("--output") + 1])
    output.mkdir(parents=True, exist_ok=True)
    manifest = output / "manifest.json"
    if "--resume" in argv:
        assert json.loads(manifest.read_text()) == policy
    else:
        assert not manifest.exists()
        manifest.write_text(json.dumps(policy))
    budget = FloorBudget(policy, transport)
    requests = [
        {"kind": "trial", "fact_id": f, "model": m, "trial": t, "prompt": PROMPT}
        for f in FACTS
        for m in ("sonnet", "terra")
        for t in range(1, 6)
    ] + [
        {"kind": "judge", "fact_id": f, "model": m, "trial": 0, "prompt": f"judge {f} {m}"}
        for f in FACTS
        for m in ("sonnet", "terra")
    ]
    for request in requests:
        for attempt in (1, 2):
            try:
                outcome, financial = budget.call(
                    request, {}, attempt, output / "budget-evidence", 5
                )
            except (OSError, ValueError, RuntimeError, KeyError, TypeError):
                return 1  # the evaluator's fixed "budget/accounting refusal"
            if financial["settled"] and outcome.stdout.strip():
                break
    return 0
'''


@pytest.fixture
def floor_packet(fourth, monkeypatch, tmp_path):
    """Run 2's halted fixture ledger after the fourth recovery, a schema-3
    Floor-resume configuration and the stand-in evaluator."""
    f = fourth
    run_recovery(f)
    wrapper = Path(sys.executable).parent / "confluence-as"
    if not wrapper.is_file():
        pytest.skip("controller packet tests need the venv's confluence-as wrapper")
    floor_root = tmp_path / "floor-checkout"
    (floor_root / "tests/floor_eval").mkdir(parents=True)
    (floor_root / "tests/floor_eval/run_eval.py").write_text(
        FAKE_EVALUATOR % {"facts": FACTS}
    )
    manifest = D.interface_manifest()
    policy_path = tmp_path / "FLOOR-POLICY.json"
    policy = {
        "run_id": RUN,
        "source_commit": FLOOR_HEAD,
        "ledger_path": str(f.ledger.path),
        "registry_sha256": f.new.digest,
        "module_sha256": manifest["module_sha256"],
        "interface_sha256": manifest["interface_sha256"],
        "roles": {
            role: {"binding_id": binding, "model_id": f.new.binding(binding).model}
            for role, binding in J.FLOOR_BINDINGS.items()
        },
    }
    policy_path.write_text(json.dumps(policy))
    for name, value in (
        ("CANONICAL", f.ledger.path),
        ("FLOOR_TRIALS", TRIALS),
        ("FLOOR_JUDGES", JUDGES),
        ("check_floor_policy", lambda config, result: policy),
        ("check_plugin_settled", lambda rows, head: None),
        ("check_source", lambda entry: None),
        ("runtime_manifest", lambda: {"files": ["fixture"]}),
        ("oauth_presence", lambda: None),
        ("registry", lambda models, proof: f.new),
    ):
        monkeypatch.setattr(J, name, value)
    monkeypatch.setattr(J, "sys", IsolatedSys())
    cli = T.FakeOAuthCLI(f.new)
    cli.check = lambda: None
    cli.argvs = []
    run = cli.run

    def recording(argv, **kwargs):
        cli.argvs.append(list(argv))
        return run(argv, **kwargs)

    cli.run = recording
    providers = []

    class Provider(T.FakeProvider):
        def __init__(self):
            super().__init__()
            providers.append(self)

        def available(self, binding):
            binding.validate()

    monkeypatch.setattr(J, "Sandbox", lambda *args, **kwargs: cli)
    monkeypatch.setattr(J, "Provider", Provider)
    runtime = tmp_path / "runtime.json"
    runtime.write_text(json.dumps({"files": ["fixture"]}))
    claude = tmp_path / "claude-fixture"
    claude.write_text("never executed\n")
    root = Path(J.__file__).resolve().parents[1]

    def entry(path):
        return {"path": str(path), "sha256": sha(path)}

    files = {name: entry(root / rel) for name, rel in J.CODE_FILES.items()}
    files.update(
        models=entry(f.new.bindings[0].pricing.evidence_path),
        proof=entry(f.new.evidence_path),
        claude=entry(claude),
        runtime_manifest=entry(runtime),
        cli_wrapper=entry(wrapper),
        floor_policy=entry(policy_path),
    )
    config = {
        "schema_version": 3,
        "selection": {
            "kind": J.FLOOR_KIND,
            "floor_run_id": RUN,
            "plugin_settled_head": PLUGIN_HEAD,
            "minimum_start_headroom_microdollars": 4_040_961,
        },
        "ledger_path": str(f.ledger.path),
        "serial": True,
        "budget_module_sha256": manifest["module_sha256"],
        "files": files,
        "sources": {
            "plugin": {"path": str(root), "head": PLUGIN_HEAD},
            "floor": {"path": str(floor_root), "head": FLOOR_HEAD},
        },
        "registry_sha256": f.new.digest,
        "cli_bin": str(Path(sys.executable).parent),
        "runtime_read_paths": [str(Path(sys.base_prefix).resolve())],
        "evidence_root": str(tmp_path / "paid"),
    }

    def write(value):
        path = tmp_path / "floor-config.json"
        path.write_text(json.dumps(value))
        return path, sha(path)

    def main(mode, value=None):
        path, digest = write(config if value is None else value)
        monkeypatch.setattr(
            sys,
            "argv",
            ["joint", "--config", str(path), "--config-sha256", digest, mode],
        )
        return J.main()

    monkeypatch.chdir(tmp_path)
    return SimpleNamespace(
        f=f,
        config=config,
        main=main,
        cli=cli,
        providers=providers,
        output=tmp_path / "paid" / J.FLOOR_OUTPUT,
    )


def provider_calls(p):
    return sum(len(provider.calls) for provider in p.providers)


def floor_rows(ledger):
    return [
        r for r in ledger.snapshot()["calls"] if r["call"]["phase"].startswith("floor-")
    ]


def test_dry_admission_reports_floor_work_without_provider_or_writes(
    floor_packet, capsys
):
    p = floor_packet
    before = sha(p.f.ledger.path)
    assert p.main("dry-admission") == 0
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "DRY_ADMITTED" and out["selection"] == J.FLOOR_KIND
    assert out["settled_trial_identities"] == 2 and out["charged_floor_attempts"] == 1
    assert out["remaining_trials"] == 18 and out["remaining_judges"] == 4
    assert out["per_call_reservation_microdollars"] == {
        "sonnet": 2020481,
        "terra": 210241,
        "judge": 4040961,
    }
    assert out["exposure_microdollars"] == p.f.exposure
    assert out["admission_headroom_microdollars"] == D.CAP - p.f.exposure
    assert p.providers == [] and p.cli.argvs == []
    assert sha(p.f.ledger.path) == before


def test_resume_issues_only_never_settled_floor_calls_and_no_plugin_call(
    floor_packet, capsys
):
    p = floor_packet
    before = {r["call"]["call_id"]: r for r in floor_rows(p.f.ledger)}
    assert p.main("run") == 0
    final = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert final["status"] == "FLOOR_RESUME_COMPLETE"
    assert final["remaining_trials"] == final["remaining_judges"] == 0
    # 20 trial identities: 2 settled replay without dispatch; the charged one
    # runs once as its commissioned attempt 2; 17 never started. Plus 4 judges.
    assert provider_calls(p) == len(p.cli.argvs) == 18 + 4
    models = {argv[argv.index("--model") + 1] for argv in p.cli.argvs}
    assert "claude-sonnet-5" not in models  # no plugin route at all
    rows = {r["call"]["call_id"]: r for r in floor_rows(p.f.ledger)}
    for call_id, row in before.items():
        assert rows[call_id] == row  # settled/charged history unchanged
    retry = floor_call("sonnet", "G042", 4, attempt=2)
    assert rows[retry.call_id]["status"] == "settled"
    assert rows[p.f.target.call_id]["status"] == "charged-uncertain"
    assert {r["call"]["attempt"] for r in rows.values()} == {1, 2}
    assert sum(r["call"]["attempt"] == 2 for r in rows.values()) == 1
    # A second run replays every sealed outcome: no dispatch, no charge.
    snapshot = sha(p.f.ledger.path)
    assert p.main("run") == 0
    assert provider_calls(p) == 22 and sha(p.f.ledger.path) == snapshot


def test_clean_host_stop_reserves_nothing_and_the_same_packet_resumes(
    floor_packet, monkeypatch, capsys
):
    p = floor_packet
    issued = []

    def guard():
        if len(issued) == 5:
            D.check_host_headroom(lambda: (2000, 2784))
        issued.append(1)

    monkeypatch.setattr(D.BudgetLauncher, "host_guard", staticmethod(guard))
    exposure = p.f.ledger.snapshot()["exposure"]
    assert p.main("run") == 2
    stopped = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert stopped["status"] == "STOPPED_INCOMPLETE"
    assert stopped["floor_stop"]["exception_type"] == "BudgetStop"
    assert "host process headroom guard" in stopped["floor_stop"]["message"]
    snapshot = p.f.ledger.snapshot()
    assert not snapshot["metadata"]["halted"] and provider_calls(p) == 5
    assert all(
        r["status"] in {"settled", "charged-uncertain"} for r in snapshot["calls"]
    )
    assert snapshot["exposure"] > exposure
    (sidecar,) = (p.output / "controller-stops").iterdir()
    assert json.loads(sidecar.read_text())["exception_type"] == "BudgetStop"
    monkeypatch.setattr(D.BudgetLauncher, "host_guard", staticmethod(lambda: None))
    assert p.main("dry-admission") == 0
    assert json.loads(capsys.readouterr().out)["remaining_trials"] == 18 - 5
    assert p.main("run") == 0
    assert provider_calls(p) == 22  # each never-settled call dispatched once


def test_interrupted_floor_call_records_its_cause_and_blocks_both_modes(
    floor_packet, monkeypatch, capsys
):
    p = floor_packet
    run = p.cli.run

    def exhausted(argv, **kwargs):
        if len(p.cli.argvs) == 3:
            raise BlockingIOError(errno.EAGAIN, "Resource temporarily unavailable")
        return run(argv, **kwargs)

    p.cli.run = exhausted
    assert p.main("run") == 2
    lines = capsys.readouterr().out.strip().splitlines()
    stopped = json.loads(lines[-1])
    logged = [
        json.loads(line[len("floor-stop ") :])
        for line in lines
        if line.startswith("floor-stop ")
    ]
    assert logged and logged[-1]["exception_type"] == "BlockingIOError"
    assert logged[-1]["errno"] == "EAGAIN" and stopped["floor_stop"] == logged[-1]
    assert "prompt" not in logged[-1] and Path(logged[-1]["evidence"]).is_file()
    snapshot = p.f.ledger.snapshot()
    (row,) = [r for r in snapshot["calls"] if r["status"] == "uncertain"]
    assert snapshot["metadata"]["halted"] and row["stop_reason"] == "interrupted"
    assert row["stop_detail"]["exception_type"] == "BlockingIOError"
    assert Path(row["stop_detail"]["evidence"]).is_file()
    before = sha(p.f.ledger.path)
    calls = provider_calls(p)
    for mode in ("dry-admission", "run"):
        assert p.main(mode) == 2
        assert json.loads(capsys.readouterr().out)["status"] == "STOPPED_INCOMPLETE"
    assert provider_calls(p) == calls and sha(p.f.ledger.path) == before


def test_floor_resume_admits_only_dry_admission_and_run(floor_packet, capsys):
    p = floor_packet
    for mode in ("probe", "recover-and-transition"):
        assert p.main(mode) == 2
        assert json.loads(capsys.readouterr().out)["status"] == "STOPPED_INCOMPLETE"
    assert p.providers == []


@pytest.mark.parametrize(
    "mutate",
    [
        lambda c: c["selection"].update(extra=1),
        lambda c: c["selection"].update(floor_run_id="other-run"),
        lambda c: c["selection"].update(plugin_settled_head="xyz"),
        lambda c: c["selection"].update(minimum_start_headroom_microdollars=0),
        lambda c: c["selection"].update(minimum_start_headroom_microdollars=4_040_960),
        lambda c: c["files"].update(prior_ledger=c["files"]["models"]),
        lambda c: c["files"].update(recovery_plan=c["files"]["models"]),
        lambda c: c["files"].pop("floor_policy"),
        lambda c: c["sources"].pop("floor"),
        lambda c: c.update(schema_version=2),
    ],
)
def test_floor_resume_refuses_unreviewed_shapes_before_any_provider(
    floor_packet, mutate, capsys
):
    p = floor_packet
    config = json.loads(json.dumps(p.config))
    mutate(config)
    before = sha(p.f.ledger.path)
    for mode in ("dry-admission", "run"):
        assert p.main(mode, config) == 2
        assert json.loads(capsys.readouterr().out)["status"] == "STOPPED_INCOMPLETE"
    assert p.providers == [] and sha(p.f.ledger.path) == before


def test_floor_resume_refuses_a_still_halted_ledger(fourth, monkeypatch):
    f = fourth  # the fourth recovery has not run
    config = {
        "ledger_path": str(f.ledger.path),
        "selection": {
            "kind": J.FLOOR_KIND,
            "floor_run_id": RUN,
            "plugin_settled_head": PLUGIN_HEAD,
            "minimum_start_headroom_microdollars": 4_040_961,
        },
        "sources": {"floor": {"head": FLOOR_HEAD}},
    }
    monkeypatch.setattr(J, "check_plugin_settled", lambda rows, head: None)
    with pytest.raises(D.BudgetStop, match="halted"):
        J.check_floor_resume_ledger(config, f.new)


class StubFloor:
    APPROVED_BUDGET_SHA256 = APPROVED_INTERFACE_SHA256 = "0" * 64

    class FloorBudget:
        def __init__(self, binding_id, run_id, source_commit, fail=None):
            self.policy = {"run_id": run_id, "source_commit": source_commit}
            self.launchers = {
                role: SimpleNamespace(binding=SimpleNamespace(binding_id=binding_id))
                for role in ("sonnet", "terra", "judge")
            }
            self.calls, self.fail = [], fail

        def call(self, request, command, attempt, evidence, timeout):
            self.calls.append((request["fact_id"], request["trial"], attempt))
            if self.fail:
                raise self.fail
            return "outcome", {}


RETRY = {
    "retry": dict(D.COMMISSIONED_RETRIES[4]),
    "record_sha256": "e" * 64,
    "source_head": FLOOR_HEAD,
    "predecessor_call_id": "f" * 64,
}


def adapted(tmp_path, binding_id="floor-sonnet55-api", source=FLOOR_HEAD, fail=None):
    floor = SimpleNamespace(FloorBudget=StubFloor.FloorBudget)
    J.install_floor_adapter(floor, [RETRY], tmp_path)
    return floor.FloorBudget(binding_id, RUN, source, fail)


def request(fact="G042", trial=4, model="sonnet", kind="trial"):
    return {"kind": kind, "fact_id": fact, "model": model, "trial": trial}


def test_adapter_issues_only_the_commissioned_replacement_attempt(tmp_path):
    budget = adapted(tmp_path)
    for item in (request(), request(trial=3), request(fact="G041")):
        for attempt in (1, 2):
            budget.call(item, {}, attempt, tmp_path, 5)
    assert budget.calls == [
        ("G042", 4, 2),
        ("G042", 4, 2),
        ("G042", 3, 1),
        ("G042", 3, 2),
        ("G041", 4, 1),
        ("G041", 4, 2),
    ]
    other_model = adapted(tmp_path, binding_id="floor-haiku45-api")
    other_model.call(request(model="terra"), {}, 1, tmp_path, 5)
    other_source = adapted(tmp_path, source="d" * 40)
    other_source.call(request(), {}, 1, tmp_path, 5)
    judge = adapted(tmp_path, binding_id="floor-opus55-api")
    judge.call(request(kind="judge", trial=0), {}, 1, tmp_path, 5)
    assert [c[2] for c in other_model.calls + other_source.calls + judge.calls] == [
        1,
        1,
        1,
    ]


def test_adapter_records_a_stopped_call_and_re_raises(tmp_path, capsys):
    error = BlockingIOError(errno.EAGAIN, "Resource temporarily unavailable")
    budget = adapted(tmp_path, fail=error)
    with pytest.raises(BlockingIOError) as raised:
        budget.call(request(), {}, 1, tmp_path, 5)
    assert raised.value is error
    line = capsys.readouterr().out.strip()
    entry = json.loads(line[len("floor-stop ") :])
    assert entry["attempt"] == 2 and entry["exception_type"] == "BlockingIOError"
    sealed = json.loads(Path(entry["evidence"]).read_text())
    assert {k: sealed[k] for k in ("fact_id", "model", "trial")} == {
        "fact_id": "G042",
        "model": "sonnet",
        "trial": 4,
    }
    assert [entry] == J.LAST_FLOOR_STOP


def test_load_floor_binds_the_evaluator_to_the_controller_budget_module(tmp_path):
    folder = tmp_path / "tests/floor_eval"
    folder.mkdir(parents=True)
    (folder / "run_eval.py").write_text(
        'APPROVED_BUDGET_SHA256 = "0" * 64\nAPPROVED_INTERFACE_SHA256 = "1" * 64\n'
    )
    floor = J.load_floor({"sources": {"floor": {"path": str(tmp_path)}}})
    manifest = D.interface_manifest()
    assert manifest["module_sha256"] == floor.APPROVED_BUDGET_SHA256
    assert manifest["interface_sha256"] == floor.APPROVED_INTERFACE_SHA256


def coverage_rows(rows):
    return [
        {
            "call": {
                "call_id": f"id-{n}",
                "phase": phase,
                "task": task,
                "trial": trial,
                "attempt": attempt,
                "source_commit": FLOOR_HEAD,
            },
            "binding_id": binding,
            "status": status,
            "actual": 10 if status == "settled" else None,
        }
        for n, (phase, task, trial, attempt, binding, status) in enumerate(rows)
    ]


def test_floor_coverage_counts_logical_identities(monkeypatch):
    monkeypatch.setattr(J, "FLOOR_TRIALS", TRIALS)
    monkeypatch.setattr(J, "FLOOR_JUDGES", JUDGES)
    sonnet, judge = "floor-sonnet55-api", "floor-opus55-api"
    rows = coverage_rows(
        [
            ("floor-trial", f"{RUN}/sonnet/G042", 4, 1, sonnet, "charged-uncertain"),
            ("floor-trial", f"{RUN}/sonnet/G042", 4, 2, sonnet, "settled"),
            ("floor-trial", f"{RUN}/sonnet/G042", 3, 1, sonnet, "settled"),
            ("floor-judge", f"{RUN}/sonnet/G042", 1, 1, judge, "settled"),
            (
                "routing-reaccept",
                "r1/confluence-01",
                1,
                1,
                "plugin-sonnet5-api",
                "settled",
            ),
            ("floor-trial", "other-run/sonnet/G042", 1, 1, sonnet, "settled"),
        ]
    )
    coverage = J.floor_coverage(rows, RUN, FLOOR_HEAD)
    assert coverage == {
        "settled_trial_identities": 2,
        "settled_judge_identities": 1,
        "charged_floor_attempts": 1,
        "settled_retry_attempts": 1,
        "pending_settlements": 0,
        "remaining_trials": len(TRIALS) - 2,
        "remaining_judges": len(JUDGES) - 1,
        "settled_floor_microdollars": 30,
    }
    for bad in (
        ("floor-trial", f"{RUN}/sonnet/G999", 1, 1, sonnet, "settled"),
        ("floor-trial", f"{RUN}/terra/G042", 1, 1, sonnet, "settled"),
        ("floor-trial", f"{RUN}/sonnet/G042", 1, 1, sonnet, "uncertain"),
        ("floor-other", f"{RUN}/sonnet/G042", 1, 1, sonnet, "settled"),
    ):
        with pytest.raises(D.BudgetStop):
            J.floor_coverage(coverage_rows([bad]), RUN, FLOOR_HEAD)
    foreign = coverage_rows(
        [("floor-trial", f"{RUN}/sonnet/G042", 1, 1, sonnet, "settled")]
    )
    foreign[0]["call"]["source_commit"] = "d" * 40
    with pytest.raises(D.BudgetStop):
        J.floor_coverage(foreign, RUN, FLOOR_HEAD)


def test_plugin_stage_must_be_settled_on_its_own_head():
    import yaml

    root = Path(J.__file__).parents[1]
    items = []
    for phase, path, key in [
        ("sufficiency", root / "tests/e2e/test_cases.yaml", "tasks"),
        ("routing", root / "skills/confluence/tests/routing_golden.yaml", "tests"),
    ]:
        for task in yaml.safe_load(path.read_text())[key]:
            for trial in range(1, 6):
                first = (phase, task["id"], trial) == ("sufficiency", "read-page", 1)
                items.append(
                    {
                        "call": {
                            "phase": phase,
                            "task": task["id"],
                            "trial": trial,
                            "attempt": 2 if first else 1,
                            "source_commit": PLUGIN_HEAD,
                        },
                        "binding_id": "plugin-sonnet5-api",
                        "status": "settled",
                        "receipt": {"fixture": True},
                        "outcome": {"fixture": True},
                    }
                )
    predecessor = {
        "call": {
            "phase": "sufficiency",
            "task": "read-page",
            "trial": 1,
            "attempt": 1,
            "source_commit": "a" * 40,
        },
        "binding_id": "plugin-sonnet5-api",
        "status": "charged-uncertain",
    }
    J.check_plugin_settled([predecessor, *items], PLUGIN_HEAD)
    with pytest.raises(D.BudgetStop, match="another head"):
        J.check_plugin_settled([predecessor, *items], "d" * 40)
    with pytest.raises(D.BudgetStop):
        J.check_plugin_settled([predecessor, *items[1:]], PLUGIN_HEAD)


def test_admission_headroom_credits_validated_pending_settlements():
    snapshot = {
        "headroom": 3_079_520,
        "calls": [
            {
                "status": "reserved",
                "reservation": 3_020_480,
                "partial_receipt": {"actual_usd": "0.034100"},
                "outcome": {"path": "sealed"},
            },
            {
                "status": "reserved",
                "reservation": 3_020_480,
                "partial_receipt": None,
                "outcome": None,
            },
            {"status": "settled", "reservation": 3_020_480},
        ],
    }
    assert J.admission_headroom(snapshot) == 3_079_520 + 3_020_480 - 34_100
