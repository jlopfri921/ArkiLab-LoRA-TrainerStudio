"""Static regression coverage for shared trainer setting finder (no GPU required)."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "assets" / "orkilab" / "orkilab-pilot.js"
CSS = ROOT / "assets" / "orkilab" / "orkilab-pilot.css"


class TrainerSettingFinderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = JS.read_text(encoding="utf-8")
        cls.css = CSS.read_text(encoding="utf-8")

    def test_search_uses_existing_controls(self):
        self.assertIn('sidebar.querySelectorAll(".form-group")', self.js)
        self.assertIn('group.querySelector("input[id],select[id],textarea[id]")', self.js)
        self.assertIn('stages.find(([,items])=>items.includes(panel))', self.js)

    def test_search_is_bounded_and_does_not_write_control_values(self):
        self.assertIn('.slice(0,8)', self.js)
        self.assertIn('stage=entry.stage;mode="Expert";render();', self.js)
        self.assertIn('entry.control.focus({preventScroll:true})', self.js)
        self.assertNotIn("entry.control.value=", self.js)

    def test_accessible_and_responsive(self):
        self.assertIn('search.type="search"', self.js)
        self.assertIn('search.setAttribute("aria-label"', self.js)
        self.assertIn('searchResults.setAttribute("aria-live","polite")', self.js)
        self.assertIn('.orki-pilot-nav .orki-setting-results', self.css)


if __name__ == "__main__":
    unittest.main()
