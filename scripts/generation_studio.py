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
import shutil
from flask import jsonify, request, Response, stream_with_context, abort
from urllib.parse import urlencode
from generation_history import GenerationHistory, describe_outputs
import project_layout
from comfyui_connect import validate_settings, DEFAULT_SETTINGS, get_json, NoRedirect
from workflow_library import inspect_graph
from generation_parameters import editable_fields, apply_edits
from workflow_conversion import convert_visual, node_schema, validate_prompt

def register(app, base):
    base = Path(base)
    jobs = {}
    records = GenerationHistory(base)
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

    @app.post("/api/workspace/generation/bridge/install")
    def bridge_install():
        if not local():
            return jsonify(error="Manage workflows on the launcher PC"), 403
        if request.mimetype != "application/json" or not 0 < (request.content_length or 0) <= 4096:
            return jsonify(error="Invalid request"), 400
        body = request.get_json(silent=True)
        raw = body.get("folder") if isinstance(body, dict) else None
        if not isinstance(raw, str) or not raw.strip():
            return jsonify(error="Select the ComfyUI custom_nodes folder"), 400
        try:
            root = Path(raw.strip()).expanduser()
            if not root.is_absolute() or root.name.lower() != "custom_nodes" or not root.is_dir():
                raise ValueError("Select the ComfyUI custom_nodes folder")
            root = root.resolve()
            source = base / "integrations" / "orkilab_bridge"
            target = root / "orkilab_bridge"
            for rel in ("__init__.py", "js/bridge.js"):
                dst = target / rel
                if not dst.resolve().is_relative_to(root) or not (source / rel).is_file():
                    raise ValueError("Invalid bridge installation path")
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source / rel, dst)
            return jsonify(installed=True, folder=str(target))
        except (OSError, ValueError) as exc:
            return jsonify(error="Bridge installation failed", detail=str(exc)[:300]), 400

    @app.post("/api/workspace/generation/prepare")
    def generation_prepare():
        if not local():
            return jsonify(error="Manage workflows on the launcher PC"), 403
        if request.mimetype != "application/json" or not 0 < (request.content_length or 0) <= 16_000_000:
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
            bridge = body.get("bridge_prompt")
            if bridge is not None:
                if fmt != "ui" or inspect_graph(bridge)["format"] != "api":
                    raise ValueError("Invalid bridge prompt")
                graph = bridge
            elif fmt == "ui":
                graph = convert_visual(graph, cfg["url"], get_json)
            schemas = {kind: node_schema(cfg["url"], kind, get_json)
                       for kind in {n["class_type"] for n in graph.values()}}
            validate_prompt(graph, schemas)
            fields = editable_fields(graph, schemas)
            token = uuid.uuid4().hex
            with lock:
                for key in list(prepared):
                    if time.monotonic() - prepared[key][0] > 1800:
                        prepared.pop(key)
                while len(prepared) >= 20:
                    prepared.pop(next(iter(prepared)))
                prepared[token] = (time.monotonic(), ident, cfg["url"], hashlib.sha256(raw.encode()).hexdigest(), graph, fields, schemas)
            return jsonify(token=token, node_count=len(graph), converted=fmt=="ui", graph=graph, fields=fields)
        except (OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
            return jsonify(error="Workflow preparation failed", detail=str(exc)[:500]), 400

    @app.post("/api/workspace/generation/parameters")
    def generation_parameters():
        if not local():
            return jsonify(error="Manage workflows on the launcher PC"), 403
        if request.mimetype != "application/json" or not 0 < (request.content_length or 0) <= 2_000_000:
            return jsonify(error="Invalid request"), 400
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or not isinstance(body.get("token"), str):
            return jsonify(error="Invalid request"), 400
        cfg = config()
        if cfg["mode"] == "native":
            return jsonify(error="ComfyUI is disabled in native mode"), 409
        try:
            with lock:
                item = prepared.get(body["token"])
                if not item or time.monotonic() - item[0] > 1800 or item[2] != cfg["url"]:
                    return jsonify(error="Prepare workflow before generating"), 409
                graph = apply_edits(item[4], item[5], body.get("edits"))
                validate_prompt(graph, item[6])
                fields = editable_fields(graph, item[6])
                token = uuid.uuid4().hex
                prepared.pop(body["token"])
                prepared[token] = (*item[:4], graph, fields, item[6])
            return jsonify(token=token, graph=graph, fields=fields)
        except (ValueError, TypeError, KeyError, RecursionError, OverflowError) as exc:
            return jsonify(error="Invalid parameter changes", detail=str(exc)[:300]), 400

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
                try:
                    with closing(sqlite3.connect(base / "settings" / "orkilab" / "workflows.sqlite3")) as con:
                        row = con.execute("SELECT name FROM workflows WHERE id=?", (body["workflow_id"],)).fetchone()
                    records.add(token, cfg["url"], ident, body["workflow_id"], row[0] if row else body["workflow_id"], graph)
                except (OSError, sqlite3.Error, ValueError) as exc:
                    app.logger.warning("Generation submitted but history unavailable: %s", exc)
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
        saved = records.get(token)
        if saved and saved["state"] in ("completed","error"):
            return jsonify(state=saved["state"], outputs=json.loads(saved["outputs"]))
        if not job and saved:
            job = (saved["url"], saved["prompt_id"])
        if not job:
            return jsonify(error="Generation job not found"), 404
        url, ident = job
        url = validate_settings({"url":url}, DEFAULT_SETTINGS)["url"]
        try:
            history = get_json(url, "/history/" + ident, max_bytes=16_000_000)
            entry = history.get(ident) if isinstance(history, dict) else None
            if not isinstance(entry, dict):
                queue = get_json(url, "/queue")
                if not isinstance(queue, dict):
                    raise ValueError("Invalid queue")
                for key, state in (("queue_running", "running"), ("queue_pending", "queued")):
                    if any(isinstance(item, list) and len(item) > 1 and item[1] == ident for item in queue.get(key, [])):
                        records.update(token,state,[])
                        return jsonify(state=state, outputs=[])
                return jsonify(state="unknown", outputs=[])
            status = entry.get("status") or {}
            state = "error" if status.get("status_str") == "error" else "completed" if status.get("completed") else "unknown"
            outputs = describe_outputs(entry)
            records.update(token,state,outputs)
            return jsonify(state=state, outputs=outputs)
        except (OSError, ValueError, TypeError) as exc:
            return jsonify(error="Could not read generation status", detail=str(exc)[:300]), 502

    @app.get("/api/workspace/generation/history")
    def generation_history():
        if not local():
            return jsonify(error="Manage workflows on the launcher PC"), 403
        try:
            offset = max(0,min(100000,int(request.args.get("offset",0))))
        except ValueError:
            return jsonify(error="Invalid request"),400
        return jsonify(jobs=records.list(100,offset))

    @app.get("/api/workspace/generation/history/<token>")
    def generation_history_detail(token):
        if not local():
            return jsonify(error="Manage workflows on the launcher PC"),403
        row = records.get(token)
        if not row:
            return jsonify(error="Generation job not found"),404
        return jsonify(id=token, name=row["name"], graph=json.loads(row["graph"]), workflow_id=row["workflow_id"])

    @app.get("/api/workspace/generation/media/<token>/<int:index>")
    def generation_media(token,index):
        if not local():
            abort(403)
        row = records.get(token)
        if not row:
            abort(404)
        outputs = json.loads(row["outputs"])
        if not 0 <= index < len(outputs):
            abort(404)
        item = outputs[index]
        try:
            url = validate_settings({"url":row["url"]},DEFAULT_SETTINGS)["url"]
            query = urlencode({key:item[key] for key in ("filename","subfolder","type")})
            headers = {}
            byte_range = request.headers.get("Range","")
            if re.fullmatch(r"bytes=\d*-\d*",byte_range):
                headers["Range"] = byte_range
            upstream = build_opener(ProxyHandler({}),NoRedirect()).open(Request(url+"/view?"+query,headers=headers),timeout=15)
        except (OSError,ValueError):
            abort(404)
        def chunks():
            with upstream:
                while True:
                    chunk = upstream.read(65536)
                    if not chunk:
                        break
                    yield chunk
        response = Response(stream_with_context(chunks()),status=upstream.status,mimetype=item["mime"])
        response.call_on_close(upstream.close)
        for key in ("Content-Length","Content-Range","Accept-Ranges"):
            if upstream.headers.get(key):
                response.headers[key] = upstream.headers[key]
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = "default-src 'none'; sandbox"
        if request.args.get("download") == "1" or item["mime"] == "application/octet-stream":
            from werkzeug.http import dump_options_header
            response.headers["Content-Disposition"] = dump_options_header("attachment",{"filename":item["filename"]})
        return response
