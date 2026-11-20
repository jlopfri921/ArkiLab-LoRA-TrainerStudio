"""Regression guard for ComfyUI Bridge postMessage serialization safety."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "integrations" / "orkilab_bridge" / "js" / "bridge.js"
GENERATION = ROOT / "scripts" / "generation_studio.py"


class BridgeCloneSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bridge = BRIDGE.read_text(encoding="utf-8")
        cls.generation = GENERATION.read_text(encoding="utf-8")

    def test_graph_to_prompt_is_serialized_before_message(self):
        self.assertIn("const converted = await app.graphToPrompt();", self.bridge)
        self.assertIn("JSON.stringify(converted.output", self.bridge)
        self.assertIn("prompt = JSON.parse(serialized)", self.bridge)
        self.assertIn('opener.postMessage({type:"orkilab.result",token,prompt}, origin)', self.bridge)
        self.assertNotIn('prompt:converted.output', self.bridge)

    def test_non_json_errors_are_reported_safely(self):
        self.assertIn("Unsupported non-JSON value in converted prompt", self.bridge)
        self.assertIn("Cannot serialize ComfyUI prompt:", self.bridge)
        self.assertIn("Bridge conversion failed:", self.bridge)
        self.assertIn("console.error", self.bridge)
        self.assertIn('event.origin !== origin', self.bridge)
        self.assertIn('event.data?.token !== token', self.bridge)

    def test_install_action_overwrites_bridge_code(self):
        self.assertIn('shutil.copyfile(source / rel, dst)', self.generation)
        self.assertIn('"js/bridge.js"', self.generation)


if __name__ == "__main__":
    unittest.main()
