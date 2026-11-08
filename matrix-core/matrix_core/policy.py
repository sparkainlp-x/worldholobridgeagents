"""Pure reference policy decisions; this package never executes payments."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping
import json

from jsonschema import Draft202012Validator, FormatChecker


SCHEMA_PATH = (
    Path(__file__).parents[1] / "schemas" / "v0.1.0" / "core.schema.json"
)
PRIVILEGED_ROLES = {"facilitator", "tenant_admin"}


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason_codes: tuple[str, ...]


def _schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_records(records: Iterable[Mapping[str, Any]]) -> tuple[str, ...]:
    """Return schema and relationship violations without making policy decisions."""
    records = list(records)
    validator = Draft202012Validator(_schema(), format_checker=FormatChecker())
    errors = [
        f"SCHEMA_INVALID:{error.json_path}"
        for record in records
        for error in validator.iter_errors(record)
    ]
    ids = [record.get("id") for record in records]
    if len(ids) != len(set(ids)):
        errors.append("DUPLICATE_RECORD_ID")
    by_id = {record.get("id"): record for record in records}
    for record in records:
        for field in (
            "participant_id", "installation_id", "organization_id",
            "partner_engagement_id", "funding_case_id", "budget_line_id",
            "authorization_id", "subject_id",
        ):
            target_id = record.get(field)
            if target_id is None:
                continue
            target = by_id.get(target_id)
            if target is not None and target.get("tenant_id") != record.get("tenant_id"):
                errors.append("CROSS_TENANT_REFERENCE")
        if record.get("record_type") == "membership":
            installation = by_id.get(record.get("installation_id"))
            participant = by_id.get(record.get("participant_id"))
            if installation and installation.get("record_type") != "installation":
                errors.append("INVALID_INSTALLATION_REFERENCE")
            if participant and participant.get("record_type") != "participant":
                errors.append("INVALID_PARTICIPANT_REFERENCE")
        if record.get("record_type") == "budget_line":
            funding = by_id.get(record.get("funding_case_id"))
            if funding and funding.get("record_type") != "funding_case":
                errors.append("INVALID_FUNDING_REFERENCE")
            if record.get("reserved_minor", 0) + record.get("settled_minor", 0) > record.get(
                "limit_minor", 0
            ):
                errors.append("BUDGET_ACCOUNTING_INVALID")
    return tuple(sorted(set(errors)))


def _decision(errors: list[str]) -> Decision:
    return Decision(not errors, tuple(sorted(set(errors))) or ("POLICY_REQUIREMENTS_MET",))


def decide_activation(
    records: Iterable[Mapping[str, Any]],
    installation_id: str,
    actor: Mapping[str, str],
    now: datetime,
) -> Decision:
    """Evaluate activation against current records and the caller-provided clock."""
    records = list(records)
    validation_errors = list(validate_records(records))
    if validation_errors:
        return _decision(validation_errors)
    by_id = {record["id"]: record for record in records}
    installation = by_id.get(installation_id)
    if not installation or installation.get("record_type") != "installation":
        return _decision(["INSTALLATION_NOT_FOUND"])
    reasons: list[str] = []
    tenant_id = installation["tenant_id"]
    if actor.get("tenant_id") != tenant_id:
        reasons.append("TENANT_MISMATCH")
    memberships = [
        row for row in records
        if row.get("record_type") == "membership"
        and row.get("installation_id") == installation_id
        and row.get("participant_id") == actor.get("id")
        and row.get("tenant_id") == tenant_id
        and row.get("active") is True
        and row.get("role") == actor.get("role")
        and row.get("role") in PRIVILEGED_ROLES
        and (row.get("valid_until") is None or _after(row["valid_until"], now))
    ]
    if not memberships:
        reasons.append("ACTOR_ROLE_UNAUTHORIZED")
    if installation["status"] not in {"draft", "ready"}:
        reasons.append("INVALID_INSTALLATION_STATE")
    if installation["stop_requested"] or installation["status"] == "stopped":
        reasons.append("STOP_CONTROL_ACTIVE")
    if any(
        row.get("record_type") == "evidence"
        and row.get("tenant_id") == tenant_id
        and row.get("subject_id") == installation_id
        and (
            row.get("review_status") != "reviewed"
            or row.get("execution_status") in {"not_run", "unknown", "failed"}
        )
        for row in records
    ):
        reasons.append("EVIDENCE_UNREVIEWED_OR_UNKNOWN")
    participants = installation["participant_ids"]
    for participant_id in participants:
        participant = by_id.get(participant_id)
        if (
            not participant
            or participant.get("record_type") != "participant"
            or participant.get("tenant_id") != tenant_id
            or participant.get("status") != "active"
        ):
            reasons.append("PARTICIPANT_UNAVAILABLE")
            continue
        consents = [
            row for row in records
            if row.get("record_type") == "consent"
            and row.get("participant_id") == participant_id
            and row.get("tenant_id") == tenant_id
            and row.get("purpose") == "installation_activation"
            and row.get("recipient") == "matrix-core"
            and "installation_status" in row.get("field_scopes", [])
            and row.get("revoked_at") is None
            and _at_or_before(row.get("valid_from"), now)
            and _after(row.get("expires_at"), now)
        ]
        if not consents:
            reasons.append("CONSENT_MISSING_EXPIRED_OR_REVOKED")
        acceptances = [
            row for row in records
            if row.get("record_type") == "participant_acceptance"
            and row.get("installation_id") == installation_id
            and row.get("participant_id") == participant_id
            and row.get("tenant_id") == tenant_id
            and row.get("plan_version_id") == installation["plan_version_id"]
            and row.get("equipment_manifest_version_id")
            == installation["equipment_manifest_version_id"]
            and row.get("withdrawn_at") is None
            and _at_or_before(row.get("accepted_at"), now)
        ]
        if not acceptances:
            reasons.append("CURRENT_ACCEPTANCE_MISSING")
    equipment = [
        row for row in records
        if row.get("record_type") == "equipment"
        and row.get("installation_id") == installation_id
        and row.get("tenant_id") == tenant_id
        and row.get("manifest_version_id")
        == installation["equipment_manifest_version_id"]
        and row.get("review_status") == "reviewed"
    ]
    if not equipment:
        reasons.append("EQUIPMENT_MANIFEST_UNREVIEWED_OR_STALE")
    for check_type in installation["required_check_types"]:
        checks = [
            row for row in records
            if row.get("record_type") == "installation_check"
            and row.get("installation_id") == installation_id
            and row.get("tenant_id") == tenant_id
            and row.get("check_type") == check_type
            and row.get("status") == "passed"
            and row.get("configuration_version") == installation["configuration_version"]
            and any(
                membership.get("record_type") == "membership"
                and membership.get("installation_id") == installation_id
                and membership.get("participant_id") == row.get("reviewed_by")
                and membership.get("tenant_id") == tenant_id
                and membership.get("active") is True
                and membership.get("role")
                in {"safety_reviewer", "accessibility_lead", "tenant_admin"}
                and (
                    membership.get("valid_until") is None
                    or _after(membership["valid_until"], now)
                )
                for membership in records
            )
            and _at_or_before(row.get("completed_at"), now)
            and _after(row.get("expires_at"), now)
        ]
        if not checks:
            reasons.append("REQUIRED_CHECK_MISSING_STALE_OR_UNREVIEWED")
    return _decision(reasons)


def decide_referral(
    records: Iterable[Mapping[str, Any]],
    referral_id: str,
    actor: Mapping[str, str],
    now: datetime,
    known_jurisdictions: set[str],
) -> Decision:
    """Check referral enablement separately from publicity permission."""
    records = list(records)
    errors = list(validate_records(records))
    if errors:
        return _decision(errors)
    by_id = {record["id"]: record for record in records}
    referral = by_id.get(referral_id)
    if not referral or referral.get("record_type") != "referral":
        return _decision(["REFERRAL_NOT_FOUND"])
    reasons: list[str] = []
    tenant_id = referral["tenant_id"]
    if actor.get("tenant_id") != tenant_id:
        reasons.append("TENANT_MISMATCH")
    if not any(
        row.get("record_type") == "membership"
        and row.get("installation_id") == referral["installation_id"]
        and row.get("participant_id") == actor.get("id")
        and row.get("tenant_id") == tenant_id
        and row.get("active") is True
        and row.get("role") in {"facilitator", "tenant_admin"}
        and row.get("role") == actor.get("role")
        and (row.get("valid_until") is None or _after(row["valid_until"], now))
        for row in records
    ):
        reasons.append("ACTOR_ROLE_UNAUTHORIZED")
    organization = by_id.get(referral["organization_id"])
    engagement = by_id.get(referral["partner_engagement_id"])
    agreement = by_id.get(engagement.get("agreement_evidence_id")) if engagement else None
    if (
        not organization
        or organization.get("tenant_id") != tenant_id
        or organization.get("status") != "verified"
        or organization.get("jurisdiction") not in known_jurisdictions
    ):
        reasons.append("JURISDICTION_UNKNOWN_OR_ORGANIZATION_UNVERIFIED")
    if (
        not engagement
        or engagement.get("tenant_id") != tenant_id
        or engagement.get("organization_id") != referral["organization_id"]
        or engagement.get("status") != "signed"
        or not agreement
        or agreement.get("tenant_id") != tenant_id
        or agreement.get("evidence_type") != "partner_agreement"
        or agreement.get("review_status") != "reviewed"
        or agreement.get("execution_status") != "passed"
    ):
        reasons.append("PARTNER_AGREEMENT_NOT_VERIFIED")
    if referral["status"] != "enabled":
        reasons.append("REFERRAL_NOT_ENABLED")
    consent_ok = any(
        row.get("record_type") == "consent"
        and row.get("tenant_id") == tenant_id
        and row.get("participant_id") == referral["participant_id"]
        and row.get("purpose") == referral["purpose"]
        and row.get("recipient") == referral["recipient"]
        and set(referral["field_scopes"]).issubset(set(row.get("field_scopes", [])))
        and row.get("revoked_at") is None
        and _at_or_before(row.get("valid_from"), now)
        and _after(row.get("expires_at"), now)
        for row in records
    )
    if not consent_ok:
        reasons.append("REFERRAL_SCOPE_CONSENT_MISSING")
    return _decision(reasons)


def request_installation_stop(
    records: Iterable[Mapping[str, Any]],
    installation_id: str,
    actor: Mapping[str, str],
    now: datetime,
    audit_event_id: str,
) -> tuple[Decision, list[dict[str, Any]]]:
    """Apply an immediate, irreversible stop without consulting financial state."""
    records = [dict(record) for record in records]
    errors = list(validate_records(records))
    if errors:
        return _decision(errors), records
    by_id = {record["id"]: record for record in records}
    installation = by_id.get(installation_id)
    if not installation or installation.get("record_type") != "installation":
        return _decision(["INSTALLATION_NOT_FOUND"]), records
    if actor.get("tenant_id") != installation["tenant_id"]:
        return _decision(["TENANT_MISMATCH"]), records
    is_participant = actor.get("id") in installation["participant_ids"]
    is_operator = any(
        row.get("record_type") == "membership"
        and row.get("installation_id") == installation_id
        and row.get("participant_id") == actor.get("id")
        and row.get("tenant_id") == installation["tenant_id"]
        and row.get("active") is True
        and row.get("role") in PRIVILEGED_ROLES | {"safety_reviewer"}
        and row.get("role") == actor.get("role")
        for row in records
    )
    if not is_participant and not is_operator:
        return _decision(["ACTOR_ROLE_UNAUTHORIZED"]), records
    if installation["status"] in {"stopped", "withdrawn", "closed"}:
        return _decision(["STOP_ALREADY_ACTIVE"]), records
    at = _timestamp(now)
    installation["status"] = "stopped"
    installation["stop_requested"] = True
    installation["revision"] += 1
    installation["updated_at"] = at
    records.append(_audit_event(
        installation, audit_event_id, actor, "installation_stop", "stop", at
    ))
    return _decision([]), records


def withdraw_participant(
    records: Iterable[Mapping[str, Any]],
    installation_id: str,
    participant_id: str,
    actor: Mapping[str, str],
    now: datetime,
    audit_event_id: str,
) -> tuple[Decision, list[dict[str, Any]]]:
    """Withdraw one participant and leave other participants' state untouched."""
    records = [dict(record) for record in records]
    errors = list(validate_records(records))
    if errors:
        return _decision(errors), records
    by_id = {record["id"]: record for record in records}
    installation = by_id.get(installation_id)
    if not installation or installation.get("record_type") != "installation":
        return _decision(["INSTALLATION_NOT_FOUND"]), records
    if actor.get("tenant_id") != installation["tenant_id"]:
        return _decision(["TENANT_MISMATCH"]), records
    if actor.get("id") != participant_id or participant_id not in installation["participant_ids"]:
        return _decision(["PARTICIPANT_WITHDRAWAL_UNAUTHORIZED"]), records
    acceptance = next(
        (
            row for row in records
            if row.get("record_type") == "participant_acceptance"
            and row.get("installation_id") == installation_id
            and row.get("participant_id") == participant_id
            and row.get("tenant_id") == installation["tenant_id"]
            and row.get("withdrawn_at") is None
        ),
        None,
    )
    if acceptance is None:
        return _decision(["CURRENT_ACCEPTANCE_MISSING"]), records
    at = _timestamp(now)
    acceptance["withdrawn_at"] = at
    acceptance["revision"] += 1
    acceptance["updated_at"] = at
    remaining = [item for item in installation["participant_ids"] if item != participant_id]
    if remaining:
        installation["participant_ids"] = remaining
    else:
        installation["status"] = "stopped"
        installation["stop_requested"] = True
    installation["revision"] += 1
    installation["updated_at"] = at
    records.append(_audit_event(
        installation, audit_event_id, actor, "participant_withdrawal", "withdraw", at
    ))
    return _decision([]), records


def _audit_event(
    installation: Mapping[str, Any],
    event_id: str,
    actor: Mapping[str, str],
    action: str,
    decision: str,
    at: str,
) -> dict[str, Any]:
    return {
        "schema_version": "0.1.0",
        "record_type": "audit_event",
        "id": event_id,
        "tenant_id": installation["tenant_id"],
        "environment": installation["environment"],
        "classification": "synthetic",
        "revision": 1,
        "created_at": at,
        "updated_at": at,
        "subject_id": installation["id"],
        "actor_id": actor["id"],
        "actor_role": actor.get("role", "participant"),
        "action": action,
        "decision": decision,
        "reason_codes": [],
        "occurred_at": at,
    }


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _timestamp(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _after(value: str, now: datetime) -> bool:
    return _parse(value) > now


def _at_or_before(value: str, now: datetime) -> bool:
    return _parse(value) <= now
