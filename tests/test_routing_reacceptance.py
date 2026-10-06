"""Routing-only re-acceptance selection: fake provider/CLI, temporary ledgers only.

No canonical ledger, credential, provider or model call: every ledger here is a
tmp_path fixture and the canonical path is redirected before any config check.
"""

import fcntl
import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from tests import (
    evaluation_budget as D,
    joint_evaluation as J,
    test_joint_evaluation as T,
)
from tests.test_charged_recovery import recovery as recovery, run_recovery, sha
from tests.test_joint_evaluation import reg as reg
from tests.test_second_recovery import second as second
from tests.test_third_recovery import third as third

ROOT = Path(J.__file__).resolve().parents[1]
GOLDEN = yaml.safe_load(
    (ROOT / "skills/confluence/tests/routing_golden.yaml").read_text()
)["tests"]
OLD, NEW = "b" * 40, "c" * 40
SKILL_IDS = {"confluence": "confluence-assistant-skills:confluence", "jira": "jira"}
ENV_NAMES = (
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
    "PYTEST_ADDOPTS",
    "EVALUATION_SOURCE_COMMIT",
    "HARNESS_CLI_BIN",
    "TMPDIR",
)


@pytest.fixture(autouse=True)
def prompt_broker_shutdown(monkeypatch):
    """Shorten only the local broker's shutdown poll; hundreds of fake trials."""
    import socketserver

    serve = socketserver.BaseServer.serve_forever
    monkeypatch.setattr(
        socketserver.BaseServer,
        "serve_forever",
        lambda self, poll_interval=0.01: serve(self, poll_interval),
    )


class FakeRoutingCLI(T.FakeOAuthCLI):
    """Real broker round trip, then a native-shaped Skill observation line."""

    def __init__(self, reg, choose):
        super().__init__(reg)
        self.choose = choose
        self.argvs = []

    def run(self, argv, *, on_line=None, prompt="", **kwargs):
        self.argvs.append(list(argv))
        lines = []
        rc, _stdout, stderr = super().run(argv, on_line=lines.append, **kwargs)
        skill = self.choose(prompt)
        if skill:
            block = {
                "type": "tool_use",
                "name": "Skill",
                "input": {"skill": SKILL_IDS[skill]},
            }
            lines.insert(
                0,
                json.dumps({"type": "assistant", "message": {"content": [block]}}),
            )
        for line in lines:
            if on_line:
                on_line(line)
        return rc, "".join(line + "\n" for line in lines), stderr


def detect(line):
    event = json.loads(line)
    for block in (event.get("message") or {}).get("content", []):
        if block.get("name") == "Skill":
            return block["input"]["skill"].rsplit(":", 1)[-1]
    return None


def by_product(prompt):
    return (
        "confluence" if "Confluence" in prompt else "jira" if "Jira" in prompt else None
    )


def routing_cmd(binding):
    return ["claude", "--print", "--tools", "Bash,Skill", "--model", binding.model]


def plugin_launcher(ledger, registry, cli, evidence, reacceptance=None, binding=None):
    binding = binding or registry.binding("plugin-sonnet5-api")
    transport = J.ProductionTransport(
        {"files": {}, "evidence_root": str(evidence)}, registry, cli, T.FakeProvider()
    )
    return J.JointLauncher(ledger, binding, transport, reacceptance), transport


def routing(launcher, task, trial, source, prompt=None, attempt=1):
    return launcher.run(
        routing_cmd(launcher.binding),
        prompt or f"Confluence {task}",
        call=D.Call(f"uuid-{task}-{trial}", "routing", task, trial, source, attempt),
        detect_line=detect,
        timeout=5,
    )


def rows(ledger, phase):
    return [r for r in ledger.snapshot()["calls"] if r["call"]["phase"] == phase]


def test_reacceptance_trial_gets_fresh_identity_beside_settled_joint_row(tmp_path, reg):
    ledger = D.Ledger.create(tmp_path / "ledger.sqlite3", reg)
    binding = reg.binding("plugin-sonnet5-api")
    cli = FakeRoutingCLI(reg, by_product)
    joint, transport = plugin_launcher(ledger, reg, cli, tmp_path / "joint")
    assert routing(joint, "confluence-03", 1, OLD).result == "confluence"
    (old_row,) = rows(ledger, "routing")
    provider_calls = len(transport.provider.calls)
    # The joint selection cannot re-measure a settled routing trial on new bytes.
    with pytest.raises(D.BudgetStop, match="resume source or request mismatch"):
        routing(joint, "confluence-03", 1, NEW)
    assert len(transport.provider.calls) == provider_calls

    reaccept, transport = plugin_launcher(
        ledger, reg, cli, tmp_path / "re", ("rr-1", NEW)
    )
    outcome = routing(reaccept, "confluence-03", 1, NEW)
    assert outcome.result == "confluence" and len(transport.provider.calls) == 1
    (row,) = rows(ledger, J.REACCEPT_PHASE)
    assert row["call"] == {
        "call_id": D._digest([J.REACCEPT_KIND, "rr-1", "confluence-03", 1])[:32],
        "phase": "routing-reaccept",
        "task": "rr-1/confluence-03",
        "trial": 1,
        "source_commit": NEW,
        "attempt": 1,
    }
    assert row["status"] == "settled" and row["reservation"] == binding.validate()
    assert rows(ledger, "routing") == [old_row]
    argv = cli.argvs[-1]
    assert argv[argv.index("--max-turns") + 1] == "1"
    assert (tmp_path / "re/calls" / row["call"]["call_id"]).is_dir()

    # Same packet restart restores the sealed outcome: no reserve, no dispatch.
    before = sha(ledger.path)
    again, transport = plugin_launcher(ledger, reg, cli, tmp_path / "re", ("rr-1", NEW))
    assert routing(again, "confluence-03", 1, NEW).result == "confluence"
    assert transport.provider.calls == [] and sha(ledger.path) == before
    # A new reviewed run id is a fresh measurement, never a replay.
    fresh, transport = plugin_launcher(
        ledger, reg, cli, tmp_path / "re2", ("rr-2", NEW)
    )
    routing(fresh, "confluence-03", 1, NEW)
    assert len(transport.provider.calls) == 1
    assert len(rows(ledger, J.REACCEPT_PHASE)) == 2


@pytest.mark.parametrize(
    "mutation",
    [
        {"phase": "sufficiency"},
        {"phase": "floor-trial"},
        {"attempt": 2},
        {"source_commit": OLD},
    ],
)
def test_reacceptance_refuses_other_phases_retries_and_sources(tmp_path, reg, mutation):
    ledger = D.Ledger.create(tmp_path / "ledger.sqlite3", reg)
    binding = reg.binding("plugin-sonnet5-api")
    cli = FakeRoutingCLI(reg, by_product)
    launcher, transport = plugin_launcher(
        ledger, reg, cli, tmp_path / "re", ("rr-1", NEW)
    )
    call = replace(D.Call("uuid", "routing", "confluence-01", 1, NEW), **mutation)
    with pytest.raises(D.BudgetStop, match="only its own routing trials"):
        launcher.run(routing_cmd(binding), "prompt", call=call, timeout=5)
    assert transport.provider.calls == [] and ledger.snapshot()["calls"] == []


def test_reacceptance_refuses_any_other_binding(tmp_path, reg):
    ledger = D.Ledger.create(tmp_path / "ledger.sqlite3", reg)
    launcher, transport = plugin_launcher(
        ledger,
        reg,
        FakeRoutingCLI(reg, by_product),
        tmp_path,
        ("rr-1", NEW),
        binding=reg.binding("floor-sonnet55-api"),
    )
    with pytest.raises(D.BudgetStop, match="only its own routing trials"):
        routing(launcher, "confluence-01", 1, NEW)
    assert transport.provider.calls == []


def test_reacceptance_on_three_link_ledger_keeps_history_and_counts_once(third):
    f = third
    run_recovery(f)
    before = f.ledger.snapshot()
    launcher, transport = plugin_launcher(
        f.ledger,
        f.new,
        FakeRoutingCLI(f.new, by_product),
        f.path.parent / "re",
        ("rr-1", NEW),
    )
    outcome = routing(launcher, "jira-01", 5, NEW, prompt="Jira jira-01")
    after = f.ledger.snapshot()
    assert outcome.result == "jira" and len(transport.provider.calls) == 1
    old = {r["call"]["call_id"]: r for r in before["calls"]}
    new = {r["call"]["call_id"]: r for r in after["calls"]}
    assert len(new) == len(old) + 1 and all(new[k] == v for k, v in old.items())
    assert {r["status"] for r in old.values()} >= {"charged-uncertain", "settled"}
    assert after["exposure"] == before["exposure"] + D.microdollars(
        outcome.receipt.actual_usd
    )
    assert not after["metadata"]["halted"]


def ledger_rows(tmp_path, run_id="rr-1", source=NEW, skill=by_product):
    items = []
    for case in GOLDEN:
        for trial in range(1, 6):
            outcome = tmp_path / f"{run_id}-{case['id']}-{trial}.json"
            outcome.write_text(json.dumps({"result": skill(case["input"])}))
            items.append(
                {
                    "call": {
                        "call_id": f"{case['id']}-{trial}",
                        "phase": J.REACCEPT_PHASE,
                        "task": f"{run_id}/{case['id']}",
                        "trial": trial,
                        "source_commit": source,
                        "attempt": 1,
                    },
                    "binding_id": "plugin-sonnet5-api",
                    "status": "settled",
                    "actual": 34,
                    "receipt": {"fixture": True},
                    "outcome": {"path": str(outcome)},
                }
            )
    return items


def test_reacceptance_completion_tally_and_exact_coverage(tmp_path):
    items = ledger_rows(tmp_path)
    tally, settled = J.check_reacceptance_completion(items, "rr-1", NEW)
    assert settled == 50 * 34
    assert {k: v["correct"] for k, v in tally.items()} == dict.fromkeys(
        [case["id"] for case in GOLDEN], 5
    )
    # Other run ids and the joint run's own rows are not this run's evidence.
    other = ledger_rows(tmp_path, run_id="rr-0")
    assert J.check_reacceptance_completion(other + items, "rr-1", NEW)[1] == 1700
    for bad in [
        items[:-1],
        [*items, items[-1]],
        [{**items[0], "status": "uncertain"}, *items[1:]],
        [{**items[0], "call": {**items[0]["call"], "attempt": 2}}, *items[1:]],
        [{**items[0], "call": {**items[0]["call"], "source_commit": OLD}}, *items[1:]],
        [{**items[0], "binding_id": "floor-sonnet55-api"}, *items[1:]],
        [{**items[0], "call": {**items[0]["call"], "task": "rr-1/extra"}}, *items],
    ]:
        with pytest.raises(D.BudgetStop):
            J.check_reacceptance_completion(bad, "rr-1", NEW)


def test_joint_resume_completion_ignores_reacceptance_rows(tmp_path, reg, monkeypatch):
    """A later same-packet joint resume (for Floor completion) is not disturbed."""
    import pytest as pytest_module

    ledger = D.Ledger.create(tmp_path / "ledger.sqlite3", reg)
    cli = FakeRoutingCLI(reg, by_product)
    joint, _ = plugin_launcher(ledger, reg, cli, tmp_path / "joint")
    routing(joint, "confluence-01", 1, OLD)
    reaccept, _ = plugin_launcher(ledger, reg, cli, tmp_path / "re", ("rr-1", NEW))
    routing(reaccept, "confluence-01", 1, NEW)
    floor = tmp_path / "floor/tests/floor_eval"
    floor.mkdir(parents=True)
    marker = tmp_path / "floor-ran"
    (floor / "run_eval.py").write_text(
        "from pathlib import Path\n"
        "def main(transport=None):\n"
        f"    Path({str(marker)!r}).write_text('ran')\n"
        "    return 0\n"
    )
    config = {
        "sources": {
            "plugin": {"path": str(ROOT), "head": OLD},
            "floor": {"path": str(tmp_path / "floor"), "head": "d" * 40},
        },
        "files": {"floor_policy": {"path": "fixture", "sha256": "e" * 64}},
        "cli_bin": str(tmp_path),
        "evidence_root": str(tmp_path / "joint-evidence"),
        "ledger_path": str(ledger.path),
    }
    checked = []
    monkeypatch.setattr(J, "check_plugin_completion", checked.append)
    monkeypatch.setattr(pytest_module, "main", lambda args: 0)
    monkeypatch.setattr(sys, "argv", list(sys.argv))
    for name in (*ENV_NAMES, "E2E_SUFFICIENCY"):
        monkeypatch.setenv(name, "restored-after-test")
    monkeypatch.chdir(tmp_path)
    J.run_joint(config, SimpleNamespace(rate_limited=False))
    (plugin_rows,) = checked
    assert [r["call"]["phase"] for r in plugin_rows] == ["routing"]
    assert plugin_rows[0]["call"]["source_commit"] == OLD
    assert marker.read_text() == "ran"


def test_joint_completion_would_refuse_relabelled_reacceptance_rows(tmp_path):
    joint = []
    for phase, path, key in [
        ("sufficiency", ROOT / "tests/e2e/test_cases.yaml", "tasks"),
        ("routing", ROOT / "skills/confluence/tests/routing_golden.yaml", "tests"),
    ]:
        for task in yaml.safe_load(path.read_text())[key]:
            for trial in range(1, 6):
                joint.append(
                    {
                        "call": {
                            "phase": phase,
                            "task": task["id"],
                            "trial": trial,
                            "attempt": 1,
                        },
                        "binding_id": "plugin-sonnet5-api",
                        "status": "settled",
                        "receipt": {"fixture": True},
                        "outcome": {"fixture": True},
                    }
                )
    J.check_plugin_completion(joint)
    relabelled = [
        {**r, "call": {**r["call"], "phase": "routing"}} for r in ledger_rows(tmp_path)
    ]
    with pytest.raises(D.BudgetStop):
        J.check_plugin_completion(joint + relabelled)
    assert J.REACCEPT_PHASE not in ("sufficiency", "routing")


def run_config(tmp_path, ledger, run_id="rr-1"):
    return {
        "schema_version": 2,
        "selection": {
            "kind": J.REACCEPT_KIND,
            "run_id": run_id,
            "minimum_start_headroom_microdollars": 6_000_000,
        },
        "files": {},
        "sources": {"plugin": {"path": str(ROOT), "head": NEW}},
        "cli_bin": str(tmp_path / "bin"),
        "evidence_root": str(tmp_path / "paid"),
        "ledger_path": str(ledger.path),
    }


@pytest.mark.parametrize("miss", [0, 2])
def test_run_reacceptance_selects_only_routing_and_scores_from_ledger(
    tmp_path, reg, monkeypatch, miss
):
    import pytest as pytest_module

    ledger = D.Ledger.create(tmp_path / "ledger.sqlite3", reg)
    config = run_config(tmp_path, ledger)
    misses = {"n": 0}

    def choose(prompt):
        # Simulate the pre-fix confluence-03 deferral on `miss` trials.
        if "permissions" in prompt and misses["n"] < miss:
            misses["n"] += 1
            return None
        return by_product(prompt)

    cli = FakeRoutingCLI(reg, choose)
    pytest_args = []

    def fake_pytest_main(args):
        pytest_args.append(args)
        launcher = D.require_launcher()
        failed = 0
        for case in GOLDEN:
            correct = 0
            for trial in range(1, 6):
                outcome = launcher.run(
                    routing_cmd(launcher.binding),
                    case["input"],
                    call=D.harness_call("routing", case["id"], trial),
                    detect_line=detect,
                    timeout=5,
                )
                correct += outcome.result == case.get("expected_skill")
            failed += correct < 4
        return 1 if failed else 0

    def forbidden(*args, **kwargs):
        raise AssertionError("routing re-acceptance crossed into Floor/sufficiency")

    monkeypatch.setattr(pytest_module, "main", fake_pytest_main)
    monkeypatch.setattr(J, "load_floor", forbidden)
    monkeypatch.setattr(J, "finish_floor", forbidden)
    monkeypatch.setattr(J, "check_plugin_completion", forbidden)
    for name in ENV_NAMES:
        monkeypatch.setenv(name, "restored-after-test")
    monkeypatch.chdir(tmp_path)
    with J.admission(config, reg, cli, T.FakeProvider(), ledger) as transport:
        passed, tally, settled = J.run_reacceptance(config, transport)
    (args,) = pytest_args
    assert args[-1] == "skills/confluence/tests/test_routing.py"
    assert not any("e2e" in a or "floor" in a or "sufficiency" in a for a in args)
    assert passed is (miss == 0)
    assert tally["confluence-03"]["correct"] == 5 - miss
    assert all(v["correct"] == 5 for k, v in tally.items() if k != "confluence-03")
    snapshot = ledger.snapshot()
    assert len(snapshot["calls"]) == 50 and settled == snapshot["exposure"] == 50 * 34
    assert {r["call"]["phase"] for r in snapshot["calls"]} == {J.REACCEPT_PHASE}
    assert all(a[a.index("--max-turns") + 1] == "1" for a in cli.argvs)
    assert len(cli.argvs) == 50 and (tmp_path / "paid/calls").is_dir()


def reacceptance_pytest(tmp_path, reg, monkeypatch, trials, status):
    import pytest as pytest_module

    ledger = D.Ledger.create(tmp_path / "ledger.sqlite3", reg)
    config = run_config(tmp_path, ledger)

    def fake_pytest_main(args):
        launcher = D.require_launcher()
        for case in GOLDEN:
            for trial in range(1, trials + 1):
                launcher.run(
                    routing_cmd(launcher.binding),
                    case["input"],
                    call=D.harness_call("routing", case["id"], trial),
                    detect_line=detect,
                    timeout=5,
                )
        return status

    monkeypatch.setattr(pytest_module, "main", fake_pytest_main)
    for name in ENV_NAMES:
        monkeypatch.setenv(name, "restored-after-test")
    monkeypatch.chdir(tmp_path)
    return config, ledger


@pytest.mark.parametrize(("trials", "status"), [(0, 0), (1, 1), (0, 5)])
def test_run_reacceptance_refuses_incomplete_runs(
    tmp_path, reg, monkeypatch, trials, status
):
    config, ledger = reacceptance_pytest(tmp_path, reg, monkeypatch, trials, status)
    cli = FakeRoutingCLI(reg, by_product)
    with (
        J.admission(config, reg, cli, T.FakeProvider(), ledger) as transport,
        pytest.raises(D.BudgetStop, match=r"coverage differs|incomplete"),
    ):
        J.run_reacceptance(config, transport)
    assert len(cli.argvs) == 10 * trials


@pytest.mark.parametrize(("correct", "status"), [(5, 1), (3, 0)])
def test_run_reacceptance_refuses_ledger_and_pytest_disagreement(
    tmp_path, reg, monkeypatch, correct, status
):
    config, ledger = reacceptance_pytest(tmp_path, reg, monkeypatch, 0, status)
    tally = {case["id"]: {"correct": correct} for case in GOLDEN}
    monkeypatch.setattr(
        J, "check_reacceptance_completion", lambda rows, run_id, head: (tally, 0)
    )
    cli = FakeRoutingCLI(reg, by_product)
    with (
        J.admission(config, reg, cli, T.FakeProvider(), ledger) as transport,
        pytest.raises(D.BudgetStop, match="disagree"),
    ):
        J.run_reacceptance(config, transport)


def test_ledger_gate_requires_existing_quiescent_ledger_and_headroom(tmp_path, reg):
    ledger = D.Ledger.create(tmp_path / "ledger.sqlite3", reg)
    config = run_config(tmp_path, ledger)
    _, snapshot = J.check_reacceptance_ledger(config, reg)
    assert snapshot["headroom"] == D.CAP
    reservation = reg.binding("plugin-sonnet5-api").validate()
    for minimum in (reservation - 1, D.CAP + 1):
        bad = {**config, "selection": {**config["selection"]}}
        bad["selection"]["minimum_start_headroom_microdollars"] = minimum
        with pytest.raises(D.BudgetStop):
            J.check_reacceptance_ledger(bad, reg)
    launcher, _ = plugin_launcher(
        ledger, reg, FakeRoutingCLI(reg, by_product), tmp_path / "joint"
    )
    routing(launcher, "confluence-01", 1, OLD)
    full = {**config, "selection": {**config["selection"]}}
    full["selection"]["minimum_start_headroom_microdollars"] = D.CAP
    with pytest.raises(D.BudgetStop, match="headroom"):
        J.check_reacceptance_ledger(full, reg)
    missing = {**config, "ledger_path": str(tmp_path / "absent.sqlite3")}
    with pytest.raises(D.BudgetStop, match="existing ledger"):
        J.check_reacceptance_ledger(missing, reg)
    assert not (tmp_path / "absent.sqlite3").exists()
    assert not (tmp_path / "absent.init.json").exists()
    ledger.reserve(
        D.Call("halt", "routing", "x", 1, OLD), reg.binding("plugin-sonnet5-api")
    )
    ledger.uncertain("halt", "interrupted", halt=True)
    with pytest.raises(D.BudgetStop, match="halted"):
        J.check_reacceptance_ledger(config, reg)


@pytest.mark.parametrize("suffix", [".joint-lock", ".sqlite3.controller"])
def test_quiescence_refuses_while_another_writer_holds_a_lock(tmp_path, suffix):
    path = tmp_path / "ledger.sqlite3"
    J.check_quiescent(path)
    with (tmp_path / ("ledger" + suffix)).open("a") as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(D.BudgetStop, match="another ledger writer"):
            J.check_quiescent(path)
    J.check_quiescent(path)


def file_entry(path):
    path = Path(path)
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


@pytest.fixture
def packet(tmp_path, reg, monkeypatch):
    """A complete schema-2 packet against a redirected temporary canonical ledger."""
    wrapper = Path(sys.executable).parent / "confluence-as"
    if not wrapper.is_file():
        pytest.skip("controller packet tests need the venv's confluence-as wrapper")
    canonical = (tmp_path / "out/confluence-evaluation").resolve()
    canonical.mkdir(parents=True)
    canonical = canonical / "aggregate-budget-v2.sqlite3"
    monkeypatch.setattr(J, "CANONICAL", canonical)
    ledger = D.Ledger.create(canonical, reg)
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
    monkeypatch.setattr(J, "oauth_presence", lambda: None)
    monkeypatch.setattr(J, "check_source", lambda entry: None)
    monkeypatch.setattr(J, "runtime_manifest", lambda: {"files": ["fixture"]})
    manifest = tmp_path / "runtime.json"
    manifest.write_text(json.dumps({"files": ["fixture"]}))
    claude = tmp_path / "claude-fixture"
    claude.write_text("not executed\n")
    files = {name: file_entry(ROOT / rel) for name, rel in J.CODE_FILES.items()}
    files.update(
        models=file_entry(reg.bindings[0].pricing.evidence_path),
        proof=file_entry(reg.evidence_path),
        claude=file_entry(claude),
        runtime_manifest=file_entry(manifest),
        cli_wrapper=file_entry(wrapper),
    )
    config = {
        "schema_version": 2,
        "selection": {
            "kind": J.REACCEPT_KIND,
            "run_id": "rr-1",
            "minimum_start_headroom_microdollars": 6_000_000,
        },
        "ledger_path": str(canonical),
        "serial": True,
        "budget_module_sha256": D.interface_manifest()["module_sha256"],
        "files": files,
        "sources": {"plugin": {"path": str(ROOT), "head": NEW}},
        "registry_sha256": reg.digest,
        "cli_bin": str(Path(sys.executable).parent),
        "runtime_read_paths": [str(Path(sys.base_prefix).resolve())],
        "evidence_root": str(tmp_path / "paid"),
    }

    def write(value):
        path = tmp_path / "config.json"
        path.write_text(json.dumps(value))
        return path, hashlib.sha256(path.read_bytes()).hexdigest()

    return SimpleNamespace(config=config, write=write, ledger=ledger)


def test_checked_config_admits_routing_packet_without_floor(packet, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("routing re-acceptance consulted Floor inputs")

    monkeypatch.setattr(J, "load_floor", forbidden)
    monkeypatch.setattr(J, "check_floor_policy", forbidden)
    config, result, sandbox = J.checked_config(*packet.write(packet.config))
    assert J.is_reacceptance(config) and sandbox is not None
    assert result.digest == packet.config["registry_sha256"]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda c: c["sources"].update(floor={"path": "/", "head": "c" * 40}),
        lambda c: c["files"].update(floor_policy=c["files"]["models"]),
        lambda c: c["files"].update(prior_ledger=c["files"]["models"]),
        lambda c: c["files"].update(recovery_plan=c["files"]["models"]),
        lambda c: c.pop("selection"),
        lambda c: c.update(schema_version=1),
        lambda c: c["selection"].update(kind="routing-and-floor"),
        lambda c: c["selection"].update(run_id="a/b"),
        lambda c: c["selection"].update(run_id=""),
        lambda c: c["selection"].update(minimum_start_headroom_microdollars=True),
        lambda c: c["selection"].update(minimum_start_headroom_microdollars=0),
        lambda c: c["selection"].update(extra=1),
    ],
)
def test_checked_config_refuses_unreviewed_selection_shapes(
    packet, monkeypatch, mutate
):
    def forbidden(*args, **kwargs):
        raise AssertionError("refusal must precede Floor and ledger access")

    for name in ("load_floor", "check_floor_policy", "check_reacceptance_ledger"):
        monkeypatch.setattr(J, name, forbidden)
    config = json.loads(json.dumps(packet.config))
    mutate(config)
    with pytest.raises(D.BudgetStop):
        J.checked_config(*packet.write(config))


def test_recovery_mode_refuses_routing_packet(packet):
    with pytest.raises(D.BudgetStop, match="no recovery"):
        J.checked_config(*packet.write(packet.config), recovery=True)


def test_dry_admission_reports_cap_state_without_provider(packet, monkeypatch, capsys):
    path, digest = packet.write(packet.config)

    def forbidden(*args, **kwargs):
        raise AssertionError("dry admission crossed the paid boundary")

    monkeypatch.setattr(J, "Provider", forbidden)
    monkeypatch.setattr(J, "open_ledger", forbidden)
    monkeypatch.setattr(
        sys,
        "argv",
        ["joint", "--config", str(path), "--config-sha256", digest, "dry-admission"],
    )
    before = sha(packet.ledger.path)
    assert J.main() == 0
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "DRY_ADMITTED" and out["api_calls"] == 0
    assert out["selection"] == J.REACCEPT_KIND and out["run_id"] == "rr-1"
    assert out["planned_trials"] == 50 and out["source_commit"] == NEW
    assert out["exposure_microdollars"] == 0 and out["headroom_microdollars"] == D.CAP
    assert out["per_call_reservation_microdollars"] == 3020480
    assert sha(packet.ledger.path) == before
    for mode in ("probe", "recover-and-transition"):
        monkeypatch.setattr(
            sys,
            "argv",
            ["joint", "--config", str(path), "--config-sha256", digest, mode],
        )
        assert J.main() == 2
        assert json.loads(capsys.readouterr().out)["status"] == "STOPPED_INCOMPLETE"
    lock = J.CANONICAL.with_suffix(".joint-lock")
    with lock.open("a") as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "joint",
                "--config",
                str(path),
                "--config-sha256",
                digest,
                "dry-admission",
            ],
        )
        monkeypatch.setattr(J, "check_reacceptance_ledger", forbidden)
        assert J.main() == 2
    assert json.loads(capsys.readouterr().out)["status"] == "STOPPED_INCOMPLETE"
