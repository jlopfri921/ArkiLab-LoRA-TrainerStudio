"""Opt-in image captions via a user-installed local Ollama vision model.

This module never downloads models, starts Ollama, writes images, or saves a caption.
Only the explicit POST request performs generation. The API is loopback-only.
"""
import base64
import http.client
import socket
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
OLLAMA_BASE = "http://127.0.0.1:11434"
MAX_MODEL_ITEMS = 40
MAX_OLLAMA_JSON = 1024 * 1024
MODEL_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_./:-]{0,99}$")
def cloud_model_name(name):
    # Ollama can route an apparently local endpoint to cloud-backed models.
    # Keep this adapter explicitly offline-only.
    lower = name.lower()
    return lower.endswith(":cloud") or lower.endswith("-cloud") or lower.endswith("/cloud")

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


def ollama_json(path, payload=None, timeout=4):
    """Bounded local Ollama metadata lookup; never follow redirects or proxies."""
    encoded = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        OLLAMA_BASE + path, data=encoded, method="POST" if encoded is not None else "GET",
        headers={"Content-Type": "application/json"} if encoded is not None else {},
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirects())
    with opener.open(req, timeout=timeout) as response:
        data = response.read(MAX_OLLAMA_JSON + 1)
    if len(data) > MAX_OLLAMA_JSON:
        raise ValueError("Local Ollama response too large")
    return json.loads(data)


def stream_caption(payload, job):
    """Read a cancellable Ollama stream; closing the socket requests inference stop."""
    connection = http.client.HTTPConnection("127.0.0.1", 11434, timeout=120)
    job["connection"] = connection
    chunks = []
    size = 0
    try:
        if job["cancelled"].is_set():
            raise InterruptedError("Cancelled")
        connection.connect()
        if job["cancelled"].is_set():
            raise InterruptedError("Cancelled")
        connection.request("POST", "/api/generate",
                           body=json.dumps(payload).encode("utf-8"),
                           headers={"Content-Type": "application/json"})
        response = connection.getresponse()
        if response.status != 200:
            raise ValueError("Ollama rejected the streaming generation")
        for _ in range(2000):
            if job["cancelled"].is_set():
                raise InterruptedError("Cancelled")
            line = response.readline(65537)
            if not line:
                break
            if len(line) > 65536:
                raise ValueError("Ollama streaming message too large")
            item = json.loads(line)
            if not isinstance(item, dict):
                raise ValueError("Invalid Ollama streaming response")
            if item.get("error"):
                raise ValueError("Ollama streaming generation failed")
            chunk = item.get("response", "")
            if not isinstance(chunk, str):
                raise ValueError("Invalid Ollama text chunk")
            size += len(chunk)
            if size <= MAX_CAPTION + 1:
                chunks.append(chunk)
            if item.get("done"):
                if job["cancelled"].is_set():
                    raise InterruptedError("Cancelled")
                return {"response": "".join(chunks), "truncated": size > MAX_CAPTION}
        raise ValueError("Ollama streaming response ended before completion")
    finally:
        connection.close()


def register(app, db, project_exists, local, valid_origin):
    busy = threading.Lock()
    state_lock = threading.Lock()
    active = {"job": None}

    @app.get("/api/workspace/ollama/vision-models")
    def local_vision_models():
        if not local() or not valid_origin():
            return jsonify(error="Local same-origin access required"), 403
        try:
            tags = ollama_json("/api/tags")
            models = tags.get("models", []) if isinstance(tags, dict) else []
            if not isinstance(models, list):
                raise ValueError("Invalid Ollama model list")
            matches = []
            for item in models[:MAX_MODEL_ITEMS]:
                if not isinstance(item, dict) or item.get("remote_host") or item.get("remote_model"):
                    continue
                name = item.get("name") or item.get("model")
                if not isinstance(name, str) or not MODEL_PATTERN.fullmatch(name) or cloud_model_name(name):
                    continue
                try:
                    info = ollama_json("/api/show", {"model": name}, timeout=3)
                    capabilities = info.get("capabilities", []) if isinstance(info, dict) else []
                    if isinstance(capabilities, list) and "vision" in capabilities:
                        matches.append({"name": name, "size": item.get("size", 0)})
                except (urllib.error.URLError, urllib.error.HTTPError, OSError,
                        TimeoutError, ValueError, TypeError, json.JSONDecodeError):
                    # Unknown capability is not proof a model supports vision.
                    continue
            return jsonify(models=matches, examined=min(len(models), MAX_MODEL_ITEMS),
                           truncated=len(models) > MAX_MODEL_ITEMS)
        except (urllib.error.URLError, urllib.error.HTTPError, OSError,
                TimeoutError, ValueError, TypeError, json.JSONDecodeError):
            return jsonify(error="Local Ollama is unavailable or cannot list models"), 503

    @app.post("/api/workspace/datasets/<project_id>/<image_id>/caption/suggest/cancel")
    def cancel_caption(project_id, image_id):
        if not local() or not valid_origin():
            return jsonify(error="Local same-origin access required"), 403
        if not project_exists(project_id):
            return jsonify(error="Active project not found"), 404
        if request.mimetype != "application/json" or not 0 < (request.content_length or 0) <= 256:
            return jsonify(error="Invalid cancellation request"), 400
        data = request.get_json(silent=True)
        request_id = data.get("request_id") if isinstance(data, dict) else None
        if not isinstance(request_id, str) or not re.fullmatch("[0-9a-f]{32}", request_id):
            return jsonify(error="Invalid cancellation token"), 400
        with state_lock:
            job = active["job"]
            if (not job or job["id"] != request_id or job["project"] != project_id
                    or job["image"] != image_id):
                return jsonify(error="No matching active caption generation"), 404
            job["cancelled"].set()
            connection = job.get("connection")
        if connection:
            try:
                if connection.sock:
                    connection.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            connection.close()
        return jsonify(cancel_requested=True)

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
        request_id = data.get("request_id")
        if request_id is not None and (not isinstance(request_id, str)
                                     or not re.fullmatch("[0-9a-f]{32}", request_id)):
            return jsonify(error="Invalid generation token"), 400
        if not isinstance(model, str) or not MODEL_PATTERN.fullmatch(model) or cloud_model_name(model):
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
            return jsonify(error="Ollama is still processing another image. Wait for that request to finish or cancel it before retrying."), 409
        job = None
        if request_id is not None:
            job = {"id": request_id, "project": project_id, "image": image_id,
                   "cancelled": threading.Event(), "connection": None}
            with state_lock:
                active["job"] = job
        try:
            payload = json.dumps({
                "model": model, "prompt": prompt,
                "images": [base64.b64encode(binary).decode("ascii")],
                # Reasoning-capable vision models (e.g. gemma4:26b) may
                # otherwise spend their token budget on hidden thinking and
                # return an empty user-visible caption. This is a caption task.
                "think": False,
                "stream": request_id is not None, "keep_alive": "0",
                "options": {"num_predict": 640}
            }).encode("utf-8")
            req = urllib.request.Request(
                OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"},
                method="POST"
            )
            try:
                if job is not None:
                    result = stream_caption(json.loads(payload), job)
                else:
                    # Preserve the original single-request API for older clients.
                    with urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirects()).open(
                            req, timeout=120) as response:
                        result = json.load(response)
            except (InterruptedError, urllib.error.HTTPError, urllib.error.URLError,
                    TimeoutError, OSError, http.client.HTTPException, ValueError) as exc:
                if job is not None and job["cancelled"].is_set():
                    return jsonify(error="Local caption generation cancelled"), 409
                return jsonify(error="Local Ollama request failed; check Ollama, the vision model and GPU availability",
                               detail=str(exc)[:200]), 502
            if job is not None and job["cancelled"].is_set():
                return jsonify(error="Local caption generation cancelled"), 409
            if not isinstance(result, dict) or not isinstance(result.get("response"), str):
                return jsonify(error="Invalid response from local vision model"), 502
            suggestion = result["response"].strip()
            if not suggestion:
                return jsonify(error="The vision model returned no description. Check that it supports image understanding, then retry."), 422
            if any(ord(ch) < 32 and ch not in "\n\t" for ch in suggestion):
                return jsonify(error="Vision model returned unsupported characters"), 422
            return jsonify(caption=suggestion[:MAX_CAPTION], model=model,
                           truncated=result.get("truncated", False) or len(suggestion) > MAX_CAPTION,
                           saved=False, note="Preview only. Review and save manually.")
        except (ValueError, TypeError, json.JSONDecodeError):
            return jsonify(error="Unable to decode local vision response"), 502
        finally:
            if job is not None:
                with state_lock:
                    if active["job"] is job:
                        active["job"] = None
            busy.release()
