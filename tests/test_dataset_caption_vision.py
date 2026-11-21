"""Local vision-caption preview tests, no GPU or Ollama installation required."""
import base64
import io
import json
import sqlite3
import sys
import tempfile
import unittest
import urllib.error
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


class LocalCaptionPreviewTests(unittest.TestCase):
    def setUp(self):
        try:
            from flask import Flask
            import dataset_studio
        except ModuleNotFoundError as exc:
            if exc.name == "flask":
                self.skipTest("Flask not installed in lightweight test runner")
            raise
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.folder = self.base / "images"
        self.folder.mkdir()
        self.image = self.folder / "person.png"
        self.data = b"fake image bytes used only in mock vision requests"
        self.image.write_bytes(self.data)
        self.project = "c" * 32
        projects = self.base / "settings" / "orkilab" / "projects.sqlite3"
        projects.parent.mkdir(parents=True)
        with closing(sqlite3.connect(projects)) as conn, conn:
            conn.execute("CREATE TABLE projects (id TEXT PRIMARY KEY, archived INTEGER NOT NULL)")
            conn.execute("INSERT INTO projects VALUES (?,0)", (self.project,))
        app = Flask(__name__)
        app.config["TESTING"] = True
        dataset_studio.register(app, self.base)
        self.client = app.test_client()
        self.base_url = "/api/workspace/datasets/" + self.project
        self.assertEqual(self.client.post(self.base_url, json={"folder": str(self.folder)}).status_code, 200)
        image_id = self.client.get(self.base_url).get_json()["images"][0]["id"]
        self.endpoint = self.base_url + "/" + image_id + "/caption/suggest"
        self.caption = self.base_url + "/" + image_id + "/caption"

    def test_preview_never_saves_caption_or_modifies_originals(self):
        class FakeReply:
            def __enter__(self): return io.BytesIO(json.dumps({"response": "a person in a red coat"}).encode())
            def __exit__(self, *_): return False
        class FakeOpener:
            def open(self, request, timeout):
                self.check_request(request, timeout)
                return FakeReply()
            def check_request(self, request, timeout):
                self.assertEqual(request.full_url, "http://127.0.0.1:11434/api/generate")
                self.assertEqual(timeout, 120)
                body = json.loads(request.data)
                self.assertEqual(body["model"], "vision-local:latest")
                self.assertEqual(body["images"], [base64.b64encode(self.data).decode()])
                self.assertEqual(body["keep_alive"], "0")
                self.assertFalse(body["stream"])
        fake = FakeOpener()
        fake.assertEqual = self.assertEqual
        fake.assertFalse = self.assertFalse
        fake.data = self.data
        with patch("dataset_caption_vision.urllib.request.build_opener", return_value=fake):
            result = self.client.post(self.endpoint, json={"confirm": True, "model": "vision-local:latest"})
        self.assertEqual(result.status_code, 200, result.get_data(as_text=True))
        self.assertEqual(result.get_json()["caption"], "a person in a red coat")
        self.assertIs(result.get_json()["saved"], False)
        self.assertEqual(self.client.get(self.caption).get_json()["caption"], "")
        self.assertEqual(self.image.read_bytes(), self.data)
        self.assertFalse((self.folder / "person.txt").exists())

    def test_explicit_consent_local_origin_and_bad_inputs(self):
        good = {"confirm": True, "model": "vision-local:latest"}
        cases = [
            ({"model": "vision-local:latest"}, 400),
            ({"confirm": False, "model": "vision-local:latest"}, 400),
            ({"confirm": True, "model": "bad model"}, 400),
            ({"confirm": True, "model": "x"*101}, 400),
            ({"confirm": True, "model": "valid", "prompt": ""}, 400),
            ({"confirm": True, "model": "valid", "prompt": "x"*701}, 400),
        ]
        for data, status in cases:
            with self.subTest(data=data):
                self.assertEqual(self.client.post(self.endpoint, json=data).status_code, status)
        self.assertEqual(self.client.post(self.endpoint, json=good,
            headers={"Origin": "https://other.example"}).status_code, 403)
        self.assertEqual(self.client.post(self.endpoint, json=good,
            environ_overrides={"REMOTE_ADDR": "203.0.113.3"}).status_code, 403)
        missing = self.base_url + "/" + "a"*32 + "/caption/suggest"
        self.assertEqual(self.client.post(missing, json=good).status_code, 404)

    def test_unavailable_ollama_returns_safe_error_without_saving(self):
        class DeadOpener:
            def open(self, *args, **kwargs):
                raise urllib.error.URLError("connection refused")
        with patch("dataset_caption_vision.urllib.request.build_opener", return_value=DeadOpener()):
            result = self.client.post(self.endpoint, json={"confirm": True, "model": "vision-local:latest"})
        self.assertEqual(result.status_code, 502)
        self.assertIn("Ollama", result.get_json()["error"])
        self.assertEqual(self.client.get(self.caption).get_json()["revision"], 0)
        self.assertEqual(self.image.read_bytes(), self.data)


if __name__ == "__main__":
    unittest.main()
