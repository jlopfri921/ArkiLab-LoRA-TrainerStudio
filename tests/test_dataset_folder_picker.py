"""Tests for the native desktop directory picker without opening dialogs."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


class FolderPickerTests(unittest.TestCase):
    def setUp(self):
        try:
            from flask import Flask
            import dataset_folder_picker
        except ModuleNotFoundError as exc:
            if exc.name == "flask":
                self.skipTest("Flask not installed")
            raise
        self.module = dataset_folder_picker
        self.app = Flask(__name__)
        self.app.config["TESTING"] = True
        dataset_folder_picker.register(self.app, lambda: True, lambda: True)
        self.client = self.app.test_client()
        self.endpoint = "/api/workspace/datasets/browse-folder"

    def test_dialog_selection_and_cancel(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(self.module.sys, "platform", "win32"):
                with patch.object(self.module.subprocess, "run") as run:
                    run.return_value.returncode = 0
                    run.return_value.stdout = folder + "\n"
                    selected = self.client.post(self.endpoint, json={})
                    self.assertEqual(selected.status_code, 200)
                    self.assertEqual(Path(selected.get_json()["folder"]), Path(folder).resolve())
                    run.return_value.stdout = ""
                    cancel = self.client.post(self.endpoint, json={})
                    self.assertTrue(cancel.get_json()["cancelled"])

    def test_headless_fallback_preserves_manual_entry(self):
        with patch.object(self.module.sys, "platform", "linux"):
            with patch.dict(self.module.os.environ, {}, clear=True):
                result = self.client.post(self.endpoint, json={})
        self.assertEqual(result.status_code, 422)
        self.assertIn("Paste", result.get_json()["error"])

    def test_no_dialog_for_denied_remote_request(self):
        app = __import__("flask").Flask(__name__)
        app.config["TESTING"] = True
        self.module.register(app, lambda: False, lambda: True)
        with patch.object(self.module, "select_folder") as native:
            response = app.test_client().post(self.endpoint, json={})
            self.assertEqual(response.status_code, 403)
            native.assert_not_called()

    def test_no_dialog_for_cross_origin_request(self):
        app = __import__("flask").Flask(__name__)
        app.config["TESTING"] = True
        self.module.register(app, lambda: True, lambda: False)
        with patch.object(self.module, "select_folder") as native:
            response = app.test_client().post(self.endpoint, json={})
            self.assertEqual(response.status_code, 403)
            native.assert_not_called()


if __name__ == "__main__":
    unittest.main()
