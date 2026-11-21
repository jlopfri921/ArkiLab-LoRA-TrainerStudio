"""Dataset Studio alpha non-destructive and local-only regression tests."""
import sqlite3
from contextlib import closing
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
        with closing(sqlite3.connect(dbpath)) as conn, conn:
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

    def test_metadata_review_filter_sort_and_batch_no_file_changes(self):
        import struct
        first = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\x0dIHDR" + struct.pack(">II", 640, 480) + b"\x08\x02\x00\x00\x00"
        self.photo.write_bytes(first)
        other = self.folder / "other.gif"
        other.write_bytes(b"GIF89a" + struct.pack("<HH", 120, 90) + b"x" * 10)
        before = {p.name: p.read_bytes() for p in (self.photo, other)}
        self.assertEqual(self.client.post(self.prefix, json={"folder": str(self.folder)}).get_json()["imported"], 2)
        listing = self.client.get(self.prefix + "?sort=resolution").get_json()["images"]
        self.assertEqual([(x["width"], x["height"]) for x in listing], [(640, 480), (120, 90)])
        self.assertEqual(self.client.get(self.prefix + "?sort=invalid").status_code, 400)
        selected = [listing[0]["id"]]
        batch = self.prefix + "/batch"
        marked = self.client.post(batch, json={"action": "review", "ids": selected, "review": "approved"})
        self.assertEqual(marked.status_code, 200, marked.get_data(as_text=True))
        approved = self.client.get(self.prefix + "?review=approved").get_json()["images"]
        self.assertEqual(len(approved), 1)
        self.assertEqual(approved[0]["id"], selected[0])
        self.assertEqual(len(self.client.get(self.prefix + "?review=unreviewed").get_json()["images"]), 1)
        self.assertEqual(self.client.get(self.prefix + "?review=invalid").status_code, 400)
        self.assertEqual(self.client.get(self.prefix + "?search=other").get_json()["images"][0]["name"], "other.gif")
        self.assertEqual(self.client.post(batch, json={"action": "review", "review": "bad", "ids": selected}).status_code, 400)
        self.assertEqual(self.client.post(batch, json={"action": "remove", "ids": selected}).get_json()["updated"], 1)
        self.assertEqual(len(self.client.get(self.prefix).get_json()["images"]), 1)
        for p in (self.photo, other):
            self.assertEqual(p.read_bytes(), before[p.name])

    def test_reject_cross_site_mutations_and_overlarge_batch(self):
        cross = {"Origin": "http://evil.example"}
        self.assertEqual(self.client.post(self.prefix, json={"folder": str(self.folder)}, headers=cross).status_code, 403)
        self.assertEqual(self.client.post(self.prefix + "/batch", json={"action": "remove", "ids": ["a"*32]}, headers=cross).status_code, 403)
        self.assertEqual(self.client.post(self.prefix + "/batch", json={"action": "remove", "ids": ["a"*32] * 201}).status_code, 400)
        self.assertEqual(self.client.post(self.prefix + "/batch", json={"action": "remove", "ids": ["../" * 11]}).status_code, 400)

    def test_schema_migrates_existing_index_without_losing_review(self):
        self.client.post(self.prefix, json={"folder": str(self.folder)})
        db = self.base / "settings" / "orkilab" / "datasets.sqlite3"
        with closing(sqlite3.connect(db)) as conn, conn:
            conn.execute("UPDATE dataset_images SET review='approved'")
            conn.execute("ALTER TABLE dataset_images DROP COLUMN width")
            conn.execute("ALTER TABLE dataset_images DROP COLUMN height")
        listing = self.client.get(self.prefix).get_json()["images"]
        self.assertEqual(listing[0]["review"], "approved")
        self.assertIsNone(listing[0]["width"])
        self.assertIsNone(listing[0]["height"])

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
