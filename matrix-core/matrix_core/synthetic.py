"""Deterministic, fictional fixtures shared by the demo and benchmark."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid5


_NAMESPACE = UUID("f0da39e8-47d1-4fdb-9be5-4db4cd5fc96f")
NOW = datetime(2026, 11, 8, 13, 0, tzinfo=timezone.utc)
STAMP = "2026-11-08T12:00:00Z"
LATER = "2026-11-09T12:00:00Z"
SCENARIO_CLASSES = (
    "valid", "missing_consent", "expired_consent", "revoked_consent",
    "missing_acceptance", "plan_changed", "missing_check", "stale_configuration",
    "stop_control", "cross_tenant_consent", "unreviewed_evidence",
    "unauthorized_actor",
)


def _id(seed: int, name: str) -> str:
    return str(uuid5(_NAMESPACE, f"{seed}:{name}"))


def _record(kind: str, seed: int, name: str, **fields: Any) -> dict[str, Any]:
    return {
        "schema_version": "0.1.0",
        "record_type": kind,
        "id": _id(seed, name),
        "tenant_id": _id(seed, "tenant"),
        "environment": "synthetic",
        "classification": "synthetic",
        "revision": 1,
        "created_at": STAMP,
        "updated_at": STAMP,
        **fields,
    }


def build_activation_case(seed: int, scenario_class: str = "valid") -> dict[str, Any]:
    if scenario_class not in SCENARIO_CLASSES:
        raise ValueError(f"unknown synthetic scenario class: {scenario_class}")
    tenant_id = _id(seed, "tenant")
    installation_id = _id(seed, "installation")
    participant_id = _id(seed, "participant")
    operator_id = _id(seed, "operator")
    plan_id = _id(seed, "plan-version")
    manifest_id = _id(seed, "equipment-manifest")
    records = [
        _record(
            "installation", seed, "installation", status="draft",
            installation_policy_version="matrix-installation-v0.1.0",
            participant_ids=[participant_id], plan_version_id=plan_id,
            equipment_manifest_version_id=manifest_id,
            required_check_types=["accessibility", "physical_safety"],
            configuration_version="synthetic-config-1", stop_requested=False,
            arena_enabled=True, arena_score=0,
        ),
        _record(
            "participant", seed, "participant", status="active",
        ),
        _record(
            "participant", seed, "operator", status="active",
        ),
        _record(
            "membership", seed, "facilitator-membership",
            installation_id=installation_id, participant_id=operator_id,
            role="facilitator", active=True, valid_until=None,
        ),
        _record(
            "membership", seed, "reviewer-membership",
            installation_id=installation_id, participant_id=operator_id,
            role="safety_reviewer", active=True, valid_until=None,
        ),
        _record(
            "membership", seed, "participant-membership",
            installation_id=installation_id, participant_id=participant_id,
            role="participant", active=True, valid_until=None,
        ),
        _record(
            "consent", seed, "activation-consent",
            installation_id=installation_id, participant_id=participant_id,
            purpose="installation_activation",
            recipient="matrix-core", field_scopes=["installation_status"],
            valid_from=STAMP, expires_at=LATER, revoked_at=None,
        ),
        _record(
            "equipment", seed, "equipment",
            installation_id=installation_id, manifest_version_id=manifest_id,
            items=[{"item_code": "synthetic-display", "configuration_version": "synthetic-config-1"}],
            review_status="reviewed", reviewed_by=operator_id,
            reviewed_at=STAMP, expires_at=LATER,
        ),
        _record(
            "installation_check", seed, "safety-check",
            installation_id=installation_id, check_type="physical_safety",
            status="passed", configuration_version="synthetic-config-1",
            reviewed_by=operator_id, completed_at=STAMP, expires_at=LATER,
        ),
        _record(
            "installation_check", seed, "accessibility-check",
            installation_id=installation_id, check_type="accessibility",
            status="passed", configuration_version="synthetic-config-1",
            reviewed_by=operator_id, completed_at=STAMP, expires_at=LATER,
        ),
        _record(
            "participant_acceptance", seed, "acceptance",
            installation_id=installation_id, participant_id=participant_id,
            plan_version_id=plan_id, equipment_manifest_version_id=manifest_id,
            configuration_version="synthetic-config-1",
            accepted_at=STAMP, withdrawn_at=None,
        ),
    ]
    actor = {"id": operator_id, "tenant_id": tenant_id, "role": "facilitator"}
    by_type = {row["record_type"]: row for row in records}
    if scenario_class == "missing_consent":
        records.remove(by_type["consent"])
    elif scenario_class == "expired_consent":
        by_type["consent"]["expires_at"] = STAMP
    elif scenario_class == "revoked_consent":
        by_type["consent"]["revoked_at"] = STAMP
    elif scenario_class == "missing_acceptance":
        records.remove(by_type["participant_acceptance"])
    elif scenario_class == "plan_changed":
        by_type["installation"]["plan_version_id"] = _id(seed, "changed-plan")
    elif scenario_class == "missing_check":
        records.remove(by_type["installation_check"])
    elif scenario_class == "stale_configuration":
        by_type["installation_check"]["configuration_version"] = "stale-config"
    elif scenario_class == "stop_control":
        by_type["installation"]["stop_requested"] = True
    elif scenario_class == "cross_tenant_consent":
        by_type["consent"]["tenant_id"] = _id(seed, "foreign-tenant")
    elif scenario_class == "unreviewed_evidence":
        records.append(_record(
            "evidence", seed, "unreviewed-evidence", subject_id=installation_id,
            evidence_type="safety_observation", provenance="fictional generated fixture",
            review_status="unreviewed", execution_status="unknown", sha256="a" * 64,
            expires_at=LATER,
            reviewed_by=None, reviewed_at=None,
        ))
    elif scenario_class == "unauthorized_actor":
        actor["role"] = "participant"
    return {
        "case_id": _id(seed, "case"),
        "scenario_class": scenario_class,
        "records": records,
        "installation_id": installation_id,
        "actor": actor,
        "now": NOW,
    }
