"""Non-destructive, bounded project dataset export (image + caption pairs).

A generic image/text dataset ZIP is not a guarantee of engine compatibility.
"""
import io
import json
import re
import tempfile
import zipfile
from contextlib import closing
from pathlib import Path

from flask import jsonify, request, send_file

MAX_IMAGES = 200
MAX_TOTAL_BYTES = 256 * 1024 * 1024
MAX_SINGLE_BYTES = 40 * 1024 * 1024
ALLOWED = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
HEX = set("0123456789abcdef")


def register(app, db, project_exists, local, valid_origin):
    @app.post("/api/workspace/datasets/<project_id>/training-export")
    def training_export(project_id):
        if not local() or not valid_origin():
            return jsonify(error="Local same-origin access required"), 403
        if not project_exists(project_id):
            return jsonify(error="Active project not found"), 404
        if request.mimetype != "application/json" or not 0 < (request.content_length or 0) <= 16000:
            return jsonify(error="Invalid request"), 400
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify(error="Invalid request body"), 400
        ids = body.get("image_ids")
        mode = body.get("mode")
        if (mode not in ("preview", "download") or not isinstance(ids, list)
                or not 0 < len(ids) <= MAX_IMAGES or len(set(map(str, ids))) != len(ids)
                or any(not isinstance(i, str) or len(i) != 32 or not set(i) <= HEX for i in ids)):
            return jsonify(error="Select 1-200 distinct indexed images"), 400
        if mode == "download" and body.get("confirm") is not True:
            return jsonify(error="Confirm export before downloading"), 400
        with closing(db()) as conn:
            values = ",".join("?" for _ in ids)
            # Captions table might not exist until the first caption request.
            conn.execute("""CREATE TABLE IF NOT EXISTS dataset_captions (
                image_id TEXT PRIMARY KEY, project_id TEXT NOT NULL,
                caption TEXT NOT NULL DEFAULT '', revision INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT)""")
            rows = conn.execute(
                "SELECT i.id, i.name, i.path, i.review, i.bytes, "
                "COALESCE(c.caption, '') AS caption "
                "FROM dataset_images i LEFT JOIN dataset_captions c "
                "ON c.image_id=i.id AND c.project_id=i.project_id "
                "WHERE i.project_id=? AND i.id IN (" + values + ")",
                (project_id, *ids)).fetchall()
        found = {r["id"]: dict(r) for r in rows}
        if len(found) != len(ids):
            return jsonify(error="Some images are no longer indexed in this project"), 409
        included, issues, total = [], [], 0
        used = set()
        for image_id in ids:
            r = found[image_id]
            path = Path(r["path"])
            reason = None
            if r["review"] == "rejected":
                reason = "rejected"
            elif not r["caption"].strip():
                reason = "missing_caption"
            elif path.suffix.lower() not in ALLOWED:
                reason = "unsupported_format"
            elif path.is_symlink() or not path.is_file():
                reason = "missing_or_symlink"
            else:
                try:
                    stat = path.stat()
                    if not 0 < stat.st_size <= MAX_SINGLE_BYTES or stat.st_size != r["bytes"]:
                        reason = "changed_or_oversized"
                except OSError:
                    reason = "unavailable"
            if reason:
                issues.append({"id": image_id, "name": r["name"], "reason": reason})
                continue
            stem = re.sub(r"[^\w. -]", "_", path.stem, flags=re.UNICODE).strip(" ._")[:75] or "image"
            name = stem + path.suffix.lower()
            if name.casefold() in used or (stem + ".txt").casefold() in used:
                stem += "__" + image_id[:12]
                name = stem + path.suffix.lower()
            used.update((name.casefold(), (stem + ".txt").casefold()))
            total += r["bytes"]
            if total > MAX_TOTAL_BYTES:
                return jsonify(error="Selected dataset exceeds 256 MiB; export in smaller batches"), 413
            included.append({"id": image_id, "name": name, "text": stem + ".txt",
                             "source": path, "bytes": r["bytes"], "caption": r["caption"]})
        summary = {"selected": len(ids), "ready": len(included), "skipped": issues,
                   "total_bytes": total, "format": "flat_image_txt",
                   "trainer_ready": False,
                   "note": "Generic paired export. Check your trainer's dataset requirements."}
        if mode == "preview":
            return jsonify(summary)
        if not included:
            return jsonify(error="No complete image/caption pairs to export"), 409
        # Use a spooled file, not a large in-memory BytesIO. No writes to sources.
        output = tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b")
        try:
            manifest = {"version": 1, "project_id": project_id, "format": "flat_image_txt",
                        "items": [{"id": x["id"], "image": x["name"], "caption": x["text"]}
                                  for x in included], "skipped": issues}
            with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED,
                                 compresslevel=3) as archive:
                for item in included:
                    # Recheck before reading; changes invalidate the export.
                    source = item["source"]
                    if source.is_symlink() or not source.is_file() or source.stat().st_size != item["bytes"]:
                        return jsonify(error="Source image changed during export; retry preview"), 409
                    archive.write(source, "dataset/" + item["name"])
                    archive.writestr("dataset/" + item["text"], item["caption"].encode("utf-8"))
                archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            output.seek(0)
            response = send_file(output, mimetype="application/zip", as_attachment=True,
                                 download_name="orkilab-training-dataset-" + project_id[:8] + ".zip")
            response.call_on_close(output.close)
            return response
        except (OSError, ValueError, zipfile.BadZipFile):
            output.close()
            return jsonify(error="Dataset export failed; originals unchanged"), 500
