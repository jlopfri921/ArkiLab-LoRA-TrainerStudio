"""Static regression checks for session-only GPU and RAM charts."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "GUI" / "workspace.html"
ROUTES = ROOT / "scripts" / "workspace_routes.py"


class GPUHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = UI.read_text(encoding="utf-8")
        cls.routes = ROUTES.read_text(encoding="utf-8")

    def test_os_ram_snapshot_is_optional(self):
        for fragment in ("psutil.virtual_memory()", '"system_ram"', '"available_bytes"', '"used_bytes"', "except (ImportError, OSError, ValueError):"):
            self.assertIn(fragment, self.routes)

    def test_live_history_is_bounded_and_session_only(self):
        for fragment in ("let gpuHistory=[]", "const maxGpuSamples=120", "if(gpuHistory.length>maxGpuSamples)gpuHistory.shift()", 'id="gpu-history-charts"', 'id="gpu-history-clear"', 'id="gpu-history-summary"', "recordGpuHistory(reading)", "gpuHistoryChart(", "gpuHistory=[];renderGpuHistory()"):
            self.assertIn(fragment, self.html)
        self.assertNotIn('localStorage.setItem("gpuHistory"', self.html)

    def test_missing_samples_not_treated_as_zero(self):
        self.assertIn("if(!Number.isFinite(value)){drawing=false;return;}", self.html)
        self.assertIn("Number.isFinite(x?.used)?x.used/1024:null", self.html)


if __name__ == "__main__":
    unittest.main()
