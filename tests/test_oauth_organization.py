"""OAuth-native wire parameters; official SDK to fake upstream only."""

import json

import pytest

from tests import evaluation_api as A
from tests.test_joint_evaluation import reg as reg, response


@pytest.mark.parametrize(
    "route",
    [
        "plugin-sonnet5-api",
        "floor-sonnet55-api",
        "floor-haiku45-api",
        "floor-opus55-api",
    ],
)
def test_oauth_wire_never_adds_org_gated_parameters(reg, route):
    import anthropic
    import httpx2

    binding = reg.binding(route)
    captured = []

    def exchange(req):
        body = json.loads(req.content)
        captured.append(body)
        assert "inference_geo" not in body and "service_tier" not in body
        return httpx2.Response(200, json=response(binding.model))

    provider = A.Provider.__new__(A.Provider)
    provider.client = anthropic.Anthropic(
        api_key="",
        auth_token="offline-fixture",
        max_retries=0,
        http_client=httpx2.Client(
            transport=httpx2.MockTransport(exchange), trust_env=False
        ),
    )
    try:
        request = A.prepare_request(
            {
                "model": binding.model,
                "max_tokens": 32000,
                "messages": [{"role": "user", "content": "Reply OK."}],
            },
            binding,
        )
        provider.message(request)
        assert len(captured) == 1
    finally:
        provider.client.close()


@pytest.mark.parametrize(
    "route",
    [
        "plugin-sonnet5-api",
        "floor-sonnet55-api",
        "floor-haiku45-api",
        "floor-opus55-api",
    ],
)
@pytest.mark.parametrize("scope", [None, "not_available", "absent"])
def test_oauth_default_scope_preserves_raw_and_uses_frozen_rate_basis(
    reg, route, scope
):
    binding = reg.binding(route)
    value = response(binding.model)
    if scope == "absent":
        value["usage"].pop("inference_geo")
    else:
        value["usage"]["inference_geo"] = scope
    record = A.usage_record(value, binding)
    assert record["inference_geo"] == (None if scope == "absent" else scope)
    assert record["billing_scope_basis"] == "oauth-native-default-frozen-rates"


@pytest.mark.parametrize(
    "field,value",
    [
        ("service_tier", "priority"),
        ("inference_geo", "us"),
        ("inference_geo", "unknown"),
        ("speed", "fast"),
    ],
)
def test_default_scope_does_not_admit_other_billing_modes(reg, field, value):
    body = response("claude-sonnet-5")
    body["usage"][field] = value
    with pytest.raises(A.D.BudgetStop):
        A.usage_record(body, reg.binding("plugin-sonnet5-api"))
