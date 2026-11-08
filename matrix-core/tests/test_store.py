from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
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


FINANCE_ACTOR = {"id": FACILITATOR, "tenant_id": "10000000-0000-4000-8000-000000000001", "role": "finance_approver"}


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
        rows = {row["id"]: row for row in store.snapshot()}
        self.assertEqual(rows["80000000-0000-4000-8000-000000000001"]["reserved_minor"], 100)

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
            records[0], FACILITATOR, 1
        )
        records[1]["request_digest"] = records[0]["request_digest"]
        store = self.store(records)
        decision, _ = store.reserve_payment(PAYMENT, FINANCE_ACTOR, NOW, 1)
        self.assertIn("BUDGET_LINE_EXCEEDED", decision.reason_codes)
        decision, _ = self.store().reserve_payment(
            PAYMENT, {**FINANCE_ACTOR, "role": "participant"}, NOW, 1
        )
        self.assertIn("ACTOR_ROLE_UNAUTHORIZED", decision.reason_codes)

    def test_unknown_outcome_blocks_retry_even_with_a_new_key(self):
        store = self.store()
        reserved, _ = store.reserve_payment(PAYMENT, FINANCE_ACTOR, NOW, 1)
        self.assertTrue(reserved.allowed)
        unknown = store.record_unknown_outcome(PAYMENT, NOW)
        self.assertIn("RECONCILIATION_REQUIRED_NO_RETRY", unknown.reason_codes)
        decision, _ = store.reserve_payment(PAYMENT, FINANCE_ACTOR, NOW, 2)
        self.assertIn("RECONCILIATION_REQUIRED_NO_RETRY", decision.reason_codes)

    def test_non_financial_narrative_is_rejected_by_contract(self):
        records = finance_records()
        records[0]["access_narrative"] = "synthetic excluded field"
        self.assertTrue(validate_records(records))

    def test_concurrent_reservations_cannot_overspend(self):
        records = finance_records(amount=100, limit=150)
        second = dict(records[0])
        second["id"] = "91000000-0000-4000-8000-000000000001"
        second["idempotency_key"] = "synthetic-key-0002"
        second["authorization_id"] = "a1000000-0000-4000-8000-000000000001"
        second["request_digest"] = canonical_request_digest(second, FACILITATOR, 1)
        second_authorization = dict(records[1])
        second_authorization.update(
            id=second["authorization_id"],
            environment="sandbox",
            target_id=second["id"],
            request_digest=second["request_digest"],
        )
        store = self.store([*records, second, second_authorization])
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
        decision = store.record_settled(PAYMENT, NOW, 2)
        self.assertTrue(decision.allowed)
        rows = {row["id"]: row for row in store.snapshot()}
        budget = rows["80000000-0000-4000-8000-000000000001"]
        self.assertEqual((budget["reserved_minor"], budget["settled_minor"]), (0, 100))


if __name__ == "__main__":
    unittest.main()
