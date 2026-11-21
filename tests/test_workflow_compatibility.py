"""Conservative project/workflow model-family compatibility regression tests."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from workflow_compatibility import assess_workflow, family_from_engine


def api_graph(model_filename, loader=True):
    result = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": model_filename}},
        "2": {"class_type": "KSampler", "inputs": {"seed": 42}}
    }
    if loader:
        result["3"] = {"class_type":"LoraLoaderModelOnly",
                       "inputs":{"lora_name":"Flux3Klein_LoRA_step_500.safetensors",
                                 "strength_model":1.0}}
    return result


class WorkflowCompatibilityTests(unittest.TestCase):
    def test_explicit_flux3_klein_model_is_candidate(self):
        graph = api_graph("FLUX.3-Image-Klein_NF4.safetensors")
        result = assess_workflow(graph, "image", "flux3klein")
        self.assertEqual(result["status"], "candidate")
        self.assertEqual(result["detected"], ["flux3klein"])
        self.assertTrue(result["standard_loader"])

    def test_flux2_and_sdxl_cannot_masquerade_as_flux3(self):
        for filename in ("FLUX.2-Klein_9B.safetensors", "ponyDiffusionXL.safetensors",
                         "SDXL_base.safetensors", "qwen_image_2.1.safetensors"):
            with self.subTest(filename=filename):
                result = assess_workflow(api_graph(filename), "image", "flux3klein")
                self.assertEqual(result["status"], "incompatible", result)

    def test_generic_flux_and_unknown_names_are_not_safely_compatible(self):
        for filename in ("flux_dev.safetensors", "mystery.safetensors"):
            with self.subTest(filename=filename):
                self.assertEqual(
                    assess_workflow(api_graph(filename), "image", "flux3klein")["status"],
                    "unverified")

    def test_workflow_name_and_lora_filename_are_not_base_model_evidence(self):
        graph = api_graph("mystery.safetensors")
        graph["3"]["inputs"]["lora_name"] = "FLUX.3-Image-Klein_step_100.safetensors"
        self.assertEqual(assess_workflow(graph,"image","flux3klein")["status"],"unverified")

    def test_no_lora_loader_is_not_comparable(self):
        self.assertEqual(assess_workflow(api_graph("FLUX.3-Klein.safetensors",False),
                                         "image","flux3klein")["reason"],"no_loader")

    def test_audio_video_workflows_are_not_image_comparisons(self):
        graph = api_graph("FLUX.3-Klein.safetensors")
        for cat in ("audio","video","music","3d"):
            self.assertEqual(assess_workflow(graph,cat,"flux3klein")["reason"],"non_image")

    def test_multiple_model_families_are_not_silently_approved(self):
        graph = api_graph("FLUX.3-Image-Klein.safetensors")
        graph["4"] = {"class_type":"CheckpointLoaderSimple","inputs":{"ckpt_name":"SDXL.safetensors"}}
        self.assertEqual(assess_workflow(graph,"image","flux3klein")["reason"],"mixed_models")

    def test_custom_ui_workflow_with_known_model_and_loader_is_candidate(self):
        graph = {"nodes":[
            {"id":1,"type":"UNETLoader","widgets_values":["FLUX.3-Image-Klein-NF4.safetensors"]},
            {"id":2,"type":"LoraLoaderModelOnly","widgets_values":["a.safetensors",1]},
        ]}
        self.assertEqual(assess_workflow(graph,"image","flux3klein")["status"],"candidate")

    def test_project_engine_names_are_normalized(self):
        self.assertEqual(family_from_engine("flux3klein"),"flux3klein")
        self.assertEqual(family_from_engine("flux2klein"),"flux2klein")
        self.assertIsNone(family_from_engine("unknown"))


class WorkflowCompatibilityIntegrationChecks(unittest.TestCase):
    def test_api_and_ui_are_project_scoped_and_default_to_only_candidates(self):
        library=(ROOT/"scripts"/"workflow_library.py").read_text(encoding="utf-8")
        gen=(ROOT/"scripts"/"generation_studio.py").read_text(encoding="utf-8")
        html=(ROOT/"GUI"/"workspace.html").read_text(encoding="utf-8")
        for token in ('request.args.get("project_id")','assess_workflow(', '"compatibility"',
                      '"graph"', 'Active image project not found'):
            self.assertIn(token,library)
        for token in ('id="compare-show-all"', 'id="compare-compat-status"',
                      'function loadCompareCompatibility()', 'w.compatibility?.status==="candidate"',
                      'option.disabled=true', 'id="compare-checkpoint-project"'):
            self.assertIn(token,html)
        self.assertIn('compatibility = assess_workflow(',gen)
        self.assertIn('if compatibility["status"] != "candidate"',gen)


if __name__=="__main__":
    unittest.main()
