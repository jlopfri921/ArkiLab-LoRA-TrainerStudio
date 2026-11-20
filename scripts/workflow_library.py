"""Local workflow library. Import and inspect only; never execute a graph."""
import json
import sqlite3
import uuid
from pathlib import Path
from flask import request, jsonify

MAX_BYTES = 4_000_000
CATEGORIES = ("image", "video", "audio", "music", "3d", "other")
MODEL_EXT = (".safetensors", ".ckpt", ".gguf", ".pt", ".pth", ".bin", ".onnx")

def inspect_graph(graph):
    if not isinstance(graph, dict):
        raise ValueError("Invalid workflow JSON")
    if isinstance(graph.get("nodes"), list):
        fmt = "ui"
        nodes = graph["nodes"]
        key = "type"
    else:
        fmt = "api"
        nodes = list(graph.values())
        key = "class_type"
    if not nodes or len(nodes) > 2000 or any(not isinstance(n, dict) or not isinstance(n.get(key), str) or not n[key] for n in nodes):
        raise ValueError("Unsupported workflow format")
    if fmt == "api" and any(not isinstance(n.get("inputs"), dict) for n in nodes):
        raise ValueError("Unsupported workflow format")
    types, models = set(), set()
    for n in nodes:
        types.add(n[key][:300])
        inputs = n.get("inputs", {}) if fmt == "api" else n.get("widgets_values", [])
        values = inputs.values() if isinstance(inputs, dict) else inputs if isinstance(inputs, list) else []
        for value in values:
            if isinstance(value, str) and len(value) <= 1024 and value.lower().endswith(MODEL_EXT):
                models.add(value)
    return {"format": fmt, "node_count": len(nodes), "node_types": sorted(types),
            "model_references": sorted(models)}

def register(app, base):
    path = Path(base) / "settings" / "orkilab" / "workflows.sqlite3"

    def db():
        path.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(path)
        con.row_factory = sqlite3.Row
        con.execute("CREATE TABLE IF NOT EXISTS workflows (id TEXT PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL, favorite INTEGER NOT NULL DEFAULT 0, graph TEXT NOT NULL, summary TEXT NOT NULL)")
        return con

    def allowed():
        return request.remote_addr in ("127.0.0.1", "::1")

    def public(row):
        return {"id": row["id"], "name": row["name"], "category": row["category"],
                "favorite": bool(row["favorite"]), **json.loads(row["summary"])}

    @app.route("/api/workspace/workflows", methods=["GET", "POST"])
    def workflows():
        if not allowed():
            return jsonify(error="Manage workflows on the launcher PC"), 403
        if request.method == "GET":
            with db() as con:
                rows = con.execute("SELECT id,name,category,favorite,summary FROM workflows ORDER BY favorite DESC,name COLLATE NOCASE").fetchall()
                return jsonify(workflows=[public(row) for row in rows])
        if request.mimetype != "application/json" or not 0 < (request.content_length or 0) <= MAX_BYTES:
            return jsonify(error="Invalid workflow request or file too large"), 400
        try:
            body = request.get_json()
            if not isinstance(body, dict):
                raise ValueError("Invalid workflow JSON")
            name, cat, graph = body.get("name"), body.get("category"), body.get("graph")
            if not isinstance(name, str) or not name.strip() or len(name) > 120 or cat not in CATEGORIES:
                raise ValueError("Invalid workflow name or category")
            summary = inspect_graph(graph)
            ident = uuid.uuid4().hex
            with db() as con:
                if con.execute("SELECT COUNT(*) FROM workflows").fetchone()[0] >= 500:
                    return jsonify(error="Workflow library limit reached"), 409
                con.execute("INSERT INTO workflows VALUES (?,?,?,?,?,?)",
                            (ident, name.strip(), cat, 0, json.dumps(graph, ensure_ascii=False), json.dumps(summary)))
            return jsonify(id=ident), 201
        except (ValueError, RecursionError, TypeError):
            return jsonify(error="Invalid or unsupported workflow JSON"), 400

    @app.route("/api/workspace/workflows/<ident>", methods=["GET", "PATCH"])
    def workflow(ident):
        if not allowed():
            return jsonify(error="Manage workflows on the launcher PC"), 403
        with db() as con:
            row = con.execute("SELECT * FROM workflows WHERE id=?", (ident,)).fetchone()
            if row is None:
                return jsonify(error="Workflow not found"), 404
            if request.method == "GET":
                return jsonify(**public(row), graph=json.loads(row["graph"]))
            if request.mimetype != "application/json" or not 0 < (request.content_length or 0) <= 1024:
                return jsonify(error="Invalid request"), 400
            body = request.get_json(silent=True)
            if not isinstance(body, dict) or not isinstance(body.get("favorite"), bool):
                return jsonify(error="Invalid request"), 400
            con.execute("UPDATE workflows SET favorite=? WHERE id=?", (int(body["favorite"]), ident))
            return jsonify(ok=True)
