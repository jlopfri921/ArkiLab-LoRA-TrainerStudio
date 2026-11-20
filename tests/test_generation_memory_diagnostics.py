"""Static regression checks for non-invasive per-generation memory diagnostics."""
import unittest
from pathlib import Path

WORKSPACE = (Path(__file__).resolve().parents[1] / "GUI" / "workspace.html").read_text(encoding="utf-8")


class GenerationMemoryTests(unittest.TestCase):
    def test_diagnostics_are_snapshot_only(self):
        for text in ('id="generation-resource-diagnostics"', 'id="generation-resource-readings"',
                     'function captureReading(data)', 'function showGenerationMemory()',
                     'async function sampleGenerationMemory(phase)',
                     'sampleGenerationMemory("before")', 'sampleGenerationMemory("peak")',
                     'sampleGenerationMemory("after")', 'sampleGenerationMemory("cleaned")',
                     'i%3===0', 'if(accepted)'):
            with self.subTest(text=text):
                self.assertIn(text, WORKSPACE)

    def test_readings_are_system_wide_and_missing_values_stay_missing(self):
        self.assertIn('Number.isFinite(r?.used_bytes)?r.used_bytes/1073741824:null', WORKSPACE)
        self.assertIn('gs.every(g=>Number.isFinite(g.vram_used_mib))', WORKSPACE)
        self.assertIn('this cannot identify the exact process or prove a memory leak', WORKSPACE)
        self.assertNotIn('localStorage.setItem("generationMemory"', WORKSPACE)


if __name__ == "__main__":
    unittest.main()
