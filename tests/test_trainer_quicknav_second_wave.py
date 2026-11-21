"""Second wave of trainer quick-navigation: four distinct model families.
No training form, settings or launcher logic is replaced.
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / "GUI" / "trainer_quick_nav.css").read_text(encoding="utf-8")
JS = (ROOT / "GUI" / "trainer_quick_nav.js").read_text(encoding="utf-8")
ENGINES = ("flux3klein", "qwenimage21", "krea2", "ltx23")


class SecondWaveQuickNavigationTests(unittest.TestCase):
    def test_supported_trainers_keep_existing_panels_and_add_navigation(self):
        for engine in ENGINES:
            with self.subTest(engine=engine):
                source = (ROOT / "GUI" / f"trainer_ui_{engine}.html").read_text(encoding="utf-8")
                self.assertIn(f'data-orki-engine="{engine}"', source)
                self.assertEqual(source.count('href="/trainer_quick_nav.css"'), 1)
                self.assertEqual(source.count('src="/trainer_quick_nav.js"'), 1)
                self.assertIn('class="main-grid"', source)
                self.assertIn('function togglePanel(headerEl)', source)
                self.assertIn('id="terminal"', source)
                self.assertIn('id="ds-grid"', source)
                self.assertIn('id="gallery"', source)
                self.assertIn('src="/assets/orkilab-pilot.js"', source)

    def test_common_navigation_is_read_only(self):
        self.assertIn("b.type = 'button'", JS)
        self.assertIn("target.scrollIntoView", JS)
        self.assertIn("window.togglePanel(clickable)", JS)
        for forbidden in ("fetch(", "localStorage", "sessionStorage", "innerHTML", "/api/train"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, JS)
        self.assertIn(".orkilab-quicknav-link:focus-visible", CSS)


if __name__ == "__main__":
    unittest.main()
