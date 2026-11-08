import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from matrix_core.policy import validate_records
from support import activation_records, clone


ROOT = Path(__file__).parents[1]


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


SCHEMA = json.loads(
    (ROOT / "schemas/v0.1.0/core.schema.json").read_text(encoding="utf-8"),
    object_pairs_hook=_unique_pairs,
)


class ContractTests(unittest.TestCase):
    def test_schema_is_valid_draft_2020_12(self):
        Draft202012Validator.check_schema(SCHEMA)

    def test_record_envelope_is_reusable_and_closed(self):
        envelope_validator = Draft202012Validator({
            "$schema": SCHEMA["$schema"],
            "$defs": SCHEMA["$defs"],
            "$ref": "#/$defs/record_envelope",
        })
        sample = {
            "schema_version": "0.1.0",
            "record_type": "participant",
            "id": "30000000-0000-4000-8000-000000000001",
            "tenant_id": "10000000-0000-4000-8000-000000000001",
            "environment": "synthetic",
            "classification": "synthetic",
            "revision": 1,
            "created_at": "2026-11-08T12:00:00Z",
            "updated_at": "2026-11-08T12:00:00Z",
        }
        envelope_validator.validate(sample)
        with self.assertRaises(ValidationError):
            envelope_validator.validate({**sample, "full_name": "not permitted"})

    def test_all_examples_validate_and_references_resolve(self):
        validator = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
        example_dir = ROOT / "examples"
        paths = sorted(example_dir.glob("*.json"))
        self.assertGreaterEqual(len(paths), 3)
        found_types = set()
        for path in paths:
            with self.subTest(path=path.name):
                document = json.loads(
                    path.read_text(encoding="utf-8"),
                    object_pairs_hook=_unique_pairs,
                )
                records = document.get("records", [document])
                self.assertTrue(records)
                for record in records:
                    validator.validate(record)
                    found_types.add(record["record_type"])
                self.assertEqual(validate_records(records), ())
        self.assertTrue(
            {"installation", "organization", "partner_engagement", "payment_intent"}
            .issubset(found_types)
        )

    def test_envelope_and_nested_objects_are_closed(self):
        records = activation_records()
        records[0]["unexpected"] = True
        self.assertTrue(validate_records(records))
        records = activation_records()
        equipment = next(row for row in records if row["record_type"] == "equipment")
        equipment["items"][0]["serial_number"] = "not-real"
        self.assertTrue(validate_records(records))

    def test_formats_and_integer_minor_units_are_strict(self):
        records = activation_records()
        records[0]["id"] = "not-a-uuid"
        self.assertTrue(validate_records(records))

    def test_duplicate_record_ids_are_rejected(self):
        records = activation_records()
        records.append(clone(records[1]))
        self.assertIn("DUPLICATE_RECORD_ID", validate_records(records))

    def test_installation_cannot_disable_all_required_checks(self):
        records = activation_records()
        installation = next(row for row in records if row["record_type"] == "installation")
        installation["required_check_types"] = []
        self.assertTrue(validate_records(records))
        from matrix_core.policy import decide_activation
        from support import NOW, INSTALLATION, actor
        self.assertIn(
            "SCHEMA_INVALID:$",
            decide_activation(records, INSTALLATION, actor(), NOW).reason_codes,
        )

    def test_cross_tenant_links_are_rejected(self):
        records = activation_records()
        records[3]["tenant_id"] = "11000000-0000-4000-8000-000000000001"
        self.assertIn("CROSS_TENANT_REFERENCE", validate_records(records))
        records = activation_records()
        equipment = next(row for row in records if row["record_type"] == "equipment")
        equipment["environment"] = "sandbox"
        self.assertIn("CROSS_ENVIRONMENT_REFERENCE", validate_records(records))


if __name__ == "__main__":
    unittest.main()
