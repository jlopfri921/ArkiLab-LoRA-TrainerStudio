"""Regression checks for guided Training Engines landing page."""
import json
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "GUI" / "workspace.html").read_text(encoding="utf-8")

class Inspector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids=[]
        self.filters=[]
    def handle_starttag(self, tag, attrs):
        props=dict(attrs)
        if "id" in props:self.ids.append(props["id"])
        if "data-engine-filter" in props:self.filters.append(props["data-engine-filter"])

class EngineLandingTests(unittest.TestCase):
    def test_intro_and_controls(self):
        dom=Inspector();dom.feed(HTML)
        self.assertEqual(len(dom.ids),len(set(dom.ids)))
        for fragment in ('data-home="engines"', 'class="engine-intro"',
                         'id="engines">Choose your training engine</h1>',
                         'id="filters"', 'id="engine-list"',
                         'id="engine-filter-summary"',
                         'function selectEngineFilter(next)',
                         'renderEngineCards($("engine-list"),selected)',
                         'renderEngineCards($("overview-engine-list"),engines.slice(0,6))',
                         'button.onclick=()=>{selectEngineFilter(button.dataset.engineFilter);'):
            self.assertIn(fragment,HTML)
        self.assertEqual(dom.filters,["image","video","audio"])

    def test_existing_engine_launcher_not_removed(self):
        self.assertIn('function launchButton(id)',HTML)
        self.assertIn('details,launchButton(trainer.id)',HTML)
        self.assertIn('["all","image","video","audio","multimodal"]',HTML)

    def test_new_strings_translated(self):
        keys=("Choose your training engine","Image LoRA","Video LoRA","Audio and music",
              "Explore image trainers","Explore video trainers","Explore audio trainers",
              "{count} training engines shown")
        for lang in ("es","pt","fr","de","it","ja","ko"):
            obj=json.loads((ROOT/"GUI"/"locales"/f"{lang}.json").read_text(encoding="utf-8"))
            for k in keys:
                with self.subTest(lang=lang,key=k):
                    self.assertTrue(obj.get(k))

if __name__=="__main__":
    unittest.main()
