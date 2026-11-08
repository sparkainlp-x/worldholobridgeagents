import unittest

from scripts.benchmark import contract_oracle, run_benchmark
from scripts.sample_size_sensitivity import sample_size
from matrix_core.synthetic import SCENARIO_CLASSES, build_activation_case


class EvaluationTests(unittest.TestCase):
    def test_contract_oracle_checks_generated_positive_and_negative_cases(self):
        self.assertTrue(contract_oracle(build_activation_case(812, "valid")))
        for index, scenario_class in enumerate(SCENARIO_CLASSES[1:]):
            with self.subTest(scenario_class=scenario_class):
                self.assertFalse(contract_oracle(build_activation_case(812 + index, scenario_class)))

    def test_held_out_seed_is_reported_without_policy_oracle_disagreement(self):
        output = run_benchmark(seed=41, held_out_seed=99, count=len(SCENARIO_CLASSES))
        self.assertEqual(len(output["raw_outcomes"]), 2 * len(SCENARIO_CLASSES))
        self.assertEqual(
            output["summary"]["by_dataset"]["held_out_seed"]["scenario_count"],
            len(SCENARIO_CLASSES),
        )
        self.assertEqual(output["summary"]["strict"]["false_allows"], 0)
        self.assertEqual(output["summary"]["strict"]["false_denials"], 0)
        self.assertGreater(output["summary"]["weak_boolean_baseline"]["false_allows"], 0)
        self.assertTrue(output["config"]["no_held_out_tuning"])
        self.assertEqual(
            output["summary"]["strict"]["uncertainty"],
            "No inferential interval: scenarios are deterministically generated and "
            "stratified by policy class, not sampled from a deployment or human population.",
        )
        self.assertNotIn("false_allow_wilson_95", output["summary"]["strict"])
        self.assertGreater(
            output["summary"]["ablation_no_consent"]["false_allows"], 0
        )
        self.assertGreater(
            output["summary"]["ablation_no_acceptance"]["false_allows"], 0
        )
        self.assertGreater(
            output["summary"]["ablation_no_checks"]["false_allows"], 0
        )
        self.assertEqual(len(output["config"]["ablations"]), 3)

    def test_equal_development_and_held_out_seeds_are_rejected(self):
        with self.assertRaises(ValueError):
            run_benchmark(seed=41, held_out_seed=41, count=len(SCENARIO_CLASSES))

    def test_sample_size_grid_is_explicit_assumption_only(self):
        self.assertEqual(sample_size(0.5, 0.1, 1.96), 97)
        with self.assertRaises(ValueError):
            sample_size(1.0, 0.1, 1.96)
        with self.assertRaises(ValueError):
            sample_size(0.5, 0.1, float("nan"))


if __name__ == "__main__":
    unittest.main()
