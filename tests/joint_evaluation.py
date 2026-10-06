"""The sole admitted joint launch entry point; default invocation is zero-cost.

Use the isolated scripts/joint_evaluation.py command in the reviewed packet.
Only probe/run read the environment credential. No arbitrary import/plugin argv.
"""

import argparse
import contextlib
import fcntl
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import threading
from dataclasses import replace
from pathlib import Path

from tests import evaluation_budget as D
from tests.evaluation_api import (
    Broker,
    Provider,
    RateLimitStop,
    Session,
    oauth_presence,
    request_bound,
    seal_json,
    usd,
)
from tests.evaluation_sandbox import Sandbox, SandboxStop

CODE_FILES = {
    "budget": "tests/evaluation_budget.py",
    "controller": "tests/joint_evaluation.py",
    "api": "tests/evaluation_api.py",
    "sandbox": "tests/evaluation_sandbox.py",
    "entry": "scripts/joint_evaluation.py",
}

CANONICAL = (
    Path(__file__).resolve().parents[3]
    / "out/confluence-evaluation/aggregate-budget-v2.sqlite3"
)
MODEL_ROUTES = {
    "plugin-sonnet5-api": ("claude-sonnet-5", 1_000_000),
    "floor-sonnet55-api": ("claude-sonnet-5-5", 1_000_000),
    "floor-haiku45-api": ("claude-haiku-4-5-20251001", 200_000),
    "floor-opus55-api": ("claude-opus-5-5", 1_000_000),
}

CONTEXT_SOURCES = {
    "claude-sonnet-5": "https://platform.claude.com/docs/en/docs/about-claude/models/whats-new-sonnet-5",
    "claude-sonnet-5-5": "https://platform.claude.com/docs/en/models/overview",
    "claude-opus-5-5": "https://platform.claude.com/docs/en/models/overview",
    "claude-haiku-4-5-20251001": "https://platform.claude.com/docs/en/models/overview",
}

# A schema-2 configuration selects ONLY the ten routing prompts x five trials
# on its own plugin head, in the existing canonical ledger. Its trials get a
# separate phase and a run-id-scoped task, so they never collide with (or
# replay) the joint run's settled routing rows and the joint completion check
# never counts them. No sufficiency, Floor, probe, recovery or retry.
REACCEPT_KIND = "routing-reacceptance-v1"
REACCEPT_PHASE = "routing-reaccept"
REACCEPT_BINDING = "plugin-sonnet5-api"
ROUTED_PHASES = ("routing", REACCEPT_PHASE)  # both bounded to one model turn


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def runtime_manifest():
    """Entire Python runtime source/native-library surface, never home/config files."""
    files = {Path(sys.executable).resolve(), Path(sys.prefix) / "pyvenv.cfg"}
    for root in {Path(sys.prefix).resolve(), Path(sys.base_prefix).resolve()}:
        for path in root.rglob("*"):
            if (
                path.suffix in (".py", ".pyc", ".so", ".dylib", ".pth")
                and "__pycache__" not in path.parts
            ):
                if path.is_symlink():
                    raise D.BudgetStop("runtime source symlink refused")
                if path.is_file():
                    files.add(path)
    return {"files": [{"path": str(p), "sha256": file_hash(p)} for p in sorted(files)]}


def registry(model_path, proof_path):
    model_path, proof_path = Path(model_path).resolve(), Path(proof_path).resolve()
    data = json.loads(model_path.read_text())
    bindings = []
    if len(data["routes"]) != 4:
        raise D.BudgetStop("four frozen model routes required")
    for route in data["routes"]:
        identity = route["binding_id"]
        model, context = MODEL_ROUTES[identity]
        if (
            route["model_id"],
            route["provider"],
            route["authentication"],
            route["billing"],
        ) != (
            model,
            "anthropic",
            "owner-environment-DEMO_CLAUDE_CODE_OAUTH_TOKEN",
            "api-equivalent-usage-usd-v1",
        ):
            raise D.BudgetStop("unapproved authentication/model route")
        if (route.get("max_context_tokens"), route.get("context_source")) != (
            context,
            CONTEXT_SOURCES[model],
        ):
            raise D.BudgetStop("missing frozen provider hard context maximum")
        pricing = D.ApiPricing(
            model,
            tuple(sorted(route["rates_usd_per_million_tokens"].items())),
            context,
            data["price_source"],
            data["verified_at"],
            str(model_path),
            file_hash(model_path),
        )
        binding = D.Binding(
            identity,
            model,
            "anthropic",
            "api-equivalent-usage-usd",
            "1" if identity.startswith("plugin") else "0.000001",
            "0",
            str(proof_path),
            file_hash(proof_path),
            D.LaunchContract(
                "claude-print-v1",
                "claude-code-subscription-oauth",
                "api-equivalent-usage-usd-v1",
            ),
            pricing,
        )
        binding = replace(binding, inflight_usd=usd(request_bound(binding)))
        bindings.append(binding)
    result = D.Registry(
        "confluence-joint-oauth-equivalent-20261005-v1",
        tuple(bindings),
        str(proof_path),
        file_hash(proof_path),
    )
    result.validate()
    return result


def check_source(entry):
    root = Path(entry["path"])
    env = {
        "PATH": os.defpath,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
    }
    head = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], env=env, text=True
    ).strip()
    dirty = subprocess.check_output(
        ["git", "-C", str(root), "diff", "--name-only", "HEAD"], env=env, text=True
    )
    if head != entry["head"] or dirty.strip():
        raise D.BudgetStop("source checkout changed")
    extras = subprocess.check_output(
        [
            "git",
            "-C",
            str(root),
            "ls-files",
            "--others",
            "--exclude-standard",
            "-z",
        ],
        env=env,
    ) + subprocess.check_output(
        [
            "git",
            "-C",
            str(root),
            "ls-files",
            "--others",
            "--ignored",
            "--exclude-standard",
            "-z",
        ],
        env=env,
    )
    if any(
        Path(p.decode()).suffix
        in (".py", ".pyc", ".pth", ".so", ".dylib", ".pyd", ".pyw")
        and not (
            Path(p.decode()).suffix == ".pyc"
            and "__pycache__" in Path(p.decode()).parts
        )
        for p in extras.split(b"\0")
        if p
    ):
        raise D.BudgetStop("untracked importable source refused")


def checked_config(path, expected, *, recovery=False):
    if not recovery:
        oauth_presence()
    if not (
        sys.flags.isolated
        and sys.flags.dont_write_bytecode
        and sys.pycache_prefix == "/dev/null"
    ):
        raise D.BudgetStop("isolated Python with bytecode cache disabled required")
    D._proof(str(path), expected)
    config = json.loads(Path(path).read_text())
    reaccept = is_reacceptance(config)
    required = {
        "schema_version",
        "ledger_path",
        "serial",
        "budget_module_sha256",
        "files",
        "sources",
        "registry_sha256",
        "cli_bin",
        "runtime_read_paths",
        "evidence_root",
    } | ({"selection"} if reaccept else set())
    if set(config) != required or config["schema_version"] != (2 if reaccept else 1):
        raise D.BudgetStop("incomplete controller configuration")
    if set(config["sources"]) != ({"plugin"} if reaccept else {"plugin", "floor"}):
        raise D.BudgetStop("reviewed source checkouts required")
    proofs = set(CODE_FILES) | {
        "models",
        "proof",
        "claude",
        "runtime_manifest",
        "cli_wrapper",
    }
    if reaccept:
        if recovery or set(config["files"]) != proofs:
            raise D.BudgetStop(
                "routing re-acceptance takes no recovery, Floor or prior-ledger input"
            )
        check_selection(config["selection"])
    elif not (proofs | {"prior_ledger", "floor_policy"}) <= set(config["files"]):
        raise D.BudgetStop("mandatory controller proofs missing")
    root = Path(__file__).resolve().parents[1]
    if Path(config["sources"]["plugin"]["path"]).resolve() != root:
        raise D.BudgetStop("controller source root mismatch")
    for name, relative in CODE_FILES.items():
        if Path(config["files"][name]["path"]).resolve() != root / relative:
            raise D.BudgetStop("controller module path mismatch")
    if (
        config["runtime_read_paths"] != [str(Path(sys.base_prefix).resolve())]
        or Path(config["cli_bin"]) != Path(sys.executable).parent
    ):
        raise D.BudgetStop("runtime read grants must match isolated interpreter")
    if (
        Path(config["files"]["cli_wrapper"]["path"])
        != Path(config["cli_bin"]) / "confluence-as"
    ):
        raise D.BudgetStop("executed CLI wrapper must be pinned")
    if CANONICAL.resolve() != CANONICAL:
        raise D.BudgetStop("canonical ledger cannot be redirected")
    if config["ledger_path"] != str(CANONICAL) or config["serial"] is not True:
        raise D.BudgetStop("canonical serial ledger required")
    if config["budget_module_sha256"] != D.interface_manifest()["module_sha256"]:
        raise D.BudgetStop("budget module drift")
    for entry in config["files"].values():
        D._proof(entry["path"], entry["sha256"])
    for entry in config["sources"].values():
        check_source(entry)
    result = registry(
        config["files"]["models"]["path"], config["files"]["proof"]["path"]
    )
    if result.digest != config["registry_sha256"]:
        raise D.BudgetStop("transport registry drift")
    manifest = json.loads(Path(config["files"]["runtime_manifest"]["path"]).read_text())
    if manifest != runtime_manifest():
        raise D.BudgetStop("runtime import surface changed")
    if not reaccept:
        check_floor_policy(config, result)
    if recovery:
        entry = config["files"]["recovery_plan"]
        plan = D._reviewed_recovery_plan(
            entry["path"], entry["sha256"], CANONICAL, result
        )
        if plan["provenance"]["source_heads"] != {
            name: source["head"] for name, source in config["sources"].items()
        }:
            raise D.BudgetStop("recovery configuration/source mismatch")
        return config, result, None  # Recovery never creates a child or provider.
    elif reaccept:
        # Lock probes precede any SQLite open. They detect a joint controller
        # (joint lock, held for its whole run) or a call in flight (ledger
        # controller lock). A writer idle between calls holds neither; the
        # operator's no-other-writer precondition is the guard for that.
        check_quiescent(Path(config["ledger_path"]))
        check_reacceptance_ledger(config, result)
    else:
        check_ledger_eligibility(config, result)
    sandbox = Sandbox(
        Path(config["files"]["claude"]["path"]),
        Path(config["cli_bin"]),
        [Path(p) for p in config["runtime_read_paths"]],
        [
            Path(config["sources"]["plugin"]["path"]) / "skills",
            Path(config["sources"]["plugin"]["path"]) / "tests/fixtures/jira-stub",
            Path(config["sources"]["plugin"]["path"]) / ".claude-plugin",
            Path(config["sources"]["plugin"]["path"]) / "tests/e2e/empty-mcp.json",
        ],
    )
    sandbox.check()
    return config, result, sandbox


def load_floor(config):
    path = Path(config["sources"]["floor"]["path"]) / "tests/floor_eval/run_eval.py"
    spec = importlib.util.spec_from_file_location("joint_floor", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_floor_policy(config, reg):
    floor = load_floor(config)
    root = Path(config["sources"]["floor"]["path"]) / "tests/floor_eval"
    policy_entry = config["files"]["floor_policy"]
    args = argparse.Namespace(
        policy=Path(policy_entry["path"]),
        policy_sha256=policy_entry["sha256"],
        inventory=root / "inventory.json",
        commands=root / "commands.json",
        fake_models=None,
        repo=None,
        facts=None,
        limit=None,
    )
    inventory = floor.load_json(args.inventory)
    facts = floor.selected_facts(inventory, args)
    policy, _ = floor.reviewed_policy(
        args, inventory, facts, floor.load_json(args.commands)
    )
    if (
        policy["ledger_path"],
        policy["registry_sha256"],
        policy["module_path"],
        policy["source_commit"],
        policy["kind"],
    ) != (
        str(CANONICAL),
        reg.digest,
        str(Path(D.__file__).resolve()),
        config["sources"]["floor"]["head"],
        "new",
    ):
        raise D.BudgetStop("Floor policy does not bind canonical controller")
    for role, identity in {
        "sonnet": "floor-sonnet55-api",
        "terra": "floor-haiku45-api",
        "judge": "floor-opus55-api",
    }.items():
        if policy["roles"][role] != {
            "binding_id": identity,
            "model_id": reg.binding(identity).model,
        }:
            raise D.BudgetStop("Floor role mismatch")


def check_ledger_eligibility(config, reg):
    path = Path(config["ledger_path"])
    if path.exists():
        snapshot = D.Ledger(path).snapshot()
        if (
            snapshot["metadata"]["registry_sha256"] != reg.digest
            or snapshot["metadata"]["halted"]
        ):
            raise D.BudgetStop("canonical ledger halted or registry differs")
        for row in snapshot["calls"]:
            if row["status"] in {"settled", "charged-uncertain"}:
                continue
            if (
                row["status"] != "reserved"
                or row["partial_receipt"] is None
                or row["outcome"] is None
            ):
                raise D.BudgetStop("unresolved prior charge/reservation")
            outcome = json.loads(Path(row["outcome"]["path"]).read_text())
            if outcome["timed_out"] or outcome["early_stop"]:
                raise D.BudgetStop("incomplete prior outcome")
        return
    if path.with_suffix(".init.json").exists():
        raise D.BudgetStop("prior initialization with missing ledger; no reset")
    prior = config["files"]["prior_ledger"]
    D._proof(prior["path"], prior["sha256"])
    old = json.loads(Path(prior["path"]).read_text())
    if (
        old["calls"]
        or D.microdollars(old["accounted_actual_usd"])
        or D.microdollars(old["unresolved_reservations_usd"])
    ):
        raise D.BudgetStop("prior spend requires reconciliation")


def is_reacceptance(config):
    return isinstance(config, dict) and config.get("schema_version") == 2


def check_selection(selection):
    if (
        not isinstance(selection, dict)
        or set(selection) != {"kind", "run_id", "minimum_start_headroom_microdollars"}
        or selection["kind"] != REACCEPT_KIND
        or type(selection["minimum_start_headroom_microdollars"]) is not int
        or not 0 < selection["minimum_start_headroom_microdollars"] <= D.CAP
    ):
        raise D.BudgetStop("unreviewed routing re-acceptance selection")
    D._token(selection["run_id"])
    if "/" in selection["run_id"]:
        raise D.BudgetStop("run id must not contain the task separator")


def check_quiescent(path):
    """Refuse while any joint controller or budget controller holds its lock."""
    for lock_path in (
        path.with_suffix(".joint-lock"),
        path.with_suffix(path.suffix + ".controller"),
    ):
        with lock_path.open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise D.BudgetStop("another ledger writer is active") from None
            fcntl.flock(lock, fcntl.LOCK_UN)


def check_run_id_unspent(rows, run_id, source_commit, *, reconciled):
    """One run id is one 50-trial measurement on one head, with no retry.

    A charged, uncertain or unreconciled trial of this run id, or one recorded
    on another head, binding or attempt, means the run id can never complete:
    refuse it before any reservation. Before reconciliation (dry admission) a
    reserved row is admitted only because check_ledger_eligibility has already
    proved it a complete partial receipt, which `run` settles before launching.
    """
    allowed = {"settled"} if reconciled else {"settled", "reserved"}
    for row in rows:
        call = row["call"]
        if call["phase"] != REACCEPT_PHASE or not call["task"].startswith(run_id + "/"):
            continue
        if (
            row["status"] not in allowed
            or row["binding_id"] != REACCEPT_BINDING
            or call["attempt"] != 1
            or call["source_commit"] != source_commit
        ):
            raise D.BudgetStop(
                "routing re-acceptance run id is spent; a new reviewed run id is required"
            )


def check_reacceptance_ledger(config, reg, *, reconcile=False):
    """Existing canonical ledger only; never initializes, resets or migrates.

    The reviewed minimum covers one full plugin reservation, so a charged
    uncertain stop always fits inside the shared aggregate cap.
    """
    path = Path(config["ledger_path"])
    if not path.is_file():
        raise D.BudgetStop("routing re-acceptance requires the existing ledger")
    check_ledger_eligibility(config, reg)
    ledger = D.Ledger(path)
    snapshot = reconcile_existing(ledger) if reconcile else ledger.snapshot()
    check_run_id_unspent(
        snapshot["calls"],
        config["selection"]["run_id"],
        config["sources"]["plugin"]["head"],
        reconciled=reconcile,
    )
    minimum = config["selection"]["minimum_start_headroom_microdollars"]
    if (
        snapshot["metadata"]["registry_sha256"] != reg.digest
        or minimum < reg.binding(REACCEPT_BINDING).validate()
        or snapshot["headroom"] < minimum
    ):
        raise D.BudgetStop("aggregate headroom below reviewed re-acceptance minimum")
    return ledger, snapshot


def reacceptance_summary(config, reg, snapshot):
    selection = config["selection"]
    return {
        "selection": selection["kind"],
        "run_id": selection["run_id"],
        "source_commit": config["sources"]["plugin"]["head"],
        "planned_trials": 50,
        "per_call_reservation_microdollars": reg.binding(REACCEPT_BINDING).validate(),
        "minimum_start_headroom_microdollars": selection[
            "minimum_start_headroom_microdollars"
        ],
        "exposure_microdollars": snapshot["exposure"],
        "headroom_microdollars": snapshot["headroom"],
    }


def routing_golden():
    """The ten reviewed routing prompts of this checkout, in YAML order."""
    import yaml

    plugin = Path(__file__).resolve().parents[1]
    golden = yaml.safe_load(
        (plugin / "skills/confluence/tests/routing_golden.yaml").read_text()
    )["tests"]
    if len(golden) != 10 or len({item["id"] for item in golden}) != 10:
        raise D.BudgetStop("routing inventory differs")
    return golden


def reacceptance_call(call, prompt, binding, run_id, source_commit):
    """Fresh ledger identity for one first-attempt routing trial of this run.

    Refused before any reservation unless it is one of the 50 reviewed
    (golden prompt, trial 1-5) pairs on this run's source.
    """
    call.validate()
    inputs = {item["id"]: item["input"] for item in routing_golden()}
    if (
        binding.binding_id != REACCEPT_BINDING
        or call.phase != "routing"
        or call.attempt != 1
        or call.source_commit != source_commit
        or not 1 <= call.trial <= 5
        or inputs.get(call.task) != prompt
    ):
        raise D.BudgetStop("routing re-acceptance admits only its own routing trials")
    return D.Call(
        D._digest([REACCEPT_KIND, run_id, call.task, call.trial])[:32],
        REACCEPT_PHASE,
        f"{run_id}/{call.task}",
        call.trial,
        call.source_commit,
        1,
    )


def reconcile_existing(ledger):
    """Never invent a settlement from a partial request list after a crash."""
    snapshot = ledger.snapshot()
    for row in snapshot["calls"]:
        if row["status"] == "charged-uncertain":
            continue  # Permanent conservative consumption; never reconcile/refund.
        if row["status"] == "settled":
            ledger.reconcile(D.Settlement(**row["receipt"]))  # idempotent read-back
        elif (
            row["status"] == "reserved"
            and row["partial_receipt"] is not None
            and row["outcome"] is not None
        ):
            outcome = json.loads(Path(row["outcome"]["path"]).read_text())
            if not outcome["timed_out"] and not outcome["early_stop"]:
                ledger.reconcile(D.Settlement(**row["partial_receipt"]))
    snapshot = ledger.snapshot()
    if snapshot["metadata"]["halted"] or any(
        r["status"] not in {"settled", "charged-uncertain"} for r in snapshot["calls"]
    ):
        raise D.BudgetStop(
            "unresolved prior charge/reservation; reconciliation required"
        )
    return snapshot


def open_ledger(config, reg):
    """Called only under the canonical process lock and after paid preflight."""
    check_ledger_eligibility(config, reg)
    path = Path(config["ledger_path"])
    if path.exists():
        ledger = D.Ledger(path)
        snapshot = reconcile_existing(ledger)
        if snapshot["metadata"]["registry_sha256"] != reg.digest:
            raise D.BudgetStop("canonical ledger registry mismatch; no reset")
        return ledger
    prior = config["files"]["prior_ledger"]
    D._proof(prior["path"], prior["sha256"])
    old = json.loads(Path(prior["path"]).read_text())
    if (
        old["calls"]
        or D.microdollars(old["accounted_actual_usd"])
        or D.microdollars(old["unresolved_reservations_usd"])
    ):
        raise D.BudgetStop("prior spend requires explicit reconciliation; no zero init")
    # Preserve init intent forever. Missing database after any attempted init is
    # a recovery condition, not authority to restart at zero.
    seal_json(
        path.with_suffix(".init.json"),
        {"registry_sha256": reg.digest, "prior_sha256": prior["sha256"]},
    )
    return D.Ledger.create(path, reg)


class ProductionTransport:
    offline_only = False

    def __init__(self, config, reg, sandbox, provider):
        self.config, self.registry, self.sandbox, self.provider = (
            config,
            reg,
            sandbox,
            provider,
        )
        self.local = threading.local()
        self.enabled = True
        self.rate_limited = False

    def validate(self, binding):
        if self.rate_limited:
            raise RateLimitStop("subscription rate limit; no further launches")
        if (
            not self.enabled
            or binding.provider != "anthropic"
            or self.registry.binding(binding.binding_id).digest != binding.digest
        ):
            raise D.BudgetStop("unadmitted production route")
        for entry in self.config["files"].values():
            D._proof(entry["path"], entry["sha256"])
        if request_bound(binding) != D.microdollars(binding.inflight_usd):
            raise D.BudgetStop("request exposure mismatch")
        self.local.binding = binding

    def preflight(self):
        self.sandbox.check()
        for executable in (self.sandbox.claude, self.sandbox.cli_bin / "confluence-as"):
            code, text, _ = self.sandbox.run([str(executable), "--version"], timeout=10)
            if code or (
                executable.name == "confluence-as" and "version 2." not in text
            ):
                raise D.BudgetStop("pinned toolchain preflight failed")

    def execute(self, cmd, prompt, *, call, evidence_destination, timeout, **kwargs):
        binding = self.local.binding
        session = Session(
            binding,
            call,
            self.provider,
            evidence_destination,
            single=call.phase.startswith("floor-") or call.phase == "probe",
        )
        single = call.phase.startswith("floor-") or call.phase == "probe"
        # Native Claude Code supplies an independent result usage/cost report
        # even for Floor/probe. The parent SDK only forwards its Messages.
        argv = (
            [
                str(self.sandbox.claude),
                "--print",
                "--verbose",
                "--output-format",
                "stream-json",
                "--model",
                binding.model,
                "--tools",
                "",
                "--permission-mode",
                "dontAsk",
                "--max-turns",
                "1",
                "--strict-mcp-config",
                "--mcp-config",
                str(Path(__file__).parent / "e2e/empty-mcp.json"),
            ]
            if single
            else [str(self.sandbox.claude), *cmd[1:]]
        )
        if call.phase in ROUTED_PHASES:
            argv.extend(["--max-turns", "1"])
        argv.extend(["--settings", '{"disableAllHooks":true}', "--setting-sources", ""])
        detected = [None]
        reports = []

        def observe(line):
            with (session.directory / "child.transcript.jsonl").open("a") as evidence:
                evidence.write(line + "\n")
                evidence.flush()
                os.fsync(evidence.fileno())
            if kwargs.get("on_line"):
                kwargs["on_line"](line)
            if kwargs.get("detect_line") and detected[0] is None:
                detected[0] = kwargs["detect_line"](line)
            try:
                event = json.loads(line)
                if isinstance(event, dict) and event.get("type") == "result":
                    reports.append(event)
            except ValueError:
                pass
            # Routing retains the first Skill observation but drains this one
            # bounded turn so native usage/cost can be checked before settlement.
            return False

        try:
            with Broker(session) as port:
                rc, stdout, stderr = self.sandbox.run(
                    argv,
                    prompt=prompt,
                    timeout=timeout,
                    port=port,
                    on_line=observe,
                    broker_token=session.token,
                    stop_requested=lambda: session.failed,
                )
        except SandboxStop as error:
            seal_json(
                session.directory / "child-stop.json",
                {
                    "reason": error.reason,
                    "returncode": None,
                    "stdout_partial": error.stdout,
                    "stderr": error.stderr,
                    "reservation": "retained in full",
                },
            )
            raise
        else:
            seal_json(
                session.directory / "child-stop.json",
                {
                    "reason": "session-failed" if session.failed else "completed",
                    "returncode": rc,
                    "stderr": stderr,
                    "reservation": "retained in full"
                    if session.failed
                    else "requires complete usage settlement",
                },
            )
        if session.rate_limited:
            self.rate_limited = True
            raise RateLimitStop("subscription rate limit; partial evidence retained")
        if session.failed:
            raise D.BudgetStop(
                "terminal broker failure; see safe session-stop evidence; no retries"
            )
        if len(reports) != 1:
            raise D.BudgetStop("missing or duplicate native Claude usage report")
        report = reports[0]
        seal_json(session.directory / "claude-result.json", report)
        lines = [report.get("result", "")] if single else stdout.splitlines()
        if not all(isinstance(line, str) for line in lines):
            raise D.BudgetStop("malformed Claude result")
        outcome = D.Outcome(lines=lines, stderr=stderr, returncode=rc)
        outcome.result = detected[0]
        outcome.receipt = session.settlement(
            {"lines": outcome.lines, "stderr": outcome.stderr},
            exit_code=outcome.returncode,
            claude_report=report,
        )
        return outcome

    def replay(self, command, **kwargs):
        return self.sandbox.run(
            ["/bin/bash", "--noprofile", "--norc", "-o", "pipefail", "-c", command],
            timeout=30,
        )


class JointLauncher(D.BudgetLauncher):
    def __init__(self, ledger, binding, transport, reacceptance=None):
        super().__init__(ledger, binding, transport)
        self.reacceptance = reacceptance  # (run_id, source head) or None

    def run(self, cmd, prompt, *, call, evidence_destination=None, **kwargs):
        if self.reacceptance is None:
            call = self.ledger.retry_call(call, self.binding)
        else:  # No commissioned retry exists in a re-acceptance packet.
            call = reacceptance_call(call, prompt, self.binding, *self.reacceptance)
        destination = (
            Path(self.transport.config["evidence_root"]) / "calls" / call.call_id
        )
        return super().run(
            cmd, prompt, call=call, evidence_destination=destination, **kwargs
        )


@contextlib.contextmanager
def admission(config, reg, sandbox, provider, ledger):
    if D._ADMITTED_LAUNCHER is not None:
        raise D.BudgetStop("nested controller refused")
    transport = ProductionTransport(config, reg, sandbox, provider)
    D._ADMITTED_LAUNCHER = JointLauncher(
        ledger,
        reg.binding("plugin-sonnet5-api"),
        transport,
        (config["selection"]["run_id"], config["sources"]["plugin"]["head"])
        if is_reacceptance(config)
        else None,
    )
    try:
        yield transport
    finally:
        D._ADMITTED_LAUNCHER = None
        transport.enabled = False


def run_joint(config, transport):
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    os.environ.pop("PYTEST_PLUGINS", None)
    os.environ["PYTEST_ADDOPTS"] = ""
    import pytest

    os.environ["E2E_SUFFICIENCY"] = "1"
    os.environ["EVALUATION_SOURCE_COMMIT"] = config["sources"]["plugin"]["head"]
    os.environ["HARNESS_CLI_BIN"] = config["cli_bin"]
    os.environ["TMPDIR"] = config["evidence_root"]
    os.environ["PYTEST_ADDOPTS"] = ""
    os.chdir(config["sources"]["plugin"]["path"])
    status = pytest.main(
        [
            "-q",
            "-p",
            "no:cacheprovider",
            "--confcutdir",
            config["sources"]["plugin"]["path"],
            "--rootdir",
            config["sources"]["plugin"]["path"],
            "-c",
            str(Path(config["sources"]["plugin"]["path"]) / "pytest.ini"),
            "tests/e2e/test_plugin_e2e.py",
            "skills/confluence/tests/test_routing.py",
            "--sufficiency-model",
            "claude-sonnet-5",
        ]
    )
    if transport.rate_limited:
        raise RateLimitStop("subscription rate limit; joint run stopped")
    snapshot = reconcile_existing(D.Ledger(Path(config["ledger_path"])))
    plugin_calls = [
        r for r in snapshot["calls"] if r["call"]["phase"] in ("sufficiency", "routing")
    ]
    if status not in (0, 1):
        raise D.BudgetStop("plugin incomplete; see persisted trial evidence")
    check_plugin_completion(plugin_calls)
    floor_path = (
        Path(config["sources"]["floor"]["path"]) / "tests/floor_eval/run_eval.py"
    )
    spec = importlib.util.spec_from_file_location("joint_floor", floor_path)
    floor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(floor)
    policy = config["files"]["floor_policy"]
    sys.argv = [
        str(floor_path),
        "--workers",
        "1",
        "--policy",
        policy["path"],
        "--policy-sha256",
        policy["sha256"],
        "--output",
        str(Path(config["evidence_root"]) / "floor-full-153"),
    ]
    if (Path(config["evidence_root"]) / "floor-full-153/manifest.json").exists():
        sys.argv.append("--resume")
    finish_floor(floor, transport)
    if status:
        raise D.BudgetStop("joint trials complete; plugin scoring threshold failed")


def check_plugin_completion(rows):
    """Exactly85 settled logical observations; only one charged predecessor allowed."""
    import yaml

    plugin = Path(__file__).resolve().parents[1]
    sufficiency = yaml.safe_load((plugin / "tests/e2e/test_cases.yaml").read_text())[
        "tasks"
    ]
    routing = yaml.safe_load(
        (plugin / "skills/confluence/tests/routing_golden.yaml").read_text()
    )["tests"]
    expected = {
        (phase, item["id"], trial)
        for phase, items in (("sufficiency", sufficiency), ("routing", routing))
        for item in items
        for trial in range(1, 6)
    }
    if len(expected) != 85:
        raise D.BudgetStop("plugin inventory differs")
    observations = {}
    predecessor = None
    for row in rows:
        call = row["call"]
        logical = (call["phase"], call["task"], call["trial"])
        if logical not in expected or row["binding_id"] != "plugin-sonnet5-api":
            raise D.BudgetStop("unexpected plugin observation")
        if row["status"] == "charged-uncertain":
            if (
                logical != ("sufficiency", "read-page", 1)
                or call["attempt"] != 1
                or predecessor is not None
            ):
                raise D.BudgetStop("unreviewed charged plugin predecessor")
            predecessor = logical
            continue
        if (
            row["status"] != "settled"
            or logical in observations
            or not row["receipt"]
            or not row["outcome"]
        ):
            raise D.BudgetStop(
                "plugin incomplete or duplicate; see persisted trial evidence"
            )
        observations[logical] = call["attempt"]
    if set(observations) != expected or any(
        attempt != (2 if logical == predecessor else 1)
        for logical, attempt in observations.items()
    ):
        raise D.BudgetStop("plugin logical trial coverage differs")


def run_reacceptance(config, transport):
    """Ten routing prompts x five trials on this head; never sufficiency/Floor."""
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    os.environ.pop("PYTEST_PLUGINS", None)
    os.environ["PYTEST_ADDOPTS"] = ""
    import pytest

    plugin = config["sources"]["plugin"]
    Path(config["evidence_root"]).mkdir(mode=0o700, parents=True, exist_ok=True)
    os.environ["EVALUATION_SOURCE_COMMIT"] = plugin["head"]
    os.environ["HARNESS_CLI_BIN"] = config["cli_bin"]
    os.environ["TMPDIR"] = config["evidence_root"]
    os.chdir(plugin["path"])
    status = pytest.main(
        [
            "-q",
            "-p",
            "no:cacheprovider",
            "--confcutdir",
            plugin["path"],
            "--rootdir",
            plugin["path"],
            "-c",
            str(Path(plugin["path"]) / "pytest.ini"),
            "skills/confluence/tests/test_routing.py",
        ]
    )
    if transport.rate_limited:
        raise RateLimitStop("subscription rate limit; re-acceptance stopped")
    snapshot = reconcile_existing(D.Ledger(Path(config["ledger_path"])))
    if status not in (0, 1):
        raise D.BudgetStop("routing re-acceptance incomplete; see trial evidence")
    tally, settled = check_reacceptance_completion(
        snapshot["calls"], config["selection"]["run_id"], plugin["head"]
    )
    passed = all(item["correct"] >= 4 for item in tally.values())
    if passed != (status == 0):
        raise D.BudgetStop("ledger outcomes and pytest verdict disagree")
    return passed, tally, settled


def check_reacceptance_completion(rows, run_id, source_commit):
    """Exactly 50 settled first attempts of this run; tally from sealed outcomes."""
    golden = routing_golden()
    expected = {(item["id"], trial) for item in golden for trial in range(1, 6)}
    tally = {
        item["id"]: {"expected": item.get("expected_skill"), "correct": 0}
        for item in golden
    }
    seen, settled = set(), 0
    for row in rows:
        call = row["call"]
        if call["phase"] != REACCEPT_PHASE or not call["task"].startswith(run_id + "/"):
            continue
        logical = (call["task"][len(run_id) + 1 :], call["trial"])
        if (
            logical not in expected
            or logical in seen
            or row["binding_id"] != REACCEPT_BINDING
            or call["attempt"] != 1
            or call["source_commit"] != source_commit
            or row["status"] != "settled"
            or not row["receipt"]
            or not row["outcome"]
        ):
            raise D.BudgetStop("routing re-acceptance incomplete or duplicate")
        seen.add(logical)
        # The ledger read already verified this outcome file's sealed hash.
        result = json.loads(Path(row["outcome"]["path"]).read_text())["result"]
        skill = result if isinstance(result, str) else None
        tally[logical[0]]["correct"] += skill == tally[logical[0]]["expected"]
        settled += row["actual"]
    if seen != expected:
        raise D.BudgetStop("routing re-acceptance coverage differs")
    return tally, settled


def finish_floor(floor, transport):
    status = floor.main(transport=transport)
    # Floor catches RuntimeError to preserve its partial manifest. Preserve the
    # specific terminal financial reason after that boundary, including judges.
    if transport.rate_limited:
        raise RateLimitStop("subscription rate limit; Floor partial evidence retained")
    if status:
        raise D.BudgetStop("Floor incomplete; see persisted evidence")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--config-sha256", required=True)
    parser.add_argument(
        "mode", choices=("dry-admission", "probe", "run", "recover-and-transition")
    )
    args = parser.parse_args()
    try:
        recovering = args.mode == "recover-and-transition"
        config, reg, sandbox = (
            checked_config(args.config, args.config_sha256, recovery=True)
            if recovering
            else checked_config(args.config, args.config_sha256)
        )
        reaccept = is_reacceptance(config)
        if reaccept and args.mode not in ("dry-admission", "run"):
            raise D.BudgetStop("routing re-acceptance admits only dry-admission/run")
        if recovering:
            if not CANONICAL.is_file():
                raise D.BudgetStop("recovery requires existing canonical ledger")
            with CANONICAL.with_suffix(".joint-lock").open("a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                ledger = D.Ledger(CANONICAL)
                with ledger.controller():
                    entry = config["files"]["recovery_plan"]
                    result = ledger.recover_and_transition(
                        Path(entry["path"]), entry["sha256"], reg
                    )
            print(
                json.dumps(
                    {"status": "RECOVERED_AND_TRANSITIONED", "api_calls": 0, **result}
                )
            )
            return 0
        if args.mode == "dry-admission":
            admitted = {
                "status": "DRY_ADMITTED",
                "api_calls": 0,
                "ledger_initialized": False,
                "registry_sha256": reg.digest,
                "accounting_basis": "API-equivalent USD; not subscription billing",
                "credential": "owner OAuth environment variable present; value not inspected",
                "paid_prerequisites": "token validity and exact account/model availability proved only by bounded invocation",
            }
            if reaccept:
                _, snapshot = check_reacceptance_ledger(config, reg)
                admitted.update(reacceptance_summary(config, reg, snapshot))
            print(json.dumps(admitted))
            return 0
        provider = Provider()
        for binding in reg.bindings:
            provider.available(binding)
        CANONICAL.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with CANONICAL.with_suffix(".joint-lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            ledger = (
                check_reacceptance_ledger(config, reg, reconcile=True)[0]
                if reaccept
                else open_ledger(config, reg)
            )
            with admission(config, reg, sandbox, provider, ledger) as transport:
                if args.mode == "probe":
                    binding = reg.binding("floor-haiku45-api")
                    if binding.validate() > 500_000:
                        raise D.BudgetStop("probe reservation exceeds $0.50")
                    launcher = JointLauncher(ledger, binding, transport)
                    call = D.Call(
                        "joint-oauth-availability-probe-v3",
                        "probe",
                        "oauth-equivalent-accounting-v3",
                        1,
                        config["sources"]["plugin"]["head"],
                    )
                    launcher.run(
                        ["claude", "--print", "--model", binding.model],
                        "Reply OK.",
                        call=call,
                        timeout=60,
                    )
                elif reaccept:
                    passed, tally, settled = run_reacceptance(config, transport)
                else:
                    run_joint(config, transport)
            if reaccept:
                print(
                    json.dumps(
                        {
                            "status": "ROUTING_REACCEPTANCE_COMPLETE",
                            "routing_threshold": "PASSED" if passed else "FAILED",
                            "correct_of_5": {k: v["correct"] for k, v in tally.items()},
                            "settled_microdollars": settled,
                            **reacceptance_summary(config, reg, ledger.snapshot()),
                        }
                    )
                )
                return 0 if passed else 1
            print(
                json.dumps(
                    {
                        "status": "COMPLETE",
                        "exposure_microdollars": ledger.snapshot()["exposure"],
                    }
                )
            )
        return 0
    except RateLimitStop:
        print(
            json.dumps(
                {
                    "status": "STOPPED_RATE_LIMIT",
                    "detail": "partial evidence and full reservation retained; no retries",
                }
            )
        )
        return 2
    except (D.BudgetStop, OSError, KeyError, TypeError, ValueError):
        # No exception body/locals: a dependency may retain a credential-bearing request.
        print(
            json.dumps(
                {
                    "status": "STOPPED_INCOMPLETE",
                    "detail": "admission/accounting gate refused; retain all evidence and reservations",
                }
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
