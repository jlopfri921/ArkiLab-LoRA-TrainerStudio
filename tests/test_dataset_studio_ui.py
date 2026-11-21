"""Dataset Studio UI integration invariants (no Flask, GPU or browser required)."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DatasetStudioUiChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "GUI" / "dataset_studio.html").read_text(encoding="utf-8")
        cls.workspace = (ROOT / "GUI" / "workspace.html").read_text(encoding="utf-8")
        cls.routes = (ROOT / "scripts" / "workspace_routes.py").read_text(encoding="utf-8")

    def test_workspace_has_dataset_entry_and_backend_route(self):
        self.assertIn('href="/workspace/datasets"', self.workspace)
        self.assertIn('@app.get("/workspace/datasets")', self.routes)
        self.assertIn('dataset_studio.register(app, base)', self.routes)

    def test_selection_filters_and_localized_ui_present(self):
        for selector in ("project", "folder", "search", "review-filter", "sort",
                         "select-all", "select-none", "approve", "reject", "reset", "remove"):
            with self.subTest(selector=selector):
                self.assertIn('id="' + selector + '"', self.html)
        for locale in ("en", "es", "pt", "fr", "de", "it", "ja", "ko"):
            self.assertIn("\\n" + locale + ":[", self.html)
        self.assertIn('I18N.lang', self.html)
        self.assertIn('batch("remove"', self.html)
        self.assertIn('batch("review"', self.html)
        self.assertIn('selected=new Set()', self.html)
        self.assertNotIn('innerHTML=', self.html)
        self.assertIn('textContent=item.name', self.html)


if __name__ == "__main__":
    unittest.main()
