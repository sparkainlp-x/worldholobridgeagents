#!/usr/bin/env python3
"""Run a fully synthetic activation, referral, stop, and finance reference flow."""

from __future__ import annotations

from copy import deepcopy
import json

from matrix_core.policy import (
    activate_installation,
    decide_activation,
    decide_referral,
    request_installation_stop,
    withdraw_participant,
)
from matrix_core.store import ReferenceStore, canonical_request_digest
from matrix_core.synthetic import NOW, build_activation_case


TENANT = "10000000-0000-4000-8000-000000000001"
OPERATOR = "40000000-0000-4000-8000-000000000001"
PAYMENT = "90000000-0000-4000-8000-000000000001"
AUTHORIZATION = "a0000000-0000-4000-8000-000000000001"
FUNDING = "70000000-0000-4000-8000-000000000001"
BUDGET = "80000000-0000-4000-8000-000000000001"
STAMP = "2026-11-08T12:00:00Z"
EXPIRY = "2026-11-09T12:00:00Z"


def _record(kind, identifier, tenant_id=TENANT, **fields):
    return {
        "schema_version": "0.1.0", "record_type": kind, "id": identifier,
        "tenant_id": tenant_id, "environment": "synthetic",
        "classification": "synthetic", "revision": 1,
        "created_at": STAMP, "updated_at": STAMP, **fields,
    }


def _finance_records():
    intent = _record(
        "payment_intent", PAYMENT, environment="sandbox", state="draft",
        funding_case_id=FUNDING, budget_line_id=BUDGET, purpose="equipment",
        money={"amount_minor": 1250, "currency": "CAD"},
        idempotency_key="synthetic-demo-key-0001", request_digest="0" * 64,
        authorization_id=AUTHORIZATION, reconciliation_evidence_id=None,
    )
    intent["request_digest"] = canonical_request_digest(intent, OPERATOR, 1)
    auth = _record(
        "authorization", AUTHORIZATION, environment="sandbox", target_id=PAYMENT,
        target_revision=1, request_digest=intent["request_digest"],
        actor_id=OPERATOR, actor_role="finance_approver", expires_at=EXPIRY,
        consumed_at=None,
    )
    return [
        intent,
        auth,
        _record(
            "funding_case", FUNDING, environment="sandbox", status="approved",
            currency="CAD", approved_amount_minor=5000,
            permitted_purposes=["equipment"], eligibility_review_status="reviewed",
            approval_evidence_id="71000000-0000-4000-8000-000000000001",
            eligibility_evidence_id="72000000-0000-4000-8000-000000000001",
        ),
        _record(
            "budget_line", BUDGET, environment="sandbox", funding_case_id=FUNDING,
            purpose="equipment", currency="CAD", limit_minor=5000,
            reserved_minor=0, settled_minor=0,
        ),
        _record(
            "evidence", "71000000-0000-4000-8000-000000000001",
            environment="sandbox", subject_id=FUNDING,
            evidence_type="funding_approval", provenance="synthetic fixture",
            review_status="reviewed", execution_status="not_run",
            sha256="d" * 64, expires_at=EXPIRY,
            reviewed_by=OPERATOR, reviewed_at=STAMP,
        ),
        _record(
            "evidence", "72000000-0000-4000-8000-000000000001",
            environment="sandbox", subject_id=FUNDING,
            evidence_type="eligibility_review", provenance="synthetic fixture",
            review_status="reviewed", execution_status="not_run",
            sha256="e" * 64, expires_at=EXPIRY,
            reviewed_by=OPERATOR, reviewed_at=STAMP,
        ),
    ]


def _view(decision):
    return {"allowed": decision.allowed, "reason_codes": list(decision.reason_codes)}


def run_demo():
    case = build_activation_case(20261108)
    valid_records = case["records"]
    gate_types = {"consent", "equipment", "installation_check", "participant_acceptance"}
    draft = [deepcopy(row) for row in valid_records if row["record_type"] not in gate_types]
    premature = decide_activation(draft, case["installation_id"], case["actor"], NOW)
    completed = draft + [
        deepcopy(row) for row in valid_records if row["record_type"] in gate_types
    ]
    activation, active = activate_installation(
        completed, case["installation_id"], case["actor"], NOW, expected_revision=1,
        audit_event_id="d7000000-0000-4000-8000-000000000001",
    )
    participant_id = next(
        row["participant_ids"][0] for row in active
        if row.get("record_type") == "installation"
    )
    tenant_id = next(row["tenant_id"] for row in active if row["record_type"] == "installation")
    stop, stopped = request_installation_stop(
        active, case["installation_id"],
        {"id": participant_id, "tenant_id": tenant_id, "role": "participant"},
        NOW, "d8000000-0000-4000-8000-000000000001",
    )
    withdrawal, withdrawn = withdraw_participant(
        stopped, case["installation_id"], participant_id,
        {"id": participant_id, "tenant_id": tenant_id, "role": "participant"},
        NOW, "d9000000-0000-4000-8000-000000000001",
    )
    org_id = "b0000000-0000-4000-8000-000000000001"
    engagement_id = "c0000000-0000-4000-8000-000000000001"
    referral_id = "e0000000-0000-4000-8000-000000000001"
    proposal = deepcopy(active) + [
        _record(
            "organization", org_id, name="Synthetic proposed organization",
            tenant_id=tenant_id, jurisdiction="CA-NB",
            verification_evidence_id=None, status="proposed",
        ),
        _record(
            "partner_engagement", engagement_id, organization_id=org_id,
            tenant_id=tenant_id, status="proposed", scope=["exploratory_proposal_only"],
            agreement_evidence_id=None, signer_id=None,
            signer_authority_evidence_id=None, publicity_permission=False,
        ),
        _record(
            "referral", referral_id, installation_id=case["installation_id"],
            tenant_id=tenant_id,
            participant_id=participant_id, organization_id=org_id,
            partner_engagement_id=engagement_id, purpose="accessibility_support",
            recipient="synthetic-provider", field_scopes=["preferred_contact_method"],
            status="proposed",
        ),
    ]
    referral = decide_referral(
        proposal, referral_id, case["actor"], NOW, {"CA-NB"}
    )

    finance = _finance_records()
    unauthorized_payment = ReferenceStore(finance).reserve_payment(
        PAYMENT, {"id": OPERATOR, "tenant_id": TENANT, "role": "participant"}, NOW, 1
    )[0]
    changed = deepcopy(finance)
    changed[0]["money"]["amount_minor"] += 1
    changed_request = ReferenceStore(changed).reserve_payment(
        PAYMENT, {"id": OPERATOR, "tenant_id": TENANT, "role": "finance_approver"},
        NOW, 1,
    )[0]
    replay_records = deepcopy(finance)
    replay = deepcopy(replay_records[0])
    replay.update(
        id="91000000-0000-4000-8000-000000000001",
        idempotency_key="synthetic-demo-key-0002",
    )
    replay["request_digest"] = canonical_request_digest(replay, OPERATOR, 1)
    replay_records.append(replay)
    replay_store = ReferenceStore(replay_records)
    finance_actor = {"id": OPERATOR, "tenant_id": TENANT, "role": "finance_approver"}
    first_reservation = replay_store.reserve_payment(PAYMENT, finance_actor, NOW, 1)[0]
    replayed_authorization = replay_store.reserve_payment(
        replay["id"], finance_actor, NOW, 1
    )[0]

    return {
        "notice": "All identities, records, values, evidence, and outcomes are synthetic; no provider is contacted.",
        "steps": {
            "premature_activation": _view(premature),
            "activation_after_scoped_consent_checks_and_acceptance": _view(activation),
            "participant_stop": _view(stop),
            "participant_withdrawal": _view(withdrawal),
            "referral_with_proposed_engagement": _view(referral),
            "unauthorized_payment": _view(unauthorized_payment),
            "changed_payment_request": _view(changed_request),
            "first_sandbox_reservation": _view(first_reservation),
            "replayed_authorization_for_changed_target": _view(replayed_authorization),
        },
        "final_installation_status": next(
            row["status"] for row in withdrawn if row.get("record_type") == "installation"
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2, sort_keys=True))
