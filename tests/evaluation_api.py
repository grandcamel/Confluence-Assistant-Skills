"""Serial first-party Messages broker. No credentials or provider errors in evidence."""

import hashlib
import json
import logging
import os
import secrets
import threading
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from tests import evaluation_budget as D

MAX_OUTPUT = 2048
MAX_BODY = 2_000_000
SDK_VERSION = "1.11.0"
OAUTH_BETA = "oauth-2025-04-20"  # Pinned native Claude capability; never a credential.
# Frozen native 2.1.288 basic text/tool/effort capabilities. Inline tool changes
# are refused in request content even when the native header is present.
# No long-context, fast,
# fallback, server-tool, batch or unknown capability can alter reserved exposure.
ALLOWED_BETAS = frozenset(
    {
        OAUTH_BETA,
        "claude-code-20250219",
        "interleaved-thinking-2025-05-14",
        "thinking-token-count-2026-05-13",
        "context-management-2025-06-27",
        "prompt-caching-scope-2026-01-05",
        "mid-conversation-system-2026-04-07",
        "per-turn-control-2026-07-01",
        "mid-conversation-tool-changes-2026-07-01",
        "effort-2025-11-24",
        "thinking-display-updates-2026-08-18",
    }
)


def capability_header(headers=None):
    beta = (headers or {}).get("anthropic-beta", "")
    if not isinstance(beta, str) or len(beta) > 2048:
        raise D.BudgetStop("invalid capability header")
    parts = beta.split(",") if beta else []
    if any(part not in ALLOWED_BETAS for part in parts):
        raise D.BudgetStop("unreviewed capability refused")
    return ",".join(dict.fromkeys([*parts, OAUTH_BETA]))


class RateLimitStop(D.BudgetStop):
    """Terminal subscription limit; no retry or fallback."""


class ProviderStop(D.BudgetStop):
    """Safe classification only; no SDK exception body, headers or credential."""

    def __init__(self, category, status=None):
        super().__init__("provider invocation failed; reservation retained")
        self.category = category
        self.upstream_status = status


def oauth_presence():
    """Dry admission checks only presence, never inspects a credential value."""
    if "DEMO_CLAUDE_CODE_OAUTH_TOKEN" not in os.environ:
        raise D.BudgetStop("owner DEMO_CLAUDE_CODE_OAUTH_TOKEN missing")


def owner_oauth_environment():
    """Private parent-side mapping; never passed to a child or serialized."""
    oauth_presence()
    token = os.environ["DEMO_CLAUDE_CODE_OAUTH_TOKEN"]
    if (
        not token
        or not token.strip()
        or token != token.strip()
        or any(c.isspace() for c in token)
    ):
        raise D.BudgetStop("owner OAuth token missing or malformed")
    return {"CLAUDE_CODE_OAUTH_TOKEN": token}


def seal_json(path, value):
    """Write immutable, synced evidence before letting a child observe completion."""
    data = json.dumps(value, sort_keys=True).encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    fd = os.open(Path(path).parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return hashlib.sha256(data).hexdigest()


def usd(micro):
    return format(Decimal(micro) / 1_000_000, "f")


def request_bound(binding):
    # Caching is removed at the broker; no server tools or higher price tiers.
    prices = dict(binding.pricing.rates)
    return D.microdollars(
        format(
            (
                Decimal(prices["input_tokens"]) * binding.pricing.max_context_tokens
                + Decimal(prices["output_tokens"]) * MAX_OUTPUT
            )
            / 1_000_000,
            "f",
        )
    )


def prepare_request(body, binding):
    allowed = {
        "model",
        "messages",
        "max_tokens",
        "stream",
        "system",
        "tools",
        "tool_choice",
        "temperature",
        "top_p",
        "top_k",
        "stop_sequences",
        "thinking",
        "output_config",
        "metadata",
        "service_tier",
        "context_management",
    }
    if (
        not isinstance(body, dict)
        or set(body) - allowed
        or body.get("model") != binding.model
    ):
        raise D.BudgetStop("wrong route or unsupported request field")
    if body.get("service_tier", "standard_only") not in ("auto", "standard_only"):
        raise D.BudgetStop("nonstandard service tier")
    if type(body.get("max_tokens")) is not int or body["max_tokens"] <= 0:
        raise D.BudgetStop("missing finite output bound")
    tools = body.get("tools", [])
    if not isinstance(tools, list) or any(
        not isinstance(t, dict)
        or t.get("type", "custom") != "custom"
        or t.get("name") not in ("Bash", "Skill")
        or set(t)
        - {
            "name",
            "description",
            "input_schema",
            "cache_control",
            "type",
            "defer_loading",
        }
        for t in tools
    ):
        raise D.BudgetStop("untracked server/helper tool refused")

    def scrub(value):
        if isinstance(value, list):
            return [scrub(v) for v in value]
        if isinstance(value, dict):
            if value.get("type") in (
                "image",
                "document",
                "container_upload",
                "server_tool_use",
                "mcp_tool_use",
                "tool_addition",
                "tool_removal",
                "tool_definition",
                "mcp_tool_reference",
                "mcp_toolset_reference",
            ):
                raise D.BudgetStop("nonlocal or server content refused")
            return {
                k: scrub(v)
                for k, v in value.items()
                if k not in ("cache_control", "defer_loading")
            }
        return value

    # Defense in depth before dispatch, model-specific even for JSON framing.
    # This byte limit is NOT a tokenizer bound. The exposure proof relies on the
    # frozen provider hard context maximum, with no context-expanding capability.
    if (
        len(json.dumps(body, ensure_ascii=False).encode("utf-8"))
        > binding.pricing.max_context_tokens
    ):
        raise D.BudgetStop("request exceeds frozen model admission size")
    result = scrub(body)
    context = result.pop("context_management", None)
    if context not in (
        None,
        {"edits": []},
        {"edits": [{"type": "clear_thinking_20251015", "keep": "all"}]},
    ):
        raise D.BudgetStop("server context edits refused")
    result.pop("metadata", None)
    result["max_tokens"] = min(body["max_tokens"], MAX_OUTPUT)
    thinking = result.get("thinking")
    if isinstance(thinking, dict) and thinking.get("type") == "enabled":
        # Haiku has no interleaved thinking; its budget must fit inside output.
        # The native default is 31999, so clamping output alone made a 400.
        budget = thinking.get("budget_tokens")
        if (
            binding.model != "claude-haiku-4-5-20251001"
            or type(budget) is not int
            or budget < 1024
        ):
            raise D.BudgetStop("unsupported manual thinking budget")
        if result["max_tokens"] <= 1024:
            raise D.BudgetStop("finite output cannot accommodate manual thinking")
        thinking["budget_tokens"] = min(budget, 1024)
    result["stream"] = False
    result["service_tier"] = "standard_only"
    result["inference_geo"] = "global"
    return result


def usage_record(response, binding):
    """Mandatory provider counters; absent optional zero-cache breakdown is proved by zero aggregate."""
    if not isinstance(response, dict) or response.get("model") != binding.model:
        raise D.BudgetStop("API response model mismatch")
    usage = response.get("usage")
    if (
        not isinstance(usage, dict)
        or usage.get("service_tier") != "standard"
        or usage.get("inference_geo") != "global"
    ):
        raise D.BudgetStop("missing API billing scope")
    allowed = {
        "input_tokens",
        "output_tokens",
        "cache_read_input_tokens",
        "cache_creation_input_tokens",
        "cache_creation",
        "service_tier",
        "inference_geo",
        "server_tool_use",
        "iterations",
        "output_tokens_details",
        "speed",
    }
    if set(usage) - allowed:
        raise D.BudgetStop("unknown API usage field")
    if usage.get("speed", "standard") != "standard" or usage.get("iterations") not in (
        None,
        [],
    ):
        raise D.BudgetStop("unsupported API iteration/speed accounting")
    server = usage.get("server_tool_use")
    if server not in (None, {"web_search_requests": 0, "web_fetch_requests": 0}):
        raise D.BudgetStop("server billing refused")
    counters = {
        k: usage.get(k)
        for k in (
            "input_tokens",
            "output_tokens",
            "cache_read_input_tokens",
            "cache_creation_input_tokens",
        )
    }
    if any(type(v) is not int or v < 0 for v in counters.values()):
        raise D.BudgetStop("missing or malformed API usage")
    if (
        counters["cache_creation_input_tokens"] != 0
        or counters["cache_read_input_tokens"] != 0
    ):
        raise D.BudgetStop("unexpected cached request")
    if usage.get("cache_creation") not in (
        None,
        {"ephemeral_5m_input_tokens": 0, "ephemeral_1h_input_tokens": 0},
    ):
        raise D.BudgetStop("unexpected cache breakdown")
    if (
        counters["input_tokens"] > binding.pricing.max_context_tokens
        or counters["output_tokens"] > MAX_OUTPUT
    ):
        raise D.BudgetStop("provider token bound violated")
    counters.update(cache_creation_5m_input_tokens=0, cache_creation_1h_input_tokens=0)
    request_id = response.get("id")
    D._token(request_id)
    return {
        "request_id": request_id,
        "model": binding.model,
        "service_tier": "standard",
        "inference_geo": "global",
        "speed": "standard",
        "server_tool_use": {"web_search_requests": 0, "web_fetch_requests": 0},
        "usage": counters,
    }


class Provider:
    """Parent-only subscription OAuth forwarding, never API-key fallback."""

    def __init__(self):
        if any(
            name in os.environ
            for name in (
                "ANTHROPIC_AUTH_TOKEN",
                "ANTHROPIC_CUSTOM_HEADERS",
                "ANTHROPIC_LOG",
                "ANTHROPIC_BASE_URL",
                "CLAUDE_CODE_USE_BEDROCK",
                "CLAUDE_CODE_USE_VERTEX",
                "CLAUDE_CODE_USE_FOUNDRY",
            )
        ):
            raise D.BudgetStop("ambient alternate route/logging refused")
        # Global threshold covers child loggers and root handlers too. Setting
        # a parent logger's disabled flag does not stop descendant propagation.
        logging.disable(logging.CRITICAL)
        import anthropic

        if anthropic.__version__ != SDK_VERSION:
            raise D.BudgetStop("unreviewed Anthropic SDK version")
        credentials = owner_oauth_environment()
        self.client = anthropic.Anthropic(
            api_key=None,
            auth_token=credentials["CLAUDE_CODE_OAUTH_TOKEN"],
            webhook_key="",
            base_url="https://api.anthropic.com",
            default_headers={
                "anthropic-beta": OAUTH_BETA,
                "X-Api-Key": anthropic.Omit(),
            },
            max_retries=0,
            timeout=45,
            http_client=anthropic.DefaultHttpxClient(
                trust_env=False, follow_redirects=False
            ),
        )

    def available(self, binding):
        # Subscription setup-token scopes permit inference, not a Console
        # Models API preflight. Availability is proved by the bounded call's
        # exact model response; there is no unmetered model launch here.
        binding.validate()
        if binding.contract.authentication != "claude-code-subscription-oauth":
            raise D.BudgetStop("only subscription OAuth is admitted")

    def message(self, request, *, headers=None):
        try:
            beta = capability_header(headers)
            return self.client.messages.create(
                **request, extra_headers={"anthropic-beta": beta}
            ).model_dump(exclude_none=True)
        except Exception as error:
            # Never serialize SDK exception: it can contain headers/request data.
            import anthropic

            if isinstance(error, anthropic.RateLimitError):
                raise RateLimitStop("subscription rate limit; no retry") from None
            if isinstance(error, anthropic.APIStatusError):
                status = error.status_code
                if type(status) is not int or not 100 <= status <= 599:
                    status = None
                category = (
                    "authentication-rejected"
                    if status in (401, 403)
                    else "request-rejected"
                    if status in (400, 404, 422)
                    else "upstream-http-error"
                )
                raise ProviderStop(category, status) from None
            if isinstance(error, anthropic.APIConnectionError):
                raise ProviderStop("transport-failure") from None
            raise ProviderStop("sdk-failure") from None


class Session:
    def __init__(self, binding, call, provider, directory, *, single=False):
        self.binding, self.call, self.provider = binding, call, provider
        self.directory = Path(directory)
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=False)
        self.requests = []
        self.spent = 0
        self.failed = False
        self.revoked = False
        self.single = single
        self.lock = threading.Lock()
        self.refusal = None
        self.request_fields = []
        self.token = secrets.token_hex(32)
        self.rate_limited = False

    def message(self, body, *, headers=None):
        if not self.lock.acquire(blocking=False):
            self.failed = True
            raise D.BudgetStop("concurrent helper refused")
        if self.revoked or self.failed or (self.single and self.requests):
            self.lock.release()
            raise D.BudgetStop("session closed")
        try:
            capability_header(headers)
            request = prepare_request(body, self.binding)
            if self.spent >= D.microdollars(self.binding.session_cap_usd):
                raise D.BudgetStop("session cap reached")
            # Full context-window exposure, not a token-count estimate. One
            # in-flight request only. Crash here retains the whole D reservation.
            index = len(self.requests)
            seal_json(
                self.directory / f"{index:04d}.intent.json",
                {
                    "call_id": self.call.call_id,
                    "model": self.binding.model,
                    "request_sha256": D._digest(request),
                    "bound": request_bound(self.binding),
                },
            )
            response = self.provider.message(request, headers=headers)
            seal_json(
                self.directory / f"{index:04d}.response-usage.json",
                {
                    "id": response.get("id"),
                    "model": response.get("model"),
                    "usage": response.get("usage"),
                },
            )
            record = usage_record(response, self.binding)
            if record["request_id"] in {r["request_id"] for r in self.requests}:
                raise D.BudgetStop("duplicate provider request identity")
            amount = self.binding.pricing.charge(record["usage"])
            if amount > request_bound(self.binding):
                raise D.BudgetStop("request exposure violation")
            seal_json(self.directory / f"{index:04d}.usage.json", record)
            self.requests.append(record)
            self.spent += amount
            return response
        except RateLimitStop:
            self.rate_limited = self.revoked = self.failed = True
            seal_json(
                self.directory / "rate-limit-stop.json",
                {
                    "status": "STOPPED_RATE_LIMIT",
                    "call_id": self.call.call_id,
                    "completed_requests": len(self.requests),
                    "retry_count": 0,
                    "reservation": "retained in full",
                    "equivalent_spent_microdollars": self.spent,
                },
            )
            raise
        except BaseException as error:
            self.failed = self.revoked = True
            seal_json(
                self.directory / "session-stop.json",
                {
                    "call_id": self.call.call_id,
                    "category": error.category
                    if isinstance(error, ProviderStop)
                    else "request-or-accounting-failure",
                    "upstream_status": error.upstream_status
                    if isinstance(error, ProviderStop)
                    else None,
                    "upstream_response_observed": isinstance(error, ProviderStop)
                    and error.upstream_status is not None,
                    "completed_requests": len(self.requests),
                    "intent_count": len(list(self.directory.glob("*.intent.json"))),
                    "delivery": "response observed"
                    if isinstance(error, ProviderStop)
                    and error.upstream_status is not None
                    else "unknown; never infer zero from missing response",
                    "retry_count": 0,
                    "reservation": "retained in full",
                },
            )
            raise
        finally:
            self.lock.release()

    def settlement(
        self, transcript, stop="complete", exit_code=0, *, claude_report=None
    ):
        if self.failed or not self.requests:
            raise D.BudgetStop("incomplete attributable usage; reservation retained")
        proof = self.directory / "proof.json"
        total = {
            key: sum(r["usage"][key] for r in self.requests)
            for key in D.API_USAGE_FIELDS
        }
        reported_cost = usd(self.spent)
        if self.binding.billing == "api-equivalent-usage-usd":
            reported_cost = D.crosscheck_claude_report(
                claude_report, self.binding, total, self.spent, len(self.requests)
            )
        proof_hash = seal_json(
            proof,
            {
                "schema_version": 1,
                "complete": True,
                "call_id": self.call.call_id,
                "binding_id": self.binding.binding_id,
                "pricing_sha256": self.binding.pricing.digest,
                "requests": self.requests,
                "claude_report": claude_report,
            },
        )
        transcript_hash = seal_json(self.directory / "transcript.json", transcript)
        b = self.binding
        return D.Settlement(
            self.call.call_id,
            b.binding_id,
            b.model,
            b.provider,
            b.billing,
            b.evidence_sha256,
            usd(self.spent),
            reported_cost,
            total,
            stop,
            exit_code,
            str(self.directory / "transcript.json"),
            transcript_hash,
            str(proof),
            proof_hash,
        )


def sse(response):
    """Synthesize lossless text/tool stream after complete usage is durable."""

    def event(kind, data):
        return f"event: {kind}\ndata: {json.dumps({'type': kind, **data})}\n\n"

    message = dict(response, content=[], stop_reason=None, stop_sequence=None)
    output = event("message_start", {"message": message})
    for index, block in enumerate(response["content"]):
        if block["type"] == "text":
            output += event(
                "content_block_start",
                {"index": index, "content_block": {"type": "text", "text": ""}},
            )
            output += event(
                "content_block_delta",
                {
                    "index": index,
                    "delta": {"type": "text_delta", "text": block["text"]},
                },
            )
        elif block["type"] == "tool_use":
            output += event(
                "content_block_start",
                {"index": index, "content_block": {**block, "input": {}}},
            )
            output += event(
                "content_block_delta",
                {
                    "index": index,
                    "delta": {
                        "type": "input_json_delta",
                        "partial_json": json.dumps(block["input"]),
                    },
                },
            )
        elif block["type"] == "thinking":
            output += event(
                "content_block_start",
                {"index": index, "content_block": {"type": "thinking", "thinking": ""}},
            )
            output += event(
                "content_block_delta",
                {
                    "index": index,
                    "delta": {"type": "thinking_delta", "thinking": block["thinking"]},
                },
            )
            output += event(
                "content_block_delta",
                {
                    "index": index,
                    "delta": {
                        "type": "signature_delta",
                        "signature": block["signature"],
                    },
                },
            )
        elif block["type"] == "redacted_thinking":
            output += event(
                "content_block_start", {"index": index, "content_block": block}
            )
        else:
            raise D.BudgetStop("unsupported streamed content; usage preserved")
        output += event("content_block_stop", {"index": index})
    output += event(
        "message_delta",
        {
            "delta": {
                "stop_reason": response["stop_reason"],
                "stop_sequence": response.get("stop_sequence"),
            },
            "usage": response["usage"],
        },
    )
    return output + event("message_stop", {})


class Broker:
    def __init__(self, session):
        self.session = session

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def setup(self):
                super().setup()
                self.connection.settimeout(50)

            def do_POST(self):
                try:
                    if not secrets.compare_digest(
                        self.headers.get("X-Api-Key", ""), session.token
                    ):
                        raise D.BudgetStop("stale or foreign broker session")
                    length = int(self.headers.get("Content-Length", "0"))
                    if (
                        not 0 < length <= MAX_BODY
                        or urlsplit(self.path).path != "/v1/messages"
                    ):
                        raise D.BudgetStop("broker endpoint refused")
                    body = json.loads(self.rfile.read(length))
                    session.request_fields = (
                        sorted(body) if isinstance(body, dict) else []
                    )
                    response = session.message(
                        body,
                        headers={
                            "anthropic-beta": self.headers.get("anthropic-beta", "")
                        },
                    )
                    stream = body.get("stream") is True
                    payload = (
                        sse(response) if stream else json.dumps(response)
                    ).encode()
                    self.send_response(200)
                    self.send_header(
                        "Content-Type",
                        "text/event-stream" if stream else "application/json",
                    )
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                except BaseException as exc:
                    session.refusal = (
                        str(exc)
                        if isinstance(exc, D.BudgetStop)
                        else type(exc).__name__
                    )
                    if not session.revoked:
                        session.failed = True
                    payload = json.dumps(
                        {
                            "type": "error",
                            "error": {
                                "type": "invalid_request_error",
                                "message": "joint controller terminal refusal; no retry",
                            },
                        }
                    ).encode()
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(payload)))
                    self.send_header("x-should-retry", "false")
                    self.end_headers()
                    self.wfile.write(payload)

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.server.timeout = 1
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self.server.server_port

    def __exit__(self, *args):
        self.session.revoked = True
        self.server.shutdown()
        self.thread.join()
        self.server.server_close()
