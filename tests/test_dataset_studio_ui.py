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

    def test_common_navigation_shell_on_queue_and_datasets(self):
        queue = (ROOT / "GUI" / "queue.html").read_text(encoding="utf-8")
        shell_css = (ROOT / "assets" / "orkilab" / "orkilab-shell.css").read_text(encoding="utf-8")
        shell_js = (ROOT / "assets" / "orkilab" / "orkilab-shell.js").read_text(encoding="utf-8")
        for html in (self.html, queue):
            with self.subTest(page=html[:60]):
                self.assertIn('/assets/orkilab/orkilab-shell.css', html)
                self.assertIn('/assets/orkilab/orkilab-shell.js', html)
        self.assertIn('orki-shell-header', shell_css)
        self.assertIn('orki-shell-footer', shell_css)
        self.assertIn('aria-current', shell_js)
        self.assertIn('"/workspace/datasets"', shell_js)
        self.assertIn('"/queue"', shell_js)
        self.assertIn('orkilab:language-changed', shell_js)
        self.assertIn('id="nav-datasets"', self.html)

    def test_settings_dialog_has_accessible_top_close(self):
        self.assertIn('id="settings-close-top"', self.workspace)
        self.assertIn('aria-label="Close settings"', self.workspace)
        self.assertIn('settings-dialog-head', self.workspace)
        self.assertIn('$("settings-close-top").onclick=()=>$("settings-dialog").close()', self.workspace)

    def test_compare_dialog_has_pairs_zoom_and_keyboard_close(self):
        self.assertIn('id="comparison"', self.html)
        self.assertIn('id="compare-left"', self.html)
        self.assertIn('id="compare-right"', self.html)
        self.assertIn('id="compare-zoom"', self.html)
        self.assertIn('id="compare-pair"', self.html)
        self.assertIn('dialog class="comparison-dialog"', self.html)
        self.assertIn('comparisonText={', self.html)
        self.assertIn('openComparison(item.id)', self.html)
        self.assertIn('showModal()', self.html)
        self.assertIn('removeAttribute("src")', self.html)

    def test_selection_filters_and_localized_ui_present(self):
        for selector in ("project", "folder", "search", "review-filter", "sort",
                         "select-all", "select-none", "approve", "reject", "reset", "remove"):
            with self.subTest(selector=selector):
                self.assertIn('id="' + selector + '"', self.html)
        for locale in ("en", "es", "pt", "fr", "de", "it", "ja", "ko"):
            self.assertIn(chr(10) + locale + ":[", self.html)
        self.assertIn('id="quality-filter"', self.html)
        self.assertIn('quality:$("quality-filter").value', self.html)
        self.assertIn('item.near_duplicate', self.html)
        self.assertIn('item.possible_blur', self.html)
        self.assertIn('qualityTexts={', self.html)
        self.assertIn('I18N.lang', self.html)
        self.assertIn('batch("remove"', self.html)
        self.assertIn('batch("review"', self.html)
        self.assertIn('selected=new Set()', self.html)
        self.assertNotIn('innerHTML=', self.html)
        self.assertIn('textContent=item.name', self.html)


if __name__ == "__main__":
    unittest.main()
