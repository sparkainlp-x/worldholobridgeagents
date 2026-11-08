from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Barrier
from uuid import UUID, uuid5
import unittest

from matrix_core.policy import validate_records
from matrix_core.store import ReferenceStore, canonical_request_digest
from support import (
    AUTHORIZATION,
    FACILITATOR,
    NOW,
    PAYMENT,
    actor,
    finance_records,
)


FINANCE_ACTOR = {
    "id": FACILITATOR, "tenant_id": "10000000-0000-4000-8000-000000000001",
    "environment": "sandbox", "role": "finance_approver",
}


class ReferenceStoreTests(unittest.TestCase):
    def store(self, records=None):
        return ReferenceStore(records or finance_records())

    def test_exact_authorization_reserves_budget_once(self):
        store = self.store()
        decision, result = store.reserve_payment(PAYMENT, FINANCE_ACTOR, NOW, 1)
        self.assertTrue(decision.allowed)
        self.assertEqual(result["state"], "reserved")
        rows = {row["id"]: row for row in store.snapshot()}
        self.assertEqual(rows["80000000-0000-4000-8000-000000000001"]["reserved_minor"], 100)
        self.assertIsNotNone(rows[AUTHORIZATION]["consumed_at"])

    def test_same_idempotency_request_is_replay_safe(self):
        store = self.store()
        first, _ = store.reserve_payment(PAYMENT, FINANCE_ACTOR, NOW, 1)
        replay, _ = store.reserve_payment(PAYMENT, FINANCE_ACTOR, NOW, 1)
        self.assertTrue(first.allowed)
        self.assertEqual(replay.reason_codes, ("IDEMPOTENT_REPLAY",))
        unauthorized, _ = store.reserve_payment(
            PAYMENT,
            {
                "id": "30000000-0000-4000-8000-000000000001",
                "tenant_id": FINANCE_ACTOR["tenant_id"],
                "environment": "sandbox",
                "role": "participant",
            },
            NOW,
            1,
        )
        self.assertIn("ACTOR_ROLE_UNAUTHORIZED", unauthorized.reason_codes)
        rows = {row["id"]: row for row in store.snapshot()}
        self.assertEqual(rows["80000000-0000-4000-8000-000000000001"]["reserved_minor"], 100)

    def test_foreign_tenant_environment_and_revoked_permission_deny_replay(self):
        store = self.store()
        store.reserve_payment(PAYMENT, FINANCE_ACTOR, NOW, 1)
        for actor_value, expected in (
            ({**FINANCE_ACTOR, "tenant_id": "11000000-0000-4000-8000-000000000001"}, "TENANT_MISMATCH"),
            ({**FINANCE_ACTOR, "environment": "test"}, "ENVIRONMENT_MISMATCH"),
            ({**FINANCE_ACTOR, "role": "participant"}, "ACTOR_ROLE_UNAUTHORIZED"),
        ):
            decision, result = store.reserve_payment(PAYMENT, actor_value, NOW, 1)
            self.assertIn(expected, decision.reason_codes)
            self.assertIsNone(result)
        records = finance_records()
        permission = next(row for row in records if row.get("action") == "reserve_payment")
        permission["revoked_at"] = "2026-11-08T12:30:00Z"
        decision, result = self.store(records).reserve_payment(PAYMENT, FINANCE_ACTOR, NOW, 1)
        self.assertIn("ACTOR_PERMISSION_MISSING_REVOKED_OR_EXPIRED", decision.reason_codes)
        self.assertIsNone(result)

    def test_reserved_replay_rejects_altered_request_and_malformed_inputs(self):
        reserved, snapshot = None, None
        store = self.store()
        reserved, _ = store.reserve_payment(PAYMENT, FINANCE_ACTOR, NOW, 1)
        snapshot = store.snapshot()
        payment = next(row for row in snapshot if row.get("record_type") == "payment_intent")
        payment["money"]["amount_minor"] += 1
        decision, result = self.store(snapshot).reserve_payment(
            PAYMENT, FINANCE_ACTOR, NOW, 1
        )
        self.assertIn("AUTHORIZATION_INVALID_EXPIRED_OR_REPLAYED", decision.reason_codes)
        self.assertIsNone(result)
        for payment_id, actor_value, revision in (
            ([], FINANCE_ACTOR, 1),
            (PAYMENT, None, 1),
            (PAYMENT, FINANCE_ACTOR, True),
        ):
            decision, result = self.store().reserve_payment(
                payment_id, actor_value, NOW, revision
            )
            self.assertFalse(decision.allowed)
            self.assertIsNone(result)

    def test_duplicate_ids_reject_store_before_dictionary_use(self):
        records = finance_records()
        records.append(deepcopy(records[0]))
        store = self.store(records)
        decision, result = store.reserve_payment(PAYMENT, FINANCE_ACTOR, NOW, 1)
        self.assertIn("DUPLICATE_RECORD_ID", decision.reason_codes)
        self.assertIsNone(result)

    def test_changed_authorization_or_stale_revision_denies(self):
        records = finance_records()
        records[0]["money"]["amount_minor"] = 101
        store = self.store(records)
        decision, _ = store.reserve_payment(PAYMENT, FINANCE_ACTOR, NOW, 1)
        self.assertIn("AUTHORIZATION_INVALID_EXPIRED_OR_REPLAYED", decision.reason_codes)
        decision, _ = self.store().reserve_payment(PAYMENT, FINANCE_ACTOR, NOW, 2)
        self.assertIn("STALE_REVISION", decision.reason_codes)

    def test_budget_overspend_and_unauthorized_actor_deny(self):
        records = finance_records(amount=151, limit=150)
        records[0]["request_digest"] = canonical_request_digest(
            records[0], FACILITATOR, 1, "finance_approver"
        )
        records[1]["request_digest"] = records[0]["request_digest"]
        store = self.store(records)
        decision, _ = store.reserve_payment(PAYMENT, FINANCE_ACTOR, NOW, 1)
        self.assertIn("BUDGET_LINE_EXCEEDED", decision.reason_codes)
        decision, _ = self.store().reserve_payment(
            PAYMENT, {**FINANCE_ACTOR, "role": "participant"}, NOW, 1
        )
        self.assertIn("ACTOR_ROLE_UNAUTHORIZED", decision.reason_codes)

    def test_missing_or_expired_funding_evidence_denies_reservation(self):
        records = finance_records()
        records = [
            row for row in records
            if not (row.get("record_type") == "evidence" and row["evidence_type"] == "funding_approval")
        ]
        decision, _ = self.store(records).reserve_payment(PAYMENT, FINANCE_ACTOR, NOW, 1)
        self.assertIn("RELATIONSHIP_TARGET_MISSING", decision.reason_codes)
        records = finance_records()
        evidence = next(
            row for row in records
            if row.get("record_type") == "evidence" and row["evidence_type"] == "eligibility_review"
        )
        evidence["expires_at"] = "2026-11-08T13:00:00Z"
        decision, _ = self.store(records).reserve_payment(PAYMENT, FINANCE_ACTOR, NOW, 1)
        self.assertIn("FUNDING_EVIDENCE_MISSING_EXPIRED_OR_UNREVIEWED", decision.reason_codes)
        records = finance_records()
        next(
            row for row in records
            if row.get("record_type") == "evidence" and row["evidence_type"] == "funding_approval"
        )["environment"] = "synthetic"
        decision, _ = self.store(records).reserve_payment(PAYMENT, FINANCE_ACTOR, NOW, 1)
        self.assertIn("CROSS_ENVIRONMENT_REFERENCE", decision.reason_codes)

    def test_unknown_outcome_blocks_retry_even_with_a_new_key(self):
        store = self.store()
        reserved, _ = store.reserve_payment(PAYMENT, FINANCE_ACTOR, NOW, 1)
        self.assertTrue(reserved.allowed)
        unauthorized = store.record_unknown_outcome(
            PAYMENT,
            {**FINANCE_ACTOR, "id": "30000000-0000-4000-8000-000000000001"},
            NOW,
            2,
        )
        self.assertIn("ACTOR_PERMISSION_MISSING_REVOKED_OR_EXPIRED", unauthorized.reason_codes)
        unknown = store.record_unknown_outcome(PAYMENT, FINANCE_ACTOR, NOW, 2)
        self.assertTrue(unknown.allowed)
        self.assertEqual(
            unknown.reason_codes, ("OUTCOME_MARKED_RECONCILIATION_REQUIRED",)
        )
        decision, _ = store.reserve_payment(PAYMENT, FINANCE_ACTOR, NOW, 3)
        self.assertIn("RECONCILIATION_REQUIRED_NO_RETRY", decision.reason_codes)

    def test_unknown_outcome_blocks_a_new_idempotency_key(self):
        records = finance_records()
        original, original_auth = records[0], records[1]
        original.update(state="reconciliation_required", revision=3)
        original_auth.update(consumed_at="2026-11-08T12:30:00Z", revision=2)
        budget = next(row for row in records if row["record_type"] == "budget_line")
        budget.update(reserved_minor=100, revision=2)
        retry = deepcopy(original)
        retry.update(
            id="91000000-0000-4000-8000-000000000001",
            state="draft", revision=1,
            idempotency_key="synthetic-key-0002",
            authorization_id="a1000000-0000-4000-8000-000000000001",
            reconciliation_evidence_id=None,
        )
        retry["request_digest"] = canonical_request_digest(
            retry, FACILITATOR, 1, "finance_approver"
        )
        retry_auth = deepcopy(original_auth)
        retry_auth.update(
            id=retry["authorization_id"], target_id=retry["id"],
            target_revision=1, request_digest=retry["request_digest"],
            consumed_at=None, revision=1,
        )
        retry_permissions = []
        for index, row in enumerate(
            row for row in records if row.get("record_type") == "actor_permission"
        ):
            permission = deepcopy(row)
            permission["id"] = f"77000000-0000-4000-8000-{index + 1:012d}"
            permission["target_id"] = retry["id"]
            retry_permissions.append(permission)
        store = self.store([*records, retry, retry_auth, *retry_permissions])
        decision, _ = store.reserve_payment(retry["id"], FINANCE_ACTOR, NOW, 1)
        self.assertIn("RECONCILIATION_REQUIRED_NO_RETRY", decision.reason_codes)

    def test_non_financial_narrative_is_rejected_by_contract(self):
        for field in (
            "access_narrative", "diagnostic_information", "referral_notes",
            "arena_telemetry",
        ):
            records = finance_records()
            records[0][field] = "synthetic excluded field"
            with self.subTest(field=field):
                self.assertTrue(validate_records(records))
        records = finance_records()
        records[0]["purpose"] = "participant diagnosis narrative"
        self.assertTrue(validate_records(records))

    def test_nan_and_naive_clock_are_rejected(self):
        records = finance_records()
        records[0]["money"]["amount_minor"] = float("nan")
        self.assertTrue(validate_records(records))
        decision, _ = self.store().reserve_payment(
            PAYMENT, FINANCE_ACTOR, NOW.replace(tzinfo=None), 1
        )
        self.assertIn("CLOCK_NOT_TIMEZONE_AWARE", decision.reason_codes)

    def test_concurrent_reservations_cannot_overspend(self):
        records = finance_records(amount=100, limit=150)
        second = dict(records[0])
        second["id"] = "91000000-0000-4000-8000-000000000001"
        second["idempotency_key"] = "synthetic-key-0002"
        second["authorization_id"] = "a1000000-0000-4000-8000-000000000001"
        second["request_digest"] = canonical_request_digest(
            second, FACILITATOR, 1, "finance_approver"
        )
        second_authorization = dict(records[1])
        second_authorization.update(
            id=second["authorization_id"],
            environment="sandbox",
            target_id=second["id"],
            request_digest=second["request_digest"],
        )
        second_permission = deepcopy(next(
            row for row in records
            if row.get("record_type") == "actor_permission"
            and row.get("action") == "reserve_payment"
        ))
        second_permission.update(
            id="78000000-0000-4000-8000-000000000001",
            target_id=second["id"],
        )
        store = self.store([*records, second, second_authorization, second_permission])
        barrier = Barrier(2)

        def reserve(identifier):
            barrier.wait()
            return store.reserve_payment(identifier, FINANCE_ACTOR, NOW, 1)[0].allowed

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(reserve, [PAYMENT, second["id"]]))
        self.assertEqual(sum(results), 1)
        budget = next(row for row in store.snapshot() if row["record_type"] == "budget_line")
        self.assertEqual(budget["reserved_minor"], 100)

    def test_reconciled_known_outcome_moves_reserved_to_settled(self):
        store = self.store()
        store.reserve_payment(PAYMENT, FINANCE_ACTOR, NOW, 1)
        store.record_unknown_outcome(PAYMENT, FINANCE_ACTOR, NOW, 2)
        evidence = {
            "schema_version": "0.1.0",
            "record_type": "evidence",
            "id": "73000000-0000-4000-8000-000000000001",
            "tenant_id": "10000000-0000-4000-8000-000000000001",
            "environment": "sandbox",
            "classification": "synthetic",
            "revision": 1,
            "created_at": "2026-11-08T12:00:00Z",
            "updated_at": "2026-11-08T12:00:00Z",
            "subject_id": PAYMENT,
            "evidence_type": "payment_reconciliation",
            "provenance": "synthetic reconciliation fixture",
            "review_status": "reviewed",
            "execution_status": "passed",
            "sha256": "f" * 64,
            "expires_at": "2026-11-09T12:00:00Z",
            "reviewed_by": FACILITATOR,
            "reviewed_at": "2026-11-08T12:00:00Z",
        }
        collision_store = self.store()
        collision_store.reserve_payment(PAYMENT, FINANCE_ACTOR, NOW, 1)
        collision_store.record_unknown_outcome(PAYMENT, FINANCE_ACTOR, NOW, 2)
        collision_evidence = deepcopy(evidence)
        collision_evidence["id"] = str(uuid5(
            UUID("8e5cb4af-f15c-43e8-9d10-0c1df0e8a4c4"),
            f"{PAYMENT}:payment_outcome_reconciled:4",
        ))
        collision = collision_store.record_settled(
            PAYMENT, FINANCE_ACTOR, collision_evidence, NOW, 3
        )
        self.assertIn("DUPLICATE_AUDIT_EVENT_ID", collision.reason_codes)
        collision_budget = next(
            row for row in collision_store.snapshot() if row["record_type"] == "budget_line"
        )
        self.assertEqual((collision_budget["reserved_minor"], collision_budget["settled_minor"]), (100, 0))
        decision = store.record_settled(
            PAYMENT, FINANCE_ACTOR, evidence, NOW, 3
        )
        self.assertTrue(decision.allowed)
        rows = {row["id"]: row for row in store.snapshot()}
        budget = rows["80000000-0000-4000-8000-000000000001"]
        self.assertEqual((budget["reserved_minor"], budget["settled_minor"]), (0, 100))
        self.assertEqual(rows[PAYMENT]["reconciliation_evidence_id"], evidence["id"])


if __name__ == "__main__":
    unittest.main()
