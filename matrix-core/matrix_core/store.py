"""Single-process transaction reference; not durable or distributed storage."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from hashlib import sha256
import json
from threading import RLock
from typing import Any, Mapping
from uuid import UUID, uuid5

from .policy import Decision, validate_records


_AUDIT_NAMESPACE = UUID("8e5cb4af-f15c-43e8-9d10-0c1df0e8a4c4")


def canonical_request_digest(
    intent: Mapping[str, Any], actor_id: str, target_revision: int | None = None
) -> str:
    """Hash the exact, normalized payment request bound by an authorization."""
    payload = {
        "target_id": intent["id"],
        "target_revision": (
            intent["revision"] if target_revision is None else target_revision
        ),
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
        input_records = list(records)
        source = [
            deepcopy(dict(record)) for record in input_records
            if isinstance(record, Mapping)
        ]
        self._initial_errors = validate_records(input_records)
        self._records = {record.get("id"): record for record in source}

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
            if self._initial_errors:
                return Decision(False, self._initial_errors), None
            if not _aware(now):
                return Decision(False, ("CLOCK_NOT_TIMEZONE_AWARE",)), None
            intent = self._records.get(payment_id)
            if not intent or intent.get("record_type") != "payment_intent":
                return Decision(False, ("PAYMENT_NOT_FOUND",)), None
            if actor.get("role") != "finance_approver":
                return Decision(False, ("ACTOR_ROLE_UNAUTHORIZED",)), None
            if actor.get("tenant_id") != intent["tenant_id"]:
                return Decision(False, ("TENANT_MISMATCH",)), None
            if not isinstance(actor.get("id"), str):
                return Decision(False, ("ACTOR_ID_INVALID",)), None
            authorization = self._records.get(intent["authorization_id"])
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
                if (
                    expected_revision + 1 == intent["revision"]
                    and authorization
                    and authorization.get("actor_id") == actor["id"]
                    and authorization.get("actor_role") == actor["role"]
                    and authorization.get("tenant_id") == actor["tenant_id"]
                ):
                    return Decision(True, ("IDEMPOTENT_REPLAY",)), deepcopy(intent)
                if authorization and authorization.get("actor_id") != actor["id"]:
                    return Decision(False, ("AUTHORIZATION_INVALID_EXPIRED_OR_REPLAYED",)), None
                return Decision(False, ("STALE_REVISION",)), None
            if intent["revision"] != expected_revision:
                return Decision(False, ("STALE_REVISION",)), None
            if intent["state"] not in {"draft", "authorized"}:
                return Decision(False, ("INVALID_PAYMENT_TRANSITION",)), None
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
            if not all(
                _usable_evidence(
                    self._records.get(evidence_id),
                    funding["id"],
                    evidence_type,
                    funding["tenant_id"],
                    now,
                )
                for evidence_id, evidence_type in (
                    (funding["approval_evidence_id"], "funding_approval"),
                    (funding["eligibility_evidence_id"], "eligibility_review"),
                )
            ):
                return Decision(False, ("FUNDING_EVIDENCE_MISSING_EXPIRED_OR_UNREVIEWED",)), None
            currency = intent["money"]["currency"]
            if (
                currency != funding["currency"]
                or currency != budget["currency"]
                or funding["environment"] != "sandbox"
                or budget["environment"] != "sandbox"
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
            audit_id = _audit_id(intent["id"], "payment_reservation", intent["revision"] + 1)
            if audit_id in self._records:
                return Decision(False, ("DUPLICATE_AUDIT_EVENT_ID",)), None
            intent["state"] = "reserved"
            intent["reconciliation_evidence_id"] = None
            intent["revision"] += 1
            intent["updated_at"] = _timestamp(now)
            authorization["consumed_at"] = _timestamp(now)
            authorization["revision"] += 1
            authorization["updated_at"] = _timestamp(now)
            budget["reserved_minor"] += amount
            budget["revision"] += 1
            budget["updated_at"] = _timestamp(now)
            self._append_audit(
                intent, authorization, "payment_reservation", "allow",
                ["PAYMENT_RESERVED_SANDBOX_ONLY"], now, audit_id,
            )
            return Decision(True, ("PAYMENT_RESERVED_SANDBOX_ONLY",)), deepcopy(intent)

    def record_unknown_outcome(
        self,
        payment_id: str,
        actor: Mapping[str, str],
        now: datetime,
        expected_revision: int,
    ) -> Decision:
        """Mark uncertain submission for reconciliation; never retry implicitly."""
        with self._lock:
            if self._initial_errors:
                return Decision(False, self._initial_errors)
            if not _aware(now):
                return Decision(False, ("CLOCK_NOT_TIMEZONE_AWARE",))
            intent = self._records.get(payment_id)
            if not intent or intent.get("record_type") != "payment_intent":
                return Decision(False, ("PAYMENT_NOT_FOUND",))
            if actor.get("role") != "finance_approver" or not isinstance(actor.get("id"), str):
                return Decision(False, ("ACTOR_ROLE_UNAUTHORIZED",))
            if actor.get("tenant_id") != intent["tenant_id"]:
                return Decision(False, ("TENANT_MISMATCH",))
            authorization = self._records.get(intent["authorization_id"], {})
            if (
                authorization.get("actor_id") != actor["id"]
                or authorization.get("actor_role") != actor["role"]
            ):
                return Decision(False, ("AUTHORIZATION_INVALID_EXPIRED_OR_REPLAYED",))
            if intent["revision"] != expected_revision:
                return Decision(False, ("STALE_REVISION",))
            if intent["state"] != "reserved":
                return Decision(False, ("INVALID_PAYMENT_TRANSITION",))
            audit_id = _audit_id(
                intent["id"], "payment_outcome_unknown", intent["revision"] + 1
            )
            if audit_id in self._records:
                return Decision(False, ("DUPLICATE_AUDIT_EVENT_ID",))
            intent["state"] = "reconciliation_required"
            intent["revision"] += 1
            intent["updated_at"] = _timestamp(now)
            self._append_audit(
                intent, authorization, "payment_outcome_unknown", "deny",
                ["RECONCILIATION_REQUIRED_NO_RETRY"], now, audit_id,
            )
            return Decision(True, ("OUTCOME_MARKED_RECONCILIATION_REQUIRED",))

    def record_settled(
        self,
        payment_id: str,
        actor: Mapping[str, str],
        reconciliation_evidence: Mapping[str, Any],
        now: datetime,
        expected_revision: int,
    ) -> Decision:
        """Record a known, externally reconciled outcome without contacting a provider."""
        with self._lock:
            if self._initial_errors:
                return Decision(False, self._initial_errors)
            if not _aware(now):
                return Decision(False, ("CLOCK_NOT_TIMEZONE_AWARE",))
            intent = self._records.get(payment_id)
            if not intent or intent.get("record_type") != "payment_intent":
                return Decision(False, ("PAYMENT_NOT_FOUND",))
            if actor.get("role") != "finance_approver" or not isinstance(actor.get("id"), str):
                return Decision(False, ("ACTOR_ROLE_UNAUTHORIZED",))
            if actor.get("tenant_id") != intent["tenant_id"]:
                return Decision(False, ("TENANT_MISMATCH",))
            authorization = self._records.get(intent["authorization_id"], {})
            if (
                authorization.get("actor_id") != actor["id"]
                or authorization.get("actor_role") != actor["role"]
            ):
                return Decision(False, ("AUTHORIZATION_INVALID_EXPIRED_OR_REPLAYED",))
            if intent["revision"] != expected_revision:
                return Decision(False, ("STALE_REVISION",))
            if intent["state"] not in {"reserved", "reconciliation_required"}:
                return Decision(False, ("INVALID_PAYMENT_TRANSITION",))
            evidence = deepcopy(dict(reconciliation_evidence))
            candidate_records = [*self._records.values(), evidence]
            validation_errors = validate_records(candidate_records)
            if validation_errors:
                return Decision(False, validation_errors)
            if (
                evidence.get("record_type") != "evidence"
                or evidence.get("evidence_type") != "payment_reconciliation"
                or evidence.get("subject_id") != payment_id
                or evidence.get("tenant_id") != intent["tenant_id"]
                or evidence.get("environment") != intent["environment"]
                or evidence.get("reviewed_by") != actor["id"]
                or evidence.get("review_status") != "reviewed"
                or evidence.get("execution_status") != "passed"
                or not _usable_evidence(
                    evidence, payment_id, "payment_reconciliation",
                    intent["tenant_id"], now,
                )
                or evidence.get("id") in self._records
            ):
                return Decision(False, ("PAYMENT_RECONCILIATION_EVIDENCE_INVALID",))
            audit_id = _audit_id(
                intent["id"], "payment_outcome_reconciled", intent["revision"] + 1
            )
            if audit_id in self._records or evidence.get("id") == audit_id:
                return Decision(False, ("DUPLICATE_AUDIT_EVENT_ID",))
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
            intent["reconciliation_evidence_id"] = evidence["id"]
            intent["revision"] += 1
            intent["updated_at"] = _timestamp(now)
            self._records[evidence["id"]] = evidence
            self._append_audit(
                intent, authorization, "payment_outcome_reconciled", "allow",
                ["KNOWN_OUTCOME_RECONCILED"], now, audit_id,
            )
            return Decision(True, ("KNOWN_OUTCOME_RECONCILED",))

    def _append_audit(
        self,
        intent: Mapping[str, Any],
        authorization: Mapping[str, Any],
        action: str,
        decision: str,
        reason_codes: list[str],
        now: datetime,
        event_id: str,
    ) -> None:
        at = _timestamp(now)
        self._records[event_id] = {
            "schema_version": "0.1.0",
            "record_type": "audit_event",
            "id": event_id,
            "tenant_id": intent["tenant_id"],
            "environment": intent["environment"],
            "classification": "synthetic",
            "revision": 1,
            "created_at": at,
            "updated_at": at,
            "subject_id": intent["id"],
            "actor_id": authorization.get("actor_id", intent["id"]),
            "actor_role": authorization.get("actor_role", "finance_approver"),
            "action": action,
            "decision": decision,
            "reason_codes": reason_codes,
            "occurred_at": at,
        }


def _audit_id(payment_id: str, action: str, revision: int) -> str:
    return str(uuid5(_AUDIT_NAMESPACE, f"{payment_id}:{action}:{revision}"))


def _after(value: str, now: datetime) -> bool:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) > now


def _timestamp(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


def _usable_evidence(
    evidence: Mapping[str, Any] | None,
    subject_id: str,
    evidence_type: str,
    tenant_id: str,
    now: datetime,
) -> bool:
    try:
        return bool(
            evidence
            and evidence.get("record_type") == "evidence"
            and evidence.get("tenant_id") == tenant_id
            and evidence.get("subject_id") == subject_id
            and evidence.get("evidence_type") == evidence_type
            and evidence.get("review_status") == "reviewed"
            and evidence.get("execution_status") not in {"unknown", "failed"}
            and _after(evidence["expires_at"], now)
            and datetime.fromisoformat(evidence["reviewed_at"].replace("Z", "+00:00")) <= now
        )
    except (AttributeError, KeyError, TypeError, ValueError):
        return False
