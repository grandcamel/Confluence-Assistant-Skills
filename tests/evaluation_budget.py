"""Shared $50 ledger; production admission belongs to the joint controller.

A Binding is a reviewed transport's contract, not proof supplied by the model.
Only that transport may return a Settlement (CLI total_cost_usd is insufficient).
All phases, probes and explicit retry attempts must share one ledger. Never make
one ledger per run. The default harness entry point refuses launch outside its reviewed controller.
"""

import fcntl
import hashlib
import json
import os
import re
import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from decimal import ROUND_CEILING, Decimal, InvalidOperation, localcontext
from pathlib import Path
from typing import Protocol
from uuid import uuid4

CAP = 50_000_000
TOKEN = re.compile(r"[A-Za-z0-9_.:/-]{1,160}\Z")
SHA = re.compile(r"[a-f0-9]{64}\Z")


class BudgetStop(RuntimeError):
    """Acceptance is incomplete, never a model-scoring failure or a skip."""


def microdollars(value: str) -> int:
    """Exact, conservative conversion; never accept a float or a boolean."""
    if not isinstance(value, str) or len(value) > 64:
        raise BudgetStop("cost must be a decimal string")
    try:
        with localcontext() as context:
            context.prec = 80
            amount = Decimal(value)
            if not amount.is_finite() or amount < 0 or amount > 50:
                raise BudgetStop("cost outside budget range")
            if abs(amount.as_tuple().exponent) > 64:
                raise BudgetStop("unsupported cost exponent")
            return int((amount * 1_000_000).to_integral_value(rounding=ROUND_CEILING))
    except InvalidOperation:
        raise BudgetStop("invalid cost") from None


def _token(value: str) -> None:
    if not isinstance(value, str) or not TOKEN.fullmatch(value):
        raise BudgetStop("invalid nonsecret identity")


def _proof(path: str, digest: str) -> None:
    if not isinstance(digest, str) or not SHA.fullmatch(digest):
        raise BudgetStop("invalid evidence digest")
    try:
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest:
            raise BudgetStop("evidence hash mismatch")
    except (OSError, TypeError):
        raise BudgetStop("evidence unavailable") from None


@dataclass(frozen=True)
class LaunchContract:
    """Provider-specific policy. A reviewed transport supplies the enforcement."""

    protocol: str = "offline-fake-v1"
    authentication: str = "none"
    accounting: str = "synthetic-usd"


API_USAGE_FIELDS = frozenset(
    {
        "input_tokens",
        "output_tokens",
        "cache_read_input_tokens",
        "cache_creation_input_tokens",
        "cache_creation_5m_input_tokens",
        "cache_creation_1h_input_tokens",
    }
)
API_PRICE_FIELDS = API_USAGE_FIELDS - {"cache_creation_input_tokens"}


@dataclass(frozen=True)
class ApiPricing:
    """Pinned first-party standard/global prices for actual or equivalent USD.

    Rates are verified USD per million tokens, including both cache-write TTLs.
    The trusted adapter must prove complete attributable API response usage and
    enforce this scope/context limit. No guessed default rates are installed.
    """

    model: str
    rates: tuple[tuple[str, str], ...]
    max_context_tokens: int
    source_url: str
    verified_at: str
    evidence_path: str
    evidence_sha256: str

    def validate(self):
        _token(self.model)
        if (
            not isinstance(self.rates, tuple)
            or any(not isinstance(pair, tuple) or len(pair) != 2 for pair in self.rates)
            or len(self.rates) != len(API_PRICE_FIELDS)
            or {key for key, _ in self.rates} != API_PRICE_FIELDS
        ):
            raise BudgetStop("incomplete API price schedule")
        if (
            type(self.max_context_tokens) is not int
            or not 1 <= self.max_context_tokens <= 1_000_000
        ):
            raise BudgetStop("unproved API context price bound")
        if not isinstance(self.source_url, str) or not self.source_url.startswith(
            "https://platform.claude.com/"
        ):
            raise BudgetStop("unverified API price source")
        if not isinstance(self.verified_at, str) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}", self.verified_at
        ):
            raise BudgetStop("price verification date required")
        for _, value in self.rates:
            if not isinstance(value, str) or len(value) > 32:
                raise BudgetStop("API rate must be a decimal string")
            try:
                amount = Decimal(value)
                if (
                    not amount.is_finite()
                    or amount <= 0
                    or amount > 1_000_000
                    or abs(amount.as_tuple().exponent) > 12
                ):
                    raise BudgetStop("invalid API rate")
            except InvalidOperation:
                raise BudgetStop("invalid API rate") from None
        _proof(self.evidence_path, self.evidence_sha256)

    @property
    def digest(self):
        return _digest(asdict(self))

    def charge(self, usage: dict[str, int]) -> int:
        self.validate()
        if (
            not isinstance(usage, dict)
            or set(usage) != API_USAGE_FIELDS
            or any(
                type(value) is not int or not 0 <= value <= 10**12
                for value in usage.values()
            )
            or usage["cache_creation_input_tokens"]
            != usage["cache_creation_5m_input_tokens"]
            + usage["cache_creation_1h_input_tokens"]
        ):
            raise BudgetStop("incomplete or inconsistent API usage")
        with localcontext() as context:
            context.prec = 160
            dollars = (
                sum(Decimal(rate) * usage[key] for key, rate in self.rates) / 1_000_000
            )
            return microdollars(format(dollars, "f"))


@dataclass(frozen=True)
class Binding:
    """Immutable reviewed route, cap and finite ALL-helper in-flight exposure.

    Proof must cover the price schedule, tools/credential/network containment,
    Bash, hooks, plugins and replay. A string/JSON declaration is not admission.
    """

    binding_id: str
    model: str
    provider: str
    billing: str
    session_cap_usd: str
    inflight_usd: str
    evidence_path: str
    evidence_sha256: str
    contract: LaunchContract = field(default_factory=LaunchContract)
    pricing: ApiPricing | None = None

    @property
    def digest(self):
        return _digest(asdict(self))

    def validate(self) -> int:
        for value in (self.binding_id, self.model, self.provider, self.billing):
            _token(value)
        cap = microdollars(self.session_cap_usd)
        exposure = cap + microdollars(self.inflight_usd)
        if cap == 0 or exposure > CAP:
            raise BudgetStop("unusable cap or in-flight bound")
        if self.provider == "fake":
            if (
                self.contract != LaunchContract()
                or self.billing != "synthetic-usd"
                or self.pricing is not None
            ):
                raise BudgetStop("invalid offline-only fake binding")
        elif self.provider == "anthropic":
            if self.contract not in (
                LaunchContract(
                    "claude-print-v1", "anthropic-api-key", "api-usage-usd-v1"
                ),
                LaunchContract(
                    "claude-print-v1",
                    "claude-code-subscription-oauth",
                    "api-equivalent-usage-usd-v1",
                ),
            ) or (self.contract.authentication, self.billing) not in (
                ("anthropic-api-key", "api-usage-usd"),
                ("claude-code-subscription-oauth", "api-equivalent-usage-usd"),
            ):
                raise BudgetStop(
                    "Claude requires reviewed authentication and token accounting"
                )
            if self.pricing is None or self.pricing.model != self.model:
                raise BudgetStop("API model/price mismatch")
            self.pricing.validate()
        elif self.provider == "openai":
            if (
                self.contract
                != LaunchContract("codex-unadmitted-v1", "unproved", "unproved")
                or self.billing != "unproved"
                or self.pricing is not None
            ):
                raise BudgetStop("unsupported Codex contract")
        else:
            raise BudgetStop("unsupported provider")
        _proof(self.evidence_path, self.evidence_sha256)
        return exposure


def _digest(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _binding_from_dict(data) -> Binding:
    data = dict(data)
    data["contract"] = LaunchContract(**data["contract"])
    if data["pricing"] is not None:
        prices = dict(data["pricing"])
        prices["rates"] = tuple(tuple(pair) for pair in prices["rates"])
        data["pricing"] = ApiPricing(**prices)
    return Binding(**data)


@dataclass(frozen=True)
class Registry:
    """One sealed registry for the whole $50 program; no add/update API.

    Construction and the evidence file are reviewed controller inputs, never
    environment opt-ins. Production transport admission remains separate.
    """

    registry_id: str
    bindings: tuple[Binding, ...]
    evidence_path: str
    evidence_sha256: str

    def validate(self):
        _token(self.registry_id)
        if not isinstance(self.bindings, tuple) or not self.bindings:
            raise BudgetStop("immutable nonempty binding registry required")
        ids = set()
        for binding in self.bindings:
            binding.validate()
            if binding.binding_id in ids:
                raise BudgetStop("duplicate registry binding")
            ids.add(binding.binding_id)
        _proof(self.evidence_path, self.evidence_sha256)

    @property
    def digest(self):
        return _digest(asdict(self))

    def binding(self, binding_id: str) -> Binding:
        for binding in self.bindings:
            if binding.binding_id == binding_id:
                return binding
        raise BudgetStop("route absent from reviewed registry")

    @classmethod
    def from_dict(cls, data):
        return cls(
            data["registry_id"],
            tuple(_binding_from_dict(b) for b in data["bindings"]),
            data["evidence_path"],
            data["evidence_sha256"],
        )


SCHEMA_VERSION = 3


def api_usage_charge(call, binding: Binding, proof_path: str, proof_sha256: str):
    """Compute API usage dollars from the trusted, complete per-request proof.

    This normalizes API cache TTL counters; no CLI dollar estimate is used.
    The adapter owns completeness, attribution and all side-request capture.
    Standard/global, no server tools, and pinned context bounds only.
    """
    binding.validate()
    if binding.provider != "anthropic" or binding.pricing is None:
        raise BudgetStop("not an admitted API-usage accounting basis")
    _proof(proof_path, proof_sha256)
    try:
        proof = json.loads(Path(proof_path).read_text())
        if (
            type(proof["schema_version"]) is not int
            or proof["schema_version"] != 1
            or proof["complete"] is not True
            or proof["call_id"] != call.call_id
            or proof["binding_id"] != binding.binding_id
            or proof["pricing_sha256"] != binding.pricing.digest
            or not isinstance(proof["requests"], list)
            or not proof["requests"]
        ):
            raise BudgetStop("incomplete or mismatched API cost proof")
        total = dict.fromkeys(API_USAGE_FIELDS, 0)
        ids = set()
        charge = 0
        for request in proof["requests"]:
            _token(request["request_id"])
            if request["request_id"] in ids:
                raise BudgetStop("duplicate API usage request")
            ids.add(request["request_id"])
            if (
                request["model"] != binding.model
                or request["service_tier"] != "standard"
                or not (
                    request["inference_geo"] == "global"
                    or (
                        request["inference_geo"] in (None, "not_available")
                        and (
                            (
                                binding.model == "claude-haiku-4-5-20251001"
                                and request.get("billing_scope_basis")
                                == "legacy-model-standard-rates"
                            )
                            or (
                                binding.contract.authentication
                                == "claude-code-subscription-oauth"
                                and request.get("billing_scope_basis")
                                == "oauth-native-default-frozen-rates"
                            )
                        )
                    )
                )
                or request["speed"] != "standard"
                or request["server_tool_use"]
                != {"web_search_requests": 0, "web_fetch_requests": 0}
            ):
                raise BudgetStop("API model or billing scope mismatch")
            usage = request["usage"]
            charge += binding.pricing.charge(usage)
            if charge > CAP:
                raise BudgetStop("API charge exceeds aggregate cap")
            context_tokens = (
                usage["input_tokens"]
                + usage["cache_read_input_tokens"]
                + usage["cache_creation_input_tokens"]
            )
            if context_tokens > binding.pricing.max_context_tokens:
                raise BudgetStop("API context exceeds pinned price scope")
            for key in total:
                total[key] += usage[key]
        if binding.billing == "api-equivalent-usage-usd":
            crosscheck_claude_report(
                proof["claude_report"], binding, total, charge, len(proof["requests"])
            )
        return total, charge
    except (OSError, ValueError, KeyError, TypeError):
        raise BudgetStop("malformed or unavailable API usage proof") from None


def crosscheck_claude_report(report, binding, usage, charge, requests):
    """Require native CLI token totals and cost to agree before OAuth settlement."""
    if not isinstance(report, dict) or report.get("type") != "result":
        raise BudgetStop("missing Claude usage/cost report")
    reported = report.get("usage")
    fields = {
        "input_tokens",
        "output_tokens",
        "cache_read_input_tokens",
        "cache_creation_input_tokens",
    }
    if not isinstance(reported, dict) or any(
        type(reported.get(k)) is not int or reported[k] < 0 or reported[k] != usage[k]
        for k in fields
    ):
        raise BudgetStop("Claude reported usage disagrees with captured requests")
    models = report.get("modelUsage")
    if not isinstance(models, dict) or set(models) != {binding.model}:
        raise BudgetStop("Claude reported untracked model usage")
    per_model = models[binding.model]
    names = {
        "inputTokens": "input_tokens",
        "outputTokens": "output_tokens",
        "cacheReadInputTokens": "cache_read_input_tokens",
        "cacheCreationInputTokens": "cache_creation_input_tokens",
    }
    if not isinstance(per_model, dict) or any(
        type(per_model.get(k)) is not int or per_model[k] != usage[v]
        for k, v in names.items()
    ):
        raise BudgetStop("Claude per-model usage disagrees")
    for value in (report.get("total_cost_usd"), per_model.get("costUSD")):
        if isinstance(value, bool) or not isinstance(value, (str, int, float)):
            raise BudgetStop("missing or malformed Claude equivalent cost")
        try:
            decimal = Decimal(str(value))
            if not decimal.is_finite() or decimal < 0 or decimal > 50:
                raise BudgetStop("malformed Claude equivalent cost")
            # D rounds each request upward to a microdollar. CLI reports raw
            # aggregate floating dollars, so permit only that bounded rounding.
            if abs(decimal * 1_000_000 - charge) > max(1, requests):
                raise BudgetStop("Claude equivalent cost disagrees with frozen rates")
        except InvalidOperation:
            raise BudgetStop("malformed Claude equivalent cost") from None
    return str(report["total_cost_usd"])


@dataclass(frozen=True)
class Call:
    call_id: str
    phase: str
    task: str
    trial: int
    source_commit: str
    attempt: int = 1

    def validate(self) -> None:
        for value in (self.call_id, self.phase, self.task):
            _token(value)
        if not re.fullmatch(r"[a-f0-9]{40}", self.source_commit):
            raise BudgetStop("source commit required")
        if any(type(n) is not int or n < 1 for n in (self.trial, self.attempt)):
            raise BudgetStop("invalid trial or retry attempt")


@dataclass(frozen=True)
class Settlement:
    """Trusted adapter receipt, NOT an unchecked Claude result event.

    Proof is authoritative attributable billing or a conservatively priced
    complete usage record under the Binding's verified schedule.
    """

    call_id: str
    binding_id: str
    model: str
    provider: str
    billing: str
    binding_sha256: str
    actual_usd: str
    reported_cost_usd: str
    usage: dict[str, int]
    stop_reason: str
    exit_code: int
    transcript_path: str
    transcript_sha256: str
    proof_path: str
    proof_sha256: str

    def validate(self, call: Call, binding: Binding) -> int:
        if (
            self.call_id,
            self.binding_id,
            self.model,
            self.provider,
            self.billing,
            self.binding_sha256,
        ) != (
            call.call_id,
            binding.binding_id,
            binding.model,
            binding.provider,
            binding.billing,
            binding.evidence_sha256,
        ):
            raise BudgetStop("receipt route/model/price mismatch")
        _token(self.stop_reason)
        if type(self.exit_code) is not int:
            raise BudgetStop("invalid exit status")
        required = {
            "input_tokens",
            "output_tokens",
            "cache_read_input_tokens",
            "cache_creation_input_tokens",
        }
        if binding.provider == "anthropic":
            required = API_USAGE_FIELDS
        if (
            not isinstance(self.usage, dict)
            or set(self.usage) != required
            or any(type(v) is not int or v < 0 for v in self.usage.values())
        ):
            raise BudgetStop("missing or invalid usage")
        _proof(self.transcript_path, self.transcript_sha256)
        _proof(self.proof_path, self.proof_sha256)
        microdollars(self.reported_cost_usd)
        actual = microdollars(self.actual_usd)
        if binding.provider == "anthropic":
            usage, charge = api_usage_charge(
                call, binding, self.proof_path, self.proof_sha256
            )
            if self.usage != usage or actual != charge:
                raise BudgetStop("API usage dollar amount mismatch")
        return actual


# Schema 3 adds explicit reviewed transitions; schema 2 remains readable only
# as the untouched legacy state. No ordinary read or launch migrates a ledger.
RECOVERY_TRIGGERS = {
    "protected_call_insert": "CREATE TRIGGER protected_call_insert BEFORE INSERT ON calls WHEN EXISTS (SELECT 1 FROM calls c JOIN charged_uncertain u ON c.id=u.call_id WHERE c.id=NEW.id OR c.identity=NEW.identity) BEGIN SELECT RAISE(ABORT, 'charged-uncertain call is immutable'); END",
    "registry_transitions_insert": "CREATE TRIGGER registry_transitions_insert BEFORE INSERT ON registry_transitions WHEN EXISTS (SELECT 1 FROM registry_transitions WHERE seq=NEW.seq OR sha256=NEW.sha256) BEGIN SELECT RAISE(ABORT, 'recovery evidence is append-only'); END",
    "charged_uncertain_insert": "CREATE TRIGGER charged_uncertain_insert BEFORE INSERT ON charged_uncertain WHEN EXISTS (SELECT 1 FROM charged_uncertain WHERE call_id=NEW.call_id) BEGIN SELECT RAISE(ABORT, 'recovery evidence is append-only'); END",
    "protected_call_update": "CREATE TRIGGER protected_call_update BEFORE UPDATE ON calls WHEN OLD.id IN (SELECT call_id FROM charged_uncertain) OR EXISTS (SELECT 1 FROM calls c JOIN charged_uncertain u ON c.id=u.call_id WHERE c.id=NEW.id OR c.identity=NEW.identity) BEGIN SELECT RAISE(ABORT, 'charged-uncertain call is immutable'); END",
    "protected_call_delete": "CREATE TRIGGER protected_call_delete BEFORE DELETE ON calls WHEN OLD.id IN (SELECT call_id FROM charged_uncertain) BEGIN SELECT RAISE(ABORT, 'charged-uncertain call is immutable'); END",
    **{
        f"{table}_{operation}": f"CREATE TRIGGER {table}_{operation} BEFORE {operation.upper()} ON {table} BEGIN SELECT RAISE(ABORT, 'recovery evidence is append-only'); END"
        for table in ("registry_transitions", "charged_uncertain")
        for operation in ("update", "delete")
    },
}


# Additive guards only at commissioned link3; old schemas/guard definitions stay
# byte-identical. Derive settled IDs/identities from the append-only sealed record.
SETTLED_TRIGGERS = {
    f"historical_settled_{operation}": f"CREATE TRIGGER historical_settled_{operation} BEFORE {operation.upper()} ON calls WHEN EXISTS (SELECT 1 FROM calls c, registry_transitions t, json_each(t.payload, '$.expected_calls') e WHERE t.seq=3 AND json_extract(e.value, '$.accounting_status')='settled' AND c.id=json_extract(e.value, '$.call_id') AND ({predicate})) BEGIN SELECT RAISE(ABORT, 'historical settlement is immutable'); END"
    for operation, predicate in (
        ("insert", "c.id=NEW.id OR c.identity=NEW.identity"),
        ("update", "c.id=OLD.id OR c.id=NEW.id OR c.identity=NEW.identity"),
        ("delete", "c.id=OLD.id"),
    )
}


def _recovery_schema(db):
    db.execute(
        "CREATE TABLE registry_transitions (seq INTEGER PRIMARY KEY, payload TEXT NOT NULL, sha256 TEXT UNIQUE NOT NULL)"
    )
    db.execute(
        "CREATE TABLE charged_uncertain (call_id TEXT PRIMARY KEY, payload_sha256 TEXT NOT NULL, amount INTEGER NOT NULL, transition_sha256 TEXT NOT NULL)"
    )
    for sql in RECOVERY_TRIGGERS.values():
        db.execute(sql)


def _raw_sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def _reviewed_recovery_plan(path, sha256, ledger_path, new_registry):
    try:
        return _parse_recovery_plan(path, sha256, ledger_path, new_registry)
    except (OSError, ValueError, KeyError, TypeError):
        raise BudgetStop("invalid or unavailable recovery plan") from None


def _parse_recovery_plan(path, sha256, ledger_path, new_registry):
    _proof(str(path), sha256)
    plan = json.loads(Path(path).read_text())
    required = {
        "schema_version",
        "transition_id",
        "ledger_path",
        "expected_ledger_sha256",
        "expected_metadata_sha256",
        "old_registry_sha256",
        "new_registry_sha256",
        "call",
        "initialization_marker",
        "evidence_directory",
        "evidence",
        "provenance",
    }
    if isinstance(plan, dict) and plan.get("schema_version") in (2, 3):
        required |= {
            "original_registry_sha256",
            "previous_transition",
            "expected_calls",
            "expected_charges",
            "expected_exposure_microdollars",
        }
    if isinstance(plan, dict) and plan.get("schema_version") == 3:
        required.add("retry")
    if (
        not isinstance(plan, dict)
        or set(plan) != required
        or type(plan["schema_version"]) is not int
        or plan["schema_version"] not in (1, 2, 3)
    ):
        raise BudgetStop("unsupported recovery plan")
    _token(plan["transition_id"])
    if (
        plan["ledger_path"] != str(ledger_path)
        or plan["new_registry_sha256"] != new_registry.digest
    ):
        raise BudgetStop("recovery ledger or target registry mismatch")
    for name in (
        "expected_ledger_sha256",
        "expected_metadata_sha256",
        "old_registry_sha256",
        "new_registry_sha256",
    ):
        if not isinstance(plan[name], str) or not SHA.fullmatch(plan[name]):
            raise BudgetStop("invalid recovery seal")
    call = plan["call"]
    if not isinstance(call, dict) or set(call) != {
        "call_id",
        "identity_sha256",
        "payload_sha256",
        "reservation_microdollars",
    }:
        raise BudgetStop("invalid charged call declaration")
    _token(call["call_id"])
    if (
        any(
            not isinstance(call[key], str) or not SHA.fullmatch(call[key])
            for key in ("identity_sha256", "payload_sha256")
        )
        or type(call["reservation_microdollars"]) is not int
        or not 0 < call["reservation_microdollars"] <= CAP
    ):
        raise BudgetStop("invalid conservative charge")
    marker = plan["initialization_marker"]
    if (
        not isinstance(marker, dict)
        or set(marker) != {"path", "sha256"}
        or marker["path"] != str(ledger_path.with_suffix(".init.json"))
    ):
        raise BudgetStop("recovery initialization marker mismatch")
    _proof(marker["path"], marker["sha256"])
    original_init = json.loads(Path(marker["path"]).read_text())
    if (
        set(original_init) != {"registry_sha256", "prior_sha256"}
        or original_init["registry_sha256"]
        != plan.get("original_registry_sha256", plan["old_registry_sha256"])
        or not SHA.fullmatch(original_init["prior_sha256"])
    ):
        raise BudgetStop("original initialization provenance mismatch")
    if plan["schema_version"] in (2, 3):
        prior = plan["previous_transition"]
        if (
            not isinstance(plan["original_registry_sha256"], str)
            or not SHA.fullmatch(plan["original_registry_sha256"])
            or not isinstance(prior, dict)
            or set(prior) != {"sequence", "record_sha256", "payload_sha256"}
            or type(prior["sequence"]) is not int
            or prior["sequence"] != plan["schema_version"] - 1
            or any(
                not isinstance(prior[k], str) or not SHA.fullmatch(prior[k])
                for k in ("record_sha256", "payload_sha256")
            )
        ):
            raise BudgetStop("invalid previous transition seal")
        inventory = plan["expected_calls"]
        charges = plan["expected_charges"]
        if (
            not isinstance(inventory, list)
            or len(inventory) != (2 if plan["schema_version"] == 2 else 4)
            or any(
                not isinstance(item, dict)
                or set(item)
                != {
                    "call_id",
                    "identity_sha256",
                    "payload_sha256",
                    "reservation_microdollars",
                    "accounting_status",
                }
                | ({"actual_microdollars"} if plan["schema_version"] == 3 else set())
                for item in inventory
            )
            or len({item["call_id"] for item in inventory}) != len(inventory)
            or {item["accounting_status"] for item in inventory}
            != (
                {"charged-uncertain", "uncertain"}
                if plan["schema_version"] == 2
                else {"charged-uncertain", "uncertain", "settled"}
            )
        ):
            raise BudgetStop("closed two-call inventory required")
        for item in inventory:
            _token(item["call_id"])
            if (
                any(
                    not isinstance(item[k], str) or not SHA.fullmatch(item[k])
                    for k in ("identity_sha256", "payload_sha256")
                )
                or type(item["reservation_microdollars"]) is not int
                or not 0 < item["reservation_microdollars"] <= CAP
            ):
                raise BudgetStop("invalid closed inventory")
        target = next(
            item for item in inventory if item["accounting_status"] == "uncertain"
        )
        if {
            k: v
            for k, v in target.items()
            if k not in {"accounting_status", "actual_microdollars"}
        } != call:
            raise BudgetStop("charged target differs from inventory")
        if plan["schema_version"] == 2:
            if (
                not isinstance(charges, list)
                or len(charges) != 1
                or not isinstance(charges[0], dict)
                or set(charges[0])
                != {"call_id", "payload_sha256", "amount", "transition_sha256"}
            ):
                raise BudgetStop("exact historical charge required")
            protected = next(
                item
                for item in inventory
                if item["accounting_status"] == "charged-uncertain"
            )
            if (
                charges[0]
                != {
                    "call_id": protected["call_id"],
                    "payload_sha256": protected["payload_sha256"],
                    "amount": protected["reservation_microdollars"],
                    "transition_sha256": prior["record_sha256"],
                }
                or type(plan["expected_exposure_microdollars"]) is not int
                or plan["expected_exposure_microdollars"]
                != sum(item["reservation_microdollars"] for item in inventory)
                or plan["expected_exposure_microdollars"] > CAP
            ):
                raise BudgetStop("historical charge or exposure differs")
        else:
            if (
                sum(i["accounting_status"] == "charged-uncertain" for i in inventory)
                != 2
                or sum(i["accounting_status"] == "uncertain" for i in inventory) != 1
                or sum(i["accounting_status"] == "settled" for i in inventory) != 1
                or not isinstance(charges, list)
                or len(charges) != 2
                or any(
                    not isinstance(c, dict)
                    or set(c)
                    != {"call_id", "payload_sha256", "amount", "transition_sha256"}
                    for c in charges
                )
            ):
                raise BudgetStop("exact third recovery inventory required")
            by_id = {
                i["call_id"]: i
                for i in inventory
                if i["accounting_status"] == "charged-uncertain"
            }
            if {c["call_id"] for c in charges} != set(by_id):
                raise BudgetStop("historical charges differ")
            for charge in charges:
                original = by_id[charge["call_id"]]
                if (
                    charge["payload_sha256"] != original["payload_sha256"]
                    or charge["amount"] != original["reservation_microdollars"]
                    or not isinstance(charge["transition_sha256"], str)
                    or not SHA.fullmatch(charge["transition_sha256"])
                ):
                    raise BudgetStop("historical charge seal differs")
            for item in inventory:
                actual = item["actual_microdollars"]
                if item["accounting_status"] == "settled":
                    if (
                        type(actual) is not int
                        or not 0 <= actual <= item["reservation_microdollars"]
                    ):
                        raise BudgetStop("invalid historical actual usage")
                elif actual is not None:
                    raise BudgetStop("unexpected historical actual usage")
            expected = sum(
                i["actual_microdollars"]
                if i["accounting_status"] == "settled"
                else i["reservation_microdollars"]
                for i in inventory
            )
            if (
                type(plan["expected_exposure_microdollars"]) is not int
                or plan["expected_exposure_microdollars"] != expected
                or expected > CAP
            ):
                raise BudgetStop("third recovery exposure differs")
            if plan["retry"] != {
                "binding_id": "plugin-sonnet5-api",
                "phase": "sufficiency",
                "task": "read-page",
                "trial": 1,
                "from_attempt": 1,
                "to_attempt": 2,
            }:
                raise BudgetStop("only commissioned read-page attempt2 allowed")
    folder = Path(plan["evidence_directory"])
    if not folder.is_absolute() or folder.resolve() != folder or not folder.is_dir():
        raise BudgetStop("original evidence directory unavailable")
    entries = list(folder.rglob("*"))
    if any(
        entry.is_symlink() or (not entry.is_file() and not entry.is_dir())
        for entry in entries
    ):
        raise BudgetStop("original evidence alias or special file refused")
    manifest = plan["evidence"]
    if (
        not isinstance(manifest, list)
        or not manifest
        or any(
            not isinstance(item, dict) or set(item) != {"path", "sha256"}
            for item in manifest
        )
    ):
        raise BudgetStop("complete original evidence manifest required")
    actual_paths = {str(entry) for entry in entries if entry.is_file()}
    if (
        len(manifest) != len(actual_paths)
        or {item["path"] for item in manifest} != actual_paths
    ):
        raise BudgetStop("original evidence manifest differs")
    for item in manifest:
        _proof(item["path"], item["sha256"])
    provenance = plan["provenance"]
    if (
        not isinstance(provenance, dict)
        or set(provenance) != {"owner_authority", "source_heads", "reviews"}
        or provenance["owner_authority"]
        != "c-i conservative charged recovery commissioned by dispatch owner 2026-10-05"
    ):
        raise BudgetStop("reviewed recovery authority required")
    heads = provenance["source_heads"]
    if (
        not isinstance(heads, dict)
        or set(heads) != {"plugin", "floor"}
        or any(
            not isinstance(head, str) or not re.fullmatch(r"[a-f0-9]{40}", head)
            for head in heads.values()
        )
    ):
        raise BudgetStop("recovery source provenance required")
    reviews = provenance["reviews"]
    if (
        not isinstance(reviews, list)
        or len(reviews) != 3
        or any(
            not isinstance(review, dict) or set(review) != {"lens", "path", "sha256"}
            for review in reviews
        )
        or {review["lens"] for review in reviews}
        != {"Spec", "Standards/privacy", "RISK"}
    ):
        raise BudgetStop("three recovery review receipts required")
    for review in reviews:
        _proof(review["path"], review["sha256"])
        body = Path(review["path"]).read_text()
        lines = body.strip().splitlines()
        if (
            not lines
            or lines[0] != "Verdict: PASS"
            or f"Plugin head: {heads['plugin']}" not in lines
            or f"Floor head: {heads['floor']}" not in lines
        ):
            raise BudgetStop("recovery review/source mismatch")
    return plan


def _same_economics(old, new):
    def terms(registry):
        values = []
        for binding in registry.bindings:
            value = asdict(binding)
            value.pop("evidence_path")
            value.pop("evidence_sha256")
            if value["pricing"] is not None:
                value["pricing"].pop("evidence_path")
                value["pricing"].pop("evidence_sha256")
            values.append(value)
        return sorted(values, key=lambda value: value["binding_id"])

    if terms(old) != terms(new):
        raise BudgetStop("recovery cannot change financial terms or routes")


def _transition_record(
    plan_path, plan_sha256, plan, old_metadata_payload, new_registry
):
    old_meta = json.loads(old_metadata_payload)
    if (
        _raw_sha(old_metadata_payload) != plan["expected_metadata_sha256"]
        or old_meta["version"] != (2 if plan["schema_version"] == 1 else 3)
        or old_meta["cap"] != CAP
        or old_meta["halted"] is not True
        or old_meta["registry_sha256"] != plan["old_registry_sha256"]
    ):
        raise BudgetStop("original recovery metadata mismatch")
    old_registry = Registry.from_dict(old_meta["registry"])
    old_registry.validate()
    if old_registry.digest != plan["old_registry_sha256"]:
        raise BudgetStop("original recovery registry mismatch")
    _same_economics(old_registry, new_registry)
    second = plan["schema_version"] >= 2
    if (
        second
        and old_meta.get("transition_head")
        != plan["previous_transition"]["record_sha256"]
    ):
        raise BudgetStop("historical metadata transition head differs")
    record = {
        "schema_version": plan["schema_version"],
        "sequence": plan["schema_version"],
        "previous_hash": plan["previous_transition"]["record_sha256"]
        if second
        else plan["expected_metadata_sha256"],
        "transition_id": plan["transition_id"],
        "from_registry_sha256": old_registry.digest,
        "to_registry_sha256": new_registry.digest,
        "old_metadata_payload": old_metadata_payload,
        "new_registry": asdict(new_registry),
        "plan": {"path": str(plan_path), "sha256": plan_sha256},
        "provenance": plan["provenance"],
        "charged_calls": [plan["call"]],
        "charge_status": "charged-uncertain",
        "consumed_exposure_microdollars": plan["call"]["reservation_microdollars"],
        "aggregate_cap_microdollars": CAP,
        "basis": "entire original reservation permanently consumed; actual usage unknown; never refunded",
    }
    if second:
        record.update(
            previous_transition=plan["previous_transition"],
            expected_calls=plan["expected_calls"],
            expected_charges=plan["expected_charges"],
            original_registry_sha256=plan["original_registry_sha256"],
            cumulative_consumed_exposure_microdollars=plan[
                "expected_exposure_microdollars"
            ],
        )
    if plan["schema_version"] == 3:
        record["retry"] = plan["retry"]
        record["cumulative_consumed_exposure_microdollars"] = sum(
            i["reservation_microdollars"]
            for i in plan["expected_calls"]
            if i["accounting_status"] != "settled"
        )
    return record


class Ledger:
    """Durable SQLite transactions; explicit initialization, no reset API.

    Use a trusted local directory outside child access. A missing, corrupt or
    incompatible ledger is an error, never an invitation to start at zero.
    SQLite FULL sync establishes local persistence, not hostile-host custody.
    """

    def __init__(self, path: Path):
        self.path = path.resolve()

    @classmethod
    def create(cls, path: Path, registry: Registry | Binding) -> "Ledger":
        if isinstance(registry, Binding):
            if registry.provider != "fake":
                raise BudgetStop(
                    "production ledger requires reviewed aggregate registry"
                )
            registry = Registry(
                "single-fake-test",
                (registry,),
                registry.evidence_path,
                registry.evidence_sha256,
            )
        registry.validate()
        # O_EXCL prevents simultaneous initialization or accidental reset.
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        ledger = cls(path)
        with sqlite3.connect(ledger.path) as db:
            db.execute("PRAGMA synchronous=FULL")
            db.execute(
                "CREATE TABLE metadata (id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL)"
            )
            db.execute(
                "CREATE TABLE calls (id TEXT PRIMARY KEY, identity TEXT UNIQUE NOT NULL, payload TEXT NOT NULL)"
            )
            _recovery_schema(db)
            db.execute(
                "INSERT INTO metadata VALUES (1, ?)",
                (
                    json.dumps(
                        {
                            "version": SCHEMA_VERSION,
                            "cap": CAP,
                            "registry": asdict(registry),
                            "registry_sha256": registry.digest,
                            "halted": False,
                            "transition_head": None,
                        }
                    ),
                ),
            )
        directory = os.open(ledger.path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        return ledger

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        try:
            db = sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True, timeout=5)
            try:
                db.execute("PRAGMA synchronous=FULL")
                db.execute("BEGIN IMMEDIATE")
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise
            finally:
                db.close()
        except (sqlite3.Error, ValueError, KeyError, TypeError):
            raise BudgetStop("invalid or unavailable budget ledger") from None

    def _read(self, db):
        meta = json.loads(
            db.execute("SELECT payload FROM metadata WHERE id=1").fetchone()[0]
        )
        if (
            type(meta["version"]) is not int
            or meta["version"] not in (2, SCHEMA_VERSION)
            or meta["cap"] != CAP
            or type(meta["halted"]) is not bool
        ):
            raise BudgetStop(
                "unsupported ledger schema/contract; no automatic migration or reset"
            )
        registry = Registry.from_dict(meta["registry"])
        registry.validate()
        if registry.digest != meta["registry_sha256"]:
            raise BudgetStop("registry seal mismatch")
        protected = self._charged_projection(db, meta, registry)
        records = []
        exposure = 0
        for row_id, identity, payload in db.execute(
            "SELECT id, identity, payload FROM calls ORDER BY id"
        ):
            row = json.loads(payload)
            call = Call(**row["call"])
            call.validate()
            protection = protected.get(row_id)
            if protection is not None:
                if (
                    _raw_sha(payload) != protection["payload_sha256"]
                    or _raw_sha(identity) != protection["identity_sha256"]
                ):
                    raise BudgetStop("protected original call bytes changed")
                binding = protection["registry"].binding(row["binding_id"])
            else:
                binding = registry.binding(row["binding_id"])
            if (
                protection is not None
                and protection.get("kind") == "settled"
                and row["status"] != "settled"
            ):
                raise BudgetStop("historical settlement status differs")
            bound = binding.validate()
            if row["binding_sha256"] != binding.digest:
                raise BudgetStop("per-call binding seal mismatch")
            if (
                row_id != call.call_id
                or type(row["reservation"]) is not int
                or identity != self._identity(call, binding.binding_id)
                or row["reservation"] != bound
            ):
                raise BudgetStop("invalid reservation")
            if row["status"] == "settled":
                actual = Settlement(**row["receipt"]).validate(call, binding)
                if (
                    actual > bound
                    or type(row["actual"]) is not int
                    or row["actual"] != actual
                ):
                    raise BudgetStop("invalid settlement")
                exposure += actual
            elif (
                row["status"] in {"reserved", "uncertain"}
                and row["actual"] is None
                and row["receipt"] is None
            ):
                exposure += bound
            else:
                raise BudgetStop("invalid call state")
            if row["partial_receipt"] is not None:
                partial_actual = Settlement(**row["partial_receipt"]).validate(
                    call, binding
                )
                if partial_actual > bound:
                    raise BudgetStop("partial receipt exceeds reservation")
            if row["outcome"] is not None:
                _proof(row["outcome"]["path"], row["outcome"]["sha256"])
            if row["fingerprint"] and not SHA.fullmatch(row["fingerprint"]):
                raise BudgetStop("invalid execution fingerprint")
            if protection is not None and protection.get("kind") != "settled":
                if (
                    row["status"] != "uncertain"
                    or row["stop_reason"] != "interrupted"
                    or row["reservation"] != protection["reservation_microdollars"]
                ):
                    raise BudgetStop("protected original charge state changed")
                row = {
                    **row,
                    "status": "charged-uncertain",
                    "consumed_exposure_microdollars": bound,
                    "recovery_record_sha256": protection["transition_sha256"],
                }
            records.append(row)
        if set(protected) - {row["call"]["call_id"] for row in records}:
            raise BudgetStop("orphan charged-uncertain mapping")
        if exposure > CAP:
            raise BudgetStop("ledger exceeds aggregate cap")
        return meta, records, exposure

    def _charged_projection(self, db, meta, registry):
        tables = {
            name
            for (name,) in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        if meta["version"] == 2:
            if tables != {"metadata", "calls"} or "transition_head" in meta:
                raise BudgetStop("legacy recovery schema differs")
            return {}
        if (
            tables != {"metadata", "calls", "registry_transitions", "charged_uncertain"}
            or "transition_head" not in meta
        ):
            raise BudgetStop("recovery schema incomplete")
        triggers = dict(
            db.execute("SELECT name, sql FROM sqlite_master WHERE type='trigger'")
        )
        transitions = list(
            db.execute(
                "SELECT seq, payload, sha256 FROM registry_transitions ORDER BY seq"
            )
        )
        charges = list(
            db.execute(
                "SELECT call_id, payload_sha256, amount, transition_sha256 FROM charged_uncertain ORDER BY call_id"
            )
        )
        expected_guards = RECOVERY_TRIGGERS | (
            SETTLED_TRIGGERS if len(transitions) == 3 else {}
        )
        if triggers != expected_guards:
            raise BudgetStop("immutable recovery guards differ")
        if not transitions:
            if meta["transition_head"] is not None or charges:
                raise BudgetStop("orphan recovery state")
            return {}
        # Only the three owner-commissioned recovery transitions.
        if len(transitions) > 3 or [entry[0] for entry in transitions] != list(
            range(1, len(transitions) + 1)
        ):
            raise BudgetStop("unsupported registry transition chain")
        protected = {}
        preserved_settled = {}
        root_registry = None
        expected_charges = []
        previous_record = previous_payload = previous_sha = None
        for sequence, payload, sha256 in transitions:
            record = json.loads(payload)
            historical_target = Registry.from_dict(record["new_registry"])
            historical_target.validate()
            if _digest(record) != sha256:
                raise BudgetStop("registry transition hash chain differs")
            ref = record["plan"]
            plan = _reviewed_recovery_plan(
                ref["path"], ref["sha256"], self.path, historical_target
            )
            if plan["schema_version"] != sequence:
                raise BudgetStop("transition format/order differs")
            expected = _transition_record(
                ref["path"],
                ref["sha256"],
                plan,
                record["old_metadata_payload"],
                historical_target,
            )
            if _digest(expected) != sha256:
                raise BudgetStop("registry transition provenance differs")
            if sequence == 1:
                root_registry = record["from_registry_sha256"]
            if sequence >= 2:
                if (
                    plan["previous_transition"]
                    != {
                        "sequence": sequence - 1,
                        "record_sha256": previous_sha,
                        "payload_sha256": _raw_sha(previous_payload),
                    }
                    or record["previous_hash"] != previous_sha
                    or record["from_registry_sha256"]
                    != previous_record["to_registry_sha256"]
                    or plan["expected_charges"]
                    != sorted(expected_charges, key=lambda i: i["call_id"])
                    or plan["original_registry_sha256"] != root_registry
                ):
                    raise BudgetStop("historical transition link differs")
                for prior_call in (
                    i
                    for i in plan["expected_calls"]
                    if i["accounting_status"] == "charged-uncertain"
                ):
                    known = protected.get(prior_call["call_id"])
                    if known is None or any(
                        prior_call[k] != known[k]
                        for k in (
                            "identity_sha256",
                            "payload_sha256",
                            "reservation_microdollars",
                        )
                    ):
                        raise BudgetStop("historical inventory differs")
                if sequence == 3:
                    item = next(
                        i
                        for i in plan["expected_calls"]
                        if i["accounting_status"] == "settled"
                    )
                    if item["call_id"] in protected:
                        raise BudgetStop("settlement conflicts with permanent charge")
                    preserved_settled[item["call_id"]] = {
                        **item,
                        "kind": "settled",
                        "registry": Registry.from_dict(
                            json.loads(record["old_metadata_payload"])["registry"]
                        ),
                    }
            call = plan["call"]
            if call["call_id"] in protected:
                raise BudgetStop("duplicate permanent charge")
            expected_charges.append(
                {
                    "call_id": call["call_id"],
                    "payload_sha256": call["payload_sha256"],
                    "amount": call["reservation_microdollars"],
                    "transition_sha256": sha256,
                }
            )
            protected[call["call_id"]] = {
                **call,
                "registry": Registry.from_dict(
                    json.loads(record["old_metadata_payload"])["registry"]
                ),
                "transition_sha256": sha256,
            }
            previous_record, previous_payload, previous_sha = record, payload, sha256
        expected_sql = sorted(
            (
                item["call_id"],
                item["payload_sha256"],
                item["amount"],
                item["transition_sha256"],
            )
            for item in expected_charges
        )
        if charges != expected_sql:
            raise BudgetStop("charged-uncertain mapping differs")
        if (
            meta["transition_head"] != previous_sha
            or registry.digest != previous_record["to_registry_sha256"]
        ):
            raise BudgetStop("active registry/transition head differs")
        return protected | preserved_settled

    def recover_and_transition(
        self, plan_path: Path, plan_sha256: str, registry: Registry
    ):
        """Explicit reviewed, atomic recovery; full legacy charge is irreversible.

        Caller holds controller/joint locks. No API credential or provider is
        involved. The legacy call bytes and init marker are never rewritten.
        SQLite hot-journal rollback is allowed before first-state verification;
        WAL/SHM recovery is outside this narrowly reviewed delete-journal route.
        """
        registry.validate()
        plan = _reviewed_recovery_plan(plan_path, plan_sha256, self.path, registry)
        if any(Path(str(self.path) + suffix).exists() for suffix in ("-wal", "-shm")):
            raise BudgetStop("WAL recovery is not admitted")
        with self._transaction() as db:
            if db.execute("PRAGMA journal_mode").fetchone()[0] != "delete":
                raise BudgetStop("unsupported recovery journal mode")
            meta, rows, exposure = self._read(db)
            existing = (
                list(
                    db.execute(
                        "SELECT seq,payload,sha256 FROM registry_transitions ORDER BY seq"
                    )
                )
                if meta["version"] == 3
                else []
            )
            if existing:
                tail = json.loads(existing[-1][1])
                if (
                    tail["plan"] == {"path": str(plan_path), "sha256": plan_sha256}
                    and meta["registry_sha256"] == registry.digest
                ):
                    consumed = sum(
                        item[0]
                        for item in db.execute("SELECT amount FROM charged_uncertain")
                    )
                    return {
                        "already_applied": True,
                        "registry_sha256": registry.digest,
                        "transition_sha256": meta["transition_head"],
                        "charged_uncertain_microdollars": consumed,
                        "newly_consumed_microdollars": 0,
                        "cumulative_consumed_microdollars": consumed,
                        "exposure_microdollars": exposure,
                        "halted": meta["halted"],
                    }
                if (
                    plan["schema_version"] not in (2, 3)
                    or len(existing) != plan["schema_version"] - 1
                ):
                    raise BudgetStop("conflicting duplicate recovery")
            if plan["schema_version"] == 1:
                if meta["version"] != 2 or meta["halted"] is not True or len(rows) != 1:
                    raise BudgetStop(
                        "recovery requires the exact exclusive legacy halt"
                    )
            else:
                if (
                    meta["version"] != 3
                    or meta["halted"] is not True
                    or len(existing) != plan["schema_version"] - 1
                    or len(rows) != (2 if plan["schema_version"] == 2 else 4)
                    or exposure != plan["expected_exposure_microdollars"]
                ):
                    raise BudgetStop(
                        "recovery requires the exact second-transition halt"
                    )
                seq, payload, previous_sha = existing[-1]
                if plan["previous_transition"] != {
                    "sequence": seq,
                    "record_sha256": previous_sha,
                    "payload_sha256": _raw_sha(payload),
                }:
                    raise BudgetStop("prior transition seal differs")
                actual_charges = [
                    {
                        "call_id": i,
                        "payload_sha256": p,
                        "amount": a,
                        "transition_sha256": t,
                    }
                    for i, p, a, t in db.execute(
                        "SELECT * FROM charged_uncertain ORDER BY call_id"
                    )
                ]
                if actual_charges != plan["expected_charges"]:
                    raise BudgetStop("preexisting charge differs")
                statuses = {row["call"]["call_id"]: row["status"] for row in rows}
                actual_inventory = [
                    {
                        "call_id": i,
                        "identity_sha256": _raw_sha(identity),
                        "payload_sha256": _raw_sha(payload),
                        "reservation_microdollars": json.loads(payload)["reservation"],
                        "accounting_status": statuses[i],
                    }
                    | (
                        {"actual_microdollars": json.loads(payload)["actual"]}
                        if plan["schema_version"] == 3
                        else {}
                    )
                    for i, identity, payload in db.execute(
                        "SELECT * FROM calls ORDER BY id"
                    )
                ]
                if actual_inventory != sorted(
                    plan["expected_calls"], key=lambda item: item["call_id"]
                ):
                    raise BudgetStop("closed recovery inventory differs")
            # Do not reapply this hash once committed: legitimate later calls
            # change DB bytes, but the permanent record/row/evidence seals remain.
            _proof(str(self.path), plan["expected_ledger_sha256"])
            raw_metadata = db.execute(
                "SELECT payload FROM metadata WHERE id=1"
            ).fetchone()[0]
            call = plan["call"]
            row = next(row for row in rows if row["call"]["call_id"] == call["call_id"])
            if plan["schema_version"] == 3:
                retry = plan["retry"]
                original_call = Call(**row["call"])
                if (
                    row["binding_id"],
                    original_call.phase,
                    original_call.task,
                    original_call.trial,
                    original_call.attempt,
                ) != (
                    retry["binding_id"],
                    retry["phase"],
                    retry["task"],
                    retry["trial"],
                    retry["from_attempt"],
                ):
                    raise BudgetStop(
                        "third recovery target differs from commissioned retry"
                    )
            raw_id, raw_identity, raw_payload = db.execute(
                "SELECT id, identity, payload FROM calls WHERE id=?", (call["call_id"],)
            ).fetchone()
            if (
                raw_id != call["call_id"]
                or _raw_sha(raw_identity) != call["identity_sha256"]
                or _raw_sha(raw_payload) != call["payload_sha256"]
                or row["status"] != "uncertain"
                or row["stop_reason"] != "interrupted"
                or row["actual"] is not None
                or row["receipt"] is not None
                or row["partial_receipt"] is not None
                or row["outcome"] is not None
                or row["reservation"] != call["reservation_microdollars"]
                or exposure
                != (
                    call["reservation_microdollars"]
                    if plan["schema_version"] == 1
                    else plan["expected_exposure_microdollars"]
                )
            ):
                raise BudgetStop("original uncertain call differs")
            record = _transition_record(
                plan_path, plan_sha256, plan, raw_metadata, registry
            )
            sha256 = _digest(record)
            if plan["schema_version"] == 1:
                _recovery_schema(db)
            db.execute(
                "INSERT INTO registry_transitions VALUES (?, ?, ?)",
                (record["sequence"], json.dumps(record, sort_keys=True), sha256),
            )
            db.execute(
                "INSERT INTO charged_uncertain VALUES (?, ?, ?, ?)",
                (
                    raw_id,
                    call["payload_sha256"],
                    call["reservation_microdollars"],
                    sha256,
                ),
            )
            if plan["schema_version"] == 3:
                for sql in SETTLED_TRIGGERS.values():
                    db.execute(sql)
            updated = {
                **meta,
                "version": SCHEMA_VERSION,
                "registry": asdict(registry),
                "registry_sha256": registry.digest,
                "halted": False,
                "transition_head": sha256,
            }
            db.execute(
                "UPDATE metadata SET payload=? WHERE id=1", (json.dumps(updated),)
            )
            after_meta, after_rows, after_exposure = self._read(db)
            if after_exposure != exposure or any(
                row["status"] not in {"charged-uncertain", "settled"}
                for row in after_rows
            ):
                raise BudgetStop("recovery conservation check failed")
            consumed = sum(
                i[0] for i in db.execute("SELECT amount FROM charged_uncertain")
            )
            return {
                "already_applied": False,
                "registry_sha256": registry.digest,
                "transition_sha256": sha256,
                "charged_uncertain_microdollars": consumed,
                "newly_consumed_microdollars": call["reservation_microdollars"],
                "cumulative_consumed_microdollars": consumed,
                "exposure_microdollars": after_exposure,
                "halted": after_meta["halted"],
            }

    @staticmethod
    def _identity(call, binding_id):
        return json.dumps([binding_id, call.phase, call.task, call.trial, call.attempt])

    @staticmethod
    def _approved(meta, binding):
        approved = Registry.from_dict(meta["registry"]).binding(binding.binding_id)
        if approved.digest != binding.digest:
            raise BudgetStop("binding mismatch with immutable registry")
        if meta["halted"]:
            raise BudgetStop("ledger halted")
        return approved

    def approved_binding(self, binding_id: str, registry_sha256: str):
        with self._transaction() as db:
            meta, _, _ = self._read(db)
            if meta["registry_sha256"] != registry_sha256:
                raise BudgetStop("evaluator registry pin mismatch")
            if meta["halted"]:
                raise BudgetStop("ledger halted")
            return Registry.from_dict(meta["registry"]).binding(binding_id)

    def snapshot(self):
        with self._transaction() as db:
            meta, rows, exposure = self._read(db)
            return {
                "metadata": meta,
                "calls": rows,
                "exposure": exposure,
                "headroom": CAP - exposure,
            }

    @contextmanager
    def controller(self):
        """Serial launch/reconcile including across independent processes."""
        with self.path.with_suffix(self.path.suffix + ".controller").open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise BudgetStop("another budget controller is active") from None
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def reserve(self, call: Call, binding: Binding, fingerprint: str = ""):
        if fingerprint and not SHA.fullmatch(fingerprint):
            raise BudgetStop("invalid execution fingerprint")
        call.validate()
        amount = binding.validate()
        with self._transaction() as db:
            meta, rows, exposure = self._read(db)
            self._approved(meta, binding)
            if exposure + amount > CAP:
                raise BudgetStop("aggregate headroom exhausted; acceptance incomplete")
            if any(
                r["call"]["call_id"] == call.call_id
                or self._identity(Call(**r["call"]), r["binding_id"])
                == self._identity(call, binding.binding_id)
                for r in rows
            ):
                raise BudgetStop(
                    "duplicate call/trial; explicit retry identity required"
                )
            if call.attempt > 1 and not any(
                r["binding_id"] == binding.binding_id
                and r["call"]["phase"] == call.phase
                and r["call"]["task"] == call.task
                and r["call"]["trial"] == call.trial
                and r["call"]["attempt"] == call.attempt - 1
                for r in rows
            ):
                raise BudgetStop("retry predecessor missing")
            row = {
                "call": asdict(call),
                "binding_id": binding.binding_id,
                "binding_sha256": binding.digest,
                "reservation": amount,
                "actual": None,
                "receipt": None,
                "partial_receipt": None,
                "outcome": None,
                "fingerprint": fingerprint,
                "status": "reserved",
                "reserved_at_ns": time.time_ns(),
                "terminal_at_ns": None,
                "stop_reason": "reserved",
            }
            db.execute(
                "INSERT INTO calls VALUES (?, ?, ?)",
                (
                    call.call_id,
                    self._identity(call, binding.binding_id),
                    json.dumps(row),
                ),
            )

    def retry_call(self, call: Call, binding: Binding) -> Call:
        """Select only the third plan's single commissioned replacement attempt."""
        call.validate()
        with self._transaction() as db:
            meta, rows, _ = self._read(db)
            self._approved(meta, binding)
            if meta["halted"]:
                raise BudgetStop("ledger halted")
            tail = db.execute(
                "SELECT payload FROM registry_transitions ORDER BY seq DESC LIMIT 1"
            ).fetchone()
            if tail is None:
                return call
            record = json.loads(tail[0])
            if record["schema_version"] != 3:
                return call
            retry = record["retry"]
            if (binding.binding_id, call.phase, call.task, call.trial) != (
                retry["binding_id"],
                retry["phase"],
                retry["task"],
                retry["trial"],
            ):
                return call
            if (
                call.attempt != retry["from_attempt"]
                or call.source_commit != record["provenance"]["source_heads"]["plugin"]
            ):
                raise BudgetStop("unreviewed retry/source refused")
            predecessor = next(
                r
                for r in rows
                if r["call"]["call_id"] == record["charged_calls"][0]["call_id"]
            )
            old = Call(**predecessor["call"])
            if (
                predecessor["status"] != "charged-uncertain"
                or predecessor["binding_id"] != binding.binding_id
                or (old.phase, old.task, old.trial, old.attempt)
                != (
                    retry["phase"],
                    retry["task"],
                    retry["trial"],
                    retry["from_attempt"],
                )
            ):
                raise BudgetStop("reviewed retry predecessor differs")
            identifier = _digest(
                [
                    meta["transition_head"],
                    binding.binding_id,
                    call.phase,
                    call.task,
                    call.trial,
                    retry["to_attempt"],
                ]
            )[:32]
            return Call(
                identifier,
                call.phase,
                call.task,
                call.trial,
                call.source_commit,
                retry["to_attempt"],
            )

    def cached(self, call: Call, binding: Binding, fingerprint: str):
        """Restore an exact completed observation without paying for it again."""
        call.validate()
        with self._transaction() as db:
            meta, rows, _ = self._read(db)
            self._approved(meta, binding)
            row = next(
                (
                    r
                    for r in rows
                    if self._identity(Call(**r["call"]), r["binding_id"])
                    == self._identity(call, binding.binding_id)
                ),
                None,
            )
            if row is None:
                return None
            if (
                row["call"]["source_commit"] != call.source_commit
                or row["fingerprint"] != fingerprint
            ):
                raise BudgetStop("resume source or request mismatch")
            if (
                row["status"] != "settled"
                or row["receipt"] is None
                or row["outcome"] is None
            ):
                raise BudgetStop(
                    "incomplete prior call; retain reservation; explicit retry required"
                )
            data = json.loads(Path(row["outcome"]["path"]).read_text())
            if data["receipt"] is not None:
                data["receipt"] = Settlement(**data["receipt"])
            return Outcome(**data)

    def record_outcome(self, call_id: str, outcome):
        """Durably bind terminal/partial evidence even without a final charge."""
        data = json.dumps(asdict(outcome), sort_keys=True).encode()
        digest = hashlib.sha256(data).hexdigest()
        failure = None
        with self._transaction() as db:
            meta, rows, _ = self._read(db)
            row = next((r for r in rows if r["call"]["call_id"] == call_id), None)
            if row is None or row["status"] != "reserved" or row["outcome"] is not None:
                raise BudgetStop("outcome requires one active reservation")
            directory = self.path.with_suffix(self.path.suffix + ".evidence")
            directory.mkdir(mode=0o700, exist_ok=True)
            destination = directory / (digest + ".json")
            try:
                fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                _proof(str(destination), digest)
            else:
                with os.fdopen(fd, "wb") as output:
                    output.write(data)
                    output.flush()
                    os.fsync(output.fileno())
                # Sync the new file's directory entry and the directory itself.
                for parent in (directory, directory.parent):
                    parent_fd = os.open(parent, os.O_RDONLY)
                    try:
                        os.fsync(parent_fd)
                    finally:
                        os.close(parent_fd)
            row["outcome"] = {"path": str(destination), "sha256": digest}
            # Commit receipt evidence or a known terminal-accounting halt in
            # the SAME update as Outcome. No later classification crash window.
            reason = "invalid-receipt"
            if (
                type(outcome.timed_out) is not bool
                or type(outcome.early_stop) is not bool
            ):
                failure = BudgetStop("invalid outcome stop flags")
                reason = "invalid-outcome"
            elif outcome.receipt is None and not (
                outcome.timed_out or outcome.early_stop
            ):
                failure = BudgetStop(
                    "terminal accounting missing; reservation retained"
                )
                reason = "missing-cost"
            elif outcome.receipt is not None:
                try:
                    if outcome.receipt.call_id != call_id:
                        raise BudgetStop("receipt does not belong to active call")
                    binding = Registry.from_dict(meta["registry"]).binding(
                        row["binding_id"]
                    )
                    actual = outcome.receipt.validate(Call(**row["call"]), binding)
                    if actual > row["reservation"]:
                        raise BudgetStop("reservation violation")
                except BudgetStop as exc:
                    failure = exc
                else:
                    row["partial_receipt"] = asdict(outcome.receipt)
            if failure is not None:
                meta["halted"] = True
                row.update(
                    status="uncertain",
                    stop_reason=reason,
                    terminal_at_ns=time.time_ns(),
                )
                db.execute(
                    "UPDATE metadata SET payload=? WHERE id=1", (json.dumps(meta),)
                )
            db.execute(
                "UPDATE calls SET payload=? WHERE id=?", (json.dumps(row), call_id)
            )
        if failure is not None:
            raise failure

    def uncertain(
        self,
        call_id: str,
        reason: str,
        *,
        halt=False,
        receipt: Settlement | None = None,
    ):
        _token(reason)
        with self._transaction() as db:
            meta, rows, _ = self._read(db)
            row = next((r for r in rows if r["call"]["call_id"] == call_id), None)
            if row is None or row["status"] not in {"reserved", "uncertain"}:
                raise BudgetStop("cannot mark unknown or settled call uncertain")
            if receipt is not None:
                actual = receipt.validate(
                    Call(**row["call"]),
                    Registry.from_dict(meta["registry"]).binding(row["binding_id"]),
                )
                if actual > row["reservation"]:
                    raise BudgetStop("partial receipt exceeds reservation")
                row["partial_receipt"] = asdict(receipt)
            row.update(
                status="uncertain", stop_reason=reason, terminal_at_ns=time.time_ns()
            )
            db.execute(
                "UPDATE calls SET payload=? WHERE id=?", (json.dumps(row), call_id)
            )
            if halt:
                meta["halted"] = True
                db.execute(
                    "UPDATE metadata SET payload=? WHERE id=1", (json.dumps(meta),)
                )

    def reconcile(self, receipt: Settlement):
        failure = False
        with self._transaction() as db:
            meta, rows, _ = self._read(db)
            row = next(
                (r for r in rows if r["call"]["call_id"] == receipt.call_id), None
            )
            if row is None:
                raise BudgetStop("unknown reconciliation call")
            if row["status"] == "charged-uncertain":
                raise BudgetStop(
                    "conservative charge is permanent; reconciliation refused"
                )
            if row["status"] == "settled" and row["receipt"] == asdict(receipt):
                # _read already validated the sealed receipt with its historical binding.
                return
            try:
                actual = receipt.validate(
                    Call(**row["call"]),
                    Registry.from_dict(meta["registry"]).binding(row["binding_id"]),
                )
                if actual > row["reservation"]:
                    raise BudgetStop("reservation violation")
                if row["status"] == "settled" and row["receipt"] != asdict(receipt):
                    raise BudgetStop("conflicting duplicate reconciliation")
            except BudgetStop:
                meta["halted"] = True
                db.execute(
                    "UPDATE metadata SET payload=? WHERE id=1", (json.dumps(meta),)
                )
                failure = True
            else:
                if row["status"] != "settled":
                    row.update(
                        status="settled",
                        actual=actual,
                        receipt=asdict(receipt),
                        terminal_at_ns=time.time_ns(),
                        stop_reason=receipt.stop_reason,
                    )
                    db.execute(
                        "UPDATE calls SET payload=? WHERE id=?",
                        (json.dumps(row), receipt.call_id),
                    )
        if failure:
            raise BudgetStop(
                "untrusted reconciliation; reservation retained; ledger halted"
            )


@dataclass
class Outcome:
    lines: list[str] = field(default_factory=list)
    stderr: str = ""
    returncode: int = 0
    result: object | None = None
    timed_out: bool = False
    early_stop: bool = False
    receipt: Settlement | None = None

    @property
    def stdout(self):
        return "\n".join(self.lines)


class Transport(Protocol):
    """Trusted code boundary; never implement with an unrestricted Popen.

    validate must prove containment and live cap/in-flight enforcement before
    every run; execute must reap the entire process tree even on callbacks or
    timeout. replay must deny ALL paid paths while retaining shell semantics.
    The joint controller supplies the reviewed macOS/API broker implementation.
    """

    offline_only: bool

    def validate(self, binding: Binding) -> None: ...
    def execute(
        self, cmd: list[str], prompt: str, *, call: Call, **kwargs
    ) -> Outcome: ...
    def replay(self, command: str, **kwargs) -> tuple[int, str, str]: ...


def prepare_launch(
    cmd: list[str], prompt: str, binding: Binding, *, offline_only=False
):
    """Apply only the selected provider's reviewed launch/limit contract.

    Codex has no accepted attributable billing/in-flight contract here. A
    Claude max-budget flag must never be applied to, or used to admit, Codex.
    Synthetic Codex-shaped argv is accepted only by an offline-only transport.
    """
    binding.validate()
    if binding.provider == "openai":
        raise BudgetStop(
            "Codex route refused: bounded attributable API billing and containment unproved"
        )
    if binding.provider == "fake" and offline_only is not True:
        raise BudgetStop("synthetic routes require an offline-only transport")
    if (
        not isinstance(prompt, str)
        or not isinstance(cmd, list)
        or not cmd
        or any(not isinstance(arg, str) for arg in cmd)
    ):
        raise BudgetStop("invalid trusted launch argv/prompt")
    cmd = list(cmd)
    if cmd[0] == "claude":
        model_option = "--model"
        switches = {"--print", "--verbose", "--strict-mcp-config", "--safe-mode"}
        valued = {
            "--model",
            "--output-format",
            "--permission-mode",
            "--tools",
            "--allowedTools",
            "--mcp-config",
            "--plugin-dir",
            "--max-turns",
        }
        start = 1
        cmd = ["--print" if arg == "-p" else arg for arg in cmd]
    elif binding.provider == "fake" and cmd[:2] == ["codex", "exec"]:
        model_option = "-m"
        switches = {"--skip-git-repo-check"}
        valued = {"-m", "-s", "-o"}
        start = 2
    else:
        raise BudgetStop("unbound executable/provider")
    options = {}
    index = start
    while index < len(cmd):
        option = cmd[index]
        if (
            index == len(cmd) - 1
            and option == prompt
            and option not in switches
            and option not in valued
        ):
            cmd.pop()  # One cold prompt is supplied separately, never duplicated.
            break
        if option in options and option != "--plugin-dir":
            raise BudgetStop("duplicate launch option")
        if option in switches:
            options[option] = True
            index += 1
        elif option in valued and index + 1 < len(cmd):
            if cmd[index + 1].startswith("-"):
                raise BudgetStop("option-shaped launch value refused")
            options[option] = cmd[index + 1]
            index += 2
        else:
            raise BudgetStop("unbound or non-cold launch option")
    if options.get(model_option) != binding.model:
        raise BudgetStop("unbound model")
    if cmd[0] == "claude":
        if not options.get("--print"):
            raise BudgetStop("non-cold command")
        return [*cmd, "--max-budget-usd", binding.session_cap_usd]
    if options.get("-s") != "read-only":
        raise BudgetStop("unbound synthetic Codex sandbox")
    return cmd  # Fake mode has synthetic caps; no claimed Codex CLI dollar cap.


class BudgetLauncher:
    def __init__(self, ledger: Ledger, binding: Binding, transport: Transport):
        self.ledger, self.binding, self.transport = ledger, binding, transport

    def run(
        self,
        cmd: list[str],
        prompt: str,
        *,
        call: Call,
        evidence_destination: Path | None = None,
        **kwargs,
    ) -> Outcome:
        call.validate()
        prepared = prepare_launch(
            cmd,
            prompt,
            self.binding,
            offline_only=getattr(self.transport, "offline_only", False),
        )
        if self.binding.provider != "fake":
            timeout = kwargs.get("timeout")
            if (
                isinstance(timeout, bool)
                or not isinstance(timeout, (int, float))
                or not 0 < timeout < 86400
            ):
                raise BudgetStop("finite per-call timeout required")
            if evidence_destination is None:
                raise BudgetStop("trusted per-call evidence destination required")
        if evidence_destination is not None:
            kwargs["evidence_destination"] = str(Path(evidence_destination).resolve())
        self.transport.validate(self.binding)
        fingerprint = hashlib.sha256(
            json.dumps(
                {
                    "argv": cmd,
                    "prompt": prompt,
                    "source": call.source_commit,
                    "timeout": kwargs.get("timeout"),
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()
        with self.ledger.controller():
            cached = self.ledger.cached(call, self.binding, fingerprint)
            if cached is not None:
                if kwargs.get("on_line") is not None:
                    for line in cached.lines:
                        kwargs["on_line"](line)
                return cached
            self.ledger.reserve(
                call, self.binding, fingerprint
            )  # durable BEFORE execute
            try:
                outcome = self.transport.execute(
                    prepared,
                    prompt,
                    call=call,
                    **kwargs,
                )
                self.ledger.record_outcome(call.call_id, outcome)
                if (
                    outcome.receipt is not None
                    and outcome.receipt.call_id != call.call_id
                ):
                    self.ledger.uncertain(call.call_id, "wrong-call-receipt", halt=True)
                    raise BudgetStop("receipt does not belong to active call")
                if outcome.receipt is not None:
                    try:
                        actual = outcome.receipt.validate(call, self.binding)
                        if actual > self.binding.validate():
                            raise BudgetStop("reservation violation")
                    except BudgetStop:
                        self.ledger.uncertain(
                            call.call_id, "invalid-receipt", halt=True
                        )
                        raise
                if outcome.timed_out or outcome.early_stop:
                    self.ledger.uncertain(
                        call.call_id,
                        "timeout" if outcome.timed_out else "early-stop",
                        receipt=outcome.receipt,
                    )
                elif outcome.receipt is None:
                    self.ledger.uncertain(call.call_id, "missing-cost", halt=True)
                    raise BudgetStop(
                        "terminal accounting missing; reservation retained"
                    )
                else:
                    self.ledger.reconcile(outcome.receipt)
                return outcome
            except BaseException:
                # Reconciliation may already have halted or settled the row.
                snapshot = self.ledger.snapshot()
                row = next(
                    r for r in snapshot["calls"] if r["call"]["call_id"] == call.call_id
                )
                if row["status"] == "reserved":
                    self.ledger.uncertain(call.call_id, "interrupted", halt=True)
                raise

    def replay(self, command: str, **kwargs):
        self.binding.validate()
        self.transport.validate(self.binding)
        return self.transport.replay(command, **kwargs)


_ADMITTED_LAUNCHER = None  # Set only inside the reviewed joint controller process.


def require_launcher() -> BudgetLauncher:
    """No env opt-in or self-attested JSON can enable unverified paid access."""
    if _ADMITTED_LAUNCHER is not None:
        _ADMITTED_LAUNCHER.transport.validate(_ADMITTED_LAUNCHER.binding)
        return _ADMITTED_LAUNCHER
    raise BudgetStop(
        "paid evaluation disabled: no reviewed billing/model/cap/in-flight/"
        "containment adapter is installed; use the shared $50 ledger only "
        "after that binding is implemented and accepted"
    )


def harness_call(phase: str, task: str, trial: int, *, attempt: int = 1) -> Call:
    """Stable trial identity across restarts; retries must be explicit."""
    call = Call(
        uuid4().hex,
        phase,
        task,
        trial,
        os.environ.get("EVALUATION_SOURCE_COMMIT", ""),
        attempt,
    )
    call.validate()
    return call


API_VERSION = 5


def bind_evaluator(
    *,
    ledger_path: Path,
    binding_id: str,
    registry_sha256: str,
    module_sha256: str,
    interface_sha256: str,
    transport: Transport,
) -> BudgetLauncher:
    """Bind the existing shared ledger and an explicitly reviewed code adapter.

    This cannot create/reset a ledger or admit a provider. No production adapter
    is selected by this interface; require_launcher stays closed outside the joint controller.
    Never load transport code from
    model output, environment toggles or a registry's JSON fields.
    """
    manifest = interface_manifest()
    if (
        module_sha256 != manifest["module_sha256"]
        or interface_sha256 != manifest["interface_sha256"]
    ):
        raise BudgetStop("evaluator module/interface pin mismatch")
    ledger = Ledger(ledger_path)
    binding = ledger.approved_binding(binding_id, registry_sha256)
    return BudgetLauncher(ledger, binding, transport)


def interface_manifest():
    """Portable single-module export; import by reviewed path AND exact hash."""
    from dataclasses import fields
    from inspect import signature

    records = (LaunchContract, ApiPricing, Binding, Registry, Call, Settlement, Outcome)
    functions = (
        Ledger.create,
        Ledger.reserve,
        Ledger.reconcile,
        Ledger.recover_and_transition,
        Ledger.retry_call,
        Ledger.approved_binding,
        BudgetLauncher.run,
        bind_evaluator,
        require_launcher,
        api_usage_charge,
    )
    interface = {
        "api_version": API_VERSION,
        "ledger_schema_version": SCHEMA_VERSION,
        "aggregate_cap_microdollars": CAP,
        "production_default": "refused",
        "codex_admission": "refused",
        "records": {
            record.__name__: [f.name for f in fields(record)] for record in records
        },
        "functions": {
            function.__qualname__: [
                {"name": p.name, "kind": p.kind.name, "required": p.default is p.empty}
                for p in signature(function).parameters.values()
            ]
            for function in functions
        },
        "api_usage_fields": sorted(API_USAGE_FIELDS),
        "api_price_fields": sorted(API_PRICE_FIELDS),
    }
    return {
        "interface": interface,
        "interface_sha256": _digest(interface),
        "module_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
