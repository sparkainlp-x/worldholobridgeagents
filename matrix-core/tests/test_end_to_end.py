import unittest

from examples.end_to_end import run_demo


class EndToEndTests(unittest.TestCase):
    def test_reference_flow_keeps_denials_and_stop_records_visible(self):
        result = run_demo()
        steps = result["steps"]
        self.assertFalse(steps["premature_activation"]["allowed"])
        self.assertTrue(steps["activation_after_scoped_consent_checks_and_acceptance"]["allowed"])
        self.assertTrue(steps["participant_stop"]["allowed"])
        self.assertTrue(steps["participant_withdrawal"]["allowed"])
        self.assertFalse(steps["referral_with_proposed_engagement"]["allowed"])
        self.assertFalse(steps["unauthorized_payment"]["allowed"])
        self.assertFalse(steps["changed_payment_request"]["allowed"])
        self.assertTrue(steps["first_sandbox_reservation"]["allowed"])
        self.assertFalse(steps["replayed_authorization_for_changed_target"]["allowed"])
        self.assertEqual(result["final_installation_status"], "stopped")


if __name__ == "__main__":
    unittest.main()
