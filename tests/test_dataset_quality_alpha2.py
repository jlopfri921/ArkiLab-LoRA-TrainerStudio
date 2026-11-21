"""Bounded Dataset Studio quality scanner regression tests (no GPU required)."""
import sqlite3
import struct
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


class DatasetQualityTests(unittest.TestCase):
    def setUp(self):
        try:
            from flask import Flask
            import dataset_studio
        except ModuleNotFoundError as exc:
            if exc.name == "flask":
                self.skipTest("Flask not installed in foundation-only CI")
            raise
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.folder = self.base / "source"
        self.folder.mkdir()
        self.project = "b" * 32
        dbpath = self.base / "settings" / "orkilab" / "projects.sqlite3"
        dbpath.parent.mkdir(parents=True)
        with closing(sqlite3.connect(dbpath)) as conn, conn:
            conn.execute("CREATE TABLE projects (id TEXT PRIMARY KEY, archived INTEGER NOT NULL)")
            conn.execute("INSERT INTO projects VALUES (?,0)", (self.project,))
        self.original = (b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\x0dIHDR"
                         + struct.pack(">II", 256, 256) + b"\x08\x02\x00\x00\x00")
        self.a = self.folder / "a.png"
        self.b = self.folder / "b.png"
        self.a.write_bytes(self.original)
        self.b.write_bytes(self.original)
        self.app = Flask(__name__)
        self.app.config["TESTING"] = True
        dataset_studio.register(self.app, self.base)
        self.client = self.app.test_client()
        self.root = "/api/workspace/datasets/" + self.project
        self.scan = self.root + "/quality/scan"
        self.assertEqual(self.client.post(self.root, json={"folder": str(self.folder)}).status_code, 200)

    def test_exact_duplicates_resolution_and_originals_unchanged(self):
        one = self.client.post(self.scan, json={"cursor": None, "limit": 1})
        self.assertEqual(one.status_code, 200, one.get_data(as_text=True))
        self.assertFalse(one.get_json()["finished"])
        nxt = one.get_json()["next_cursor"]
        self.assertEqual(len(nxt), 32)
        two = self.client.post(self.scan, json={"cursor": nxt, "limit": 1})
        self.assertEqual(two.status_code, 200)
        self.assertTrue(two.get_json()["finished"])
        images = self.client.get(self.root).get_json()["images"]
        self.assertEqual(len(images), 2)
        self.assertTrue(all(i["duplicate"] for i in images), images)
        self.assertTrue(all(i["quality"] == "low_resolution" for i in images))
        self.assertTrue(all(i["analyzed"] for i in images))
        self.assertEqual(self.a.read_bytes(), self.original)
        self.assertEqual(self.b.read_bytes(), self.original)

    def test_batch_validation_local_only_and_missing_file(self):
        self.assertEqual(self.client.post(self.scan, json={"limit": 21}).status_code, 400)
        self.assertEqual(self.client.post(self.scan, json={"limit": 0}).status_code, 400)
        self.assertEqual(self.client.post(self.scan, json={"limit": True}).status_code, 400)
        self.assertEqual(self.client.post(self.scan, json={"cursor": "../bad"}).status_code, 400)
        self.assertEqual(self.client.post(self.scan, json={"limit": 1},
                         headers={"Origin": "https://malicious.invalid"}).status_code, 403)
        self.assertEqual(self.client.post(self.scan, json={"limit": 1},
                         environ_overrides={"REMOTE_ADDR": "192.0.2.3"}).status_code, 403)
        self.a.unlink()
        first = self.client.post(self.scan, json={})
        self.assertEqual(first.status_code, 200)
        images = self.client.get(self.root).get_json()["images"]
        self.assertEqual(sum(i["quality"] == "missing" for i in images), 1)
        self.assertEqual(sum(i["duplicate"] for i in images), 0)
        self.assertEqual(self.b.read_bytes(), self.original)

    def test_scan_does_not_change_review_states(self):
        ids = [x["id"] for x in self.client.get(self.root).get_json()["images"]]
        update = self.client.post(self.root + "/batch",
                                  json={"action": "review", "review": "approved", "ids": ids})
        self.assertEqual(update.status_code, 200)
        self.assertEqual(self.client.post(self.scan, json={"limit": 20}).status_code, 200)
        images = self.client.get(self.root).get_json()["images"]
        self.assertTrue(all(i["review"] == "approved" for i in images))


if __name__ == "__main__":
    unittest.main()
