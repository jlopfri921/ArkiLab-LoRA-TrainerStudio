"""Parse the inline Workspace JS and Bridge module when Node.js is available."""
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BridgeSyntaxTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_workspace_inline_javascript_parses(self):
        html = (ROOT / "GUI" / "workspace.html").read_text(encoding="utf-8")
        scripts = re.findall(r"<script[^>]*>(.*?)</script>", html, flags=re.I | re.S)
        self.assertTrue(scripts, "No inline Workspace script found")
        for script in scripts:
            if not script.strip():
                continue
            # Windows Node.js can stop reading stdin after seeing an early
            # parse error; piping this large Workspace script then deadlocks
            # the Python subprocess writer. Validate a closed temp file instead.
            with tempfile.TemporaryDirectory() as folder:
                source = Path(folder) / "workspace_inline.js"
                source.write_text(script, encoding="utf-8")
                result = subprocess.run(
                    ["node", "--check", str(source)], capture_output=True,
                    text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_bridge_module_javascript_parses(self):
        source = (ROOT / "integrations" / "orkilab_bridge" / "js" / "bridge.js").read_text(encoding="utf-8")
        result = subprocess.run(["node", "--check", "--input-type=module"], input=source,
                                text=True, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
