"""Fourth-wave quick navigation: verify nine existing training UI files."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = ("qwenimage2512", "boogu", "zimage", "mingimage",
         "anima", "klein9b", "ernie", "mossimage", "ideogram4")


class FourthWaveQuickNavTests(unittest.TestCase):
    def test_new_navigation_is_present_without_replacing_trainers(self):
        for name in NAMES:
            with self.subTest(name=name):
                content = (ROOT/"GUI"/f"trainer_ui_{name}.html").read_text(encoding="utf-8")
                self.assertEqual(content.count('href="/trainer_quick_nav.css"'), 1)
                self.assertEqual(content.count('src="/trainer_quick_nav.js"'), 1)
                self.assertIn(f'data-orki-engine="{name}"', content)
                self.assertIn('function togglePanel(headerEl)', content)
                self.assertIn('class="main-grid"', content)
                self.assertIn('id="terminal"', content)
                self.assertIn('id="ds-grid"', content)
                self.assertLess(content.index('src="/trainer_quick_nav.js"'),content.index('</body>'))

    def test_shared_script_does_not_mutate_trainer_settings(self):
        script=(ROOT/"GUI"/"trainer_quick_nav.js").read_text(encoding="utf-8")
        for forbidden in ("fetch(", "localStorage", "sessionStorage", "/api/train", "innerHTML"):
            self.assertNotIn(forbidden, script)
        self.assertIn("b.type = 'button'", script)


if __name__ == "__main__":
    unittest.main()
