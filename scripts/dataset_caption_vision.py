"""Opt-in image captions via a user-installed local Ollama vision model.

This module never downloads models, starts Ollama, writes images, or saves a caption.
Only the explicit POST request performs generation. The API is loopback-only.
"""
import base64
import json
import re
import threading
import urllib.error
import urllib.request
from contextlib import closing
from pathlib import Path

from flask import jsonify, request

MAX_IMAGE_BYTES = 12 * 1024 * 1024
MAX_CAPTION = 2000
MAX_PROMPT = 700
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_./:-]{0,99}$")
class NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        # Prevent Ollama/misconfigured local proxies from redirecting image
        # bytes to a remote destination.
        return None


DEFAULT_PROMPT = ("Describe the visible content of this image for image-model LoRA "
                  "training. Be factual and concise. Include subject, appearance, "
                  "clothing, action, composition, background and lighting when visible. "
                  "Do not infer identities or hidden attributes. Respond with the "
                  "caption only, no markdown or introductory text.")


def register(app, db, project_exists, local, valid_origin):
    busy = threading.Lock()

    @app.post("/api/workspace/datasets/<project_id>/<image_id>/caption/suggest")
    def suggest_caption(project_id, image_id):
        if not local() or not valid_origin():
            return jsonify(error="Local same-origin access required"), 403
        if not project_exists(project_id):
            return jsonify(error="Active project not found"), 404
        if request.mimetype != "application/json" or not 0 < (request.content_length or 0) <= 4096:
            return jsonify(error="Invalid generation request"), 400
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or data.get("confirm") is not True:
            return jsonify(error="Explicit confirmation required"), 400
        model = data.get("model")
        prompt = data.get("prompt", DEFAULT_PROMPT)
        if not isinstance(model, str) or not MODEL_PATTERN.fullmatch(model):
            return jsonify(error="Choose an installed Ollama vision model"), 400
        if not isinstance(prompt, str) or not 0 < len(prompt) <= MAX_PROMPT:
            return jsonify(error="Invalid caption prompt"), 400
        if not isinstance(image_id, str) or not re.fullmatch("[0-9a-f]{32}", image_id):
            return jsonify(error="Invalid image reference"), 404
        with closing(db()) as conn:
            row = conn.execute("SELECT path FROM dataset_images WHERE project_id=? AND id=?",
                               (project_id, image_id)).fetchone()
        if row is None:
            return jsonify(error="Image not indexed in this project"), 404
        path = Path(row["path"])
        allowed = {".png", ".jpg", ".jpeg", ".webp"}
        if path.is_symlink() or not path.is_file() or path.suffix.lower() not in allowed:
            return jsonify(error="Image unavailable or unsupported for vision"), 400
        try:
            with path.open("rb") as file:
                binary = file.read(MAX_IMAGE_BYTES + 1)
            if not 0 < len(binary) <= MAX_IMAGE_BYTES:
                return jsonify(error="Image exceeds 12 MB vision limit"), 413
        except OSError:
            return jsonify(error="Cannot read indexed image"), 404
        if not busy.acquire(blocking=False):
            return jsonify(error="A local vision caption is already running"), 409
        try:
            payload = json.dumps({
                "model": model, "prompt": prompt,
                "images": [base64.b64encode(binary).decode("ascii")],
                "stream": False, "keep_alive": "0",
                "options": {"num_predict": 420}
            }).encode("utf-8")
            req = urllib.request.Request(
                OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"},
                method="POST"
            )
            try:
                # A fixed loopback destination: no user-controlled remote host.
                with urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirects()).open(
                        req, timeout=120) as response:
                    result = json.load(response)
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
                return jsonify(error="Local Ollama request failed; verify Ollama is running, "
                                     "the vision model is installed, and GPU memory is available",
                               detail=str(exc)[:200]), 502
            if not isinstance(result, dict) or not isinstance(result.get("response"), str):
                return jsonify(error="Invalid response from local vision model"), 502
            suggestion = result["response"].strip()
            if not suggestion:
                return jsonify(error="Vision model returned an empty caption"), 422
            if any(ord(ch) < 32 and ch not in "\n\t" for ch in suggestion):
                return jsonify(error="Vision model returned unsupported characters"), 422
            return jsonify(caption=suggestion[:MAX_CAPTION], model=model,
                           truncated=len(suggestion) > MAX_CAPTION,
                           saved=False, note="Preview only. Review and save manually.")
        except (ValueError, TypeError, json.JSONDecodeError):
            return jsonify(error="Unable to decode local vision response"), 502
        finally:
            busy.release()
