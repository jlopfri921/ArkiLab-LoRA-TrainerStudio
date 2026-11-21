"""Dataset Studio 0.4 beta.1: versioned manual captions stored only in SQLite.

No sidecar writes, model calls, image mutations or cloud requests.
"""
import sqlite3
from contextlib import closing
from datetime import datetime, timezone

from flask import jsonify, request

MAX_CAPTION_CHARS = 2000
MAX_HISTORY = 25


def register(app, db, project_exists, local, valid_origin):
    def ensure_schema(conn):
        conn.execute("""CREATE TABLE IF NOT EXISTS dataset_captions (
            image_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            caption TEXT NOT NULL DEFAULT '',
            revision INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS dataset_caption_history (
            image_id TEXT NOT NULL, project_id TEXT NOT NULL,
            revision INTEGER NOT NULL, caption TEXT NOT NULL,
            changed_at TEXT NOT NULL,
            PRIMARY KEY(image_id, revision)
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_caption_history_project "
                     "ON dataset_caption_history(project_id, image_id, revision)")

    def fetch_image(conn, project_id, image_id):
        if (len(image_id) != 32 or
                any(c not in "0123456789abcdef" for c in image_id)):
            return False
        return conn.execute("SELECT 1 FROM dataset_images WHERE project_id=? AND id=?",
                            (project_id, image_id)).fetchone() is not None

    @app.route("/api/workspace/datasets/<project_id>/<image_id>/caption",
               methods=["GET", "PUT"])
    def image_caption(project_id, image_id):
        if not local():
            return jsonify(error="Manage captions on the launcher PC"), 403
        if not project_exists(project_id):
            return jsonify(error="Active project not found"), 404
        if request.method == "PUT" and not valid_origin():
            return jsonify(error="Cross-origin changes are not allowed"), 403
        if request.method == "PUT":
            if (request.mimetype != "application/json" or not
                    0 < (request.content_length or 0) <= 10000):
                return jsonify(error="Invalid caption request"), 400
            body = request.get_json(silent=True)
            if not isinstance(body, dict):
                return jsonify(error="Invalid caption body"), 400
            caption = body.get("caption")
            expected = body.get("expected_revision")
            if not isinstance(caption, str) or len(caption) > MAX_CAPTION_CHARS:
                return jsonify(error="Caption must be at most 2000 characters"), 400
            if any(ord(c) < 32 and c not in "\n\t" for c in caption):
                return jsonify(error="Caption contains control characters"), 400
            if isinstance(expected, bool) or not isinstance(expected, int) or expected < 0:
                return jsonify(error="Expected revision is required"), 400
        with closing(db()) as conn:
            ensure_schema(conn)
            if not fetch_image(conn, project_id, image_id):
                return jsonify(error="Image not indexed in this project"), 404
            row = conn.execute(
                "SELECT caption,revision,updated_at FROM dataset_captions "
                "WHERE project_id=? AND image_id=?", (project_id, image_id)
            ).fetchone()
            current = dict(row) if row else {"caption": "", "revision": 0, "updated_at": None}
            if request.method == "GET":
                return jsonify(**current)
            if expected != current["revision"]:
                return jsonify(error="Caption changed in another tab", current=current), 409
            if caption == current["caption"]:
                return jsonify(**current)
            now = datetime.now(timezone.utc).isoformat()
            revision = expected + 1
            try:
                with conn:
                    conn.execute(
                        "INSERT INTO dataset_captions(image_id,project_id,caption,revision,updated_at)"
                        " VALUES (?,?,?,?,?) ON CONFLICT(image_id) DO UPDATE SET "
                        "caption=excluded.caption,revision=excluded.revision,updated_at=excluded.updated_at",
                        (image_id, project_id, caption, revision, now))
                    conn.execute(
                        "INSERT INTO dataset_caption_history(image_id,project_id,revision,caption,changed_at) "
                        "VALUES (?,?,?,?,?)",
                        (image_id, project_id, revision, caption, now))
                    conn.execute(
                        "DELETE FROM dataset_caption_history WHERE image_id=? AND project_id=? "
                        "AND revision NOT IN (SELECT revision FROM dataset_caption_history "
                        "WHERE image_id=? AND project_id=? ORDER BY revision DESC LIMIT ?)",
                        (image_id, project_id, image_id, project_id, MAX_HISTORY))
            except sqlite3.Error:
                return jsonify(error="Could not save caption"), 500
            return jsonify(caption=caption, revision=revision, updated_at=now)

    @app.get("/api/workspace/datasets/<project_id>/<image_id>/caption/history")
    def caption_history(project_id, image_id):
        if not local():
            return jsonify(error="View captions on the launcher PC"), 403
        if not project_exists(project_id):
            return jsonify(error="Active project not found"), 404
        with closing(db()) as conn:
            ensure_schema(conn)
            if not fetch_image(conn, project_id, image_id):
                return jsonify(error="Image not indexed in this project"), 404
            rows = [dict(row) for row in conn.execute(
                "SELECT revision,caption,changed_at FROM dataset_caption_history "
                "WHERE project_id=? AND image_id=? ORDER BY revision DESC LIMIT ?",
                (project_id, image_id, MAX_HISTORY)
            )]
        return jsonify(history=rows)
