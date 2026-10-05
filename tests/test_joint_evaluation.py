"""Zero-cost production boundary tests; fake provider, real local OS sandbox."""

import json
import os
import shlex
import sys
import threading
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from tests import evaluation_budget as D
from tests.evaluation_api import (
    Broker,
    Provider,
    RateLimitStop,
    Session,
    prepare_request,
    request_bound,
    sse,
    usage_record,
)
from tests.evaluation_sandbox import Sandbox
from tests.joint_evaluation import (
    CONTEXT_SOURCES,
    MODEL_ROUTES,
    JointLauncher,
    ProductionTransport,
    open_ledger,
    reconcile_existing,
    registry,
)


@pytest.fixture
def reg(tmp_path):
    routes = []
    for identity, (model, _) in MODEL_ROUTES.items():
        rate = "1" if "haiku" in identity else "4" if "opus" in identity else "2"
        routes.append(
            {
                "binding_id": identity,
                "model_id": model,
                "provider": "anthropic",
                "authentication": "owner-environment-DEMO_CLAUDE_CODE_OAUTH_TOKEN",
                "billing": "api-equivalent-usage-usd-v1",
                "max_context_tokens": MODEL_ROUTES[identity][1],
                "context_source": CONTEXT_SOURCES[model],
                "rates_usd_per_million_tokens": {
                    "input_tokens": rate,
                    "output_tokens": str(int(rate) * 5),
                    "cache_read_input_tokens": "0.2",
                    "cache_creation_5m_input_tokens": "2.5",
                    "cache_creation_1h_input_tokens": "4",
                },
            }
        )
    model_path = tmp_path / "models.json"
    proof = tmp_path / "proof.json"
    model_path.write_text(
        json.dumps(
            {
                "routes": routes,
                "price_source": "https://platform.claude.com/docs/en/about-claude/pricing",
                "verified_at": "2026-10-05",
            }
        )
    )
    proof.write_text("{}")
    return registry(model_path, proof)


def response(model="claude-haiku-4-5-20251001"):
    return {
        "id": "msg_fixture",
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": [{"type": "text", "text": "OK"}],
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {
            "input_tokens": 7,
            "output_tokens": 2,
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0,
            "service_tier": "standard",
            "inference_geo": "global",
        },
    }


class FakeProvider:
    def __init__(self, mode="ok"):
        self.mode = mode
        self.calls = []

    def message(self, request, **kwargs):
        self.calls.append(request)
        if self.mode == "timeout":
            raise TimeoutError("synthetic timeout")
        if self.mode == "crash":
            raise KeyboardInterrupt
        if self.mode == "rate-limit":
            raise RateLimitStop("synthetic subscription limit")
        result = response(request["model"])
        result["id"] += str(len(self.calls))
        if self.mode == "missing":
            result.pop("usage")
        if self.mode == "malformed":
            result["usage"]["output_tokens"] = True
        return result


def call(n=1):
    return D.Call(f"call-{n}", "probe", f"fixture-{n}", 1, "a" * 40)


def body(binding):
    return {
        "model": binding.model,
        "max_tokens": 64,
        "messages": [{"role": "user", "content": "OK?"}],
    }


def claude_report(binding, requests=1):
    usage = dict.fromkeys(D.API_USAGE_FIELDS, 0)
    usage.update(input_tokens=7 * requests, output_tokens=2 * requests)
    charge = binding.pricing.charge(usage)
    return {
        "type": "result",
        "subtype": "success",
        "result": "OK",
        "usage": {
            k: usage[k]
            for k in (
                "input_tokens",
                "output_tokens",
                "cache_read_input_tokens",
                "cache_creation_input_tokens",
            )
        },
        "total_cost_usd": charge / 1_000_000,
        "modelUsage": {
            binding.model: {
                "inputTokens": usage["input_tokens"],
                "outputTokens": usage["output_tokens"],
                "cacheReadInputTokens": 0,
                "cacheCreationInputTokens": 0,
                "costUSD": charge / 1_000_000,
            }
        },
    }


class FakeOAuthCLI:
    """Offline native-output client: consumes the real broker, never a credential."""

    claude = Path("/fixture/claude")

    def __init__(self, reg):
        self.reg = reg
        self.report_mode = "ok"

    def run(self, argv, *, port=None, broker_token=None, on_line=None, **kwargs):
        import http.client

        model = argv[argv.index("--model") + 1]
        binding = next(b for b in self.reg.bindings if b.model == model)
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
        connection.request(
            "POST",
            "/v1/messages",
            json.dumps(body(binding)),
            {"X-Api-Key": broker_token},
        )
        response = connection.getresponse()
        response.read()
        connection.close()
        if response.status != 200:
            return 1, "", "offline broker refused"
        report = claude_report(binding)
        if self.report_mode == "missing":
            report.pop("usage")
        elif self.report_mode == "mismatch":
            report["total_cost_usd"] = 0.5
        line = json.dumps(report)
        if on_line:
            on_line(line)
        return 0, line + "\n", ""


def launcher(tmp_path, reg, mode="ok"):
    config = {"files": {}, "evidence_root": str(tmp_path / "evidence")}
    ledger = D.Ledger.create(tmp_path / "ledger.sqlite3", reg)
    provider = FakeProvider(mode)
    transport = ProductionTransport(config, reg, FakeOAuthCLI(reg), provider)
    return JointLauncher(ledger, reg.binding("floor-haiku45-api"), transport), provider


def invoke(launch, identity):
    return launch.run(
        ["claude", "--print", "--model", launch.binding.model],
        "OK?",
        call=identity,
        timeout=60,
    )


def test_success_usage_accounting_and_duplicate_reconcile(tmp_path, reg):
    launch, provider = launcher(tmp_path, reg)
    result = invoke(launch, call())
    assert result.stdout == "OK"
    assert result.receipt.actual_usd == "0.000017"
    launch.ledger.reconcile(result.receipt)
    assert reconcile_existing(launch.ledger)["exposure"] == 17
    cached = invoke(launch, call())
    assert cached.stdout == result.stdout
    assert len(provider.calls) == 1
    assert launch.binding.validate() == 210241


@pytest.mark.parametrize("mode", ["missing", "malformed", "timeout", "crash"])
def test_unknown_charge_halts_and_restart_retains_reservation(tmp_path, reg, mode):
    launch, provider = launcher(tmp_path, reg, mode)
    with pytest.raises((D.BudgetStop, TimeoutError, KeyboardInterrupt)):
        invoke(launch, call())
    snapshot = launch.ledger.snapshot()
    assert snapshot["metadata"]["halted"]
    assert snapshot["calls"][0]["status"] == "uncertain"
    assert snapshot["exposure"] == launch.binding.validate()
    with pytest.raises(D.BudgetStop):
        reconcile_existing(launch.ledger)
    with pytest.raises(D.BudgetStop):
        invoke(launch, call(2))
    assert len(provider.calls) == 1


def test_crash_after_outcome_before_settle_reconciles_once(tmp_path, reg):
    launch, provider = launcher(tmp_path, reg)
    c = call()
    b = launch.binding
    launch.ledger.reserve(c, b)
    session = Session(b, c, provider, tmp_path / "interrupted")
    session.message(body(b))
    receipt = session.settlement({"answer": "OK"}, claude_report=claude_report(b))
    launch.ledger.record_outcome(c.call_id, D.Outcome(lines=["OK"], receipt=receipt))
    assert reconcile_existing(launch.ledger)["exposure"] == 17
    assert reconcile_existing(launch.ledger)["exposure"] == 17


def test_crash_before_outcome_cannot_release_reservation(tmp_path, reg):
    launch, _ = launcher(tmp_path, reg)
    launch.ledger.reserve(call(), launch.binding)
    with pytest.raises(D.BudgetStop, match="unresolved"):
        reconcile_existing(launch.ledger)
    assert launch.ledger.snapshot()["exposure"] == 210241


def test_cap_exhaustion_suppresses_next_provider_call(tmp_path, reg, monkeypatch):
    # Same production ledger path, reduced aggregate limit for this fixture.
    monkeypatch.setattr(D, "CAP", 210250)
    single = replace(reg, bindings=(reg.binding("floor-haiku45-api"),))
    launch, provider = launcher(tmp_path, single)
    invoke(launch, call())
    with pytest.raises(D.BudgetStop, match="headroom"):
        invoke(launch, call(2))
    assert len(provider.calls) == 1
    assert launch.ledger.snapshot()["exposure"] == 17


@pytest.mark.parametrize(
    "mutation",
    [
        lambda x: x.update(model="terra"),
        lambda x: x.update(model="codex"),
        lambda x: x.update(service_tier="priority"),
        lambda x: x.update(inference_geo="us"),
        lambda x: x.update(
            tools=[{"type": "web_search_20260209", "name": "web_search"}]
        ),
        lambda x: x.update(tools=[{"name": "Agent", "input_schema": {}}]),
        lambda x: x.update(mcp_servers=[{"url": "https://invalid"}]),
        lambda x: x.update(max_tokens=True),
        lambda x: x.update(max_tokens=-1),
    ],
)
def test_wrong_routes_helpers_and_unbounded_requests_never_call_provider(
    tmp_path, reg, mutation
):
    b = reg.binding("floor-haiku45-api")
    provider = FakeProvider()
    session = Session(b, call(), provider, tmp_path / "session")
    request = body(b)
    mutation(request)
    with pytest.raises(D.BudgetStop):
        session.message(request)
    assert not provider.calls


@pytest.mark.parametrize(
    "field,value",
    [
        ("input_tokens", None),
        ("output_tokens", -1),
        ("cache_read_input_tokens", 1),
        ("cache_creation_input_tokens", 3),
        ("service_tier", "priority"),
        ("inference_geo", None),
        ("speed", "fast"),
        ("future_charge", 1),
        ("server_tool_use", {"web_search_requests": 1, "web_fetch_requests": 0}),
    ],
)
def test_malformed_usage_refused(reg, field, value):
    value_response = response()
    value_response["usage"][field] = value
    with pytest.raises(D.BudgetStop):
        usage_record(value_response, reg.binding("floor-haiku45-api"))


def test_cache_controls_removed_before_bounded_dispatch(reg):
    b = reg.binding("floor-haiku45-api")
    request = body(b)
    request["system"] = [
        {
            "type": "text",
            "text": "test",
            "cache_control": {"type": "ephemeral", "ttl": "1h"},
        }
    ]
    request["max_tokens"] = 999999
    prepared = prepare_request(request, b)
    assert "cache_control" not in str(prepared)
    assert prepared["max_tokens"] == 2048
    assert prepared["service_tier"] == "standard_only"
    assert request_bound(b) == 210240


def test_single_request_session_refuses_helper(tmp_path, reg):
    b = reg.binding("floor-haiku45-api")
    provider = FakeProvider()
    session = Session(b, call(), provider, tmp_path / "single", single=True)
    session.message(body(b))
    with pytest.raises(D.BudgetStop):
        session.message(body(b))
    assert len(provider.calls) == 1
    assert (
        session.settlement({}, claude_report=claude_report(b)).actual_usd == "0.000017"
    )


def test_concurrent_helper_marks_session_incomplete(tmp_path, reg):
    b = reg.binding("floor-haiku45-api")
    session = Session(b, call(), FakeProvider(), tmp_path / "concurrent")
    with session.lock, pytest.raises(D.BudgetStop, match="concurrent"):
        session.message(body(b))
    assert session.failed


def test_missing_key_refused(monkeypatch):
    for name in (
        "DEMO_CLAUDE_CODE_OAUTH_TOKEN",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_AUTH_TOKEN",
        "ANTHROPIC_CUSTOM_HEADERS",
        "ANTHROPIC_LOG",
        "ANTHROPIC_BASE_URL",
        "CLAUDE_CODE_USE_BEDROCK",
        "CLAUDE_CODE_USE_VERTEX",
        "CLAUDE_CODE_USE_FOUNDRY",
    ):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(D.BudgetStop, match="missing"):
        Provider()


def test_subscription_cannot_enable_default_launcher(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "synthetic-test-only")
    with pytest.raises(D.BudgetStop):
        D.require_launcher()


def test_probe_checks_exact_provider_context(reg, monkeypatch):
    p = object.__new__(Provider)
    # No unmetered availability call: subscription setup-token scopes only
    # authorize inference. The probe checks its exact response model instead.
    p.available(reg.binding("floor-haiku45-api"))
    with pytest.raises(D.BudgetStop):
        p.available(
            replace(
                reg.binding("floor-haiku45-api"),
                contract=D.LaunchContract(
                    "claude-print-v1", "anthropic-api-key", "api-usage-usd-v1"
                ),
            )
        )


def test_init_refuses_prior_spend_and_reinitialization(tmp_path, reg):
    prior = tmp_path / "prior.json"
    prior.write_text(
        json.dumps(
            {
                "calls": [1],
                "accounted_actual_usd": "0",
                "unresolved_reservations_usd": "0",
            }
        )
    )
    config = {
        "ledger_path": str(tmp_path / "canonical.sqlite3"),
        "files": {"prior_ledger": {"path": str(prior), "sha256": D._digest(None)}},
    }
    config["files"]["prior_ledger"]["sha256"] = (
        __import__("hashlib").sha256(prior.read_bytes()).hexdigest()
    )
    with pytest.raises(D.BudgetStop, match="prior spend"):
        open_ledger(config, reg)
    assert not Path(config["ledger_path"]).exists()
    prior.write_text(
        json.dumps(
            {
                "calls": [],
                "accounted_actual_usd": "0",
                "unresolved_reservations_usd": "0",
            }
        )
    )
    config["files"]["prior_ledger"]["sha256"] = (
        __import__("hashlib").sha256(prior.read_bytes()).hexdigest()
    )
    ledger = open_ledger(config, reg)
    assert open_ledger(config, reg).snapshot()["exposure"] == 0
    ledger.path.unlink()  # synthetic fixture only: simulates lost canonical DB
    with pytest.raises(D.BudgetStop, match="missing ledger"):
        open_ledger(config, reg)


def test_sse_uses_real_tool_observation():
    r = response()
    r["content"] = [
        {
            "type": "tool_use",
            "id": "tool_1",
            "name": "Skill",
            "input": {"skill": "confluence"},
        }
    ]
    r["stop_reason"] = "tool_use"
    events = sse(r)
    assert "input_json_delta" in events and "confluence" in events
    assert "message_stop" in events


@pytest.fixture
def sandbox():
    if sys.platform != "darwin":
        pytest.skip("macOS containment backend; production refuses other hosts")
    cli = Path(sys.executable).parent
    return Sandbox(Path(sys.executable), cli, [Path(sys.base_prefix)], [])


def test_real_sandbox_denies_outside_file_and_process_env(tmp_path, sandbox):
    sentinel = tmp_path / "synthetic-not-a-secret.txt"
    sentinel.write_text("fixture")
    code = f"""from pathlib import Path
try:
 Path({str(sentinel)!r}).read_text()
except PermissionError:
 print('DENIED')
else:
 raise SystemExit(9)
"""
    rc, out, _ = sandbox.run(
        [str(Path(sys.executable).resolve()), "-I", "-c", code], timeout=5
    )
    assert (rc, out.strip()) == (0, "DENIED")
    rc, _, _ = sandbox.run(["/bin/ps", "eww", "-p", str(os.getpid())], timeout=5)
    assert rc != 0


def test_real_sandbox_network_only_broker_and_descendant_inheritance(sandbox):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"fixture")

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_port
        script = (
            f"import socket; s=socket.create_connection(('127.0.0.1',{port}),timeout=2); "
            "s.sendall(b'GET / HTTP/1.0\\r\\nHost: localhost\\r\\n\\r\\n'); "
            "print(s.makefile().read())"
        )
        command = [
            "/bin/bash",
            "--noprofile",
            "--norc",
            "-c",
            shlex.join([str(Path(sys.executable).resolve()), "-I", "-c", script]),
        ]
        rc, out, _ = sandbox.run(command, port=port, timeout=5)
        assert rc == 0 and "fixture" in out
        rc, _, _ = sandbox.run(command, timeout=5)
        assert rc != 0
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


@pytest.mark.parametrize("binding_id", list(MODEL_ROUTES))
def test_real_claude_uses_only_fake_broker(tmp_path, reg, sandbox, binding_id):
    binary = Path.home() / ".local/bin/claude"
    if not binary.exists():
        pytest.skip("receipt pins local Claude binary; no provider call")
    sandbox.claude = binary.resolve()
    sandbox.reads.append(sandbox.claude)
    b = reg.binding(binding_id)
    fake = FakeProvider()
    session = Session(b, call(), fake, tmp_path / "native-cli", single=True)
    with Broker(session) as port:
        rc, output, error = sandbox.run(
            [
                str(sandbox.claude),
                "--print",
                "--output-format",
                "stream-json",
                "--verbose",
                "--model",
                b.model,
                "--max-turns",
                "1",
                "--tools",
                "",
                "--permission-mode",
                "dontAsk",
                "--settings",
                '{"disableAllHooks":true}',
                "--setting-sources",
                "",
            ],
            prompt="Reply OK.",
            port=port,
            broker_token=session.token,
            timeout=20,
        )
    assert rc == 0, (error, session.refusal, session.request_fields)
    assert len(fake.calls) == 1
    assert not session.failed
    report = next(
        json.loads(line)
        for line in output.splitlines()
        if json.loads(line).get("type") == "result"
    )
    receipt = session.settlement({"output": output}, claude_report=report)
    assert D.microdollars(receipt.actual_usd) == D.microdollars(
        str(claude_report(b)["total_cost_usd"])
    )


@pytest.mark.parametrize("routing", [False, True])
def test_real_skill_and_bash_retain_tools_inside_sandbox(
    tmp_path, reg, sandbox, routing
):
    binary = Path.home() / ".local/bin/claude"
    if not binary.exists():
        pytest.skip("local pinned Claude binary needed")
    root = Path(__file__).resolve().parents[1]
    sandbox.claude = binary.resolve()
    sandbox.reads.extend(
        [
            sandbox.claude,
            root / "skills",
            root / ".claude-plugin",
            root / "tests/e2e/empty-mcp.json",
        ]
    )
    binding = reg.binding("plugin-sonnet5-api")
    provider = FakeProvider()
    original = provider.message

    def scripted(request, **kwargs):
        value = original(request)
        if len(provider.calls) == 1:
            value.update(
                content=[
                    {
                        "type": "tool_use",
                        "id": "skill_fixture",
                        "name": "Skill",
                        "input": {"skill": "confluence"},
                    }
                ],
                stop_reason="tool_use",
            )
        elif len(provider.calls) == 2:
            value.update(
                content=[
                    {
                        "type": "tool_use",
                        "id": "bash_fixture",
                        "name": "Bash",
                        "input": {
                            "command": "confluence-as --version",
                            "description": "Read local CLI version",
                        },
                    }
                ],
                stop_reason="tool_use",
            )
        return value

    provider.message = scripted
    session = Session(binding, call(), provider, tmp_path / "skill-bash")
    with Broker(session) as port:
        rc, output, error = sandbox.run(
            [
                str(sandbox.claude),
                "--print",
                "--output-format",
                "stream-json",
                "--verbose",
                "--model",
                binding.model,
                "--tools",
                "Bash,Skill",
                "--allowedTools",
                "Bash,Skill",
                "--permission-mode",
                "dontAsk",
                "--strict-mcp-config",
                "--mcp-config",
                str(root / "tests/e2e/empty-mcp.json"),
                "--plugin-dir",
                str(root),
                "--settings",
                '{"disableAllHooks":true}',
                "--setting-sources",
                "",
                *(["--max-turns", "1"] if routing else []),
            ],
            prompt="Read local CLI version.",
            port=port,
            broker_token=session.token,
            timeout=30,
        )
    assert rc == (1 if routing else 0), (error, session.refusal, session.request_fields)
    assert len(provider.calls) == (1 if routing else 3)
    if not routing:
        assert "version 2." in output
    assert not session.failed
    report = next(
        json.loads(line)
        for line in output.splitlines()
        if json.loads(line).get("type") == "result"
    )
    receipt = session.settlement({"output": output}, claude_report=report)
    assert D.microdollars(receipt.actual_usd) == (34 if routing else 102)


def test_sdk_child_logging_cannot_expose_requests_or_error(monkeypatch):
    import io
    import logging

    import anthropic
    import httpx2

    for name in (
        "ANTHROPIC_AUTH_TOKEN",
        "ANTHROPIC_CUSTOM_HEADERS",
        "ANTHROPIC_LOG",
        "ANTHROPIC_BASE_URL",
        "CLAUDE_CODE_USE_BEDROCK",
        "CLAUDE_CODE_USE_VERTEX",
        "CLAUDE_CODE_USE_FOUNDRY",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DEMO_CLAUDE_CODE_OAUTH_TOKEN", "synthetic-test-only")
    output = io.StringIO()
    handler = logging.StreamHandler(output)
    root = logging.getLogger()
    old_level, old_disabled = root.level, root.manager.disable
    root.setLevel(logging.DEBUG)
    logging.disable(logging.NOTSET)
    root.addHandler(handler)
    original_client = anthropic.DefaultHttpxClient

    def fail(request):
        raise RuntimeError("SYNTHETIC_SENSITIVE_ERROR")

    monkeypatch.setattr(
        anthropic,
        "DefaultHttpxClient",
        lambda **kw: original_client(transport=httpx2.MockTransport(fail), **kw),
    )
    try:
        provider = Provider()
        with pytest.raises(
            D.BudgetStop, match="provider invocation failed; reservation retained"
        ):
            provider.message(
                {
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 1,
                    "messages": [
                        {"role": "user", "content": "SYNTHETIC_PRIVATE_PROMPT"}
                    ],
                }
            )
        provider.client.close()
        assert output.getvalue() == ""
    finally:
        root.removeHandler(handler)
        root.setLevel(old_level)
        logging.disable(old_disabled)


def test_replay_keeps_pipefail(sandbox, reg):
    transport = ProductionTransport({"files": {}}, reg, sandbox, FakeProvider())
    code, _, _ = transport.replay("false | /usr/bin/head -1")
    assert code != 0


@pytest.mark.parametrize(
    "field,value",
    [
        ("ledger_path", "/tmp/second-ledger"),
        ("registry_sha256", "b" * 64),
        ("source_commit", "0" * 40),
        ("kind", "historical"),
    ],
)
def test_floor_policy_semantics_checked_before_provider(
    tmp_path, reg, monkeypatch, field, value
):
    from types import SimpleNamespace

    from tests import joint_evaluation as joint

    policy = {
        "ledger_path": str(joint.CANONICAL),
        "registry_sha256": reg.digest,
        "source_commit": "a" * 40,
        "kind": "new",
        "module_path": str(Path(D.__file__).resolve()),
    }
    policy[field] = value
    fake_floor = SimpleNamespace(
        load_json=lambda p: {},
        selected_facts=lambda i, a: [],
        reviewed_policy=lambda *args: (policy, {}),
    )
    monkeypatch.setattr(joint, "load_floor", lambda c: fake_floor)
    config = {
        "sources": {"floor": {"path": str(tmp_path), "head": "a" * 40}},
        "files": {
            "floor_policy": {"path": str(tmp_path / "policy"), "sha256": "b" * 64}
        },
    }
    with pytest.raises(D.BudgetStop, match="canonical controller"):
        joint.check_floor_policy(config, reg)


def test_dry_eligibility_does_not_release_uncertain_reservation(tmp_path, reg):
    from tests.joint_evaluation import check_ledger_eligibility

    launch, _ = launcher(tmp_path, reg)
    launch.ledger.reserve(call(), launch.binding)
    with pytest.raises(D.BudgetStop, match="unresolved"):
        check_ledger_eligibility({"ledger_path": str(launch.ledger.path)}, reg)
    assert launch.ledger.snapshot()["calls"][0]["status"] == "reserved"


def test_dry_mode_never_constructs_provider_or_initializes_ledger(
    tmp_path, reg, monkeypatch, capsys
):
    from tests import joint_evaluation as joint

    monkeypatch.setattr(
        sys,
        "argv",
        ["joint", "--config", "unused", "--config-sha256", "0" * 64, "dry-admission"],
    )
    monkeypatch.setattr(joint, "checked_config", lambda *args: ({}, reg, None))

    def forbidden(*args):
        raise AssertionError("dry mode crossed paid boundary")

    monkeypatch.setattr(joint, "Provider", forbidden)
    monkeypatch.setattr(joint, "open_ledger", forbidden)
    assert joint.main() == 0
    assert json.loads(capsys.readouterr().out)["api_calls"] == 0


def test_broker_capability_prevents_detached_child_reuse(tmp_path, reg):
    import http.client

    b = reg.binding("floor-haiku45-api")
    fake = FakeProvider()
    session = Session(b, call(), fake, tmp_path / "stale")
    with Broker(session) as port:
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        connection.request(
            "POST",
            "/v1/messages",
            json.dumps(body(b)),
            {"X-Api-Key": "obsolete-fixture-capability"},
        )
        response = connection.getresponse()
        assert response.status == 400
        assert response.getheader("x-should-retry") == "false"
        connection.close()
    assert fake.calls == []


def test_sandbox_denies_keychain_mach_lookup_without_requesting_credentials(sandbox):
    script = """import ctypes
lib=ctypes.CDLL('/usr/lib/libSystem.B.dylib')
bootstrap=ctypes.c_uint.in_dll(lib,'bootstrap_port').value
port=ctypes.c_uint()
rc=lib.bootstrap_look_up(bootstrap,b'com.apple.securityd',ctypes.byref(port))
print('DENIED' if rc else 'ALLOWED')
"""
    rc, out, _ = sandbox.run(
        [str(Path(sys.executable).resolve()), "-I", "-c", script], timeout=5
    )
    assert rc == 0 and out.strip() == "DENIED"


@pytest.mark.parametrize("ignored", [False, True])
@pytest.mark.parametrize("filename", ["conftest.py", "shadow.cpython-313-darwin.so"])
def test_untracked_importable_source_refused(tmp_path, monkeypatch, ignored, filename):
    from tests import joint_evaluation as joint

    (tmp_path / filename).write_text(
        "raise AssertionError('unreviewed code must not execute')"
    )

    def git(argv, **kw):
        if "rev-parse" in argv:
            return "a" * 40 + "\n"
        if "diff" in argv:
            return ""
        if ("--ignored" in argv) == ignored:
            return filename.encode() + b"\0"
        return b""

    monkeypatch.setattr(joint.subprocess, "check_output", git)
    with pytest.raises(D.BudgetStop, match="untracked importable"):
        joint.check_source({"path": str(tmp_path), "head": "a" * 40})


def test_launch_flags_ignore_stale_bytecode(tmp_path):
    import py_compile
    import subprocess

    source = tmp_path / "review_fixture.py"
    source.write_text("VALUE='stale'\n")
    stamp = source.stat().st_mtime_ns
    py_compile.compile(str(source), doraise=True)
    source.write_text("VALUE='fresh'\n")
    os.utime(source, ns=(stamp, stamp))
    program = (
        "import sys; sys.path.insert(0, sys.argv[1]); "
        "import review_fixture; print(review_fixture.VALUE)"
    )
    env = {"PATH": os.defpath}
    normal = subprocess.check_output(
        [sys.executable, "-I", "-c", program, str(tmp_path)], env=env, text=True
    )
    assert normal.strip() == "stale"
    isolated = subprocess.check_output(
        [
            sys.executable,
            "-I",
            "-B",
            "-X",
            "pycache_prefix=/dev/null",
            "-c",
            program,
            str(tmp_path),
        ],
        env=env,
        text=True,
    )
    assert isolated.strip() == "fresh"


def test_entry_refuses_missing_cache_isolation(tmp_path):
    import subprocess

    entry = Path(__file__).parents[1] / "scripts/joint_evaluation.py"
    result = subprocess.run(
        [sys.executable, "-I", str(entry), "--help"],
        env={"PATH": os.defpath},
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "pycache_prefix=/dev/null" in result.stderr


def test_bootstrap_refuses_native_shadow_before_import(tmp_path):
    import shutil
    import subprocess

    scripts = tmp_path / "scripts"
    scripts.mkdir()
    entry = scripts / "joint_evaluation.py"
    shutil.copyfile(Path(__file__).parents[1] / "scripts/joint_evaluation.py", entry)
    package = tmp_path / "tests"
    package.mkdir()
    (package / "__init__.py").write_text("raise AssertionError('imported too soon')\n")
    env = {"PATH": os.defpath, "GIT_CONFIG_GLOBAL": os.devnull}
    for argv in (
        ["git", "init", "-q"],
        ["git", "add", "scripts", "tests"],
        [
            "git",
            "-c",
            "user.name=Offline Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
    ):
        subprocess.run(argv, cwd=tmp_path, env=env, check=True, capture_output=True)
    (package / "joint_evaluation.cpython-313-darwin.so").write_bytes(b"untrusted")
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-X",
            "pycache_prefix=/dev/null",
            str(entry),
            "--help",
        ],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "refused before controller import" in result.stderr
    assert "imported too soon" not in result.stderr


def test_no_api_key_fallback_when_owner_oauth_missing(monkeypatch):
    monkeypatch.delenv("DEMO_CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "synthetic-api-key-never-used")
    with pytest.raises(D.BudgetStop, match="missing"):
        Provider()


@pytest.mark.parametrize("limited", [False, True])
def test_fake_oauth_sdk_exact_bearer_route_and_zero_retries(monkeypatch, limited):
    import anthropic
    import httpx2

    for name in (
        "ANTHROPIC_AUTH_TOKEN",
        "ANTHROPIC_CUSTOM_HEADERS",
        "ANTHROPIC_LOG",
        "ANTHROPIC_BASE_URL",
        "CLAUDE_CODE_USE_BEDROCK",
        "CLAUDE_CODE_USE_VERTEX",
        "CLAUDE_CODE_USE_FOUNDRY",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DEMO_CLAUDE_CODE_OAUTH_TOKEN", "synthetic-oauth-token")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "synthetic-api-key-never-forwarded")
    calls = []

    def exchange(request):
        calls.append(request)
        assert str(request.url) == "https://api.anthropic.com/v1/messages"
        assert request.headers["authorization"] == "Bearer synthetic-oauth-token"
        assert "x-api-key" not in request.headers
        assert "oauth-2025-04-20" in request.headers["anthropic-beta"]
        if limited:
            return httpx2.Response(
                429,
                json={
                    "type": "error",
                    "error": {"type": "rate_limit_error", "message": "synthetic"},
                },
            )
        return httpx2.Response(200, json=response())

    original = anthropic.DefaultHttpxClient
    monkeypatch.setattr(
        anthropic,
        "DefaultHttpxClient",
        lambda **kw: original(transport=httpx2.MockTransport(exchange), **kw),
    )
    provider = Provider()
    try:
        if limited:
            with pytest.raises(RateLimitStop):
                provider.message(
                    {
                        "model": "claude-haiku-4-5-20251001",
                        "max_tokens": 1,
                        "messages": [{"role": "user", "content": "offline"}],
                    }
                )
        else:
            assert (
                provider.message(
                    {
                        "model": "claude-haiku-4-5-20251001",
                        "max_tokens": 1,
                        "messages": [{"role": "user", "content": "offline"}],
                    }
                )["usage"]["input_tokens"]
                == 7
            )
        assert len(calls) == 1
    finally:
        provider.client.close()


@pytest.mark.parametrize("mode", ["missing", "mismatch"])
def test_cli_report_missing_or_disagreeing_keeps_full_reservation(tmp_path, reg, mode):
    launch, provider = launcher(tmp_path, reg)
    launch.transport.sandbox.report_mode = mode
    with pytest.raises(D.BudgetStop):
        invoke(launch, call())
    snapshot = launch.ledger.snapshot()
    assert snapshot["metadata"]["halted"]
    assert snapshot["exposure"] == 210241
    assert len(provider.calls) == 1


def test_oauth_rate_limit_is_terminal_partial_stop_without_retry(tmp_path, reg):
    launch, provider = launcher(tmp_path, reg, "rate-limit")
    with pytest.raises(RateLimitStop):
        invoke(launch, call())
    snapshot = launch.ledger.snapshot()
    assert snapshot["metadata"]["halted"]
    assert snapshot["exposure"] == 210241
    path = (
        Path(launch.transport.config["evidence_root"])
        / "calls"
        / call().call_id
        / "rate-limit-stop.json"
    )
    stop = json.loads(path.read_text())
    assert stop["status"] == "STOPPED_RATE_LIMIT" and stop["retry_count"] == 0
    assert stop["completed_requests"] == 0
    with pytest.raises(D.BudgetStop):
        invoke(launch, call(2))
    assert len(provider.calls) == 1


def test_dry_refuses_absent_oauth_before_any_provider_or_ledger(
    tmp_path, monkeypatch, capsys
):
    from tests import joint_evaluation as joint

    monkeypatch.delenv("DEMO_CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "joint",
            "--config",
            str(tmp_path / "unused"),
            "--config-sha256",
            "0" * 64,
            "dry-admission",
        ],
    )
    assert joint.main() == 2
    assert json.loads(capsys.readouterr().out)["status"] == "STOPPED_INCOMPLETE"


def test_children_receive_no_provider_auth_variables(sandbox, monkeypatch):
    names = (
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_AUTH_TOKEN",
        "CLAUDE_CODE_OAUTH_TOKEN",
        "CLAUDE_CODE_OAUTH_REFRESH_TOKEN",
        "DEMO_CLAUDE_CODE_OAUTH_TOKEN",
    )
    for name in names:
        monkeypatch.setenv(name, "synthetic-parent-only")
    program = (
        "import os; print(','.join(n for n in " + repr(names) + " if n in os.environ))"
    )
    rc, stdout, _ = sandbox.run(
        [str(Path(sys.executable).resolve()), "-I", "-c", program], timeout=5
    )
    assert rc == 0 and not stdout.strip()


@pytest.mark.parametrize(
    "capability",
    [
        "context-2m-2026-01-01",
        "fast-mode-2026-02-01",
        "server-side-fallback-2026-07-01",
        "message-batches-2024-09-24",
        "web-search-2025-03-05",
        "unknown",
        "oauth-2025-04-20\r\nX-Other: bad",
    ],
)
def test_unreviewed_capability_refused_before_forward(tmp_path, reg, capability):
    binding = reg.binding("floor-haiku45-api")
    provider = FakeProvider()
    session = Session(binding, call(), provider, tmp_path / "capability")
    with pytest.raises(D.BudgetStop):
        session.message(
            {"model": binding.model, "max_tokens": 5, "messages": []},
            headers={"anthropic-beta": capability},
        )
    assert provider.calls == []
    assert not list(session.directory.glob("request-*/intent.json"))


def test_model_specific_input_admission_size_before_forward(tmp_path, reg):
    binding = reg.binding("floor-haiku45-api")
    provider = FakeProvider()
    session = Session(binding, call(), provider, tmp_path / "oversized")
    with pytest.raises(D.BudgetStop, match="admission size"):
        session.message(
            {
                "model": binding.model,
                "max_tokens": 5,
                "messages": [{"role": "user", "content": "x" * 200_000}],
            }
        )
    assert provider.calls == []


def test_missing_context_maximum_refuses_registry(tmp_path, reg):
    route_path = Path(reg.bindings[0].pricing.evidence_path)
    data = json.loads(route_path.read_text())
    data["routes"][0].pop("max_context_tokens")
    route_path.write_text(json.dumps(data))
    with pytest.raises(D.BudgetStop, match="hard context"):
        registry(route_path, reg.evidence_path)


@pytest.mark.parametrize("phase", ["floor-trial", "floor-judge"])
def test_floor_caught_rate_limit_preserves_terminal_reason(tmp_path, reg, phase):
    from tests.joint_evaluation import finish_floor

    launch, provider = launcher(tmp_path, reg, "rate-limit")
    transport = launch.transport

    class PartialFloor:
        def main(self, *, transport):
            try:
                invoke(launch, replace(call(), phase=phase))
            except RuntimeError:
                return 1
            raise AssertionError("expected limit")

    with pytest.raises(RateLimitStop, match="Floor partial"):
        finish_floor(PartialFloor(), transport)
    assert len(provider.calls) == 1
    with pytest.raises(RateLimitStop):
        transport.validate(reg.binding("floor-haiku45-api"))
    assert len(provider.calls) == 1


@pytest.mark.parametrize("binding_id", list(MODEL_ROUTES))
def test_frozen_hard_context_maximum_is_covered_before_dispatch(reg, binding_id):
    binding = reg.binding(binding_id)
    limit = binding.pricing.max_context_tokens
    accepted = {
        "model": binding.model,
        "max_tokens": 2048,
        "messages": [{"role": "user", "content": "x" * (limit - 300)}],
    }
    assert prepare_request(accepted, binding)["max_tokens"] == 2048
    usage = dict.fromkeys(D.API_USAGE_FIELDS, 0)
    usage.update(input_tokens=limit, output_tokens=2048)
    assert binding.pricing.charge(usage) == request_bound(binding)
    assert binding.validate() > request_bound(binding)


@pytest.mark.parametrize(
    "block_type",
    [
        "tool_addition",
        "tool_removal",
        "tool_definition",
        "mcp_tool_reference",
        "mcp_toolset_reference",
    ],
)
def test_mid_conversation_tool_escape_refused_before_forward(tmp_path, reg, block_type):
    binding = reg.binding("floor-sonnet55-api")
    provider = FakeProvider()
    session = Session(binding, call(), provider, tmp_path / "inline-escape")
    request = body(binding)
    request["messages"] = [
        {
            "role": "system",
            "content": [
                {
                    "type": block_type,
                    "tool": {
                        "type": "tool_definition",
                        "definition": {
                            "type": "web_search_20250305",
                            "name": "web_search",
                        },
                    },
                }
            ],
        }
    ]
    with pytest.raises(D.BudgetStop, match="server content"):
        session.message(
            request,
            headers={
                "anthropic-beta": "per-turn-control-2026-07-01,mid-conversation-tool-changes-2026-07-01"
            },
        )
    assert provider.calls == []


def test_inline_tool_capability_refused_before_forward(tmp_path, reg):
    binding = reg.binding("floor-sonnet55-api")
    provider = FakeProvider()
    session = Session(binding, call(), provider, tmp_path / "inline-capability")
    with pytest.raises(D.BudgetStop, match="capability"):
        session.message(
            body(binding), headers={"anthropic-beta": "inline-tools-2026-09-15"}
        )
    assert provider.calls == []
