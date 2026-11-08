import unittest

from matrix_core.policy import (
    decide_activation,
    decide_referral,
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
    activation_records,
    actor,
    referral_records,
)


class ActivationPolicyTests(unittest.TestCase):
    def decide(self, records, caller=None):
        return decide_activation(records, INSTALLATION, caller or actor(), NOW)

    def test_complete_current_synthetic_installation_is_allowed(self):
        decision = self.decide(activation_records())
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.reason_codes, ("POLICY_REQUIREMENTS_MET",))

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
            row["record_type"] == "membership" and row["role"] == "safety_reviewer"
        )]
        self.assertIn("REQUIRED_CHECK_MISSING_STALE_OR_UNREVIEWED", self.decide(records).reason_codes)

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
            "reviewed_by": None, "reviewed_at": None,
        })
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

    def test_proposed_engagement_does_not_authorize_referral(self):
        next(row for row in self.records if row["record_type"] == "partner_engagement")["status"] = "proposed"
        self.assertIn("PARTNER_AGREEMENT_NOT_VERIFIED", self.decide().reason_codes)

    def test_scope_escalation_or_unknown_jurisdiction_denies(self):
        referral = next(row for row in self.records if row["record_type"] == "referral")
        referral["field_scopes"].append("diagnostic_details")
        self.assertIn("REFERRAL_SCOPE_CONSENT_MISSING", self.decide().reason_codes)
        referral["field_scopes"].pop()
        self.assertIn(
            "JURISDICTION_UNKNOWN_OR_ORGANIZATION_UNVERIFIED",
            self.decide({"UNKNOWN"}).reason_codes,
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
            {**participant, "id": second, "display_label": "Synthetic participant two"},
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
        self.assertFalse(resumed.allowed)
        self.assertEqual(unchanged, updated)


if __name__ == "__main__":
    unittest.main()
