"""Dependency-free foundation checks: no network, no GPU."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BAT = "Update_LoRAlab-TrainerStudio.bat"
SH = "Update_LoRAlab-TrainerStudio.sh"


class BrandingTests(unittest.TestCase):
    def test_branding(self):
        html = (ROOT / "GUI/launcher.html").read_text(encoding="utf-8")
        cfg = json.loads((ROOT / "GUI/launcher.json").read_text(encoding="utf-8"))
        version = (ROOT / "VERSION_ARKILAB").read_text().strip()
        self.assertEqual(cfg["arkilab_version"], version)
        self.assertIn(version, (ROOT / "README.md").read_text(encoding="utf-8"))
        self.assertIn("arkilab-version", html)
        for name in ("arkilab-icon.svg", "arkilab-logo-dark.svg", "arkilab-logo-light.svg"):
            path = ROOT / "assets/arkilab" / name
            self.assertTrue(ET.parse(path).getroot().tag.endswith("svg"))
        self.assertIn("/assets/arkilab/arkilab-icon.svg", html)
        self.assertIn("/assets/arkilab/arkilab-logo-dark.svg", html)
        self.assertIn("Academia SD", (ROOT / "LICENSE").read_text(encoding="utf-8"))
        self.assertIn("AcademiaSD LoRAlab Trainer Studio", html)

    def test_updater_guards(self):
        for name in (BAT, SH):
            text = (ROOT / name).read_text(encoding="utf-8").lower()
            for pattern in ("git reset --hard", "git remote set-url", "git checkout -f"):
                self.assertNotIn(pattern, text)
            for pattern in ("git merge --ff-only", "git diff --quiet", "git diff --cached --quiet", "--deps"):
                self.assertIn(pattern, text)


@unittest.skipUnless(shutil.which("git") and (os.name == "nt" or shutil.which("bash")), "Git and platform shell required")
class UpdaterTests(unittest.TestCase):
    def git(self, cwd, *args):
        return subprocess.run(["git", *args], cwd=cwd, check=True,
                              capture_output=True, text=True).stdout.strip()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.remote = root / "remote.git"
        self.source = root / "source"
        self.local = root / "local"
        self.git(root, "init", "--bare", str(self.remote))
        self.git(root, "init", "-b", "main", str(self.source))
        self.git(self.source, "config", "user.email", "test@example.invalid")
        self.git(self.source, "config", "user.name", "Test")
        for name in (BAT, SH):
            shutil.copyfile(ROOT / name, self.source / name)
        (self.source / "data.txt").write_text("base")
        self.git(self.source, "add", ".")
        self.git(self.source, "commit", "-m", "initial")
        self.git(self.source, "remote", "add", "origin", str(self.remote))
        self.git(self.source, "push", "-u", "origin", "main")
        self.git(root, "clone", "-b", "main", str(self.remote), str(self.local))
        self.git(self.local, "config", "user.email", "test@example.invalid")
        self.git(self.local, "config", "user.name", "Test")
        self.origin = self.git(self.local, "remote", "get-url", "origin")
        (self.source / "data.txt").write_text("remote update")
        self.git(self.source, "commit", "-am", "remote update")
        self.git(self.source, "push")

    def update(self):
        cmd = ["cmd", "/d", "/c", BAT] if os.name == "nt" else ["bash", SH]
        result = subprocess.run(cmd, cwd=self.local, input="\n", capture_output=True, text=True, timeout=30)
        self.assertEqual(self.origin, self.git(self.local, "remote", "get-url", "origin"))
        return result

    def test_fast_forward(self):
        result = self.update()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.local / "data.txt").read_text(), "remote update")

    def test_dirty(self):
        (self.local / "data.txt").write_text("keep local")
        self.assertNotEqual(self.update().returncode, 0)
        self.assertEqual((self.local / "data.txt").read_text(), "keep local")

    def test_staged(self):
        (self.local / "data.txt").write_text("staged")
        self.git(self.local, "add", "data.txt")
        self.assertNotEqual(self.update().returncode, 0)
        self.assertEqual((self.local / "data.txt").read_text(), "staged")

    def test_diverged(self):
        (self.local / "data.txt").write_text("local commit")
        self.git(self.local, "commit", "-am", "local commit")
        old = self.git(self.local, "rev-parse", "HEAD")
        self.assertNotEqual(self.update().returncode, 0)
        self.assertEqual(old, self.git(self.local, "rev-parse", "HEAD"))

    def test_detached(self):
        self.git(self.local, "checkout", "--detach")
        self.assertNotEqual(self.update().returncode, 0)


if __name__ == "__main__":
    unittest.main()
