"""Dataset Studio alpha.2: bounded, explicit and non-destructive quality scanning."""
import hashlib
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from flask import jsonify, request

MAX_SCAN_BATCH = 20
MAX_FILE_BYTES = 40 * 1024 * 1024
MIN_DIMENSION = 512


def register(app, db, project_exists, local, valid_origin):
    @app.post("/api/workspace/datasets/<project_id>/quality/scan")
    def scan_dataset_quality(project_id):
        if not local() or not valid_origin():
            return jsonify(error="Quality scans are available on the launcher PC only"), 403
        if not project_exists(project_id):
            return jsonify(error="Active project not found"), 404
        if request.mimetype != "application/json" or not 0 < (request.content_length or 0) <= 1024:
            return jsonify(error="Invalid scan request"), 400
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify(error="Invalid scan request"), 400
        cursor, limit = payload.get("cursor"), payload.get("limit", MAX_SCAN_BATCH)
        if cursor is not None and (not isinstance(cursor, str) or len(cursor) != 32
                                   or any(ch not in "0123456789abcdef" for ch in cursor)):
            return jsonify(error="Invalid cursor"), 400
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_SCAN_BATCH:
            return jsonify(error="Invalid batch size"), 400

        with closing(db()) as conn:
            # The scan uses a stable UUID cursor and a bounded batch, never a whole-folder crawl.
            rows = [dict(row) for row in conn.execute(
                "SELECT id,path,bytes,width,height FROM dataset_images "
                "WHERE project_id=? AND id>? ORDER BY id LIMIT ?",
                (project_id, cursor or "", limit + 1))]
            has_more = len(rows) > limit
            work = rows[:limit]
            updated = []
            for row in work:
                path = Path(row["path"])
                digest = None
                flag = "missing"
                try:
                    if path.is_symlink() or not path.is_file():
                        pass
                    else:
                        before = path.stat()
                        if not 0 < before.st_size <= MAX_FILE_BYTES:
                            flag = "unsupported"
                        else:
                            sha = hashlib.sha256()
                            with path.open("rb") as stream:
                                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                                    sha.update(chunk)
                            after = path.stat()
                            if before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns:
                                flag = "changed"
                            else:
                                digest = sha.hexdigest()
                                width, height = row["width"], row["height"]
                                if not width or not height:
                                    flag = "unknown_resolution"
                                elif min(width, height) < MIN_DIMENSION:
                                    flag = "low_resolution"
                                else:
                                    flag = "ok"
                except (OSError, ValueError):
                    flag = "unavailable"
                updated.append((digest, flag, datetime.now(timezone.utc).isoformat(), project_id, row["id"]))

            with conn:
                conn.executemany(
                    "UPDATE dataset_images SET quality_sha256=?,quality_flag=?,quality_scanned_at=? "
                    "WHERE project_id=? AND id=?", updated)
            # Progress is the cursor-based number processed, not a fabricated percent from GPU work.
            total = conn.execute("SELECT COUNT(*) FROM dataset_images WHERE project_id=?", (project_id,)).fetchone()[0]
            done = conn.execute("SELECT COUNT(*) FROM dataset_images WHERE project_id=? AND id<=?",
                                (project_id, work[-1]["id"] if work else cursor or "")).fetchone()[0]
        return jsonify(processed=len(work), total=total, done=done,
                       next_cursor=work[-1]["id"] if has_more and work else None,
                       finished=not has_more, low_resolution=sum(x[1] == "low_resolution" for x in updated))

