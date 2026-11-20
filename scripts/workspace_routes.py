"""Workspace routes, alongside the existing launcher."""
from flask import jsonify, request, send_from_directory
import shutil
from pathlib import Path

from workspace_store import ProjectStore
import comfyui_connect


def register(app, base, load_config):
    base = Path(base)
    comfyui_connect.register(app, base)
    store = ProjectStore(base / "settings" / "orkilab" / "projects.sqlite3")

    @app.get("/workspace")
    def workspace_page():
        return send_from_directory(str(base / "GUI"), "workspace.html")

    @app.get("/api/workspace/overview")
    def workspace_overview():
        try:
            import psutil
            ram = psutil.virtual_memory()
            memory = {"total": ram.total, "available": ram.available}
        except (ImportError, OSError):
            memory = None
        disk = shutil.disk_usage(base)
        return jsonify({"engines": load_config()["trainers"],
                        "memory": memory, "disk": {"total": disk.total, "free": disk.free},
                        "version": load_config().get("arkilab_version", "development")})

    @app.route("/api/workspace/projects", methods=["GET", "POST"])
    def workspace_projects():
        if request.method == "GET":
            return jsonify({"projects": store.list(request.args.get("archived") == "1")})
        if request.mimetype != "application/json":
            return jsonify({"error": "JSON required"}), 415
        if request.content_length is None or request.content_length > 16384:
            return jsonify({"error": "Invalid request size"}), 413
        try:
            engines = {x["id"] for x in load_config()["trainers"]}
            return jsonify(store.create(request.get_json(silent=True), engines)), 201
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    @app.post("/api/workspace/projects/<project_id>/archive")
    def workspace_archive(project_id):
        if request.mimetype != "application/json":
            return jsonify({"error": "JSON required"}), 415
        if request.content_length is None or request.content_length > 1024:
            return jsonify({"error": "Invalid request size"}), 413
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or not isinstance(body.get("archived"), bool):
            return jsonify({"error": "Expected archived boolean"}), 400
        if not store.archive(project_id, body["archived"]):
            return jsonify({"error": "Project not found"}), 404
        return jsonify({"ok": True})
