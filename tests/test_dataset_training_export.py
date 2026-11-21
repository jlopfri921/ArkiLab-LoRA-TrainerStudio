"""Training dataset export smoke and non-destructive behavior."""
import io
import sqlite3
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


class TrainingDatasetExportTests(unittest.TestCase):
    def setUp(self):
        try:
            from flask import Flask
            import dataset_studio
        except ModuleNotFoundError as exc:
            if exc.name == "flask":
                self.skipTest("Flask unavailable")
            raise
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        folder = self.root / "images"
        folder.mkdir()
        self.image = folder / "test.png"
        self.original = b"\x89PNG\r\n\x1a\n" + b"X" * 128
        self.image.write_bytes(self.original)
        self.project_id = "a" * 32
        db = self.root / "settings" / "orkilab" / "projects.sqlite3"
        db.parent.mkdir(parents=True)
        with sqlite3.connect(db) as connection:
            connection.execute("CREATE TABLE projects (id TEXT PRIMARY KEY, archived INTEGER NOT NULL)")
            connection.execute("INSERT INTO projects VALUES (?, 0)", (self.project_id,))
        app = Flask(__name__)
        app.config["TESTING"] = True
        dataset_studio.register(app, self.root)
        self.client = app.test_client()
        self.path = "/api/workspace/datasets/" + self.project_id
        self.assertEqual(self.client.post(self.path, json={"folder": str(folder)}).status_code, 200)
        self.image_id = self.client.get(self.path).get_json()["images"][0]["id"]
        self.export = self.path + "/training-export"

    def test_caption_pair_and_unchanged_source(self):
        missing = self.client.post(self.export, json={
            "mode": "preview", "image_ids": [self.image_id]}).get_json()
        self.assertEqual(missing["ready"], 0)
        self.assertEqual(missing["skipped"][0]["reason"], "missing_caption")
        caption_url = self.path + "/" + self.image_id + "/caption"
        saved = self.client.put(caption_url, json={
            "caption": "person in red", "expected_revision": 0})
        self.assertEqual(saved.status_code, 200)
        preview = self.client.post(self.export, json={
            "mode": "preview", "image_ids": [self.image_id]})
        self.assertEqual(preview.get_json()["ready"], 1)
        self.assertFalse(preview.get_json()["trainer_ready"])
        self.assertEqual(self.client.post(self.export, json={
            "mode": "download", "image_ids": [self.image_id]}).status_code, 400)
        result = self.client.post(self.export, json={
            "mode": "download", "image_ids": [self.image_id], "confirm": True})
        self.assertEqual(result.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(result.data)) as archive:
            self.assertEqual(archive.read("dataset/test.png"), self.original)
            self.assertEqual(archive.read("dataset/test.txt"), b"person in red")
            self.assertIn("manifest.json", archive.namelist())
        self.assertEqual(self.image.read_bytes(), self.original)
        self.assertFalse(self.image.with_suffix(".txt").exists())

    def test_invalid_cross_project_and_changed_source(self):
        invalid = self.client.post(self.export, json={
            "mode": "preview", "image_ids": ["b" * 32]})
        self.assertEqual(invalid.status_code, 409)
        self.image.write_bytes(b"changed")
        changed = self.client.post(self.export, json={
            "mode": "preview", "image_ids": [self.image_id]}).get_json()
        self.assertEqual(changed["ready"], 0)
        self.assertEqual(changed["skipped"][0]["reason"], "missing_caption")


if __name__ == "__main__":
    unittest.main()
