"""Native CLI + real parent SDK at the failure seam, fake upstream only."""

import json
import time
from pathlib import Path

import pytest

from tests import evaluation_budget as D
from tests.evaluation_api import Provider, prepare_request
from tests.joint_evaluation import JointLauncher, ProductionTransport
from tests.test_joint_evaluation import call, reg as reg, response, sandbox as sandbox


def test_native_haiku_manual_thinking_fits_capped_output(reg):
    binding = reg.binding("floor-haiku45-api")
    request = {
        "model": binding.model,
        "max_tokens": 32000,
        "messages": [{"role": "user", "content": "Reply OK."}],
        "thinking": {"type": "enabled", "budget_tokens": 31999, "display": "updates"},
    }
    result = prepare_request(request, binding)
    assert result["max_tokens"] == 2048
    assert 1024 <= result["thinking"]["budget_tokens"] < result["max_tokens"]
    assert request["thinking"]["budget_tokens"] == 31999


@pytest.mark.parametrize("case", ["success", "400", "401", "403", "500", "timeout"])
def test_exact_native_parent_sdk_failure_terminates_without_retry(
    tmp_path, reg, sandbox, case
):
    import anthropic
    import httpx2

    native = Path.home() / ".local/bin/claude"
    if not native.exists():
        pytest.skip("pinned native CLI required")
    sandbox.claude = native.resolve()
    sandbox.reads.extend([sandbox.claude, Path(__file__).parent / "e2e/empty-mcp.json"])
    forwarded = []

    def exchange(request):
        body = json.loads(request.content)
        forwarded.append(
            {"max_tokens": body["max_tokens"], "thinking": body.get("thinking")}
        )
        thinking = body.get("thinking", {})
        if case == "success":
            assert thinking["type"] == "enabled"
            assert 1024 <= thinking["budget_tokens"] < body["max_tokens"]
            return httpx2.Response(200, json=response())
        if case == "timeout":
            raise httpx2.ReadTimeout(
                "synthetic timeout includes fake secret", request=request
            )
        return httpx2.Response(
            int(case),
            json={
                "type": "error",
                "error": {
                    "type": "authentication_error"
                    if case in ("401", "403")
                    else "invalid_request_error",
                    "message": "Synthetic provider validation failure",
                    "unselected": "synthetic-body-must-not-be-logged",
                },
            },
        )

    provider = Provider.__new__(Provider)
    provider.client = anthropic.Anthropic(
        api_key=None,
        auth_token="offline-fake-not-a-credential",
        max_retries=0,
        http_client=httpx2.Client(
            transport=httpx2.MockTransport(exchange), trust_env=False
        ),
    )
    binding = reg.binding("floor-haiku45-api")
    ledger = D.Ledger.create(tmp_path / "fixture.sqlite3", reg)
    transport = ProductionTransport(
        {"files": {}, "evidence_root": str(tmp_path / "evidence")},
        reg,
        sandbox,
        provider,
    )
    launch = JointLauncher(ledger, binding, transport)
    identity = call()
    start = time.monotonic()
    try:
        if case == "success":
            result = launch.run(
                ["claude", "--print", "--model", binding.model],
                "Reply OK.",
                call=identity,
                timeout=10,
            )
            assert result.stdout == "OK" and result.receipt.actual_usd == "0.000017"
        else:
            with pytest.raises(D.BudgetStop):
                launch.run(
                    ["claude", "--print", "--model", binding.model],
                    "Reply OK.",
                    call=identity,
                    timeout=10,
                )
            assert time.monotonic() - start < 8, (
                "terminal upstream failure must not wait for native retry timeout"
            )
            row = ledger.snapshot()
            assert row["metadata"]["halted"] and row["exposure"] == 210241
            evidence = tmp_path / "evidence/calls" / identity.call_id
            stop = json.loads((evidence / "session-stop.json").read_text())
            assert stop["upstream_status"] == (None if case == "timeout" else int(case))
            assert stop["upstream_response_observed"] is (case != "timeout")
            assert stop["reservation"] == "retained in full"
            child = json.loads((evidence / "child-stop.json").read_text())
            assert child["reason"] == "session-failed" and child["returncode"] == 130
            assert (
                "synthetic-body-must-not-be-logged"
                not in (evidence / "session-stop.json").read_text()
            )
            assert (
                "synthetic timeout includes fake secret"
                not in (evidence / "session-stop.json").read_text()
            )
        assert len(forwarded) == 1
    finally:
        provider.client.close()


@pytest.mark.parametrize(
    "max_tokens,budget", [(1024, 31999), (2048, True), (2048, 1023)]
)
def test_invalid_manual_thinking_refused_before_dispatch(reg, max_tokens, budget):
    binding = reg.binding("floor-haiku45-api")
    with pytest.raises(D.BudgetStop, match="thinking"):
        prepare_request(
            {
                "model": binding.model,
                "max_tokens": max_tokens,
                "messages": [],
                "thinking": {"type": "enabled", "budget_tokens": budget},
            },
            binding,
        )


def test_timeout_preserves_partial_child_output_and_redacts_local_capability(sandbox):
    from tests.evaluation_sandbox import SandboxStop

    capability = "synthetic-local-capability-not-a-provider-token"
    with pytest.raises(SandboxStop) as captured:
        sandbox.run(
            ["/bin/bash", "-c", f"echo {capability}; echo fixture-stderr >&2; sleep 5"],
            broker_token=capability,
            timeout=1,
        )
    assert captured.value.reason == "timeout"
    assert "fixture-stderr" in captured.value.stderr
    assert "<broker-capability-redacted>" in captured.value.stdout
    assert capability not in captured.value.stdout


def test_repaired_probe_has_distinct_logical_identity(
    tmp_path, reg, monkeypatch, capsys
):
    import contextlib
    import sys
    from types import SimpleNamespace

    from tests import joint_evaluation as joint

    ledger = D.Ledger.create(tmp_path / "fixture.sqlite3", reg)
    observed = []
    config = {"sources": {"plugin": {"head": "a" * 40}}}
    monkeypatch.setattr(joint, "CANONICAL", ledger.path)
    monkeypatch.setattr(joint, "checked_config", lambda *args: (config, reg, None))
    monkeypatch.setattr(
        joint, "Provider", lambda: SimpleNamespace(available=lambda binding: None)
    )
    monkeypatch.setattr(joint, "open_ledger", lambda *args: ledger)
    monkeypatch.setattr(joint, "admission", lambda *args: contextlib.nullcontext(None))
    monkeypatch.setattr(
        joint,
        "JointLauncher",
        lambda *args: SimpleNamespace(run=lambda *a, **kw: observed.append(kw["call"])),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["joint", "--config", "unused", "--config-sha256", "0" * 64, "probe"],
    )
    assert joint.main() == 0
    assert json.loads(capsys.readouterr().out)["status"] == "COMPLETE"
    old = D.Call(
        "joint-oauth-availability-probe-v1",
        "probe",
        "oauth-equivalent-accounting",
        1,
        "a" * 40,
    )
    new = observed[0]
    assert new.call_id == "joint-oauth-availability-probe-v3"
    assert D.Ledger._identity(new, "floor-haiku45-api") != D.Ledger._identity(
        old, "floor-haiku45-api"
    )
