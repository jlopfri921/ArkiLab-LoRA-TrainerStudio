"""Dataset Studio alpha.1: non-destructive project-linked image index."""
import os
import sqlite3
import uuid
from contextlib import closing
from pathlib import Path

from flask import jsonify, request, send_file

EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
MIMES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
         ".webp": "image/webp", ".gif": "image/gif", ".bmp": "image/bmp"}
MAX_IMAGES = 2000
MAX_FILE_BYTES = 40 * 1024 * 1024


def register(app, base):
    base = Path(base)
    dbpath = base / "settings" / "orkilab" / "datasets.sqlite3"
    projects_path = base / "settings" / "orkilab" / "projects.sqlite3"

    def local():
        return request.remote_addr in ("127.0.0.1", "::1")

    def db():
        dbpath.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(dbpath, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("""CREATE TABLE IF NOT EXISTS dataset_images (
          id TEXT PRIMARY KEY, project_id TEXT NOT NULL, path TEXT NOT NULL,
          name TEXT NOT NULL, bytes INTEGER NOT NULL, review TEXT NOT NULL DEFAULT 'unreviewed',
          UNIQUE(project_id, path))""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_dataset_project ON dataset_images(project_id)")
        return conn

    def project_exists(project_id):
        if not isinstance(project_id, str) or len(project_id) != 32:
            return False
        if not projects_path.exists():
            return False
        with closing(sqlite3.connect(projects_path)) as conn:
            row = conn.execute("SELECT 1 FROM projects WHERE id=? AND archived=0",
                               (project_id,)).fetchone()
            return row is not None

    @app.route("/api/workspace/datasets/<project_id>", methods=["GET", "POST"])
    def datasets(project_id):
        if not local():
            return jsonify(error="Manage datasets on the launcher PC"), 403
        if not project_exists(project_id):
            return jsonify(error="Active project not found"), 404
        if request.method == "GET":
            query = request.args.get("search", "").strip().lower()
            if len(query) > 120:
                return jsonify(error="Search too long"), 400
            with closing(db()) as conn:
                rows = [dict(r) for r in conn.execute(
                    "SELECT id,name,bytes,review,path FROM dataset_images WHERE project_id=? ORDER BY name,id LIMIT ?",
                    (project_id, MAX_IMAGES))]
            return jsonify(images=[
                {"id": r["id"], "name": r["name"], "bytes": r["bytes"],
                 "review": r["review"], "missing": not Path(r["path"]).is_file()}
                for r in rows if query in r["name"].lower()])
        if request.mimetype != "application/json" or not 0 < (request.content_length or 0) <= 4096:
            return jsonify(error="Invalid request"), 400
        body = request.get_json(silent=True)
        folder = body.get("folder") if isinstance(body, dict) else None
        if not isinstance(folder, str) or not folder.strip() or len(folder) > 1024:
            return jsonify(error="Choose an absolute image folder"), 400
        root = Path(folder.strip()).expanduser()
        if not root.is_absolute() or not root.is_dir() or root.is_symlink():
            return jsonify(error="Choose an existing absolute folder"), 400
        try:
            files = []
            with os.scandir(root) as entries:
                for entry in entries:
                    if len(files) >= MAX_IMAGES:
                        break
                    if not entry.is_file(follow_symlinks=False):
                        continue
                    p = Path(entry.path)
                    if p.suffix.lower() not in EXTENSIONS:
                        continue
                    stat = entry.stat(follow_symlinks=False)
                    if not 0 < stat.st_size <= MAX_FILE_BYTES:
                        continue
                    files.append((uuid.uuid4().hex, project_id, str(p.resolve()),
                                  p.name, stat.st_size))
            with closing(db()) as conn, conn:
                before = conn.total_changes
                conn.executemany("INSERT OR IGNORE INTO dataset_images(id,project_id,path,name,bytes) VALUES (?,?,?,?,?)",
                                 files)
                added = conn.total_changes - before
            return jsonify(imported=added, scanned=len(files), note="Indexed by reference; originals unchanged")
        except (OSError, sqlite3.Error, ValueError):
            return jsonify(error="Could not index the selected folder"), 400

    @app.route("/api/workspace/datasets/<project_id>/<image_id>", methods=["GET", "DELETE"])
    def dataset_image(project_id, image_id):
        if not local():
            return jsonify(error="Manage datasets on the launcher PC"), 403
        if not project_exists(project_id):
            return jsonify(error="Active project not found"), 404
        if len(image_id) != 32:
            return jsonify(error="Image not found"), 404
        with closing(db()) as conn:
            row = conn.execute(
                "SELECT path,name FROM dataset_images WHERE project_id=? AND id=?",
                (project_id, image_id)).fetchone()
            if row is None:
                return jsonify(error="Image not found"), 404
            if request.method == "DELETE":
                with conn:
                    conn.execute("DELETE FROM dataset_images WHERE project_id=? AND id=?",
                                 (project_id, image_id))
                return jsonify(ok=True, note="Reference removed; original file unchanged")
        path = Path(row["path"])
        try:
            # Only serve a file still at the indexed location, never a directory or a symlink.
            if path.is_symlink() or not path.is_file() or path.suffix.lower() not in EXTENSIONS:
                return jsonify(error="Image missing or unavailable"), 404
            stat = path.stat()
            if not 0 < stat.st_size <= MAX_FILE_BYTES:
                return jsonify(error="Image size is unsupported"), 413
            response = send_file(path, mimetype=MIMES[path.suffix.lower()], conditional=True,
                                 as_attachment=False, download_name=row["name"])
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Content-Security-Policy"] = "default-src 'none'; sandbox"
            return response
        except OSError:
            return jsonify(error="Image missing or unavailable"), 404
