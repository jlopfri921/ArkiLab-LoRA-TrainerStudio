"""Caption Studio manual versioning and safety tests; originals must never change."""
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


class CaptionStudioTests(unittest.TestCase):
    def setUp(self):
        try:
            from flask import Flask
            import dataset_studio
        except ModuleNotFoundError as exc:
            if exc.name == "flask":
                self.skipTest("Flask not present in lightweight foundation job")
            raise
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.folder = self.base / "photos"
        self.folder.mkdir()
        self.original = b"not decoded during caption editing"
        self.picture = self.folder / "sample.png"
        self.picture.write_bytes(self.original)
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
        self.library = "/api/workspace/datasets/" + self.project
        response = self.client.post(self.library, json={"folder": str(self.folder)})
        self.assertEqual(response.status_code, 200)
        image_id = self.client.get(self.library).get_json()["images"][0]["id"]
        self.caption = self.library + "/" + image_id + "/caption"
        self.history = self.caption + "/history"

    def test_save_version_restore_and_no_original_file_write(self):
        initial = self.client.get(self.caption).get_json()
        self.assertEqual(initial["caption"], "")
        self.assertEqual(initial["revision"], 0)
        one = self.client.put(self.caption, json={"caption": "person, red jacket", "expected_revision": 0})
        self.assertEqual(one.status_code, 200, one.get_data(as_text=True))
        self.assertEqual(one.get_json()["revision"], 1)
        two = self.client.put(self.caption, json={"caption": "person, red coat", "expected_revision": 1})
        self.assertEqual(two.get_json()["revision"], 2)
        self.assertEqual([x["revision"] for x in self.client.get(self.history).get_json()["history"]], [2, 1])
        restore = self.client.put(self.caption, json={"caption": "person, red jacket", "expected_revision": 2})
        self.assertEqual(restore.get_json()["revision"], 3)
        self.assertEqual(self.client.get(self.caption).get_json()["caption"], "person, red jacket")
        empty = self.client.put(self.caption, json={"caption": "", "expected_revision": 3})
        self.assertEqual(empty.get_json()["revision"], 4)
        self.assertEqual(self.client.get(self.caption).get_json()["caption"], "")
        self.assertEqual(self.picture.read_bytes(), self.original)
        self.assertFalse((self.folder / "sample.txt").exists())

    def test_conflict_validation_and_isolation(self):
        self.assertEqual(self.client.put(self.caption, json={"caption": "first", "expected_revision": 0}).status_code, 200)
        stale = self.client.put(self.caption, json={"caption": "stale", "expected_revision": 0})
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(self.client.get(self.caption).get_json()["caption"], "first")
        self.assertEqual(self.client.put(self.caption, json={"caption": "x" * 2001, "expected_revision": 1}).status_code, 400)
        self.assertEqual(self.client.put(self.caption, json={"caption": "ok", "expected_revision": True}).status_code, 400)
        self.assertEqual(self.client.put(self.caption, json={"caption": "bad\\x00control", "expected_revision": 1}).status_code, 400)
        self.assertEqual(self.client.put(self.caption, json={"caption": "ok", "expected_revision": 1},
                         headers={"Origin": "https://attacker.example"}).status_code, 403)
        self.assertEqual(self.client.get(self.caption,
                         environ_overrides={"REMOTE_ADDR": "203.0.113.4"}).status_code, 403)
        self.assertEqual(self.client.get(self.library + "/" + "a"*32 + "/caption").status_code, 404)
        self.assertEqual(self.picture.read_bytes(), self.original)

    def test_history_is_bounded_and_unchanged_caption_does_not_increment(self):
        for revision in range(31):
            saved = self.client.put(self.caption,
                                    json={"caption": "caption "+str(revision), "expected_revision": revision})
            self.assertEqual(saved.status_code, 200)
        same = self.client.put(self.caption, json={"caption": "caption 30", "expected_revision": 31})
        self.assertEqual(same.get_json()["revision"], 31)
        history = self.client.get(self.history).get_json()["history"]
        self.assertEqual(len(history), 25)
        self.assertEqual(history[0]["revision"], 31)
        self.assertEqual(history[-1]["revision"], 7)
        self.assertEqual(self.picture.read_bytes(), self.original)


if __name__ == "__main__":
    unittest.main()
