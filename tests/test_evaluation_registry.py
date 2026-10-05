"""One aggregate ceiling across routes; API pricing fixtures, no paid clients."""

import hashlib
import json
import multiprocessing
import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from tests.evaluation_budget import (
    API_USAGE_FIELDS,
    CAP,
    ApiPricing,
    Binding,
    BudgetLauncher,
    BudgetStop,
    LaunchContract,
    Ledger,
    Outcome,
    Registry,
    Settlement,
    api_usage_charge,
    bind_evaluator,
    interface_manifest,
    prepare_launch,
    require_launcher,
)
from tests.test_evaluation_budget import artifact, call, receipt


class RouteFake:
    offline_only = True

    def __init__(self, ledger, binding, *, uncertain=False):
        self.ledger, self.binding = ledger, binding
        self.uncertain = uncertain
        self.executions = []

    def validate(self, binding):
        assert binding == self.binding

    def execute(self, argv, prompt, *, call, **kwargs):
        state = self.ledger.snapshot()
        row = next(r for r in state["calls"] if r["call"]["call_id"] == call.call_id)
        assert row["binding_id"] == self.binding.binding_id
        assert row["reservation"] == self.binding.validate()
        self.executions.append(argv)
        if self.uncertain:
            return Outcome(timed_out=True)
        return Outcome(receipt=receipt(self.ledger, self.binding, call, "0.5"))

    def replay(self, command, **kwargs):
        raise BudgetStop("all secondary paid paths refused")


def registry_at(tmp_path, bindings):
    path, digest = artifact(
        tmp_path / "registry-review.json", '{"offline_review": true}'
    )
    return Registry("confluence-evaluation-v2", tuple(bindings), path, digest)


@pytest.fixture
def mixed(tmp_path):
    path, sha = artifact(tmp_path / "bounds.json", '{"synthetic_bounds":true}')
    models = ("claude-sonnet-5", "gpt-5.6-terra", "claude-opus-5")
    bounds = (("2", "1"), ("3", "1"), ("4", "1"))
    bindings = tuple(
        Binding(
            f"fake-{name}", model, "fake", "synthetic-usd", cap, inflight, path, sha
        )
        for name, model, (cap, inflight) in zip(
            ("sonnet", "terra", "opus"), models, bounds, strict=True
        )
    )
    registry = registry_at(tmp_path, bindings)
    ledger = Ledger.create(tmp_path / "aggregate.sqlite3", registry)
    transports = tuple(RouteFake(ledger, b) for b in bindings)
    launchers = tuple(
        BudgetLauncher(ledger, b, t) for b, t in zip(bindings, transports, strict=True)
    )
    return ledger, registry, launchers, transports


def argv(binding):
    if binding.model == "gpt-5.6-terra":
        return [
            "codex",
            "exec",
            "-m",
            binding.model,
            "-s",
            "read-only",
            "--skip-git-repo-check",
        ]
    return ["claude", "--print", "--model", binding.model, "--tools", ""]


def test_stage5_floor_models_judges_probes_retries_share_ceiling(mixed):
    ledger, registry, launchers, _ = mixed
    phases = (
        "stage5",
        "floor-sonnet",
        "floor-terra",
        "floor-judge-sonnet",
        "floor-judge-terra",
        "probe",
    )
    indices = (0, 0, 1, 2, 2, 0)
    for number, (phase, index) in enumerate(zip(phases, indices, strict=True)):
        launcher = launchers[index]
        launcher.run(
            argv(launcher.binding), "cold", call=call(f"call{number}", phase=phase)
        )
    launchers[1].run(
        argv(launchers[1].binding),
        "cold",
        call=call("terra-retry", phase="floor-terra", attempt=2),
    )
    state = Ledger(ledger.path).snapshot()
    assert state["metadata"]["registry_sha256"] == registry.digest
    assert state["exposure"] == 3_500_000
    assert {row["binding_id"] for row in state["calls"]} == {
        b.binding_id for b in registry.bindings
    }
    for row in state["calls"]:
        binding = registry.binding(row["binding_id"])
        assert row["binding_sha256"] == binding.digest
        assert row["reservation"] == binding.validate()
        ledger.reconcile(Settlement(**row["receipt"]))
    assert ledger.snapshot()["exposure"] == state["exposure"]


def test_cross_model_trial_identity_is_distinct_but_route_restart_is_cached(mixed):
    ledger, _, launchers, transports = mixed
    for i, launcher in enumerate(launchers):
        launcher.run(
            argv(launcher.binding), "cold", call=call(f"call{i}", phase="floor")
        )
    for i, launcher in enumerate(launchers):
        restarted = BudgetLauncher(Ledger(ledger.path), launcher.binding, transports[i])
        restarted.run(
            argv(launcher.binding), "cold", call=call(f"uuid{i}", phase="floor")
        )
    assert len(ledger.snapshot()["calls"]) == 3
    assert [len(t.executions) for t in transports] == [1, 1, 1]


def test_interleaved_uncertainty_exhausts_one_shared_cap(mixed):
    ledger, _, launchers, transports = mixed
    for transport in transports:
        transport.uncertain = True
    for n in range(12):
        launcher = launchers[n % 3]
        launcher.run(argv(launcher.binding), "cold", call=call(f"c{n}", trial=n + 1))
    assert ledger.snapshot()["exposure"] == 48_000_000
    for i, launcher in enumerate(launchers):
        with pytest.raises(BudgetStop, match="headroom"):
            launcher.run(
                argv(launcher.binding), "cold", call=call(f"refused{i}", trial=20)
            )
    assert sum(len(t.executions) for t in transports) == 12


def test_registry_cannot_replace_route_or_reservation_on_restart(mixed):
    ledger, registry, launchers, _ = mixed
    launcher = launchers[0]
    launcher.run(argv(launcher.binding), "cold", call=call())
    changed = replace(launcher.binding, session_cap_usd="1")
    with pytest.raises(BudgetStop, match="binding mismatch"):
        ledger.reserve(call("next", trial=2), changed)
    with pytest.raises(BudgetStop, match="registry pin"):
        ledger.approved_binding(launcher.binding.binding_id, "0" * 64)
    assert ledger.snapshot()["exposure"] == 500_000
    with pytest.raises(FileExistsError):
        Ledger.create(ledger.path, replace(registry, bindings=(changed,)))
    assert ledger.snapshot()["metadata"]["registry_sha256"] == registry.digest


@pytest.mark.parametrize("damage", ["row-binding", "row-bound", "registry-seal"])
def test_each_row_validates_its_own_binding_and_seal(mixed, damage):
    ledger, _, launchers, _ = mixed
    launchers[1].run(argv(launchers[1].binding), "cold", call=call())
    with sqlite3.connect(ledger.path) as db:
        if damage == "registry-seal":
            meta = json.loads(db.execute("SELECT payload FROM metadata").fetchone()[0])
            meta["registry_sha256"] = "0" * 64
            db.execute("UPDATE metadata SET payload=?", (json.dumps(meta),))
        else:
            row = json.loads(db.execute("SELECT payload FROM calls").fetchone()[0])
            row["binding_id" if damage == "row-binding" else "reservation"] = (
                "fake-sonnet" if damage == "row-binding" else 3_000_000
            )
            db.execute("UPDATE calls SET payload=?", (json.dumps(row),))
    with pytest.raises(BudgetStop):
        ledger.snapshot()


@pytest.mark.parametrize("version", [1, 999, True])
def test_unsupported_schema_never_resets_or_migrates_spend(tmp_path, version):
    path = tmp_path / "prior.sqlite3"
    meta = {
        "version": version,
        "cap": CAP,
        "halted": False,
        "binding": {"legacy": True},
    }
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE metadata (id INTEGER PRIMARY KEY, payload TEXT)")
        db.execute(
            "CREATE TABLE calls (id TEXT PRIMARY KEY, identity TEXT, payload TEXT)"
        )
        db.execute("INSERT INTO metadata VALUES (1, ?)", (json.dumps(meta),))
        db.execute(
            "INSERT INTO calls VALUES ('prior-spend', 'old', ?)",
            (json.dumps({"actual": 2_000_000, "reservation": 3_000_000}),),
        )
    before = path.read_bytes()
    with pytest.raises(BudgetStop, match="no automatic migration or reset"):
        Ledger(path).snapshot()
    assert path.read_bytes() == before
    with sqlite3.connect(path) as db:
        assert (
            json.loads(db.execute("SELECT payload FROM calls").fetchone()[0])["actual"]
            == 2_000_000
        )


def reserve_route(path, binding, number, queue):
    try:
        Ledger(Path(path)).reserve(
            call(f"contender{number}", trial=number + 1), binding
        )
        queue.put("reserved")
    except BudgetStop:
        queue.put("stopped")


def test_mixed_controllers_compete_under_same_remaining_headroom(mixed):
    ledger, registry, _, _ = mixed
    for n in range(15):
        ledger.reserve(
            call(f"prior{n}", task="prior", trial=n + 1), registry.bindings[0]
        )
    context = multiprocessing.get_context("spawn")
    queue = context.Queue()
    children = [
        context.Process(
            target=reserve_route,
            args=(str(ledger.path), registry.bindings[i + 1], i, queue),
        )
        for i in range(2)
    ]
    for child in children:
        child.start()
    for child in children:
        child.join(15)
        assert child.exitcode == 0
    assert sorted(queue.get(timeout=2) for _ in children) == ["reserved", "stopped"]
    assert ledger.snapshot()["exposure"] in {49_000_000, 50_000_000}


@pytest.fixture
def api_binding(tmp_path):
    path, digest = artifact(
        tmp_path / "price-evidence.json", '{"synthetic_verified_rates":true}'
    )
    rates = (
        ("input_tokens", "3"),
        ("output_tokens", "15"),
        ("cache_read_input_tokens", "0.3"),
        ("cache_creation_5m_input_tokens", "3.75"),
        ("cache_creation_1h_input_tokens", "6"),
    )
    pricing = ApiPricing(
        "claude-sonnet-5",
        rates,
        200_000,
        "https://platform.claude.com/docs/en/about-claude/pricing",
        "2026-10-05",
        path,
        digest,
    )
    bound_path, bound_sha = artifact(
        tmp_path / "api-binding.json", '{"synthetic_route_bounds":true}'
    )
    return Binding(
        "sonnet-api",
        "claude-sonnet-5",
        "anthropic",
        "api-usage-usd",
        "2",
        "1",
        bound_path,
        bound_sha,
        LaunchContract("claude-print-v1", "anthropic-api-key", "api-usage-usd-v1"),
        pricing,
    )


def api_proof(tmp_path, binding, invocation):
    usage = dict.fromkeys(API_USAGE_FIELDS, 0)
    usage.update(
        input_tokens=1000,
        output_tokens=100,
        cache_read_input_tokens=200,
        cache_creation_input_tokens=300,
        cache_creation_5m_input_tokens=100,
        cache_creation_1h_input_tokens=200,
    )
    proof = {
        "schema_version": 1,
        "complete": True,
        "call_id": invocation.call_id,
        "binding_id": binding.binding_id,
        "pricing_sha256": binding.pricing.digest,
        "requests": [
            {
                "request_id": "msg_fake1",
                "model": binding.model,
                "service_tier": "standard",
                "inference_geo": "global",
                "speed": "standard",
                "server_tool_use": {"web_search_requests": 0, "web_fetch_requests": 0},
                "usage": usage,
            }
        ],
    }
    path, digest = artifact(
        tmp_path / f"{invocation.call_id}.api-usage.json", json.dumps(proof)
    )
    return path, digest, proof


def test_api_usage_cost_uses_api_rates_not_cli_estimate(api_binding, tmp_path):
    binding = api_binding
    invocation = call()
    proof_path, proof_sha, _ = api_proof(tmp_path, binding, invocation)
    usage, micro = api_usage_charge(invocation, binding, proof_path, proof_sha)
    assert micro == 6135
    # A zero CLI estimate cannot release an API charge: actual is independently computed.
    ledger = Ledger.create(tmp_path / "api.sqlite3", registry_at(tmp_path, (binding,)))
    ledger.reserve(invocation, binding)
    charge = replace(
        receipt(ledger, replace(binding, provider="fake"), invocation, "0.006135"),
        provider="anthropic",
        billing="api-usage-usd",
        usage=usage,
        reported_cost_usd="0",
        proof_path=proof_path,
        proof_sha256=proof_sha,
    )
    ledger.reconcile(charge)
    assert ledger.snapshot()["exposure"] == 6135
    ledger.reconcile(charge)
    assert ledger.snapshot()["exposure"] == 6135


@pytest.mark.parametrize(
    "fault",
    [
        "cache-total",
        "cache-missing",
        "negative",
        "float",
        "model",
        "tier",
        "geo",
        "speed",
        "tools",
        "context",
        "duplicate",
        "incomplete",
        "price",
        "empty",
    ],
)
def test_api_usage_ambiguity_refuses_settlement(api_binding, tmp_path, fault):
    binding, invocation = api_binding, call()
    path, _, proof = api_proof(tmp_path, binding, invocation)
    request = proof["requests"][0]
    usage = request["usage"]
    if fault == "cache-total":
        usage["cache_creation_input_tokens"] += 1
    elif fault == "cache-missing":
        usage.pop("cache_creation_1h_input_tokens")
    elif fault == "negative":
        usage["input_tokens"] = -1
    elif fault == "float":
        usage["input_tokens"] = 1.1
    elif fault == "context":
        usage["input_tokens"] = 200_001
    elif fault == "tools":
        request["server_tool_use"]["web_search_requests"] = 1
    elif fault in {"model", "tier", "geo", "speed"}:
        request[
            {
                "model": "model",
                "tier": "service_tier",
                "geo": "inference_geo",
                "speed": "speed",
            }[fault]
        ] = "wrong"
    elif fault == "duplicate":
        proof["requests"].append(dict(request))
    elif fault == "incomplete":
        proof["complete"] = False
    elif fault == "price":
        proof["pricing_sha256"] = "0" * 64
    else:
        proof["requests"] = []
    Path(path).write_text(json.dumps(proof))
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    with pytest.raises(BudgetStop):
        api_usage_charge(invocation, binding, path, digest)


def test_subscription_route_and_no_price_schedule_are_refused(api_binding):
    for changed in (
        replace(
            api_binding,
            contract=LaunchContract("claude-print-v1", "subscription", "cli-estimate"),
        ),
        replace(api_binding, billing="subscription-estimate"),
        replace(api_binding, pricing=None),
    ):
        with pytest.raises(BudgetStop):
            changed.validate()


def test_codex_contract_never_gets_claude_budget_or_spawns(api_binding, tmp_path):
    path, sha = artifact(tmp_path / "codex-unadmitted.json", '{"not_admitted":true}')
    terra = Binding(
        "terra-unadmitted",
        "gpt-5.6-terra",
        "openai",
        "unproved",
        "2",
        "1",
        path,
        sha,
        LaunchContract("codex-unadmitted-v1", "unproved", "unproved"),
    )
    registry = registry_at(tmp_path, (api_binding, terra))
    ledger = Ledger.create(tmp_path / "all-routes.sqlite3", registry)
    transport = RouteFake(ledger, terra)
    launcher = BudgetLauncher(ledger, terra, transport)
    with pytest.raises(BudgetStop, match="Codex route refused"):
        launcher.run(argv(terra), "cold", call=call())
    assert transport.executions == []
    assert ledger.snapshot()["calls"] == []
    with pytest.raises(BudgetStop):
        prepare_launch(
            ["codex", "exec", "-m", terra.model, "--max-budget-usd", "2"],
            "cold",
            api_binding,
        )


def test_floor_claude_normalization_preserves_single_cold_prompt(api_binding):
    prepared = prepare_launch(
        [
            "claude",
            "-p",
            "--model",
            api_binding.model,
            "--safe-mode",
            "--tools",
            "",
            "--output-format",
            "text",
            "question",
        ],
        "question",
        api_binding,
    )
    assert prepared[:2] == ["claude", "--print"]
    assert "question" not in prepared
    assert prepared[-2:] == ["--max-budget-usd", "2"]
    with pytest.raises(BudgetStop):
        prepare_launch(
            ["claude", "--print", "--model", api_binding.model, "different"],
            "question",
            api_binding,
        )


def test_frozen_evaluator_interface_binds_existing_aggregate_only(mixed, tmp_path):
    ledger, registry, _, transports = mixed
    manifest = interface_manifest()
    kwargs = {
        "ledger_path": ledger.path,
        "binding_id": "fake-terra",
        "registry_sha256": registry.digest,
        "module_sha256": manifest["module_sha256"],
        "interface_sha256": manifest["interface_sha256"],
        "transport": transports[1],
    }
    bound = bind_evaluator(**kwargs)
    assert bound.ledger.path == ledger.path
    assert bound.binding.model == "gpt-5.6-terra"
    for field in ("module_sha256", "interface_sha256", "registry_sha256"):
        with pytest.raises(BudgetStop):
            bind_evaluator(**{**kwargs, field: "0" * 64})
    with pytest.raises(BudgetStop):
        bind_evaluator(**{**kwargs, "ledger_path": tmp_path / "new.sqlite3"})
    assert not (tmp_path / "new.sqlite3").exists()
    with pytest.raises(BudgetStop, match="no reviewed"):
        require_launcher()


def test_registry_duplicate_routes_or_lost_approval_are_refused(mixed):
    ledger, registry, _, _ = mixed
    with pytest.raises(BudgetStop):
        replace(
            registry, bindings=(registry.bindings[0], registry.bindings[0])
        ).validate()
    Path(registry.evidence_path).unlink()
    with pytest.raises(BudgetStop, match="evidence"):
        ledger.snapshot()


class ApiFake(RouteFake):
    """Synthetic API response proof, not a client or credential consumer."""

    def execute(self, argv, prompt, *, call, **kwargs):
        self.executions.append(argv)
        assert argv[-2:] == ["--max-budget-usd", self.binding.session_cap_usd]
        assert "evidence_destination" in kwargs
        assert self.binding.contract.authentication == "anthropic-api-key"
        proof_path, proof_sha, _ = api_proof(
            self.ledger.path.parent, self.binding, call
        )
        usage, charge = api_usage_charge(call, self.binding, proof_path, proof_sha)
        # Normalize computed usage dollars to six decimal places, no CLI estimates.
        usd = f"{charge // 1_000_000}.{charge % 1_000_000:06d}"
        settlement = replace(
            receipt(self.ledger, self.binding, call, usd),
            usage=usage,
            reported_cost_usd="0",
            proof_path=proof_path,
            proof_sha256=proof_sha,
        )
        return Outcome(lines=["fake answer"], receipt=settlement)


def test_api_sonnet_terra_fake_and_api_opus_interleave(api_binding, tmp_path):
    sonnet = api_binding
    opus = replace(
        sonnet,
        binding_id="opus-api",
        model="claude-opus-5",
        pricing=replace(sonnet.pricing, model="claude-opus-5"),
    )
    terra = Binding(
        "terra-fake",
        "gpt-5.6-terra",
        "fake",
        "synthetic-usd",
        "3",
        "1",
        sonnet.evidence_path,
        sonnet.evidence_sha256,
    )
    registry = registry_at(tmp_path, (sonnet, terra, opus))
    ledger = Ledger.create(tmp_path / "shared-api.sqlite3", registry)
    transports = (
        ApiFake(ledger, sonnet),
        RouteFake(ledger, terra),
        ApiFake(ledger, opus),
    )
    for index, (binding, transport) in enumerate(
        zip(registry.bindings, transports, strict=True)
    ):
        launcher = BudgetLauncher(ledger, binding, transport)
        launcher.run(
            argv(binding),
            "prompt",
            call=call(f"route{index}", phase="floor"),
            timeout=120,
            evidence_destination=tmp_path,
        )
    assert ledger.snapshot()["exposure"] == 512_270
    assert [row["actual"] for row in ledger.snapshot()["calls"]] == [
        6135,
        500_000,
        6135,
    ]
    # An API route cannot be enabled by forwarding a subscription HOME env alone.
    with pytest.raises(BudgetStop, match="evidence destination"):
        BudgetLauncher(ledger, sonnet, transports[0]).run(
            argv(sonnet), "prompt", call=call("extra", trial=2), timeout=120
        )


def test_api_request_rounding_and_repeated_request_usage(api_binding, tmp_path):
    path, _, proof = api_proof(tmp_path, api_binding, call())
    usage = dict.fromkeys(API_USAGE_FIELDS, 0)
    usage["cache_read_input_tokens"] = 1  # $0.0000003 -> one microdollar per request.
    proof["requests"][0]["usage"] = usage
    proof["requests"].append({**proof["requests"][0], "request_id": "msg_fake2"})
    Path(path).write_text(json.dumps(proof))
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    total, charge = api_usage_charge(call(), api_binding, path, digest)
    assert total["cache_read_input_tokens"] == 2
    assert charge == 2


@pytest.mark.parametrize("fault", ["actual", "usage", "price-evidence"])
def test_api_settlement_mismatch_retains_reservation_and_halts(
    api_binding, tmp_path, fault
):
    ledger = Ledger.create(
        tmp_path / "api-fault.sqlite3", registry_at(tmp_path, (api_binding,))
    )
    invocation = call()
    ledger.reserve(invocation, api_binding)
    path, sha, _ = api_proof(tmp_path, api_binding, invocation)
    usage, _ = api_usage_charge(invocation, api_binding, path, sha)
    charge = replace(
        receipt(ledger, api_binding, invocation, "0.006135"),
        usage=usage,
        proof_path=path,
        proof_sha256=sha,
    )
    if fault == "actual":
        charge = replace(charge, actual_usd="0")
    elif fault == "usage":
        charge = replace(charge, usage={**usage, "output_tokens": 0})
    else:
        # The price schedule pins are independent of the route's bound evidence.
        charge = replace(charge, proof_sha256="0" * 64)
    with pytest.raises(BudgetStop):
        ledger.reconcile(charge)
    state = ledger.snapshot()
    assert state["exposure"] == 3_000_000
    assert state["metadata"]["halted"]


def test_production_create_requires_reviewed_registry(api_binding, tmp_path):
    with pytest.raises(BudgetStop, match="reviewed aggregate registry"):
        Ledger.create(tmp_path / "single-api.sqlite3", api_binding)
    assert not (tmp_path / "single-api.sqlite3").exists()


def test_synthetic_contract_cannot_enable_unmarked_live_transport(mixed):
    ledger, _, launchers, transports = mixed
    transport = transports[0]
    transport.offline_only = False
    with pytest.raises(BudgetStop, match="offline-only"):
        launchers[0].run(argv(launchers[0].binding), "prompt", call=call())
    assert ledger.snapshot()["calls"] == []


@pytest.mark.parametrize(
    "value",
    ["--continue", "--resume=prior", "--fallback-model=other", "--max-budget-usd=50"],
)
def test_option_shaped_values_cannot_escape_closed_launch_parser(mixed, value):
    ledger, _, launchers, transports = mixed
    launcher = launchers[0]
    command = argv(launcher.binding)
    command[-1] = value  # The value of --tools, not an accepted new option.
    with pytest.raises(BudgetStop, match="option-shaped"):
        launcher.run(command, "prompt", call=call())
    assert transports[0].executions == []
    assert ledger.snapshot()["calls"] == []
