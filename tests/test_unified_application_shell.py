"""Unified Workspace chrome regression contract (no browser/GPU dependency)."""
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = ("workspace.html", "queue.html", "dataset_studio.html")
CSS_PATH = "/assets/orkilab/orkilab-app-shell.css"
JS_PATH = "/assets/orkilab/orkilab-shell.js"


class Elements(HTMLParser):
    def __init__(self):
        super().__init__()
        self.css_links = []
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "link" and attrs.get("rel") == "stylesheet":
            self.css_links.append(attrs.get("href"))
        if tag == "script" and attrs.get("src"):
            self.scripts.append(attrs["src"])


class UnifiedChromeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css = (ROOT / "assets" / "orkilab" / "orkilab-app-shell.css").read_text(encoding="utf-8")
        cls.js = (ROOT / "assets" / "orkilab" / "orkilab-shell.js").read_text(encoding="utf-8")

    def test_every_main_page_loads_same_final_css_and_shell_controller(self):
        for name in PAGES:
            with self.subTest(page=name):
                html = (ROOT / "GUI" / name).read_text(encoding="utf-8")
                parsed = Elements()
                parsed.feed(html)
                self.assertEqual(parsed.css_links[-1], CSS_PATH)
                self.assertIn(JS_PATH, parsed.scripts)
                self.assertEqual(parsed.scripts.count(JS_PATH), 1)

    def test_single_visual_source_for_header_nav_grid_context_and_footer(self):
        for needle in (
            "--orki-app-bg:", "--orki-app-panel:", "--orki-app-border:",
            "--orki-app-text:", "--orki-app-accent:", "--orki-app-gradient:",
            "--orki-app-width:1440px", "--orki-app-side:200px",
            "--orki-app-gap:24px", "--orki-app-radius:16px",
            ".orki-app-header", ".orki-app-nav", ".orki-app-context",
            ".orki-app-footer", ".queue-shell", ".studio-layout",
            "#home-navigation", "#comfy-navigation", "@media(max-width:760px)"
        ):
            with self.subTest(css=needle):
                self.assertIn(needle, self.css)

    def test_shell_is_installed_on_workspace_queue_dataset_and_comfyui(self):
        for needle in (
            "function unifiedFooter(", "function renderWorkspaceChrome(",
            'document.querySelector("#home-navigation")',
            'document.querySelector("#workspace-body")',
            'document.querySelector("#comfy-navigation")',
            'page === "queue" ? ".queue-sidebar" : ".studio-navigation"',
            'body.classList.add("orki-app-frame"',
            'unifiedFooter(content, names[locale])',
            'unifiedFooter(content, t)',
            'header.classList.add("orki-shell-header", "orki-app-header")',
            'canonical.className = ',
            'canonicalNav.cloneNode(true)',
            'nav.replaceWith(canonical)',
        ):
            with self.subTest(js=needle):
                self.assertIn(needle, self.js)

    def test_queue_does_not_acquire_a_second_language_selector(self):
        helper = (ROOT / "assets" / "orkilab" / "orkilab-ui.js").read_text(encoding="utf-8")
        self.assertIn("#ui-lang,#workspace-language,#orki-language,.queue-shell,.studio-layout", helper)
        self.assertIn('selector.id = "orki-shell-language"', self.js)
        self.assertIn('header.querySelector("#workspace-language")', self.js)

    def test_comfy_global_actions_are_keyed_by_original_ids_not_translated_text(self):
        self.assertIn('button.id === "settings-open" ? "settings" : "shutdown"', self.js)
        self.assertIn('global.removeAttribute("id")', self.js)
        self.assertIn('document.querySelector("#comfy-navigation")', self.js)

    def test_standalone_uses_actual_workspace_markup_not_an_alternate_menu(self):
        self.assertIn('source.querySelector("body > header")', self.js)
        self.assertIn('source.querySelector("#home-navigation")', self.js)
        self.assertIn('source.querySelector("#workspace-context")', self.js)
        self.assertIn('fetch("/workspace"', self.js)
        self.assertIn('I18N.apply(canonical)', self.js)
        self.assertIn('location.href = "/workspace?dialog=" + mode', self.js)
        self.assertIn('content.append(footer)', self.js)


if __name__ == "__main__":
    unittest.main()
