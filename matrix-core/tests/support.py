from copy import deepcopy
from datetime import datetime, timezone

from matrix_core.store import canonical_request_digest


NOW = datetime(2026, 11, 8, 13, 0, tzinfo=timezone.utc)
STAMP = "2026-11-08T12:00:00Z"
LATER = "2026-11-09T12:00:00Z"
TENANT = "10000000-0000-4000-8000-000000000001"
INSTALLATION = "20000000-0000-4000-8000-000000000001"
PARTICIPANT = "30000000-0000-4000-8000-000000000001"
FACILITATOR = "40000000-0000-4000-8000-000000000001"
PLAN = "50000000-0000-4000-8000-000000000001"
MANIFEST = "60000000-0000-4000-8000-000000000001"
FUNDING = "70000000-0000-4000-8000-000000000001"
BUDGET = "80000000-0000-4000-8000-000000000001"
PAYMENT = "90000000-0000-4000-8000-000000000001"
AUTHORIZATION = "a0000000-0000-4000-8000-000000000001"


def record(record_type, identifier, **fields):
    return {
        "schema_version": "0.1.0",
        "record_type": record_type,
        "id": identifier,
        "tenant_id": TENANT,
        "environment": "synthetic",
        "classification": "synthetic",
        "revision": 1,
        "created_at": STAMP,
        "updated_at": STAMP,
        **fields,
    }


def activation_records():
    return [
        record(
            "installation", INSTALLATION, status="draft",
            participant_ids=[PARTICIPANT], plan_version_id=PLAN,
            equipment_manifest_version_id=MANIFEST,
            required_check_types=["physical_safety"],
            configuration_version="cfg-1", stop_requested=False,
            arena_enabled=True, arena_score=0,
        ),
        record("participant", PARTICIPANT, display_label="Synthetic participant", status="active"),
        record(
            "membership", "41000000-0000-4000-8000-000000000001",
            installation_id=INSTALLATION, participant_id=FACILITATOR,
            role="facilitator", active=True, valid_until=None,
        ),
        record(
            "membership", "42000000-0000-4000-8000-000000000001",
            installation_id=INSTALLATION, participant_id=FACILITATOR,
            role="safety_reviewer", active=True, valid_until=None,
        ),
        record(
            "consent", "51000000-0000-4000-8000-000000000001",
            participant_id=PARTICIPANT, purpose="installation_activation",
            recipient="matrix-core", field_scopes=["installation_status"],
            valid_from=STAMP, expires_at=LATER, revoked_at=None,
        ),
        record(
            "equipment", "61000000-0000-4000-8000-000000000001",
            installation_id=INSTALLATION, manifest_version_id=MANIFEST,
            items=[{"item_code": "display-1", "configuration_version": "cfg-1"}],
            review_status="reviewed",
        ),
        record(
            "installation_check", "62000000-0000-4000-8000-000000000001",
            installation_id=INSTALLATION, check_type="physical_safety",
            status="passed", configuration_version="cfg-1",
            reviewed_by=FACILITATOR, completed_at=STAMP, expires_at=LATER,
        ),
        record(
            "participant_acceptance", "52000000-0000-4000-8000-000000000001",
            installation_id=INSTALLATION, participant_id=PARTICIPANT,
            plan_version_id=PLAN, equipment_manifest_version_id=MANIFEST,
            accepted_at=STAMP, withdrawn_at=None,
        ),
    ]


def actor(role="facilitator", tenant=TENANT):
    return {"id": FACILITATOR, "tenant_id": tenant, "role": role}


def finance_records(amount=100, limit=150):
    intent = record(
        "payment_intent", PAYMENT, environment="sandbox", state="draft",
        funding_case_id=FUNDING, budget_line_id=BUDGET, purpose="equipment",
        money={"amount_minor": amount, "currency": "CAD"},
        idempotency_key="synthetic-key-0001", request_digest="0" * 64,
        authorization_id=AUTHORIZATION,
    )
    intent["request_digest"] = canonical_request_digest(
        intent, FACILITATOR, intent["revision"]
    )
    authorization = record(
        "authorization", AUTHORIZATION, environment="sandbox",
        target_id=PAYMENT, target_revision=1,
        request_digest=intent["request_digest"], actor_id=FACILITATOR,
        actor_role="finance_approver", expires_at=LATER, consumed_at=None,
    )
    return [
        intent,
        authorization,
        record(
            "funding_case", FUNDING, status="approved", currency="CAD",
            approved_amount_minor=limit, permitted_purposes=["equipment"],
            eligibility_review_status="reviewed",
        ),
        record(
            "budget_line", BUDGET, funding_case_id=FUNDING, purpose="equipment",
            currency="CAD", limit_minor=limit, reserved_minor=0, settled_minor=0,
        ),
    ]


def referral_records():
    installation_id = INSTALLATION
    organization_id = "b0000000-0000-4000-8000-000000000001"
    engagement_id = "c0000000-0000-4000-8000-000000000001"
    evidence_id = "d0000000-0000-4000-8000-000000000001"
    referral_id = "e0000000-0000-4000-8000-000000000001"
    records = activation_records()
    records.extend([
        record(
            "organization", organization_id, name="Synthetic organization",
            jurisdiction="CA-NB", status="verified",
        ),
        record(
            "evidence", evidence_id, subject_id=engagement_id,
            evidence_type="partner_agreement", provenance="synthetic fixture",
            review_status="reviewed", execution_status="passed",
            sha256="a" * 64, reviewed_by=FACILITATOR, reviewed_at=STAMP,
        ),
        record(
            "partner_engagement", engagement_id, organization_id=organization_id,
            status="signed", scope=["referral:accessibility"], agreement_evidence_id=evidence_id,
            publicity_permission=False,
        ),
        record(
            "referral", referral_id, installation_id=installation_id,
            participant_id=PARTICIPANT, organization_id=organization_id,
            partner_engagement_id=engagement_id, purpose="accessibility_support",
            recipient="synthetic-provider", field_scopes=["preferred_contact_method"],
            status="enabled",
        ),
        record(
            "consent", "f0000000-0000-4000-8000-000000000001",
            participant_id=PARTICIPANT, purpose="accessibility_support",
            recipient="synthetic-provider", field_scopes=["preferred_contact_method"],
            valid_from=STAMP, expires_at=LATER, revoked_at=None,
        ),
    ])
    return records, referral_id


def clone(records):
    return deepcopy(records)
