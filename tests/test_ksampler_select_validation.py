"""Check safe errors for ambiguous KSamplerSelect metadata from ComfyUI."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from workflow_conversion import validate_prompt, combo_choices
from generation_parameters import editable_fields, apply_edits


class KSamplerSelectValidationTests(unittest.TestCase):
    def setUp(self):
        self.graph = {
            "75:61": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
            "90": {"class_type": "SaveImage", "inputs": {}},
        }
        self.schemas = {
            "KSamplerSelect": {"input": {"required": {"sampler_name": [["euler", "heun"]]}}, "output": ["SAMPLER"]},
            "SaveImage": {"input": {"required": {}}, "output_node": True},
        }

    def test_valid_enum_sampler_name(self):
        validate_prompt(self.graph, self.schemas)

    def test_v3_combo_accepts_declared_sampler(self):
        self.schemas["KSamplerSelect"]["input"]["required"]["sampler_name"] = [
            "COMBO", {"options": ["euler", "heun", "dpmpp_2m"]}
        ]
        validate_prompt(self.graph, self.schemas)
        fields = editable_fields(self.graph, self.schemas)
        field = next(f for f in fields if f["name"] == "sampler_name")
        self.assertEqual(field["kind"], "choice")
        self.assertEqual(field["choices"], ["euler", "heun", "dpmpp_2m"])
        changed = apply_edits(self.graph, fields, [
            {"node": "75:61", "name": "sampler_name", "value": "heun"}
        ])
        validate_prompt(changed, self.schemas)
        self.assertEqual(changed["75:61"]["inputs"]["sampler_name"], "heun")

    def test_v3_combo_rejects_values_outside_options(self):
        self.schemas["KSamplerSelect"]["input"]["required"]["sampler_name"] = [
            "COMBO", {"options": ["euler", "heun"]}
        ]
        self.graph["75:61"]["inputs"]["sampler_name"] = "not_a_sampler"
        with self.assertRaisesRegex(ValueError, "unavailable option"):
            validate_prompt(self.graph, self.schemas)

    def test_v3_combo_rejects_missing_or_untrusted_options(self):
        for descriptor in (["COMBO"], ["COMBO", {}],
                           ["COMBO", {"options": []}],
                           ["COMBO", {"options": ["euler", {"unsafe": True}]}]):
            with self.subTest(descriptor=descriptor):
                self.schemas["KSamplerSelect"]["input"]["required"]["sampler_name"] = descriptor
                with self.assertRaisesRegex(ValueError, "invalid dropdown metadata"):
                    validate_prompt(self.graph, self.schemas)
                self.assertIsNone(combo_choices(descriptor))

    def test_custom_type_mismatch_has_specific_guidance(self):
        self.schemas["KSamplerSelect"]["input"]["required"]["sampler_name"] = ["SAMPLER"]
        with self.assertRaisesRegex(ValueError, "sampler_name is 'SAMPLER'.*custom node overrides KSamplerSelect"):
            validate_prompt(self.graph, self.schemas)

    def test_other_custom_types_are_still_rejected(self):
        self.graph["75:61"]["class_type"] = "AnotherSelector"
        self.schemas["AnotherSelector"] = {"input": {"required": {"sampler_name": ["SAMPLER"]}}, "output": ["SAMPLER"]}
        with self.assertRaisesRegex(ValueError, "requires a link"):
            validate_prompt(self.graph, self.schemas)


if __name__ == "__main__":
    unittest.main()
