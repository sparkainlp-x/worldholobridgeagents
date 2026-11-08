"""Single-process transaction reference; not durable or distributed storage."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from hashlib import sha256
import json
from threading import RLock
from typing import Any, Mapping

from .policy import Decision, validate_records


def canonical_request_digest(
    intent: Mapping[str, Any], actor_id: str, target_revision: int | None = None
) -> str:
    """Hash the exact, normalized payment request bound by an authorization."""
    payload = {
        "target_id": intent["id"],
        "target_revision": target_revision or intent["revision"],
        "tenant_id": intent["tenant_id"],
        "environment": intent["environment"],
        "actor_id": actor_id,
        "funding_case_id": intent["funding_case_id"],
        "budget_line_id": intent["budget_line_id"],
        "purpose": intent["purpose"],
        "money": intent["money"],
        "idempotency_key": intent["idempotency_key"],
    }
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


class ReferenceStore:
    """Lock-protected in-memory reservation and idempotency behavior only."""

    def __init__(self, records: list[Mapping[str, Any]]):
        self._lock = RLock()
        self._records = {record["id"]: deepcopy(dict(record)) for record in records}

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return deepcopy(list(self._records.values()))

    def reserve_payment(
        self,
        payment_id: str,
        actor: Mapping[str, str],
        now: datetime,
        expected_revision: int,
    ) -> tuple[Decision, dict[str, Any] | None]:
        """Atomically validate, consume one authorization, and reserve budget."""
        with self._lock:
            intent = self._records.get(payment_id)
            if not intent or intent.get("record_type") != "payment_intent":
                return Decision(False, ("PAYMENT_NOT_FOUND",)), None
            matching = [
                row for row in self._records.values()
                if row.get("record_type") == "payment_intent"
                and row.get("tenant_id") == intent["tenant_id"]
                and row.get("idempotency_key") == intent["idempotency_key"]
            ]
            if len(matching) > 1:
                return Decision(False, ("IDEMPOTENCY_KEY_CONFLICT",)), None
            if intent["state"] in {"unknown", "reconciliation_required"}:
                return Decision(False, ("RECONCILIATION_REQUIRED_NO_RETRY",)), None
            if intent["state"] == "reserved":
                if expected_revision + 1 == intent["revision"]:
                    return Decision(True, ("IDEMPOTENT_REPLAY",)), deepcopy(intent)
                return Decision(False, ("STALE_REVISION",)), None
            if intent["revision"] != expected_revision:
                return Decision(False, ("STALE_REVISION",)), None
            if intent["state"] not in {"draft", "authorized"}:
                return Decision(False, ("INVALID_PAYMENT_TRANSITION",)), None
            if actor.get("role") != "finance_approver":
                return Decision(False, ("ACTOR_ROLE_UNAUTHORIZED",)), None
            if intent["environment"] != "sandbox":
                return Decision(False, ("SANDBOX_ONLY",)), None
            if any(
                row.get("record_type") == "payment_intent"
                and row.get("state") == "reconciliation_required"
                and row.get("funding_case_id") == intent["funding_case_id"]
                and row.get("budget_line_id") == intent["budget_line_id"]
                and row.get("purpose") == intent["purpose"]
                and row.get("money") == intent["money"]
                for row in self._records.values()
            ):
                return Decision(False, ("RECONCILIATION_REQUIRED_NO_RETRY",)), None
            amount = intent["money"]["amount_minor"]
            if type(amount) is not int or amount < 0:
                return Decision(False, ("INVALID_MONEY_AMOUNT",)), None
            authorization = self._records.get(intent["authorization_id"])
            funding = self._records.get(intent["funding_case_id"])
            budget = self._records.get(intent["budget_line_id"])
            if not authorization or authorization.get("record_type") != "authorization":
                return Decision(False, ("AUTHORIZATION_MISSING",)), None
            if not funding or not budget:
                return Decision(False, ("FUNDING_OR_BUDGET_MISSING",)), None
            if authorization["tenant_id"] != intent["tenant_id"] or funding["tenant_id"] != intent[
                "tenant_id"
            ] or budget["tenant_id"] != intent["tenant_id"]:
                return Decision(False, ("CROSS_TENANT_REFERENCE",)), None
            digest = canonical_request_digest(intent, actor["id"], expected_revision)
            if (
                intent["request_digest"] != digest
                or authorization["request_digest"] != digest
                or authorization["target_id"] != payment_id
                or authorization["target_revision"] != expected_revision
                or authorization["actor_id"] != actor["id"]
                or authorization["actor_role"] != actor["role"]
                or authorization["environment"] != "sandbox"
                or authorization["consumed_at"] is not None
                or not _after(authorization["expires_at"], now)
            ):
                return Decision(False, ("AUTHORIZATION_INVALID_EXPIRED_OR_REPLAYED",)), None
            if (
                funding["status"] != "approved"
                or funding["eligibility_review_status"] != "reviewed"
                or intent["purpose"] not in funding["permitted_purposes"]
            ):
                return Decision(False, ("FUNDING_NOT_APPROVED_FOR_PURPOSE",)), None
            currency = intent["money"]["currency"]
            if (
                currency != funding["currency"]
                or currency != budget["currency"]
                or budget["funding_case_id"] != funding["id"]
                or budget["purpose"] != intent["purpose"]
            ):
                return Decision(False, ("CURRENCY_OR_BUDGET_PURPOSE_MISMATCH",)), None
            budget_used = budget["reserved_minor"] + budget["settled_minor"]
            if budget_used + amount > budget["limit_minor"]:
                return Decision(False, ("BUDGET_LINE_EXCEEDED",)), None
            funding_reserved = sum(
                row.get("reserved_minor", 0)
                for row in self._records.values()
                if row.get("record_type") == "budget_line"
                and row.get("funding_case_id") == funding["id"]
            )
            funding_settled = sum(
                row.get("settled_minor", 0)
                for row in self._records.values()
                if row.get("record_type") == "budget_line"
                and row.get("funding_case_id") == funding["id"]
            )
            if funding_reserved + funding_settled + amount > funding["approved_amount_minor"]:
                return Decision(False, ("APPROVED_FUNDING_EXCEEDED",)), None
            candidate_records = list(self._records.values())
            validation_errors = validate_records(candidate_records)
            if validation_errors:
                return Decision(False, validation_errors), None
            intent["state"] = "reserved"
            intent["revision"] += 1
            intent["updated_at"] = _timestamp(now)
            authorization["consumed_at"] = _timestamp(now)
            authorization["revision"] += 1
            authorization["updated_at"] = _timestamp(now)
            budget["reserved_minor"] += amount
            budget["revision"] += 1
            budget["updated_at"] = _timestamp(now)
            return Decision(True, ("PAYMENT_RESERVED_SANDBOX_ONLY",)), deepcopy(intent)

    def record_unknown_outcome(self, payment_id: str, now: datetime) -> Decision:
        """Mark uncertain submission for reconciliation; never retry implicitly."""
        with self._lock:
            intent = self._records.get(payment_id)
            if not intent or intent.get("record_type") != "payment_intent":
                return Decision(False, ("PAYMENT_NOT_FOUND",))
            if intent["state"] != "reserved":
                return Decision(False, ("INVALID_PAYMENT_TRANSITION",))
            intent["state"] = "reconciliation_required"
            intent["revision"] += 1
            intent["updated_at"] = _timestamp(now)
            return Decision(False, ("RECONCILIATION_REQUIRED_NO_RETRY",))

    def record_settled(
        self, payment_id: str, now: datetime, expected_revision: int
    ) -> Decision:
        """Record a known, externally reconciled outcome without contacting a provider."""
        with self._lock:
            intent = self._records.get(payment_id)
            if not intent or intent.get("record_type") != "payment_intent":
                return Decision(False, ("PAYMENT_NOT_FOUND",))
            if intent["revision"] != expected_revision:
                return Decision(False, ("STALE_REVISION",))
            if intent["state"] not in {"reserved", "reconciliation_required"}:
                return Decision(False, ("INVALID_PAYMENT_TRANSITION",))
            budget = self._records.get(intent["budget_line_id"])
            if not budget or budget.get("tenant_id") != intent["tenant_id"]:
                return Decision(False, ("FUNDING_OR_BUDGET_MISSING",))
            amount = intent["money"]["amount_minor"]
            if budget["reserved_minor"] < amount:
                return Decision(False, ("BUDGET_ACCOUNTING_INVALID",))
            budget["reserved_minor"] -= amount
            budget["settled_minor"] += amount
            budget["revision"] += 1
            budget["updated_at"] = _timestamp(now)
            intent["state"] = "settled"
            intent["revision"] += 1
            intent["updated_at"] = _timestamp(now)
            return Decision(True, ("KNOWN_OUTCOME_RECONCILED",))


def _after(value: str, now: datetime) -> bool:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) > now


def _timestamp(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")
