"""Third wave: navigation pilot on mixed media trainer interfaces."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINES = ("ltx25", "minimaxh3", "wan22", "fibo2", "yue2")


class TrainerQuickNavThirdWave(unittest.TestCase):
    def test_all_five_trainers_keep_the_existing_layout(self):
        for name in ENGINES:
            with self.subTest(name=name):
                source = (ROOT / "GUI" / ("trainer_ui_" + name + ".html")).read_text(encoding="utf-8")
                self.assertIn('data-orki-engine="' + name + '"', source)
                self.assertEqual(1, source.count('href="/trainer_quick_nav.css"'))
                self.assertEqual(1, source.count('src="/trainer_quick_nav.js"'))
                self.assertIn('class="main-grid"', source)
                self.assertIn('function togglePanel(headerEl)', source)
                self.assertIn('id="terminal"', source)
                self.assertIn('id="ds-grid"', source)
                self.assertIn('src="/assets/orkilab-pilot.js"', source)
                self.assertLess(source.index('src="/trainer_quick_nav.js"'),source.index('</body>'))

    def test_navigation_script_is_non_destructive(self):
        script = (ROOT / "GUI" / "trainer_quick_nav.js").read_text(encoding="utf-8")
        for forbidden in ("fetch(", "/api/train", "localStorage", "sessionStorage", "innerHTML"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, script)
        self.assertIn("window.togglePanel(clickable)", script)
        self.assertIn("target.scrollIntoView", script)


if __name__ == "__main__":
    unittest.main()
