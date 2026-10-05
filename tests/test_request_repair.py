"""Exact native request + SDK/fake upstream, never an owner credential or paid call."""

import json
from pathlib import Path

import pytest

from tests import evaluation_budget as D
from tests.evaluation_api import Provider, usage_record
from tests.joint_evaluation import JointLauncher, ProductionTransport
from tests.test_joint_evaluation import call, reg as reg, response, sandbox as sandbox


def test_native_haiku_matches_legacy_api_schema(tmp_path, reg, sandbox):
    import anthropic
    import httpx2

    native = Path.home() / ".local/bin/claude"
    assert native.exists(), "pinned native CLI is an offline acceptance prerequisite"
    sandbox.claude = native.resolve()
    sandbox.reads.extend([sandbox.claude, Path(__file__).parent / "e2e/empty-mcp.json"])
    sent = []

    def exchange(request):
        assert request.url.path == "/v1/messages" and request.url.query == b"beta=true"
        assert request.headers["x-app"] == "cli"
        assert request.headers["user-agent"] == "claude-cli/2.1.288 (external, sdk-cli)"
        assert {"oauth-2025-04-20", "claude-code-20250219"} <= set(
            request.headers["anthropic-beta"].split(",")
        )
        body = json.loads(request.content)
        sent.append(body)
        if "inference_geo" in body:
            return httpx2.Response(
                400,
                json={
                    "type": "error",
                    "error": {
                        "type": "invalid_request_error",
                        "message": "inference_geo is not supported for this model",
                    },
                },
            )
        value = response()
        value["usage"].pop("inference_geo")
        return httpx2.Response(200, json=value)

    provider = Provider.__new__(Provider)
    provider.client = anthropic.Anthropic(
        api_key=None,
        auth_token="offline-fixture-oauth",
        max_retries=0,
        http_client=httpx2.Client(
            transport=httpx2.MockTransport(exchange), trust_env=False
        ),
    )
    ledger = D.Ledger.create(tmp_path / "fixture.sqlite3", reg)
    transport = ProductionTransport(
        {"files": {}, "evidence_root": str(tmp_path / "evidence")},
        reg,
        sandbox,
        provider,
    )
    binding = reg.binding("floor-haiku45-api")
    try:
        result = JointLauncher(ledger, binding, transport).run(
            ["claude", "--print", "--model", binding.model],
            "Reply OK.",
            call=call(),
            timeout=10,
        )
        assert result.stdout == "OK" and ledger.snapshot()["exposure"] == 17
        assert len(sent) == 1 and "inference_geo" not in sent[0]
    finally:
        provider.client.close()


@pytest.mark.parametrize("geo", ["absent", None, "not_available"])
def test_legacy_usage_keeps_raw_scope_and_derives_standard_rates(reg, geo):
    value = response()
    if geo == "absent":
        value["usage"].pop("inference_geo")
    else:
        value["usage"]["inference_geo"] = geo
    record = usage_record(value, reg.binding("floor-haiku45-api"))
    assert record["inference_geo"] == (None if geo == "absent" else geo)
    assert record["billing_scope_basis"] == "legacy-model-standard-rates"


@pytest.mark.parametrize("geo", [None, "not_available", "us"])
def test_later_models_cannot_use_legacy_scope(reg, geo):
    binding = reg.binding("floor-sonnet55-api")
    value = response(binding.model)
    value["usage"]["inference_geo"] = geo
    with pytest.raises(D.BudgetStop, match="scope"):
        usage_record(value, binding)


def test_api_error_diagnostic_is_allowlisted_redacted_and_bounded(reg, tmp_path):
    import anthropic
    import httpx2

    from tests.evaluation_api import Session

    secret = "sk-ant-oat01-offline-SYNTHETIC-token-not-real"

    def exchange(request):
        return httpx2.Response(
            400,
            headers={
                "request-id": "req_01OfflineFixture123",
                "authorization": f"Bearer {secret}",
            },
            json={
                "type": "error",
                "error": {
                    "type": "invalid_request_error",
                    "message": f"Invalid API key: {secret}",
                    "extra": "request-body-must-not-persist",
                },
                "request": "request-body-must-not-persist",
            },
        )

    provider = Provider.__new__(Provider)
    provider.client = anthropic.Anthropic(
        api_key="",
        auth_token=secret,
        max_retries=0,
        http_client=httpx2.Client(
            transport=httpx2.MockTransport(exchange), trust_env=False
        ),
    )
    session = Session(
        reg.binding("floor-haiku45-api"), call(), provider, tmp_path / "failure"
    )
    try:
        with pytest.raises(D.BudgetStop):
            session.message(
                {"model": session.binding.model, "max_tokens": 64, "messages": []}
            )
        stop = json.loads((session.directory / "session-stop.json").read_text())
        summary = stop["upstream_error"]
        assert summary == {
            "type": "error",
            "error": {
                "type": "invalid_request_error",
                "message": "Invalid API key: <REDACTED>",
            },
            "request_id": "req_01OfflineFixture123",
        }
        assert secret not in json.dumps(
            stop
        ) and "request-body-must-not-persist" not in json.dumps(stop)
    finally:
        provider.client.close()


@pytest.mark.parametrize(
    "message",
    [
        '{"headers":{"authorization":"Bearer sk-ant-oat01-fixture"}}',
        'Request body: {"messages":[{"content":"private prompt"}]}',
        "Authorization: Bearer offline-fixture",
        "x" * 10000,
    ],
)
def test_serialized_or_oversized_error_message_is_suppressed(message):
    from tests.evaluation_api import safe_error_summary

    result = safe_error_summary(
        {
            "type": "error",
            "error": {"type": "invalid_request_error", "message": message},
        },
        None,
    )
    assert result["error"]["message"] == "<REDACTED REQUEST OR OVERSIZED CONTENT>"


def test_generic_validation_message_survives_and_caps_after_redaction():
    from tests.evaluation_api import safe_error_summary

    message = "inference_geo: Extra inputs are not permitted"
    assert safe_error_summary(
        {"type": "error", "error": {"message": message}}, None
    ) == {"type": "error", "error": {"message": message}}
    secret = "synthetic-opaque-token"
    result = safe_error_summary(
        {"type": "error", "error": {"message": "q" * 1010 + secret + "z" * 400}},
        None,
        secrets_to_redact=(secret,),
    )
    assert len(result["error"]["message"]) == 1024 and secret not in str(result)


def test_prompt_full_excerpt_escaped_nonce_and_controls_are_redacted():
    from tests.evaluation_api import safe_error_summary

    prompt = 'top secret customer information and syntheticaccount123456 "quoted"'
    message = (
        "bad top secret customer and syntheticaccount123456; "
        + json.dumps(prompt)[1:-1]
        + "\x00 "
        + "a" * 64
    )
    result = safe_error_summary(
        {"type": "error", "error": {"message": message}},
        None,
        request={"messages": [{"content": prompt}]},
    )
    saved = result["error"]["message"]
    assert "top secret customer" not in saved and "syntheticaccount123456" not in saved
    assert "a" * 64 not in saved and "\x00" not in saved and "<REDACTED>" in saved


@pytest.mark.parametrize(
    "body,request_id",
    [
        (None, None),
        ([], {}),
        ({"type": {}}, []),
        ({"type": "error", "error": []}, 9),
        (
            {"type": "error", "error": {"type": [], "message": {"nested": "secret"}}},
            "bad",
        ),
    ],
)
def test_malformed_summary_shapes_are_safe(body, request_id):
    from tests.evaluation_api import safe_error_summary

    result = safe_error_summary(body, request_id)
    assert result in ({}, {"type": "error"})


def test_request_id_cannot_echo_known_token_or_nonce():
    from tests.evaluation_api import safe_error_summary

    token = "req_SyntheticOpaqueSecret"
    assert safe_error_summary({}, token, secrets_to_redact=(token,)) == {}
    assert safe_error_summary({}, "req_" + "a" * 64) == {}


@pytest.mark.parametrize("status", [429, 500, 401, 403, 422])
def test_failure_summary_keeps_only_selected_fields_with_no_retry(
    reg, tmp_path, status
):
    import anthropic
    import httpx2

    from tests.evaluation_api import Session

    seen = []

    def exchange(request):
        seen.append(1)
        return httpx2.Response(
            status,
            headers={"request-id": "req_OfflineCase1234"},
            json={
                "type": "error",
                "error": {
                    "type": "rate_limit_error" if status == 429 else "api_error",
                    "message": "Temporary validation failure: Bearer sk-ant-oat01-fixture",
                    "details": "MUST NOT PERSIST",
                },
                "request": "MUST NOT PERSIST",
            },
        )

    provider = Provider.__new__(Provider)
    provider.client = anthropic.Anthropic(
        api_key="",
        auth_token="fixture",
        max_retries=0,
        http_client=httpx2.Client(
            transport=httpx2.MockTransport(exchange), trust_env=False
        ),
    )
    session = Session(
        reg.binding("floor-haiku45-api"), call(), provider, tmp_path / str(status)
    )
    try:
        with pytest.raises(D.BudgetStop):
            session.message(
                {"model": session.binding.model, "max_tokens": 64, "messages": []}
            )
        saved = json.loads(
            (
                session.directory
                / ("rate-limit-stop.json" if status == 429 else "session-stop.json")
            ).read_text()
        )
        assert len(seen) == 1 and saved["upstream_status"] == status
        assert saved["upstream_error"]["error"]["message"].endswith("Bearer <REDACTED>")
        assert "MUST NOT PERSIST" not in json.dumps(saved)
    finally:
        provider.client.close()


def test_request_redaction_budget_exhaustion_suppresses_diagnostic():
    from tests.evaluation_api import safe_error_summary

    result = safe_error_summary(
        {"type": "error", "error": {"message": "unsafe excerpt"}},
        "req_OfflineCase1234",
        request={"messages": ["text"] * 10001},
    )
    assert result == {
        "type": "error",
        "error": {"message": "<REDACTED REQUEST OR OVERSIZED CONTENT>"},
    }
