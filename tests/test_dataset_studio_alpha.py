"""Dataset Studio alpha non-destructive and local-only regression tests."""
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


class DatasetIndexTests(unittest.TestCase):
    def setUp(self):
        try:
            from flask import Flask
            import dataset_studio
        except ModuleNotFoundError as exc:
            if exc.name == "flask":
                self.skipTest("Flask unavailable in lightweight foundation job")
            raise
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.folder = self.base / "originals"
        self.folder.mkdir()
        self.photo = self.folder / "sample.png"
        self.photo.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 32)
        self.project = "a" * 32
        dbpath = self.base / "settings" / "orkilab" / "projects.sqlite3"
        dbpath.parent.mkdir(parents=True)
        with sqlite3.connect(dbpath) as conn:
            conn.execute("CREATE TABLE projects (id TEXT PRIMARY KEY, archived INTEGER NOT NULL)")
            conn.execute("INSERT INTO projects VALUES (?,0)", (self.project,))
        app = Flask(__name__)
        app.config["TESTING"] = True
        dataset_studio.register(app, self.base)
        self.client = app.test_client()
        self.prefix = "/api/workspace/datasets/" + self.project

    def test_remote_access_is_rejected(self):
        for method, suffix in (("GET", ""), ("POST", ""), ("DELETE", "/" + "b" * 32)):
            with self.subTest(method=method):
                response = self.client.open(
                    self.prefix + suffix, method=method,
                    environ_overrides={"REMOTE_ADDR": "198.51.100.42"},
                    json={} if method == "POST" else None)
                self.assertEqual(response.status_code, 403)

    def test_import_is_non_destructive_and_idempotent(self):
        original = self.photo.read_bytes()
        endpoint = self.prefix
        payload = {"folder": str(self.folder)}
        imported = self.client.post(endpoint, json=payload)
        self.assertEqual(imported.status_code, 200, imported.get_data(as_text=True))
        self.assertEqual(imported.get_json()["imported"], 1)
        self.assertEqual(self.client.post(endpoint, json=payload).get_json()["imported"], 0)
        listing = self.client.get(endpoint).get_json()["images"]
        self.assertEqual(len(listing), 1)
        photo_url = endpoint + "/" + listing[0]["id"]
        self.assertEqual(self.client.get(photo_url).status_code, 200)
        self.assertEqual(self.client.delete(photo_url).status_code, 200)
        self.assertEqual(self.client.get(endpoint).get_json()["images"], [])
        self.assertEqual(self.photo.read_bytes(), original)

    def test_missing_and_unsupported_input(self):
        self.assertEqual(self.client.post(self.prefix, json={"folder": "/missing/dataset"}).status_code, 400)
        self.assertEqual(self.client.get("/api/workspace/datasets/" + "z"*32).status_code, 404)
        self.assertEqual(self.client.post(self.prefix, json={"folder": str(self.photo)}).status_code, 400)
        (self.folder / "not_an_image.txt").write_text("hello", encoding="utf-8")
        result = self.client.post(self.prefix, json={"folder": str(self.folder)})
        self.assertEqual(result.get_json()["imported"], 1)
        self.photo.unlink()
        row = self.client.get(self.prefix).get_json()["images"][0]
        self.assertTrue(row["missing"])
        self.assertEqual(self.client.get(self.prefix + "/" + row["id"]).status_code, 404)


if __name__ == "__main__":
    unittest.main()
