"""Explicit submission of saved ComfyUI API graphs; no automatic execution."""
import json
import hashlib
import time
import re
import sqlite3
import threading
import uuid
from contextlib import closing
from urllib.request import Request, build_opener, ProxyHandler
from urllib.error import HTTPError
from pathlib import Path
from flask import jsonify, request
import project_layout
from comfyui_connect import validate_settings, DEFAULT_SETTINGS, get_json, NoRedirect
from workflow_library import inspect_graph
from workflow_conversion import convert_visual, node_schema, validate_prompt

def register(app, base):
    base = Path(base)
    jobs = {}
    prepared = {}
    lock = threading.Lock()

    def config():
        try:
            return validate_settings(json.loads((base / "settings" / "orkilab" / "comfyui.json").read_text(encoding="utf-8")), DEFAULT_SETTINGS)
        except (OSError, ValueError, TypeError):
            return dict(DEFAULT_SETTINGS)

    def local():
        return request.remote_addr in ("127.0.0.1", "::1")

    def submit(url, graph):
        payload = json.dumps({"prompt": graph, "client_id": str(uuid.uuid4())}, allow_nan=False).encode()
        req = Request(url + "/prompt", data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with build_opener(ProxyHandler({}), NoRedirect()).open(req, timeout=30) as response:
            result = json.loads(response.read(1_000_001))
        ident = result.get("prompt_id") if isinstance(result, dict) else None
        if not isinstance(ident, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", ident):
            raise ValueError("ComfyUI did not return a valid job ID")
        return ident

    def read_graph(ident):
        path = base / "settings" / "orkilab" / "workflows.sqlite3"
        if not path.is_file():
            return None
        with closing(sqlite3.connect(path)) as con:
            row = con.execute("SELECT graph FROM workflows WHERE id=?", (ident,)).fetchone()
        return row[0] if row else None

    @app.post("/api/workspace/generation/prepare")
    def generation_prepare():
        if not local():
            return jsonify(error="Manage workflows on the launcher PC"), 403
        if request.mimetype != "application/json" or not 0 < (request.content_length or 0) <= 2048:
            return jsonify(error="Invalid request"), 400
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or not isinstance(body.get("workflow_id"), str):
            return jsonify(error="Invalid request"), 400
        cfg = config()
        if cfg["mode"] == "native":
            return jsonify(error="ComfyUI is disabled in native mode"), 409
        ident = body["workflow_id"]
        raw = read_graph(ident)
        if raw is None:
            return jsonify(error="Workflow not found"), 404
        try:
            graph = json.loads(raw)
            fmt = inspect_graph(graph)["format"]
            if fmt == "ui":
                graph = convert_visual(graph, cfg["url"], get_json)
            else:
                schemas = {kind: node_schema(cfg["url"], kind, get_json)
                           for kind in {n["class_type"] for n in graph.values()}}
                validate_prompt(graph, schemas)
            token = uuid.uuid4().hex
            with lock:
                for key in list(prepared):
                    if time.monotonic() - prepared[key][0] > 1800:
                        prepared.pop(key)
                while len(prepared) >= 20:
                    prepared.pop(next(iter(prepared)))
                prepared[token] = (time.monotonic(), ident, cfg["url"], hashlib.sha256(raw.encode()).hexdigest(), graph)
            return jsonify(token=token, node_count=len(graph), converted=fmt=="ui", graph=graph)
        except (OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
            return jsonify(error="Workflow preparation failed", detail=str(exc)[:500]), 400

    @app.post("/api/workspace/generation")
    def generation_submit():
        if not local():
            return jsonify(error="Manage workflows on the launcher PC"), 403
        if request.mimetype != "application/json" or not 0 < (request.content_length or 0) <= 2048:
            return jsonify(error="Invalid request"), 400
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or body.get("confirm") is not True or not isinstance(body.get("workflow_id"), str):
            return jsonify(error="Explicit generation confirmation required"), 400
        cfg = config()
        if cfg["mode"] == "native":
            return jsonify(error="ComfyUI is disabled in native mode"), 409
        raw = read_graph(body["workflow_id"])
        if raw is None:
            return jsonify(error="Workflow not found"), 404
        token = body.get("token")
        if not isinstance(token, str):
            return jsonify(error="Prepare workflow before generating"), 409
        try:
            with lock:
                item = prepared.get(token)
                if not item or time.monotonic() - item[0] > 1800 or item[1:4] != (body["workflow_id"], cfg["url"], hashlib.sha256(raw.encode()).hexdigest()):
                    return jsonify(error="Prepare workflow before generating"), 409
                graph = item[4]
                if project_layout.training_in_progress(base):
                    return jsonify(error="Training is active. Finish training before generating."), 409
                queue = get_json(cfg["url"], "/queue")
                if not isinstance(queue, dict) or not all(isinstance(queue.get(k), list) for k in ("queue_running", "queue_pending")):
                    return jsonify(error="Could not verify ComfyUI queue"), 502
                if queue["queue_running"] or queue["queue_pending"]:
                    return jsonify(error="ComfyUI queue is busy"), 409
                prepared.pop(token, None)
                ident = submit(cfg["url"], graph)
                token = uuid.uuid4().hex
                jobs[token] = (cfg["url"], ident)
                while len(jobs) > 100:
                    jobs.pop(next(iter(jobs)))
            return jsonify(id=token, prompt_id=ident), 201
        except HTTPError as exc:
            return jsonify(error="ComfyUI rejected the request", detail=f"HTTP {exc.code}"), 502
        except (OSError, ValueError, TypeError) as exc:
            return jsonify(error="Generation submission could not be confirmed. Check ComfyUI before retrying.", detail=str(exc)[:300]), 502

    @app.get("/api/workspace/generation/<token>")
    def generation_status(token):
        if not local():
            return jsonify(error="Manage workflows on the launcher PC"), 403
        with lock:
            job = jobs.get(token)
        if not job:
            return jsonify(error="Generation job not found"), 404
        url, ident = job
        try:
            history = get_json(url, "/history/" + ident, max_bytes=16_000_000)
            entry = history.get(ident) if isinstance(history, dict) else None
            if not isinstance(entry, dict):
                queue = get_json(url, "/queue")
                if not isinstance(queue, dict):
                    raise ValueError("Invalid queue")
                for key, state in (("queue_running", "running"), ("queue_pending", "queued")):
                    if any(isinstance(item, list) and len(item) > 1 and item[1] == ident for item in queue.get(key, [])):
                        return jsonify(state=state, outputs=[])
                return jsonify(state="unknown", outputs=[])
            status = entry.get("status") or {}
            state = "error" if status.get("status_str") == "error" else "completed" if status.get("completed") else "unknown"
            outputs = []
            for node in (entry.get("outputs") or {}).values():
                if not isinstance(node, dict):
                    continue
                for kind in ("images", "gifs", "audio", "video", "videos"):
                    for item in node.get(kind, []) if isinstance(node.get(kind), list) else []:
                        if isinstance(item, dict) and isinstance(item.get("filename"), str):
                            outputs.append({"filename":item["filename"][:500], "kind":kind})
            return jsonify(state=state, outputs=outputs[:100])
        except (OSError, ValueError, TypeError) as exc:
            return jsonify(error="Could not read generation status", detail=str(exc)[:300]), 502
