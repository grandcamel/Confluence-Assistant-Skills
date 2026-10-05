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
            ):
                raise D.BudgetStop("nonlocal or server content refused")
            return {
                k: scrub(v)
                for k, v in value.items()
                if k not in ("cache_control", "defer_loading")
            }
        return value

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
    """Only paid runtime reads the key. Explicit endpoint/auth, no proxy/login/retry fallback."""

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
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key or not key.strip():
            raise D.BudgetStop("owner ANTHROPIC_API_KEY missing")
        self.client = anthropic.Anthropic(
            api_key=key,
            auth_token=None,
            webhook_key="",
            base_url="https://api.anthropic.com",
            max_retries=0,
            timeout=45,
            http_client=anthropic.DefaultHttpxClient(
                trust_env=False, follow_redirects=False
            ),
        )

    def available(self, binding):
        try:
            info = self.client.models.retrieve(binding.model).model_dump()
            maximum = info.get("max_input_tokens")
            if (
                info.get("id") != binding.model
                or type(maximum) is not int
                or not 0 < maximum <= binding.pricing.max_context_tokens
            ):
                raise D.BudgetStop("exact model/context availability unproved")
        except Exception:
            raise D.BudgetStop("account/model availability unproved") from None

    def message(self, request):
        try:
            return self.client.messages.create(**request).model_dump(exclude_none=True)
        except Exception:
            # Never serialize SDK exception: it can contain headers/request data.
            raise D.BudgetStop("API failure; charge uncertain") from None


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

    def message(self, body):
        if not self.lock.acquire(blocking=False):
            self.failed = True
            raise D.BudgetStop("concurrent helper refused")
        if self.revoked or self.failed or (self.single and self.requests):
            self.lock.release()
            raise D.BudgetStop("session closed")
        try:
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
            response = self.provider.message(request)
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
        except BaseException:
            self.failed = True
            raise
        finally:
            self.lock.release()

    def settlement(self, transcript, stop="complete", exit_code=0):
        if self.failed or not self.requests:
            raise D.BudgetStop("incomplete attributable usage; reservation retained")
        proof = self.directory / "proof.json"
        proof_hash = seal_json(
            proof,
            {
                "schema_version": 1,
                "complete": True,
                "call_id": self.call.call_id,
                "binding_id": self.binding.binding_id,
                "pricing_sha256": self.binding.pricing.digest,
                "requests": self.requests,
            },
        )
        total = {
            key: sum(r["usage"][key] for r in self.requests)
            for key in D.API_USAGE_FIELDS
        }
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
            usd(self.spent),
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
                    response = session.message(body)
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
                except Exception as exc:
                    session.refusal = (
                        str(exc)
                        if isinstance(exc, D.BudgetStop)
                        else type(exc).__name__
                    )
                    if not session.revoked:
                        session.failed = True
                    self.send_error(403, "joint controller refused request")

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
