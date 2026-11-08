"""Pure reference policy decisions; this package never executes payments."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
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


@lru_cache(maxsize=1)
def _schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    schema = _schema()
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate_records(records: Iterable[Mapping[str, Any]]) -> tuple[str, ...]:
    """Return schema and relationship violations without making policy decisions."""
    records = list(records)
    validator = _validator()
    errors = [
        f"SCHEMA_INVALID:{error.json_path}"
        for record in records
        for error in validator.iter_errors(record)
    ]
    safe_records = [record for record in records if isinstance(record, Mapping)]
    if len(safe_records) != len(records):
        errors.append("SCHEMA_INVALID:$")
    if any(error.startswith("SCHEMA_INVALID:") for error in errors):
        return tuple(sorted(set(errors)))
    ids = [record.get("id") for record in safe_records if isinstance(record.get("id"), str)]
    if len(ids) != len(set(ids)):
        errors.append("DUPLICATE_RECORD_ID")
    by_id = {
        record.get("id"): record for record in safe_records
        if isinstance(record.get("id"), str)
    }
    entity_types = {
        record.get("id"): record.get("record_type") for record in safe_records
        if isinstance(record.get("id"), str)
    }
    natural_keys: set[tuple[Any, ...]] = set()
    for record in safe_records:
        for field in (
            "participant_id", "installation_id", "organization_id",
            "partner_engagement_id", "funding_case_id", "budget_line_id",
            "authorization_id", "subject_id",
        ):
            target_id = record.get(field)
            if not isinstance(target_id, str):
                continue
            target = by_id.get(target_id)
            if target is not None and target.get("tenant_id") != record.get("tenant_id"):
                errors.append("CROSS_TENANT_REFERENCE")
            elif target is not None and target.get("environment") != record.get("environment"):
                errors.append("CROSS_ENVIRONMENT_REFERENCE")
        references = {
            "installation": [
                (item, "participant") for item in record.get("participant_ids", [])
            ],
            "membership": [
                (record.get("installation_id"), "installation"),
                (record.get("participant_id"), "participant"),
            ],
            "access_preferences": [(record.get("participant_id"), "participant")],
            "consent": [(record.get("participant_id"), "participant")],
            "equipment": [(record.get("installation_id"), "installation")],
            "installation_check": [(record.get("installation_id"), "installation")],
            "participant_acceptance": [
                (record.get("installation_id"), "installation"),
                (record.get("participant_id"), "participant"),
            ],
            "partner_engagement": [(record.get("organization_id"), "organization")],
            "organization": [
                (record.get("verification_evidence_id"), "evidence")
            ],
            "referral": [
                (record.get("installation_id"), "installation"),
                (record.get("participant_id"), "participant"),
                (record.get("organization_id"), "organization"),
                (record.get("partner_engagement_id"), "partner_engagement"),
            ],
            "budget_line": [(record.get("funding_case_id"), "funding_case")],
            "funding_case": [
                (record.get("approval_evidence_id"), "evidence"),
                (record.get("eligibility_evidence_id"), "evidence"),
            ],
            "payment_intent": [
                (record.get("funding_case_id"), "funding_case"),
                (record.get("budget_line_id"), "budget_line"),
                (record.get("authorization_id"), "authorization"),
                (record.get("reconciliation_evidence_id"), "evidence"),
            ],
            "revenue_allocation": [
                *[
                    (item, "funding_case")
                    for item in record.get("funding_case_ids", [])
                ],
                (record.get("policy_approval_evidence_id"), "evidence"),
                (record.get("funding_review_evidence_id"), "evidence"),
            ],
            "authorization": [(record.get("target_id"), "payment_intent")],
            "audit_event": [(record.get("subject_id"), None)],
            "evidence": [(record.get("subject_id"), None)],
        }.get(record.get("record_type"), [])
        for target_id, expected_type in references:
            if not isinstance(target_id, str):
                continue
            target = by_id.get(target_id)
            if target is None:
                errors.append("RELATIONSHIP_TARGET_MISSING")
            elif expected_type and entity_types.get(target_id) != expected_type:
                errors.append("RELATIONSHIP_TARGET_TYPE_INVALID")
            elif target.get("tenant_id") != record.get("tenant_id"):
                errors.append("CROSS_TENANT_REFERENCE")
            elif target.get("environment") != record.get("environment"):
                errors.append("CROSS_ENVIRONMENT_REFERENCE")
        if record.get("record_type") == "partner_engagement":
            evidence_id = record.get("agreement_evidence_id")
            if evidence_id:
                evidence = by_id.get(evidence_id)
                if not evidence or evidence.get("record_type") != "evidence":
                    errors.append("PARTNER_AGREEMENT_EVIDENCE_MISSING")
                elif (
                    evidence.get("tenant_id") != record.get("tenant_id")
                    or evidence.get("subject_id") != record.get("id")
                    or evidence.get("evidence_type") != "partner_agreement"
                ):
                    errors.append("PARTNER_AGREEMENT_EVIDENCE_MISMATCH")
            authority_id = record.get("signer_authority_evidence_id")
            if authority_id:
                authority = by_id.get(authority_id)
                if not authority or authority.get("record_type") != "evidence":
                    errors.append("SIGNER_AUTHORITY_EVIDENCE_MISSING")
                elif (
                    authority.get("tenant_id") != record.get("tenant_id")
                    or authority.get("subject_id") != record.get("organization_id")
                    or authority.get("evidence_type") != "signer_authority"
                ):
                    errors.append("SIGNER_AUTHORITY_EVIDENCE_MISMATCH")
        if record.get("record_type") == "payment_intent":
            evidence_id = record.get("reconciliation_evidence_id")
            if evidence_id:
                evidence = by_id.get(evidence_id)
                if (
                    not evidence
                    or evidence.get("record_type") != "evidence"
                    or evidence.get("tenant_id") != record.get("tenant_id")
                    or evidence.get("subject_id") != record.get("id")
                    or evidence.get("evidence_type") != "payment_reconciliation"
                ):
                    errors.append("PAYMENT_RECONCILIATION_EVIDENCE_MISMATCH")
        evidence_references = []
        if record.get("record_type") == "organization":
            evidence_references.append((
                record.get("verification_evidence_id"), record.get("id"),
                "organization_verification",
            ))
        if record.get("record_type") == "funding_case":
            evidence_references.extend([
                (record.get("approval_evidence_id"), record.get("id"), "funding_approval"),
                (record.get("eligibility_evidence_id"), record.get("id"), "eligibility_review"),
            ])
        if record.get("record_type") == "revenue_allocation":
            evidence_references.extend([
                (
                    record.get("policy_approval_evidence_id"), record.get("id"),
                    "revenue_policy_approval",
                ),
                (
                    record.get("funding_review_evidence_id"), record.get("id"),
                    "funding_restriction_review",
                ),
            ])
        for evidence_id, subject_id, evidence_type in evidence_references:
            if evidence_id is None:
                continue
            evidence = by_id.get(evidence_id)
            if (
                not evidence
                or evidence.get("record_type") != "evidence"
                or evidence.get("tenant_id") != record.get("tenant_id")
                or evidence.get("subject_id") != subject_id
                or evidence.get("evidence_type") != evidence_type
            ):
                errors.append("LINKED_EVIDENCE_MISSING_OR_MISMATCHED")
        if record.get("record_type") == "membership" and record.get("active"):
            key = (
                record.get("installation_id"), record.get("participant_id"),
                record.get("role"),
            )
            if all(isinstance(value, str) for value in key):
                if key in natural_keys:
                    errors.append("DUPLICATE_ACTIVE_MEMBERSHIP")
                natural_keys.add(key)
        if (
            record.get("record_type") == "participant_acceptance"
            and record.get("withdrawn_at") is None
        ):
            key = (
                record.get("installation_id"), record.get("participant_id"),
                record.get("plan_version_id"),
                record.get("equipment_manifest_version_id"),
            )
            if all(isinstance(value, str) for value in key):
                if key in natural_keys:
                    errors.append("DUPLICATE_CURRENT_ACCEPTANCE")
                natural_keys.add(key)
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
            reserved = record.get("reserved_minor")
            settled = record.get("settled_minor")
            limit = record.get("limit_minor")
            if (
                type(reserved) is int and type(settled) is int and type(limit) is int
                and reserved + settled > limit
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
    if not _aware(now):
        return _decision(["CLOCK_NOT_TIMEZONE_AWARE"])
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
            or not _after(row.get("expires_at"), now)
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
        and _after(row.get("expires_at"), now)
        and _at_or_before(row.get("reviewed_at"), now)
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
    if not _aware(now):
        return _decision(["CLOCK_NOT_TIMEZONE_AWARE"])
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
    participant = by_id.get(referral["participant_id"])
    organization_evidence = (
        by_id.get(organization.get("verification_evidence_id")) if organization else None
    )
    installation = by_id.get(referral["installation_id"])
    engagement = by_id.get(referral["partner_engagement_id"])
    agreement = by_id.get(engagement.get("agreement_evidence_id")) if engagement else None
    signer_authority = (
        by_id.get(engagement.get("signer_authority_evidence_id")) if engagement else None
    )
    authorized_reviewers = {
        row.get("participant_id")
        for row in records
        if row.get("record_type") == "membership"
        and row.get("installation_id") == referral["installation_id"]
        and row.get("tenant_id") == tenant_id
        and row.get("role") == "tenant_admin"
        and row.get("active") is True
        and (row.get("valid_until") is None or _after(row["valid_until"], now))
    }
    if (
        not organization
        or organization.get("tenant_id") != tenant_id
        or organization.get("status") != "verified"
        or organization.get("jurisdiction") not in known_jurisdictions
        or not organization_evidence
        or organization_evidence.get("tenant_id") != tenant_id
        or organization_evidence.get("evidence_type") != "organization_verification"
        or organization_evidence.get("subject_id") != organization.get("id")
        or organization_evidence.get("review_status") != "reviewed"
        or organization_evidence.get("execution_status") in {"unknown", "failed"}
        or not _after(organization_evidence.get("expires_at"), now)
        or not _at_or_before(organization_evidence.get("reviewed_at"), now)
        or organization_evidence.get("reviewed_by") not in {
            row.get("participant_id") for row in records
            if row.get("record_type") == "membership"
            and row.get("installation_id") == referral["installation_id"]
            and row.get("tenant_id") == tenant_id
            and row.get("role") == "tenant_admin"
            and row.get("active") is True
            and (row.get("valid_until") is None or _after(row["valid_until"], now))
        }
    ):
        reasons.append("JURISDICTION_UNKNOWN_OR_ORGANIZATION_UNVERIFIED")
    if (
        not installation
        or installation.get("tenant_id") != tenant_id
        or installation.get("status") != "active"
        or installation.get("stop_requested") is True
        or referral["participant_id"] not in installation.get("participant_ids", [])
        or not participant
        or participant.get("tenant_id") != tenant_id
        or participant.get("status") != "active"
    ):
        reasons.append("INSTALLATION_OR_PARTICIPANT_NOT_ACTIVE")
    required_scope = {
        "accessibility_support": "referral:accessibility",
        "device_setup": "referral:device_setup",
        "learning_access": "referral:learning_access",
    }.get(referral["purpose"])
    if engagement and required_scope not in engagement.get("scope", []):
        reasons.append("PARTNER_SCOPE_INSUFFICIENT")
    if (
        not engagement
        or engagement.get("tenant_id") != tenant_id
        or engagement.get("organization_id") != referral["organization_id"]
        or engagement.get("status") != "signed"
        or not agreement
        or agreement.get("tenant_id") != tenant_id
        or agreement.get("evidence_type") != "partner_agreement"
        or agreement.get("review_status") != "reviewed"
        or agreement.get("execution_status") in {"unknown", "failed"}
        or agreement.get("subject_id") != engagement.get("id")
        or not _after(agreement.get("expires_at"), now)
        or not _at_or_before(agreement.get("reviewed_at"), now)
        or agreement.get("reviewed_by") not in authorized_reviewers
        or not signer_authority
        or signer_authority.get("tenant_id") != tenant_id
        or signer_authority.get("evidence_type") != "signer_authority"
        or signer_authority.get("subject_id") != engagement.get("organization_id")
        or signer_authority.get("review_status") != "reviewed"
        or signer_authority.get("execution_status") in {"unknown", "failed"}
        or not _after(signer_authority.get("expires_at"), now)
        or not _at_or_before(signer_authority.get("reviewed_at"), now)
        or signer_authority.get("reviewed_by") not in authorized_reviewers
        or not engagement.get("signer_id")
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


def decide_revenue_allocation(
    records: Iterable[Mapping[str, Any]], allocation_id: str, now: datetime
) -> Decision:
    """Authorize only an explicitly approved, reviewed, non-benefit allocation."""
    if not _aware(now):
        return _decision(["CLOCK_NOT_TIMEZONE_AWARE"])
    records = list(records)
    errors = list(validate_records(records))
    if errors:
        return _decision(errors)
    by_id = {record["id"]: record for record in records}
    allocation = by_id.get(allocation_id)
    if not allocation or allocation.get("record_type") != "revenue_allocation":
        return _decision(["REVENUE_ALLOCATION_NOT_FOUND"])
    if not allocation["enabled"]:
        return _decision(["REVENUE_ALLOCATION_DISABLED"])
    reasons: list[str] = []
    if not allocation["policy_approved"]:
        reasons.append("REVENUE_POLICY_NOT_APPROVED")
    if not allocation["funding_restrictions_reviewed"]:
        reasons.append("FUNDING_RESTRICTIONS_UNREVIEWED")
    if allocation["participant_benefit_deductions"]:
        reasons.append("PARTICIPANT_BENEFIT_DEDUCTION_PROHIBITED")
    compensation = allocation["contractual_compensation_minor"]
    eligible = allocation["eligible_revenue_minor"]
    amount = eligible * allocation["allocation_basis_points"] // 10000
    if compensation <= 0 or amount > eligible - compensation:
        reasons.append("CONTRACTUAL_COMPENSATION_OR_REVENUE_BASIS_INVALID")
    if not _evidence_is_current(
        by_id.get(allocation["policy_approval_evidence_id"]),
        allocation["id"], "revenue_policy_approval", allocation["tenant_id"], now,
    ):
        reasons.append("REVENUE_POLICY_EVIDENCE_MISSING_EXPIRED_OR_UNREVIEWED")
    if not _evidence_is_current(
        by_id.get(allocation["funding_review_evidence_id"]),
        allocation["id"], "funding_restriction_review", allocation["tenant_id"], now,
    ):
        reasons.append("FUNDING_RESTRICTION_EVIDENCE_MISSING_EXPIRED_OR_UNREVIEWED")
    for funding_id in allocation["funding_case_ids"]:
        funding = by_id[funding_id]
        if (
            funding.get("tenant_id") != allocation["tenant_id"]
            or funding.get("currency") != allocation["currency"]
            or funding.get("environment") != allocation["environment"]
            or funding.get("status") != "approved"
            or funding.get("eligibility_review_status") != "reviewed"
        ):
            reasons.append("FUNDING_RESTRICTIONS_UNVERIFIED")
            continue
        if not all(
            _evidence_is_current(
                by_id.get(evidence_id), funding["id"], evidence_type,
                funding["tenant_id"], now,
            )
            for evidence_id, evidence_type in (
                (funding["approval_evidence_id"], "funding_approval"),
                (funding["eligibility_evidence_id"], "eligibility_review"),
            )
        ):
            reasons.append("FUNDING_EVIDENCE_MISSING_EXPIRED_OR_UNREVIEWED")
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
    if not _aware(now):
        return _decision(["CLOCK_NOT_TIMEZONE_AWARE"]), records
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
    event = _audit_event(
        installation, audit_event_id, actor, "installation_stop", "stop", at
    )
    event_errors = validate_records([*records, event])
    if event_errors:
        return _decision(list(event_errors)), records
    installation["status"] = "stopped"
    installation["stop_requested"] = True
    installation["revision"] += 1
    installation["updated_at"] = at
    records.append(event)
    return _decision([]), records


def activate_installation(
    records: Iterable[Mapping[str, Any]],
    installation_id: str,
    actor: Mapping[str, str],
    now: datetime,
    expected_revision: int,
    audit_event_id: str,
) -> tuple[Decision, list[dict[str, Any]]]:
    """Apply activation only when the current snapshot passes every policy gate."""
    records = [dict(record) for record in records]
    decision = decide_activation(records, installation_id, actor, now)
    if not decision.allowed:
        return decision, records
    installation = next(
        row for row in records
        if row.get("id") == installation_id and row.get("record_type") == "installation"
    )
    if installation["revision"] != expected_revision:
        return _decision(["STALE_REVISION"]), records
    event = _audit_event(
        installation, audit_event_id, actor, "installation_activation", "allow",
        _timestamp(now),
    )
    event_errors = validate_records([*records, event])
    if event_errors:
        return _decision(list(event_errors)), records
    at = _timestamp(now)
    installation["status"] = "active"
    installation["revision"] += 1
    installation["updated_at"] = at
    records.append(event)
    return decision, records


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
    if not _aware(now):
        return _decision(["CLOCK_NOT_TIMEZONE_AWARE"]), records
    errors = list(validate_records(records))
    if errors:
        return _decision(errors), records
    by_id = {record["id"]: record for record in records}
    installation = by_id.get(installation_id)
    if not installation or installation.get("record_type") != "installation":
        return _decision(["INSTALLATION_NOT_FOUND"]), records
    if installation["status"] in {"withdrawn", "closed"}:
        return _decision(["INVALID_INSTALLATION_STATE"]), records
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
    event = _audit_event(
        installation, audit_event_id, actor, "participant_withdrawal", "withdraw", at
    )
    event_errors = validate_records([*records, event])
    if event_errors:
        return _decision(list(event_errors)), records
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
    records.append(event)
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
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _timestamp(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


def _evidence_is_current(
    evidence: Mapping[str, Any] | None,
    subject_id: str,
    evidence_type: str,
    tenant_id: str,
    now: datetime,
) -> bool:
    return bool(
        evidence
        and evidence.get("record_type") == "evidence"
        and evidence.get("tenant_id") == tenant_id
        and evidence.get("subject_id") == subject_id
        and evidence.get("evidence_type") == evidence_type
        and evidence.get("review_status") == "reviewed"
        and evidence.get("execution_status") not in {"unknown", "failed"}
        and _after(evidence["expires_at"], now)
        and _at_or_before(evidence["reviewed_at"], now)
    )


def _after(value: str, now: datetime) -> bool:
    try:
        return _parse(value) > now
    except (TypeError, ValueError):
        return False


def _at_or_before(value: str, now: datetime) -> bool:
    try:
        return _parse(value) <= now
    except (TypeError, ValueError):
        return False
