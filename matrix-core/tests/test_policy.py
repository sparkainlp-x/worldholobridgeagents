import unittest

from matrix_core.policy import (
    activate_installation,
    decide_activation,
    decide_referral,
    decide_revenue_allocation,
    request_installation_stop,
    validate_records,
    withdraw_participant,
)
from support import (
    FACILITATOR,
    INSTALLATION,
    LATER,
    NOW,
    PARTICIPANT,
    TENANT,
    FUNDING,
    activation_records,
    actor,
    finance_records,
    referral_records,
    record,
)


class ActivationPolicyTests(unittest.TestCase):
    def decide(self, records, caller=None):
        return decide_activation(records, INSTALLATION, caller or actor(), NOW)

    def test_complete_current_synthetic_installation_is_allowed(self):
        decision = self.decide(activation_records())
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.reason_codes, ("POLICY_REQUIREMENTS_MET",))

    def test_reference_activation_records_audited_active_state(self):
        decision, records = activate_installation(
            activation_records(), INSTALLATION, actor(), NOW, expected_revision=1,
            audit_event_id="d7000000-0000-4000-8000-000000000001",
        )
        self.assertTrue(decision.allowed)
        installation = next(row for row in records if row["record_type"] == "installation")
        self.assertEqual(installation["status"], "active")
        self.assertEqual(installation["revision"], 2)
        self.assertTrue(any(
            row.get("record_type") == "audit_event" and row["action"] == "installation_activation"
            for row in records
        ))
        stale, unchanged = activate_installation(
            activation_records(), INSTALLATION, actor(), NOW, expected_revision=2,
            audit_event_id="d7000000-0000-4000-8000-000000000002",
        )
        self.assertIn("STALE_REVISION", stale.reason_codes)
        self.assertEqual(
            next(row for row in unchanged if row["record_type"] == "installation")["status"],
            "draft",
        )

    def test_draft_installation_without_gates_is_denied(self):
        records = activation_records()
        records = records[:2]
        decision = self.decide(records)
        self.assertFalse(decision.allowed)
        self.assertIn("ACTOR_ROLE_UNAUTHORIZED", decision.reason_codes)
        self.assertIn("CONSENT_MISSING_EXPIRED_OR_REVOKED", decision.reason_codes)
        self.assertIn("CURRENT_ACCEPTANCE_MISSING", decision.reason_codes)

    def test_consent_expiry_revocation_and_withdrawal_are_boundaries(self):
        for field, value in (("expires_at", "2026-11-08T13:00:00Z"), ("revoked_at", LATER)):
            records = activation_records()
            next(row for row in records if row["record_type"] == "consent")[field] = value
            self.assertIn("CONSENT_MISSING_EXPIRED_OR_REVOKED", self.decide(records).reason_codes)
        records = activation_records()
        acceptance = next(row for row in records if row["record_type"] == "participant_acceptance")
        acceptance["withdrawn_at"] = "2026-11-08T12:30:00Z"
        self.assertIn("CURRENT_ACCEPTANCE_MISSING", self.decide(records).reason_codes)

    def test_missing_stale_unreviewed_or_unreviewed_by_role_check_denies(self):
        records = activation_records()
        records = [row for row in records if row["record_type"] != "installation_check"]
        self.assertIn("REQUIRED_CHECK_MISSING_STALE_OR_UNREVIEWED", self.decide(records).reason_codes)
        records = activation_records()
        check = next(row for row in records if row["record_type"] == "installation_check")
        check["configuration_version"] = "old-config"
        self.assertIn("REQUIRED_CHECK_MISSING_STALE_OR_UNREVIEWED", self.decide(records).reason_codes)
        records = activation_records()
        records = [row for row in records if not (
            row["record_type"] == "membership"
            and row["role"] in {"safety_reviewer", "accessibility_lead", "tenant_admin"}
        )]
        self.assertIn("REQUIRED_CHECK_MISSING_STALE_OR_UNREVIEWED", self.decide(records).reason_codes)

    def test_expired_equipment_review_denies(self):
        records = activation_records()
        equipment = next(row for row in records if row["record_type"] == "equipment")
        equipment["expires_at"] = "2026-11-08T13:00:00Z"
        self.assertIn(
            "EQUIPMENT_MANIFEST_UNREVIEWED_OR_STALE",
            self.decide(records).reason_codes,
        )

    def test_rejected_or_conflicting_current_checks_and_equipment_deny(self):
        records = activation_records()
        check = next(
            row for row in records
            if row.get("record_type") == "installation_check"
            and row.get("check_type") == "physical_safety"
        )
        conflicting = {
            **check, "id": "64000000-0000-4000-8000-000000000001",
            "status": "failed",
        }
        records.append(conflicting)
        self.assertIn(
            "REQUIRED_CHECK_MISSING_STALE_OR_UNREVIEWED",
            self.decide(records).reason_codes,
        )
        records = activation_records()
        equipment = next(row for row in records if row.get("record_type") == "equipment")
        records.append({
            **equipment, "id": "65000000-0000-4000-8000-000000000001",
            "review_status": "rejected",
        })
        self.assertIn(
            "EQUIPMENT_MANIFEST_UNREVIEWED_OR_STALE",
            self.decide(records).reason_codes,
        )

    def test_plan_or_equipment_change_invalidates_acceptance(self):
        for field in ("plan_version_id", "equipment_manifest_version_id"):
            records = activation_records()
            installation = next(row for row in records if row["record_type"] == "installation")
            installation[field] = "f1000000-0000-4000-8000-000000000001"
            self.assertIn("CURRENT_ACCEPTANCE_MISSING", self.decide(records).reason_codes)

    def test_stop_control_blocks_activation_independent_of_finance(self):
        for field, value in (("stop_requested", True), ("status", "stopped")):
            records = activation_records()
            next(row for row in records if row["record_type"] == "installation")[field] = value
            self.assertIn("STOP_CONTROL_ACTIVE", self.decide(records).reason_codes)

    def test_tenant_role_evidence_and_arena_cannot_bypass_gates(self):
        self.assertIn(
            "TENANT_MISMATCH",
            self.decide(activation_records(), actor(tenant="11000000-0000-4000-8000-000000000001")).reason_codes,
        )
        self.assertIn("ACTOR_ROLE_UNAUTHORIZED", self.decide(activation_records(), actor("participant")).reason_codes)
        records = activation_records()
        records[0]["arena_score"] = 999999
        allowed_score = self.decide(records).allowed
        records[0]["arena_score"] = 0
        self.assertEqual(allowed_score, self.decide(records).allowed)
        records = activation_records()
        records.append({
            "schema_version": "0.1.0", "record_type": "evidence",
            "id": "d2000000-0000-4000-8000-000000000001", "tenant_id": TENANT,
            "environment": "synthetic", "classification": "synthetic", "revision": 1,
            "created_at": "2026-11-08T12:00:00Z", "updated_at": "2026-11-08T12:00:00Z",
            "subject_id": INSTALLATION, "evidence_type": "safety", "provenance": "synthetic",
            "review_status": "unreviewed", "execution_status": "unknown", "sha256": "b" * 64,
            "expires_at": LATER,
            "reviewed_by": None, "reviewed_at": None,
        })
        self.assertIn("EVIDENCE_UNREVIEWED_OR_UNKNOWN", self.decide(records).reason_codes)
        records[-1]["review_status"] = "reviewed"
        records[-1]["execution_status"] = "passed"
        records[-1]["reviewed_by"] = FACILITATOR
        records[-1]["reviewed_at"] = "2026-11-08T12:00:00Z"
        records[-1]["expires_at"] = "2026-11-08T12:59:59Z"
        self.assertIn("EVIDENCE_UNREVIEWED_OR_UNKNOWN", self.decide(records).reason_codes)

    def test_seeded_time_boundaries_never_accept_expired_consent(self):
        for minute in range(0, 60, 3):
            records = activation_records()
            consent = next(row for row in records if row["record_type"] == "consent")
            consent["expires_at"] = f"2026-11-08T12:{minute:02d}:00Z"
            self.assertFalse(self.decide(records).allowed, f"minute {minute}")


class ReferralPolicyTests(unittest.TestCase):
    def setUp(self):
        self.records, self.referral_id = referral_records()

    def decide(self, known=None):
        return decide_referral(
            self.records, self.referral_id, actor(), NOW, known or {"CA-NB"}
        )

    def test_signed_agreement_and_exact_scope_are_separate_from_publicity(self):
        self.assertTrue(self.decide().allowed)
        engagement = next(row for row in self.records if row["record_type"] == "partner_engagement")
        self.assertFalse(engagement["publicity_permission"])
        engagement["publicity_permission"] = True
        self.assertTrue(self.decide().allowed)

    def test_referral_must_fit_the_signed_engagement_scope(self):
        engagement = next(row for row in self.records if row["record_type"] == "partner_engagement")
        engagement["scope"] = ["equipment_provision"]
        self.assertIn("PARTNER_AGREEMENT_SCOPE_MISMATCH", self.decide().reason_codes)
        next(row for row in self.records if row.get("evidence_type") == "partner_agreement")[
            "authorized_scope"
        ] = ["equipment_provision"]
        self.assertIn("PARTNER_SCOPE_INSUFFICIENT", self.decide().reason_codes)

    def test_signer_authority_and_agreement_review_must_be_current(self):
        authority = next(
            row for row in self.records
            if row.get("evidence_type") == "signer_authority"
        )
        authority["review_status"] = "unreviewed"
        self.assertIn("PARTNER_AGREEMENT_NOT_VERIFIED", self.decide().reason_codes)
        authority["review_status"] = "reviewed"
        authority["expires_at"] = "2026-11-08T13:00:00Z"
        self.assertIn("PARTNER_AGREEMENT_NOT_VERIFIED", self.decide().reason_codes)
        authority["expires_at"] = LATER
        authority["reviewed_at"] = None
        self.assertTrue(any(
            reason.startswith("SCHEMA_INVALID:")
            for reason in self.decide().reason_codes
        ))

    def test_signer_authority_must_match_engagement_signer(self):
        authority = next(
            row for row in self.records
            if row.get("evidence_type") == "signer_authority"
        )
        authority["authorized_signer_id"] = "41000000-0000-4000-8000-000000000001"
        self.assertIn("SIGNER_AUTHORITY_EVIDENCE_MISMATCH", self.decide().reason_codes)

    def test_proposed_engagement_does_not_authorize_referral(self):
        engagement = next(row for row in self.records if row["record_type"] == "partner_engagement")
        engagement.update(
            status="proposed", scope=[], agreement_evidence_id=None, signer_id=None,
            signer_authority_evidence_id=None,
        )
        self.records = [
            row for row in self.records
            if row.get("evidence_type") not in {"partner_agreement", "signer_authority"}
        ]
        self.assertIn("PARTNER_AGREEMENT_NOT_VERIFIED", self.decide().reason_codes)

    def test_inactive_participant_cannot_be_referred(self):
        next(row for row in self.records if row["record_type"] == "participant")["status"] = "inactive"
        self.assertIn(
            "INSTALLATION_OR_PARTICIPANT_NOT_ACTIVE",
            self.decide().reason_codes,
        )

    def test_scope_escalation_or_unknown_jurisdiction_denies(self):
        referral = next(row for row in self.records if row["record_type"] == "referral")
        referral["field_scopes"].append("diagnostic_details")
        self.assertTrue(any(
            reason.startswith("SCHEMA_INVALID:")
            for reason in self.decide().reason_codes
        ))
        referral["field_scopes"].pop()
        self.records.remove(next(
            row for row in self.records
            if row["record_type"] == "consent"
            and row["purpose"] == "accessibility_support"
        ))
        self.assertIn("REFERRAL_SCOPE_CONSENT_MISSING", self.decide().reason_codes)
        self.assertIn(
            "JURISDICTION_UNKNOWN_OR_ORGANIZATION_UNVERIFIED",
            self.decide({"UNKNOWN"}).reason_codes,
        )
        records, referral_id = referral_records()
        referral = next(row for row in records if row["record_type"] == "referral")
        referral["recipient"] = "unapproved-recipient"
        self.assertIn(
            "REFERRAL_SCOPE_CONSENT_MISSING",
            decide_referral(records, referral_id, actor(), NOW, {"CA-NB"}).reason_codes,
        )

    def test_revoke_or_foreign_tenant_denies(self):
        consent = next(
            row for row in self.records
            if row["record_type"] == "consent" and row["purpose"] == "accessibility_support"
        )
        consent["revoked_at"] = LATER
        self.assertIn("REFERRAL_SCOPE_CONSENT_MISSING", self.decide().reason_codes)
        consent["revoked_at"] = None
        self.assertIn(
            "TENANT_MISMATCH",
            decide_referral(
                self.records, self.referral_id,
                {**actor(), "tenant_id": "11000000-0000-4000-8000-000000000001"},
                NOW, {"CA-NB"},
            ).reason_codes,
        )


class RevenueAllocationTests(unittest.TestCase):
    def test_allocation_is_disabled_until_approval_compensation_and_restriction_review(self):
        records = finance_records()
        allocation = record(
            "revenue_allocation", "f1000000-0000-4000-8000-000000000001",
            environment="sandbox", enabled=False, policy_approved=False,
            revenue_basis="net_received", eligible_revenue_minor=1000,
            currency="CAD", funding_case_ids=[FUNDING],
            policy_approval_evidence_id="f2000000-0000-4000-8000-000000000001",
            funding_review_evidence_id="f3000000-0000-4000-8000-000000000001",
            contractual_compensation_minor=100, allocation_basis_points=9000,
            funding_restrictions_reviewed=False, participant_benefit_deductions=False,
        )
        records.extend([
            allocation,
            record(
                "evidence", "f2000000-0000-4000-8000-000000000001",
                environment="sandbox", subject_id=allocation["id"],
                evidence_type="revenue_policy_approval", provenance="synthetic fixture",
                review_status="reviewed", execution_status="not_run",
                sha256="d" * 64, expires_at=LATER,
                reviewed_by=FACILITATOR, reviewed_at="2026-11-08T12:00:00Z",
            ),
            record(
                "evidence", "f3000000-0000-4000-8000-000000000001",
                environment="sandbox", subject_id=allocation["id"],
                evidence_type="funding_restriction_review", provenance="synthetic fixture",
                review_status="reviewed", execution_status="not_run",
                sha256="e" * 64, expires_at=LATER,
                reviewed_by=FACILITATOR, reviewed_at="2026-11-08T12:00:00Z",
            ),
        ])
        self.assertIn(
            "REVENUE_ALLOCATION_DISABLED",
            decide_revenue_allocation(records, allocation["id"], NOW).reason_codes,
        )
        allocation.update(
            enabled=True, policy_approved=True, funding_restrictions_reviewed=True
        )
        self.assertTrue(decide_revenue_allocation(records, allocation["id"], NOW).allowed)
        next(
            row for row in records
            if row.get("evidence_type") == "funding_restriction_review"
        )["expires_at"] = "2026-11-08T13:00:00Z"
        self.assertIn(
            "FUNDING_RESTRICTION_EVIDENCE_MISSING_EXPIRED_OR_UNREVIEWED",
            decide_revenue_allocation(records, allocation["id"], NOW).reason_codes,
        )
        next(
            row for row in records
            if row.get("evidence_type") == "funding_restriction_review"
        )["expires_at"] = LATER
        allocation["allocation_basis_points"] = 10000
        self.assertIn(
            "CONTRACTUAL_COMPENSATION_OR_REVENUE_BASIS_INVALID",
            decide_revenue_allocation(records, allocation["id"], NOW).reason_codes,
        )


class StopAndWithdrawalTests(unittest.TestCase):
    def test_participant_stop_is_immediate_and_recorded_without_finance(self):
        records = activation_records()
        decision, stopped = request_installation_stop(
            records, INSTALLATION,
            {"id": PARTICIPANT, "tenant_id": TENANT, "role": "participant"},
            NOW, "d3000000-0000-4000-8000-000000000001",
        )
        self.assertTrue(decision.allowed)
        installation = next(row for row in stopped if row["record_type"] == "installation")
        self.assertTrue(installation["stop_requested"])
        self.assertEqual(installation["status"], "stopped")
        self.assertIn("STOP_CONTROL_ACTIVE", decide_activation(
            stopped, INSTALLATION, actor(), NOW
        ).reason_codes)
        self.assertTrue(any(
            row.get("record_type") == "audit_event" and row["decision"] == "stop"
            for row in stopped
        ))

    def test_stop_ignores_unrelated_invalid_records_and_is_idempotent(self):
        records = activation_records()
        records.append({"record_type": "not-a-record", "id": "invalid"})
        decision, stopped = request_installation_stop(
            records, INSTALLATION,
            {"id": PARTICIPANT, "tenant_id": TENANT, "role": "participant"},
            NOW, "d3100000-0000-4000-8000-000000000001",
        )
        self.assertTrue(decision.allowed)
        self.assertIn({"record_type": "not-a-record", "id": "invalid"}, stopped)
        audit_count = sum(row.get("record_type") == "audit_event" for row in stopped if hasattr(row, "get"))
        repeated, unchanged = request_installation_stop(
            stopped, INSTALLATION,
            {"id": PARTICIPANT, "tenant_id": TENANT, "role": "participant"},
            NOW, "d3200000-0000-4000-8000-000000000001",
        )
        self.assertTrue(repeated.allowed)
        self.assertIn("STOP_ALREADY_ACTIVE", repeated.reason_codes)
        self.assertEqual(
            sum(row.get("record_type") == "audit_event" for row in unchanged if hasattr(row, "get")),
            audit_count,
        )

    def test_audit_event_ids_cannot_be_replayed_for_a_second_transition(self):
        activated, active = activate_installation(
            activation_records(), INSTALLATION, actor(), NOW, expected_revision=1,
            audit_event_id="d7000000-0000-4000-8000-000000000001",
        )
        self.assertTrue(activated.allowed)
        decision, unchanged = request_installation_stop(
            active, INSTALLATION,
            {"id": PARTICIPANT, "tenant_id": TENANT, "role": "participant"},
            NOW, "d7000000-0000-4000-8000-000000000001",
        )
        self.assertIn("DUPLICATE_RECORD_ID", decision.reason_codes)
        self.assertEqual(
            next(row for row in unchanged if row["record_type"] == "installation")["status"],
            "active",
        )

    def test_shared_installation_withdrawal_is_participant_specific(self):
        second = "31000000-0000-4000-8000-000000000001"
        records = activation_records()
        installation = next(row for row in records if row["record_type"] == "installation")
        installation["participant_ids"].append(second)
        participant = next(row for row in records if row["record_type"] == "participant")
        consent = next(row for row in records if row["record_type"] == "consent")
        acceptance = next(
            row for row in records if row["record_type"] == "participant_acceptance"
        )
        records.extend([
            {**participant, "id": second},
            {
                **next(row for row in records if row.get("record_type") == "membership"
                       and row.get("role") == "participant"),
                "id": "46000000-0000-4000-8000-000000000001",
                "participant_id": second,
            },
            {
                **consent, "id": "53000000-0000-4000-8000-000000000001",
                "participant_id": second,
            },
            {**acceptance, "id": "54000000-0000-4000-8000-000000000001", "participant_id": second},
        ])
        decision, updated = withdraw_participant(
            records, INSTALLATION, PARTICIPANT,
            {"id": PARTICIPANT, "tenant_id": TENANT, "role": "participant"},
            NOW, "d4000000-0000-4000-8000-000000000001",
        )
        self.assertTrue(decision.allowed)
        current_installation = next(
            row for row in updated if row["record_type"] == "installation"
        )
        self.assertEqual(current_installation["participant_ids"], [second])
        self.assertEqual(current_installation["status"], "draft")
        self.assertEqual(validate_records(updated), ())
        self.assertTrue(decide_activation(updated, INSTALLATION, actor(), NOW).allowed)
        self.assertTrue(any(
            row.get("record_type") == "audit_event" and row["decision"] == "withdraw"
            for row in updated
        ))

    def test_withdrawal_without_acceptance_revokes_only_installation_scope(self):
        second_installation = "29000000-0000-4000-8000-000000000001"
        records = activation_records()
        installation = next(row for row in records if row["record_type"] == "installation")
        other_installation = {
            **installation, "id": second_installation,
            "participant_ids": [PARTICIPANT], "status": "draft", "revision": 1,
        }
        records.append(other_installation)
        membership = next(
            row for row in records
            if row.get("record_type") == "membership" and row.get("role") == "participant"
        )
        other_membership = {
            **membership, "id": "47000000-0000-4000-8000-000000000001",
            "installation_id": second_installation, "active": True,
        }
        records.append(other_membership)
        consent = next(row for row in records if row.get("record_type") == "consent")
        other_consent = {
            **consent, "id": "48000000-0000-4000-8000-000000000001",
            "installation_id": second_installation, "revoked_at": None,
        }
        records.append(other_consent)
        records = [
            row for row in records
            if row.get("record_type") != "participant_acceptance"
        ]
        decision, updated = withdraw_participant(
            records, INSTALLATION, PARTICIPANT,
            {"id": PARTICIPANT, "tenant_id": TENANT, "role": "participant"},
            NOW, "d8000000-0000-4000-8000-000000000001",
        )
        self.assertTrue(decision.allowed)
        rows = {row["id"]: row for row in updated if isinstance(row, dict)}
        self.assertFalse(rows[membership["id"]]["active"])
        self.assertTrue(rows[other_membership["id"]]["active"])
        self.assertIsNotNone(rows[consent["id"]]["revoked_at"])
        self.assertIsNone(rows[other_consent["id"]]["revoked_at"])
        repeated, _ = withdraw_participant(
            updated, INSTALLATION, PARTICIPANT,
            {"id": PARTICIPANT, "tenant_id": TENANT, "role": "participant"},
            NOW, "d8100000-0000-4000-8000-000000000001",
        )
        self.assertTrue(repeated.allowed)
        self.assertIn("PARTICIPANT_ALREADY_WITHDRAWN", repeated.reason_codes)

    def test_withdrawal_after_activation_revokes_multiple_acceptances_and_referrals(self):
        records, _ = referral_records()
        installation = next(row for row in records if row.get("record_type") == "installation")
        historical_plan = "59000000-0000-4000-8000-000000000001"
        acceptance = next(
            row for row in records if row.get("record_type") == "participant_acceptance"
        )
        records.append({
            **acceptance,
            "id": "55000000-0000-4000-8000-000000000001",
            "plan_version_id": historical_plan,
        })
        decision, updated = withdraw_participant(
            records, INSTALLATION, PARTICIPANT,
            {"id": PARTICIPANT, "tenant_id": TENANT, "role": "participant"},
            NOW, "d8200000-0000-4000-8000-000000000001",
        )
        self.assertTrue(decision.allowed)
        acceptances = [
            row for row in updated
            if row.get("record_type") == "participant_acceptance"
        ]
        self.assertEqual(len(acceptances), 2)
        self.assertTrue(all(row["withdrawn_at"] is not None for row in acceptances))
        referral = next(row for row in updated if row.get("record_type") == "referral")
        self.assertEqual(referral["status"], "revoked")
        self.assertFalse(decide_referral(
            updated, referral["id"], actor(), NOW, {"CA-NB"}
        ).allowed)

    def test_withdrawal_after_reference_activation_is_allowed_without_finance(self):
        activation, active = activate_installation(
            activation_records(), INSTALLATION, actor(), NOW,
            expected_revision=1,
            audit_event_id="d8300000-0000-4000-8000-000000000001",
        )
        self.assertTrue(activation.allowed)
        withdrawal, updated = withdraw_participant(
            active, INSTALLATION, PARTICIPANT,
            {"id": PARTICIPANT, "tenant_id": TENANT, "role": "participant"},
            NOW, "d8400000-0000-4000-8000-000000000001",
        )
        self.assertTrue(withdrawal.allowed)
        installation = next(row for row in updated if row["record_type"] == "installation")
        self.assertEqual(installation["status"], "stopped")
        consent = next(row for row in updated if row.get("record_type") == "consent")
        self.assertIsNotNone(consent["revoked_at"])

    def test_final_participant_withdrawal_stops_without_auto_resume(self):
        decision, updated = withdraw_participant(
            activation_records(), INSTALLATION, PARTICIPANT,
            {"id": PARTICIPANT, "tenant_id": TENANT, "role": "participant"},
            NOW, "d5000000-0000-4000-8000-000000000001",
        )
        self.assertTrue(decision.allowed)
        installation = next(row for row in updated if row["record_type"] == "installation")
        self.assertEqual(installation["status"], "stopped")
        self.assertTrue(installation["stop_requested"])
        resumed, unchanged = request_installation_stop(
            updated, INSTALLATION, actor(), NOW, "d6000000-0000-4000-8000-000000000001"
        )
        self.assertTrue(resumed.allowed)
        self.assertIn("STOP_ALREADY_ACTIVE", resumed.reason_codes)
        self.assertEqual(unchanged, updated)


if __name__ == "__main__":
    unittest.main()
