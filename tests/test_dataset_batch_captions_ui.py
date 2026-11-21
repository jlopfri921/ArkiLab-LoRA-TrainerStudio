"""Dataset Studio bulk captioning UI regression and privacy checks."""
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "GUI" / "dataset_studio.html").read_text(encoding="utf-8")


class Inspect(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []

    def handle_starttag(self, tag, attrs):
        props = dict(attrs)
        if props.get("id"):
            self.ids.append(props["id"])


class BatchCaptionTests(unittest.TestCase):
    def test_single_batch_dialog_and_controls(self):
        dom = Inspect()
        dom.feed(HTML)
        self.assertEqual(len(dom.ids), len(set(dom.ids)))
        for item in ("batch-captions", "batch-caption-dialog", "batch-caption-model",
                     "batch-caption-model-refresh", "batch-caption-start",
                     "batch-caption-cancel", "batch-caption-progress",
                     "batch-caption-results", "batch-caption-save",
                     "batch-caption-status", "batch-caption-close"):
            self.assertIn(item, dom.ids)
        self.assertIn('"prepare-training","batch-captions"', HTML)

    def test_generation_is_only_opt_in_and_saves_only_after_review(self):
        self.assertIn('"/api/workspace/ollama/vision-models"', HTML)
        self.assertIn('names.includes("gemma4:26b")', HTML)
        self.assertIn('request_id:requestId', HTML)
        self.assertIn('run.controller?.abort()', HTML)
        self.assertIn('/caption/suggest/cancel', HTML)
        self.assertIn('if(existing.caption?.trim())', HTML)
        self.assertIn('if(!confirm(bt(12,{count:run.ids.length})))return;', HTML)
        self.assertIn('const items=batchPreviews.filter(x=>x.ready&&!x.saved&&x.approved&&x.caption.trim());', HTML)
        self.assertIn('expected_revision:item.revision', HTML)
        self.assertIn('const result=await api(url+"/suggest"', HTML)
        self.assertIn('const data=await api("/api/workspace/datasets/"', HTML)
        self.assertIn('batchWords={', HTML)
        self.assertIn('es:["Generar descripciones con IA"', HTML)

    def test_native_browser_and_existing_single_caption_remain_available(self):
        for item in ('id="browse-folder"', 'id="caption-ai-generate"',
                     'id="caption-ai-apply"', 'id="caption-save"'):
            self.assertIn(item, HTML)


if __name__ == "__main__":
    unittest.main()
