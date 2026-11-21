"""Caption Studio manual versioning and safety tests; originals must never change."""
import io
import json
import sqlite3
import zipfile
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
        self.assertEqual(self.client.put(self.caption, json={"caption": "bad" + chr(0) + "control", "expected_revision": 1}).status_code, 400)
        self.assertEqual(self.client.put(self.caption, json={"caption": "ok", "expected_revision": 1},
                         headers={"Origin": "https://attacker.example"}).status_code, 403)
        self.assertEqual(self.client.get(self.caption,
                         environ_overrides={"REMOTE_ADDR": "203.0.113.4"}).status_code, 403)
        self.assertEqual(self.client.get(self.library + "/" + "a"*32 + "/caption").status_code, 404)
        self.assertEqual(self.picture.read_bytes(), self.original)

    def test_export_preview_and_explicit_zip_download_never_edit_originals(self):
        image_id = self.caption.split("/")[-2]
        endpoint = self.library + "/captions/export"
        saved = self.client.put(self.caption, json={
            "caption": "sunset, orange sky, andalucía", "expected_revision": 0})
        self.assertEqual(saved.status_code, 200)
        preview = self.client.post(endpoint, json={"mode": "preview", "image_ids": [image_id]})
        self.assertEqual(preview.status_code, 200, preview.get_data(as_text=True))
        summary = preview.get_json()
        self.assertEqual((summary["selected"], summary["exportable"], summary["skipped_empty"]), (1, 1, 0))
        self.assertEqual(summary["files"][0]["revision"], 1)
        not_confirmed = self.client.post(endpoint, json={"mode": "download", "image_ids": [image_id]})
        self.assertEqual(not_confirmed.status_code, 400)
        download = self.client.post(endpoint, json={
            "mode": "download", "image_ids": [image_id], "confirm": True})
        self.assertEqual(download.status_code, 200)
        self.assertEqual(download.mimetype, "application/zip")
        self.assertIn("attachment", download.headers["Content-Disposition"])
        self.assertEqual(download.headers["Cache-Control"], "no-store")
        with zipfile.ZipFile(io.BytesIO(download.data)) as zf:
            files = zf.namelist()
            self.assertEqual(len(files), 2)
            self.assertIn("captions-manifest.json", files)
            name = next(name for name in files if name.endswith(".txt"))
            self.assertEqual(name, "captions/sample.txt")
            self.assertEqual(zf.read(name).decode("utf-8"), "sunset, orange sky, andalucía")
            manifest = json.loads(zf.read("captions-manifest.json"))
            self.assertEqual(manifest["format"], "orkilab-caption-sidecars-v1")
            self.assertEqual(manifest["files"][0]["sidecar"], name)
        self.assertEqual(self.picture.read_bytes(), self.original)
        self.assertFalse((self.folder / "sample.txt").exists())

    def test_caption_zip_preview_filters_empty_and_rejects_invalid_selection(self):
        image_id = self.caption.split("/")[-2]
        endpoint = self.library + "/captions/export"
        empty = self.client.post(endpoint, json={"mode": "preview", "image_ids": [image_id]})
        self.assertEqual(empty.status_code, 200)
        self.assertEqual(empty.get_json()["skipped_empty"], 1)
        self.assertEqual(empty.get_json()["files"], [])
        self.assertEqual(self.client.post(endpoint, json={
            "mode": "download", "image_ids": [image_id], "confirm": True}).status_code, 400)
        self.assertEqual(self.client.post(endpoint, json={
            "mode": "preview", "image_ids": [image_id] * 201}).status_code, 400)
        self.assertEqual(self.client.post(endpoint, json={
            "mode": "preview", "image_ids": [".." * 16]}).status_code, 400)
        self.assertEqual(self.client.post(endpoint, json={
            "mode": "preview", "image_ids": ["a" * 32]}).status_code, 409)
        self.assertEqual(self.client.post(endpoint, json={
            "mode": "preview", "image_ids": [image_id]},
            headers={"Origin": "https://attacker.example"}).status_code, 403)
        self.assertEqual(self.client.post(endpoint, json={
            "mode": "preview", "image_ids": [image_id]},
            environ_overrides={"REMOTE_ADDR": "203.0.113.7"}).status_code, 403)
        self.assertEqual(self.picture.read_bytes(), self.original)

    def test_caption_zip_sanitizes_weird_names_and_deduplicates_ids(self):
        image_id = self.caption.split("/")[-2]
        with closing(sqlite3.connect(self.base / "settings" / "orkilab" / "datasets.sqlite3")) as conn, conn:
            conn.execute("UPDATE dataset_images SET name=? WHERE id=?", ("../bad\\\\folder<name>.png", image_id))
        self.client.put(self.caption, json={"caption": "caption", "expected_revision": 0})
        endpoint = self.library + "/captions/export"
        download = self.client.post(endpoint, json={
            "mode": "download", "image_ids": [image_id, image_id], "confirm": True})
        self.assertEqual(download.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(download.data)) as archive:
            names = archive.namelist()
            self.assertEqual(len(names), 2)
            safe = next(name for name in names if name.endswith(".txt"))
            self.assertNotIn("../", safe)
            self.assertNotIn("\\\\", safe)
            self.assertEqual(safe.count("/"), 1)
            self.assertTrue(safe.endswith(".txt"))
        self.assertEqual(self.picture.read_bytes(), self.original)

    def test_same_image_basenames_are_disambiguated_deterministically(self):
        first_id = self.caption.split("/")[-2]
        second_id = "d" * 32
        second = self.folder / "second.png"
        second.write_bytes(b"independent original")
        database = self.base / "settings" / "orkilab" / "datasets.sqlite3"
        with closing(sqlite3.connect(database)) as conn, conn:
            conn.execute(
                "INSERT INTO dataset_images(id,project_id,path,name,bytes,review) "
                "VALUES(?,?,?,?,?,?)",
                (second_id, self.project, str(second), "sample.png", 20, "unreviewed")
            )
        first = self.client.put(self.caption, json={"caption": "first", "expected_revision": 0})
        other_url = self.library + "/" + second_id + "/caption"
        other = self.client.put(other_url, json={"caption": "second", "expected_revision": 0})
        self.assertEqual((first.status_code, other.status_code), (200, 200))
        endpoint = self.library + "/captions/export"
        preview = self.client.post(endpoint, json={
            "mode": "preview", "image_ids": [first_id, second_id]}).get_json()
        self.assertEqual(preview["exportable"], 2)
        names = [item["sidecar"] for item in preview["files"]]
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue(all(name.startswith("captions/sample__") for name in names))
        result = self.client.post(endpoint, json={
            "mode": "download", "image_ids": [first_id, second_id],
            "confirm": True})
        self.assertEqual(result.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(result.data)) as archive:
            self.assertEqual({archive.read(name).decode("utf-8") for name in names},
                             {"first", "second"})
        self.assertEqual(self.picture.read_bytes(), self.original)
        self.assertEqual(second.read_bytes(), b"independent original")

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
