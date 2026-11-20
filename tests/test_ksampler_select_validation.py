"""Check safe errors for ambiguous KSamplerSelect metadata from ComfyUI."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from workflow_conversion import validate_prompt


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
