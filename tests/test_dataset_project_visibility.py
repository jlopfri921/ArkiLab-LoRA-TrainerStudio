"""Project cards must reflect Dataset Studio references without falsifying trainer readiness."""
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


class DatasetProjectVisibilityTests(unittest.TestCase):
    def setUp(self):
        try:
            from flask import Flask
            import workspace_routes
            from workspace_store import ProjectStore
        except ModuleNotFoundError as exc:
            if exc.name == "flask":
                self.skipTest("Flask not installed")
            raise
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        store = ProjectStore(self.base / "settings" / "orkilab" / "projects.sqlite3")
        self.a = store.create(dict(name="Photos", category="image", engine="sdxl",
                                   dataset="", notes=""), {"sdxl"})
        self.b = store.create(dict(name="Empty", category="image", engine="sdxl",
                                   dataset="", notes=""), {"sdxl"})
        source = self.base / "my_sources"
        source.mkdir()
        self.source = source
        prepared = self.base / "Datasets" / "OrkiLab" / self.a["id"] / "version1"
        prepared.mkdir(parents=True)
        self.prepared = prepared
        path = self.base / "settings" / "orkilab" / "datasets.sqlite3"
        with closing(sqlite3.connect(path)) as conn, conn:
            conn.execute("CREATE TABLE dataset_images (id TEXT PRIMARY KEY, "
                         "project_id TEXT NOT NULL, path TEXT NOT NULL, review TEXT)")
            conn.execute("CREATE TABLE dataset_captions (image_id TEXT PRIMARY KEY, "
                         "project_id TEXT NOT NULL, caption TEXT)")
            conn.execute("CREATE TABLE dataset_preparations (id TEXT PRIMARY KEY, "
                         "project_id TEXT NOT NULL, path TEXT)")
            conn.execute("INSERT INTO dataset_images VALUES(?,?,?,'approved')",
                         ("c" * 32, self.a["id"], str(source / "one.png")))
            conn.execute("INSERT INTO dataset_images VALUES(?,?,?,'approved')",
                         ("d" * 32, self.a["id"], str(source / "two.png")))
            conn.execute("INSERT INTO dataset_captions VALUES(?,?,?)",
                         ("c" * 32, self.a["id"], "portrait"))
            conn.execute("INSERT INTO dataset_preparations VALUES(?,?,?)",
                         ("e" * 32, self.a["id"], str(prepared)))
        app = Flask(__name__)
        app.config["TESTING"] = True
        workspace_routes.register(app, self.base, lambda: {"trainers": [
            {"id": "sdxl", "name": "SDXL"}]})
        self.client = app.test_client()

    def test_linked_dataset_is_visible_even_when_manual_project_path_is_empty(self):
        result = self.client.get("/api/workspace/projects")
        self.assertEqual(result.status_code, 200)
        projects = {p["id"]: p for p in result.get_json()["projects"]}
        linked = projects[self.a["id"]]
        self.assertEqual(linked["dataset"], "")
        self.assertEqual(linked["dataset_image_count"], 2)
        self.assertEqual(linked["dataset_caption_count"], 1)
        self.assertEqual(linked["dataset_source_folders"], [str(self.source)])
        self.assertEqual(linked["dataset_prepared_path"], str(self.prepared))
        self.assertFalse(linked["dataset_train_ready"])
        empty = projects[self.b["id"]]
        self.assertEqual(empty["dataset_source_folders"], [])
        self.assertIsNone(empty["dataset_prepared_path"])


if __name__ == "__main__":
    unittest.main()
