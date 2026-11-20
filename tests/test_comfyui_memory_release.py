"""Regression checks for safe, explicit ComfyUI memory release."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "scripts" / "generation_studio.py"
UI = ROOT / "GUI" / "workspace.html"


class ComfyMemoryReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.backend = BACKEND.read_text(encoding="utf-8")
        cls.ui = UI.read_text(encoding="utf-8")

    def test_safe_api_guards(self):
        for snippet in (
            '@app.post("/api/workspace/comfyui/memory/release")',
            "if not local():",
            'body.get("confirm") is not True',
            'cfg["mode"] == "native"',
            "project_layout.training_in_progress(base)",
            'get_json(cfg["url"], "/queue")',
            'queue["queue_running"] or queue["queue_pending"]',
            'cfg["url"] + "/free"',
            'b\'{"unload_models":true,"free_memory":true}\'',
            'method="POST"',
            "NoRedirect()",
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, self.backend)

    def test_ui_manual_and_opt_in(self):
        for snippet in (
            'id="comfy-release-memory"',
            'id="comfy-auto-release"',
            'id="comfy-memory-status"',
            'async function releaseComfyMemory(automatic=false)',
            'comfyui/memory/release",{confirm:true}',
            'if($("comfy-auto-release").checked)await releaseComfyMemory(true)',
            'memoryAutoKey="orkilab.comfyui.autoMemoryRelease"',
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, self.ui)

    def test_no_process_kill_or_global_queue_clear(self):
        section = self.backend.split('def release_comfyui_memory():', 1)[1].split(
            '    @app.post("/api/workspace/generation/<token>/cancel")', 1)[0]
        for unsafe in ('/interrupt', '"clear": True', 'os.kill(', 'taskkill', 'terminate('):
            self.assertNotIn(unsafe, section)


if __name__ == "__main__":
    unittest.main()
