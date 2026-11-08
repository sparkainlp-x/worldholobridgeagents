import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator, FormatChecker

from matrix_core.policy import validate_records
from support import activation_records, clone


ROOT = Path(__file__).parents[1]
SCHEMA = json.loads(
    (ROOT / "schemas/v0.1.0/core.schema.json").read_text(encoding="utf-8")
)


class ContractTests(unittest.TestCase):
    def test_schema_is_valid_draft_2020_12(self):
        Draft202012Validator.check_schema(SCHEMA)

    def test_all_examples_validate_and_references_resolve(self):
        validator = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
        example_dir = ROOT / "examples"
        for path in sorted(example_dir.glob("*.json")):
            with self.subTest(path=path.name):
                document = json.loads(path.read_text(encoding="utf-8"))
                records = document.get("records", [document])
                for record in records:
                    validator.validate(record)
                self.assertEqual(validate_records(records), ())

    def test_envelope_and_nested_objects_are_closed(self):
        records = activation_records()
        records[0]["unexpected"] = True
        self.assertTrue(validate_records(records))
        records = activation_records()
        records[5]["items"][0]["serial_number"] = "not-real"
        self.assertTrue(validate_records(records))

    def test_formats_and_integer_minor_units_are_strict(self):
        records = activation_records()
        records[0]["id"] = "not-a-uuid"
        self.assertTrue(validate_records(records))

    def test_duplicate_record_ids_are_rejected(self):
        records = activation_records()
        records.append(clone(records[1]))
        self.assertIn("DUPLICATE_RECORD_ID", validate_records(records))

    def test_cross_tenant_links_are_rejected(self):
        records = activation_records()
        records[3]["tenant_id"] = "11000000-0000-4000-8000-000000000001"
        self.assertIn("CROSS_TENANT_REFERENCE", validate_records(records))


if __name__ == "__main__":
    unittest.main()
