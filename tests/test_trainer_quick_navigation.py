"""Regression checks for optional trainer quick-navigation pilot."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
JS=(ROOT/"GUI"/"trainer_quick_nav.js").read_text(encoding="utf-8")
CSS=(ROOT/"GUI"/"trainer_quick_nav.css").read_text(encoding="utf-8")

class QuickNavTests(unittest.TestCase):
    def test_pilot_is_explicitly_scoped_to_two_trainers(self):
        for name in ("flux1","sdxl"):
            text=(ROOT/"GUI"/f"trainer_ui_{name}.html").read_text(encoding="utf-8")
            self.assertIn('href="/trainer_quick_nav.css"',text)
            self.assertIn('src="/trainer_quick_nav.js"',text)
            self.assertIn('class="main-grid"',text)
            self.assertIn('function togglePanel(headerEl)',text)
            self.assertLess(text.index('src="/trainer_quick_nav.js"'),text.index("</body>"))
    def test_navigation_only_scrolls_and_opens_panels(self):
        for text in ("document.createElement('nav')","document.createElement('button')",
                     "b.type = 'button'","aria-label", "panel.classList.contains('collapsed')",
                     "window.togglePanel(clickable)","target.scrollIntoView","target.focus",
                     "if (!grid || !sidebar","if (text) addTarget"):
            self.assertIn(text,JS)
        for forbidden in ("/api/launch","/api/train","fetch(","localStorage","sessionStorage","innerHTML","eval("):
            self.assertNotIn(forbidden,JS)
        self.assertIn(".orkilab-quicknav-link:focus-visible",CSS)
        self.assertIn("@media(max-width:760px)",CSS)

if __name__=="__main__":
    unittest.main()
