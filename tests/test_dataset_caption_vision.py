"""Local vision-caption preview tests, no GPU or Ollama installation required."""
import base64
import io
import json
import sqlite3
import threading
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
        self.app = app
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
            ({"confirm": True, "model": "vision:cloud"}, 400),
            ({"confirm": True, "model": "vision:8b-cloud"}, 400),
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

    def test_installed_model_discovery_checks_vision_capability(self):
        class FakeOpener:
            def open(self, request, timeout):
                if request.full_url.endswith("/api/tags"):
                    return io.BytesIO(json.dumps({"models": [
                        {"name": "llava:latest", "size": 123},
                        {"name": "text-only:latest", "size": 88},
                        {"name": "remote:cloud", "remote_host": "https://remote.example"},
                        {"name": "remote2:latest", "remote_model": "vision:cloud"},
                        {"name": "remote3:cloud"},
                        {"name": "unknown:latest"},
                    ]}).encode())
                if request.full_url.endswith("/api/show"):
                    body = json.loads(request.data)
                    name = body["model"]
                    if name == "unknown:latest":
                        raise urllib.error.URLError("cannot check capabilities")
                    capabilities = ["completion", "vision"] if name == "llava:latest" else ["completion"]
                    return io.BytesIO(json.dumps({"capabilities": capabilities}).encode())
                raise AssertionError("Unexpected Ollama endpoint")
        with patch("dataset_caption_vision.urllib.request.build_opener", return_value=FakeOpener()):
            result = self.client.get("/api/workspace/ollama/vision-models")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.get_json()["models"], [{"name": "llava:latest", "size": 123}])
        self.assertEqual(result.get_json()["examined"], 6)
        self.assertEqual(self.client.get("/api/workspace/ollama/vision-models",
            headers={"Origin": "https://other.example"}).status_code, 403)
        self.assertEqual(self.client.get("/api/workspace/ollama/vision-models",
            environ_overrides={"REMOTE_ADDR": "203.0.113.3"}).status_code, 403)

    def test_unavailable_model_catalog_is_nonfatal(self):
        class Offline:
            def open(self, *args, **kwargs):
                raise urllib.error.URLError("refused")
        with patch("dataset_caption_vision.urllib.request.build_opener", return_value=Offline()):
            result = self.client.get("/api/workspace/ollama/vision-models")
        self.assertEqual(result.status_code, 503)
        self.assertIn("unavailable", result.get_json()["error"])

    def test_streamed_generation_preview_with_request_id(self):
        class FakeResponse:
            status = 200
            def __init__(self):
                self.lines = iter([
                    json.dumps({"response": "a person "}).encode() + b"\n",
                    json.dumps({"response": "in green", "done": True}).encode() + b"\n"
                ])
            def readline(self, limit):
                return next(self.lines, b"")
        class FakeConnection:
            def __init__(self, host, port, timeout):
                self.host, self.port, self.timeout = host, port, timeout
                self.sock = None
            def connect(self): pass
            def request(self, method, path, body, headers):
                self.payload = json.loads(body)
            def getresponse(self): return FakeResponse()
            def close(self): pass
        class TestingConnection(FakeConnection):
            def request(self, method, path, body, headers):
                super().request(method, path, body, headers)
                selftest.assertEqual((self.host, self.port), ("127.0.0.1", 11434))
                selftest.assertEqual(path, "/api/generate")
                selftest.assertTrue(self.payload["stream"])
                selftest.assertEqual(self.payload["keep_alive"], "0")
        selftest = self
        with patch("dataset_caption_vision.http.client.HTTPConnection", TestingConnection):
            result = self.client.post(self.endpoint, json={
                "confirm": True, "model": "vision-local:latest", "request_id": "f"*32})
        self.assertEqual(result.status_code, 200, result.get_data(as_text=True))
        self.assertEqual(result.get_json()["caption"], "a person in green")
        self.assertIs(result.get_json()["saved"], False)
        self.assertEqual(self.client.get(self.caption).get_json()["revision"], 0)

    def test_cancel_interrupts_stream_and_does_not_store_caption(self):
        waiting = threading.Event()
        interrupted = threading.Event()
        class FakeSocket:
            def shutdown(self, how):
                interrupted.set()
        class BlockingResponse:
            status = 200
            def readline(self, limit):
                waiting.set()
                interrupted.wait(timeout=3)
                raise OSError("connection interrupted")
        class BlockingConnection:
            def __init__(self, host, port, timeout):
                self.sock = FakeSocket()
            def connect(self): pass
            def request(self, method, path, body, headers): pass
            def getresponse(self): return BlockingResponse()
            def close(self): interrupted.set()
        result = []
        def run():
            with self.app.test_client() as client:
                result.append(client.post(self.endpoint, json={
                    "model": "vision-local:latest", "confirm": True,
                    "request_id": "a"*32}))
        with patch("dataset_caption_vision.http.client.HTTPConnection", BlockingConnection):
            thread = threading.Thread(target=run, daemon=True)
            thread.start()
            self.assertTrue(waiting.wait(timeout=3))
            cancel_url = self.endpoint + "/cancel"
            self.assertEqual(self.client.post(cancel_url, json={"request_id": "b"*32}).status_code, 404)
            self.assertEqual(self.client.post(cancel_url, json={"request_id": "a"*32},
                headers={"Origin": "https://attacker.example"}).status_code, 403)
            cancel = self.client.post(cancel_url, json={"request_id": "a"*32})
            self.assertEqual(cancel.status_code, 200)
            self.assertTrue(cancel.get_json()["cancel_requested"])
            thread.join(timeout=3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(result[0].status_code, 409)
        self.assertIn("cancelled", result[0].get_json()["error"])
        self.assertEqual(self.client.get(self.caption).get_json()["revision"], 0)
        self.assertEqual(self.image.read_bytes(), self.data)

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
