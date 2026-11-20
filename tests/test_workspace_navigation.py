"""Static Workspace UX regression checks; no GPU, browser or Flask required."""
import unittest
from html.parser import HTMLParser
from pathlib import Path

HTML = Path(__file__).resolve().parents[1] / "GUI" / "workspace.html"


class Inspect(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.views = []
        self.nav = {}
        self.context = False

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if attrs.get("data-home"):
            self.views.append(attrs["data-home"])
        if tag == "a" and attrs.get("href", "").startswith("#"):
            self.nav[attrs["href"]] = True
        if attrs.get("id") == "workspace-context":
            self.context = True


class WorkspaceNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = HTML.read_text(encoding="utf-8")
        cls.parsed = Inspect()
        cls.parsed.feed(cls.html)

    def test_unique_ids(self):
        self.assertEqual(len(self.parsed.ids), len(set(self.parsed.ids)))

    def test_main_sections_are_independent(self):
        self.assertEqual(set(self.parsed.views), {"overview", "projects", "engines"})
        self.assertIn('id="gpu-manager"', self.html)
        self.assertIn('function routeHome()', self.html)
        for link in ("#overview", "#projects", "#engines", "#gpu-manager"):
            self.assertIn(link, self.parsed.nav)

    def test_launcher_root_and_legacy_routes_work(self):
        # The same HTML is served by / and /legacy, not just /workspace.
        self.assertIn('["/","/workspace","/legacy"]', self.html)
        self.assertIn('window.addEventListener("hashchange",routeHome)', self.html)
        self.assertIn('routeWorkspace();routeHome();', self.html)
        for section in ('overview', 'projects', 'engines', 'gpu-manager'):
            self.assertIn('"' + section + '"', self.html)

    def test_context_help_is_present(self):
        self.assertTrue(self.parsed.context)
        for value in ('id="context-toggle"', 'id="context-description"',
                      'aria-controls="context-description"', 'function updateWorkspaceContext('):
            self.assertIn(value, self.html)

    def test_comfyui_remains_separate(self):
        self.assertIn('id="comfy-navigation"', self.html)
        self.assertIn('data-module="compare"', self.html)
        self.assertIn('data-module="history"', self.html)
        self.assertIn('/workspace/comfyui', self.html)


if __name__ == "__main__":
    unittest.main()
