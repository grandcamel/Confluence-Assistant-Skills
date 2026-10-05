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
    Session,
    prepare_request,
    request_bound,
    sse,
    usage_record,
)
from tests.evaluation_sandbox import Sandbox
from tests.joint_evaluation import (
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
                "authentication": "owner-environment-ANTHROPIC_API_KEY",
                "billing": "api-usage-usd-v1",
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

    def message(self, request):
        self.calls.append(request)
        if self.mode == "timeout":
            raise TimeoutError("synthetic timeout")
        if self.mode == "crash":
            raise KeyboardInterrupt
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


def launcher(tmp_path, reg, mode="ok"):
    config = {"files": {}, "evidence_root": str(tmp_path / "evidence")}
    ledger = D.Ledger.create(tmp_path / "ledger.sqlite3", reg)
    provider = FakeProvider(mode)
    transport = ProductionTransport(config, reg, None, provider)
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
    receipt = session.settlement({"answer": "OK"})
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
    assert session.settlement({}).actual_usd == "0.000017"


def test_concurrent_helper_marks_session_incomplete(tmp_path, reg):
    b = reg.binding("floor-haiku45-api")
    session = Session(b, call(), FakeProvider(), tmp_path / "concurrent")
    with session.lock, pytest.raises(D.BudgetStop, match="concurrent"):
        session.message(body(b))
    assert session.failed


def test_missing_key_refused(monkeypatch):
    for name in (
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
    class Models:
        def retrieve(self, model):
            class Info:
                def model_dump(self):
                    return {"id": model, "max_input_tokens": 200001}

            return Info()

    p = object.__new__(Provider)
    p.client = type("Client", (), {"models": Models()})()
    with pytest.raises(D.BudgetStop):
        p.available(reg.binding("floor-haiku45-api"))


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


def test_real_claude_uses_only_fake_broker(tmp_path, reg, sandbox):
    binary = Path("/Users/jasonkrueger/.local/bin/claude")
    if not binary.exists():
        pytest.skip("receipt pins local Claude binary; no provider call")
    sandbox.claude = binary.resolve()
    sandbox.reads.append(sandbox.claude)
    b = reg.binding("floor-haiku45-api")
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
                "--tools",
                "",
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
    assert session.settlement({"output": output}).actual_usd == "0.000017"


def test_real_skill_and_bash_retain_tools_inside_sandbox(tmp_path, reg, sandbox):
    binary = Path("/Users/jasonkrueger/.local/bin/claude")
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

    def scripted(request):
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
            ],
            prompt="Read local CLI version.",
            port=port,
            broker_token=session.token,
            timeout=30,
        )
    assert rc == 0, (error, session.refusal, session.request_fields)
    assert len(provider.calls) == 3
    assert "version 2." in output
    assert not session.failed


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
    monkeypatch.setenv("ANTHROPIC_API_KEY", "synthetic-test-only")
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
        with pytest.raises(D.BudgetStop, match="uncertain"):
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
        assert connection.getresponse().status == 403
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
