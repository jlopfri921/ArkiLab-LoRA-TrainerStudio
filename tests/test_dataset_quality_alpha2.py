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

    def test_quality_pairs_endpoint_returns_exact_duplicates_without_paths(self):
        self.assertEqual(self.client.post(self.scan, json={"limit": 20}).status_code, 200)
        response = self.client.get(self.root + "/quality/pairs")
        self.assertEqual(response.status_code, 200)
        pairs = response.get_json()["pairs"]
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["kind"], "exact")
        self.assertEqual(set(pairs[0]), {"left", "right", "kind"})
        self.assertEqual(self.client.get(self.root + "/quality/pairs?kind=near").get_json()["pairs"], [])
        self.assertEqual(self.client.get(self.root + "/quality/pairs?kind=unknown").status_code, 400)
        self.assertEqual(self.client.get(self.root + "/quality/pairs",
                         environ_overrides={"REMOTE_ADDR": "192.0.2.4"}).status_code, 403)
        self.assertEqual(self.a.read_bytes(), self.original)
        self.assertEqual(self.b.read_bytes(), self.original)

    def test_visual_similarity_and_blur_are_review_suggestions(self):
        from PIL import Image, ImageDraw, ImageFilter
        from image_quality_visual import near_match, visual_metrics
        scene = Image.new("RGB", (640, 640), "white")
        draw = ImageDraw.Draw(scene)
        for n in range(8):
            draw.rectangle((n * 80, n * 80, n * 80 + 36, n * 80 + 64),
                           fill=(20 + n * 18, 30, 170))
        sharp = self.folder / "scene.png"
        compressed = self.folder / "scene.jpg"
        soft = self.folder / "scene_blurred.png"
        blank = self.folder / "blank.png"
        scene.save(sharp)
        scene.save(compressed, format="JPEG", quality=95)
        scene.filter(ImageFilter.GaussianBlur(radius=9)).save(soft)
        Image.new("RGB", (640, 640), "white").save(blank)
        before = {p: p.read_bytes() for p in (sharp, compressed, soft, blank)}
        self.assertEqual(self.client.post(self.root, json={"folder": str(self.folder)}).status_code, 200)
        for _ in range(5):
            result = self.client.post(self.scan, json={"cursor": None, "limit": 20})
            self.assertEqual(result.status_code, 200)
            self.assertTrue(result.get_json()["finished"])
            break
        phash_a, sharp_score, _ = visual_metrics(sharp)
        phash_b, _, _ = visual_metrics(compressed)
        _, soft_score, _ = visual_metrics(soft)
        blank_hash, _, blank_blur = visual_metrics(blank)
        self.assertIsNotNone(phash_a)
        self.assertTrue(near_match(phash_a, phash_b))
        self.assertGreater(sharp_score, soft_score)
        self.assertIsNone(blank_hash)
        self.assertFalse(blank_blur)
        images = self.client.get(self.root).get_json()["images"]
        self.assertTrue(any(x["near_duplicate"] for x in images), images)
        self.assertTrue(any(x["blur_score"] is not None for x in images), images)
        filtered = self.client.get(self.root + "?quality=near")
        self.assertEqual(filtered.status_code, 200)
        self.assertTrue(filtered.get_json()["images"])
        comparison = self.client.get(self.root + "/quality/pairs?kind=near")
        self.assertEqual(comparison.status_code, 200)
        self.assertTrue(comparison.get_json()["pairs"])
        self.assertTrue(all(pair["kind"] == "near" for pair in comparison.get_json()["pairs"]))
        self.assertEqual(self.client.get(self.root + "?quality=typo").status_code, 400)
        for file, original in before.items():
            self.assertEqual(file.read_bytes(), original)

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
