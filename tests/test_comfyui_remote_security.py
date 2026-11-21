"""Security regression tests for local-only ComfyUI administration endpoints.

No GPU, ComfyUI server or network access required.
"""
import sys
import tempfile
import unittest
from pathlib import Path

from flask import Flask

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import comfyui_connect
import generation_studio
import workflow_library


class ComfyUILoopbackSecurityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        app = Flask(__name__)
        app.config["TESTING"] = True
        comfyui_connect.register(app, root)
        workflow_library.register(app, root)
        generation_studio.register(app, root)
        self.client = app.test_client()

    def test_remote_requests_blocked_before_any_processing(self):
        endpoints = [
            ("GET", "/api/workspace/comfyui"),
            ("POST", "/api/workspace/comfyui"),
            ("POST", "/api/workspace/comfyui/check"),
            ("POST", "/api/workspace/models"),
            ("POST", "/api/workspace/comfyui/nodes"),
            ("GET", "/api/workspace/workflows"),
            ("POST", "/api/workspace/workflows"),
            ("GET", "/api/workspace/workflows/example"),
            ("PATCH", "/api/workspace/workflows/example"),
            ("GET", "/api/workspace/workflows/folder"),
            ("POST", "/api/workspace/workflows/folder"),
            ("POST", "/api/workspace/generation/bridge/install"),
            ("POST", "/api/workspace/generation/prepare"),
            ("POST", "/api/workspace/generation/parameters"),
            ("POST", "/api/workspace/generation/compare"),
            ("POST", "/api/workspace/generation"),
            ("POST", "/api/workspace/comfyui/memory/release"),
            ("POST", "/api/workspace/generation/example/cancel"),
            ("GET", "/api/workspace/generation/example"),
            ("GET", "/api/workspace/generation/history"),
            ("GET", "/api/workspace/generation/history/example"),
            ("GET", "/api/workspace/generation/media/example/0"),
        ]
        for method, path in endpoints:
            with self.subTest(method=method, path=path):
                response = self.client.open(
                    path, method=method,
                    environ_overrides={"REMOTE_ADDR": "203.0.113.17"},
                    json={} if method in ("POST", "PATCH") else None,
                )
                self.assertEqual(response.status_code, 403,
                                 (method, path, response.get_data(as_text=True)))

    def test_local_settings_remain_available(self):
        for address in ("127.0.0.1", "::1"):
            with self.subTest(address=address):
                response = self.client.get(
                    "/api/workspace/comfyui",
                    environ_overrides={"REMOTE_ADDR": address},
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.get_json()["url"], comfyui_connect.DEFAULT)

    def test_private_only_address_validation_rejects_public_and_redirect_urls(self):
        invalid = (
            "https://example.com", "http://8.8.8.8:8188",
            "http://127.0.0.1:8188/admin", "http://127.0.0.1:8188/?x=1",
            "http://user:password@127.0.0.1:8188",
            "http://127.0.0.1:8188#frag",
        )
        for address in invalid:
            with self.subTest(address=address):
                with self.assertRaises(ValueError):
                    comfyui_connect.validate_url(address)


if __name__ == "__main__":
    unittest.main()
