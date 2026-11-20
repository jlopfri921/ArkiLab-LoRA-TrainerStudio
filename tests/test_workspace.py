"""Workspace metadata tests without GPU or Flask."""
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from workspace_store import ProjectStore


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "projects.sqlite3"
        self.store = ProjectStore(self.db)
        self.payload = dict(name="Sculpture", engine="sdxl", category="image",
                            dataset="local reference", notes="Test")

    def test_persistence_archive_restore(self):
        row = self.store.create(self.payload, {"sdxl"})
        self.assertEqual(ProjectStore(self.db).list()[0]["id"], row["id"])
        self.assertTrue(self.store.archive(row["id"]))
        self.assertEqual(self.store.list(), [])
        self.assertEqual(self.store.list(True)[0]["name"], "Sculpture")
        self.assertTrue(self.store.archive(row["id"], False))
        self.assertEqual(len(self.store.list()), 1)
        self.assertFalse(self.store.archive("missing"))

    def test_validation(self):
        for invalid in (None, {}, dict(self.payload, name=" "), dict(self.payload, engine="unknown"),
                        dict(self.payload, category="invalid"), dict(self.payload, notes="x"*4001)):
            with self.assertRaises(ValueError):
                self.store.create(invalid, {"sdxl"})
        self.assertEqual(self.store.list(), [])

    def test_data_is_not_sql(self):
        row = self.store.create(dict(self.payload, name="x'); DROP TABLE projects; --"), {"sdxl"})
        self.assertEqual(self.store.list()[0]["name"], row["name"])
