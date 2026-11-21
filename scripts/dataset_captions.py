"""Dataset Studio 0.4 beta.1: versioned manual captions stored only in SQLite.

No sidecar writes, model calls, image mutations or cloud requests.
"""
import io
import json
import re
import sqlite3
import zipfile
from contextlib import closing
from datetime import datetime, timezone

from flask import jsonify, request, send_file

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


    @app.post("/api/workspace/datasets/<project_id>/captions/export")
    def export_caption_sidecars(project_id):
        """Preview / download standalone UTF-8 .txt sidecars, never write to sources.

        The generated archive contains captions/ and a JSON manifest. It does
        not include or modify original images, .txt sidecars or project data.
        """
        if not local() or not valid_origin():
            return jsonify(error="Caption exports require a local same-origin request"), 403
        if not project_exists(project_id):
            return jsonify(error="Active project not found"), 404
        if request.mimetype != "application/json" or not 0 < (request.content_length or 0) <= 16000:
            return jsonify(error="Invalid caption export request"), 400
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify(error="Invalid caption export body"), 400
        mode, image_ids = body.get("mode"), body.get("image_ids")
        if (mode not in ("preview", "download") or not isinstance(image_ids, list)
                or not 0 < len(image_ids) <= 200):
            return jsonify(error="Select 1–200 indexed images"), 400
        if any(not isinstance(value, str) or len(value) != 32
               or any(c not in "0123456789abcdef" for c in value) for value in image_ids):
            return jsonify(error="Invalid image identifier"), 400
        if mode == "download" and body.get("confirm") is not True:
            return jsonify(error="Confirm the non-destructive export first"), 400
        image_ids = list(dict.fromkeys(image_ids))
        with closing(db()) as conn:
            ensure_schema(conn)
            values = ",".join("?" for _ in image_ids)
            found = conn.execute(
                "SELECT images.id, images.name, captions.caption, captions.revision "
                "FROM dataset_images AS images "
                "LEFT JOIN dataset_captions AS captions "
                "ON captions.image_id=images.id AND captions.project_id=images.project_id "
                "WHERE images.project_id=? AND images.id IN (" + values + ")",
                (project_id, *image_ids)
            ).fetchall()
        rows = {row["id"]: row for row in found}
        if len(rows) != len(image_ids):
            return jsonify(error="Selection contains missing project image references"), 409
        items = []
        for image_id in image_ids:
            row = rows[image_id]
            caption = row["caption"] or ""
            if not caption.strip():
                continue
            # Match the image basename for compatible trainer sidecars when
            # unique. Only append stable image IDs to resolve collisions.
            stem = row["name"].rsplit(".", 1)[0][:80]
            stem = re.sub(r"[^\w. -]", "_", stem, flags=re.UNICODE)
            stem = stem.strip(" ._") or "image"
            items.append({"image_id": image_id, "image_name": row["name"],
                          "stem": stem, "revision": row["revision"],
                          "caption": caption})
        from collections import Counter
        counts = Counter(item["stem"].casefold() for item in items)
        claimed = set()
        for item in items:
            stem = item.pop("stem")
            if counts[stem.casefold()] != 1:
                stem += "__" + item["image_id"]
            target = "captions/" + stem + ".txt"
            if target.casefold() in claimed:
                # Defend against an input basename already containing an ID
                # suffix, even when collisions span different file extensions.
                target = "captions/" + stem + "__" + item["image_id"] + ".txt"
            claimed.add(target.casefold())
            item["file"] = target
        result = {"selected": len(image_ids), "exportable": len(items),
                  "skipped_empty": len(image_ids) - len(items),
                  "files": [{"image_id": item["image_id"], "name": item["image_name"],
                             "sidecar": item["file"], "revision": item["revision"]}
                            for item in items]}
        if mode == "preview":
            return jsonify(result)
        if not items:
            return jsonify(error="No saved non-empty captions to export"), 400
        output = io.BytesIO()
        with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            for item in items:
                archive.writestr(item["file"], item["caption"].encode("utf-8"))
            archive.writestr("captions-manifest.json", json.dumps(
                {"format": "orkilab-caption-sidecars-v1", "project_id": project_id,
                 **result}, ensure_ascii=False, indent=2).encode("utf-8"))
        output.seek(0)
        response = send_file(output, mimetype="application/zip", as_attachment=True,
                             download_name="orkilab-captions-" + project_id[:8] + ".zip")
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

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
