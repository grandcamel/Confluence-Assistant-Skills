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


SCHEMA_VERSION = 2


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
                or request["inference_geo"] != "global"
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
            or meta["version"] != SCHEMA_VERSION
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
        records = []
        exposure = 0
        for row_id, identity, payload in db.execute(
            "SELECT id, identity, payload FROM calls ORDER BY id"
        ):
            row = json.loads(payload)
            call = Call(**row["call"])
            call.validate()
            binding = registry.binding(row["binding_id"])
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
            records.append(row)
        if exposure > CAP:
            raise BudgetStop("ledger exceeds aggregate cap")
        return meta, records, exposure

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
            if row["status"] == "reserved" or row["outcome"] is None:
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
        failure = None
        with self._transaction() as db:
            meta, rows, _ = self._read(db)
            row = next((r for r in rows if r["call"]["call_id"] == call_id), None)
            if row is None or row["status"] != "reserved" or row["outcome"] is not None:
                raise BudgetStop("outcome requires one active reservation")
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
            if row is None or row["status"] == "settled":
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


API_VERSION = 2


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
