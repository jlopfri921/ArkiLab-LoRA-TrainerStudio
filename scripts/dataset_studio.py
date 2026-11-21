"""Dataset Studio alpha.1: non-destructive project-linked image index."""
import os
import sqlite3
import struct
import uuid
from contextlib import closing
from pathlib import Path

from flask import jsonify, request, send_file
import dataset_quality
from image_quality_visual import near_match

EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
MIMES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
         ".webp": "image/webp", ".gif": "image/gif", ".bmp": "image/bmp"}
MAX_IMAGES = 2000
MAX_FILE_BYTES = 40 * 1024 * 1024
REVIEWS = {"unreviewed", "approved", "rejected"}


def dimensions(path):
    """Bounded image-header inspection: never decode an image or modify originals."""
    try:
        with open(path, "rb") as source:
            h = source.read(32)
            if h.startswith(b"\x89PNG\r\n\x1a\n") and h[12:16] == b"IHDR":
                w, hgt = struct.unpack(">II", h[16:24])
            elif h[:3] in (b"GIF",) and h[3:6] in (b"87a", b"89a"):
                w, hgt = struct.unpack("<HH", h[6:10])
            elif h[:2] == b"BM" and len(h) >= 26:
                w, hgt = struct.unpack("<ii", h[18:26])
                hgt = abs(hgt)
            elif h[:4] == b"RIFF" and h[8:12] == b"WEBP" and h[12:16] == b"VP8X":
                w = 1 + int.from_bytes(h[24:27], "little")
                hgt = 1 + int.from_bytes(h[27:30], "little")
            elif h[:3] == b"\xff\xd8\xff":
                source.seek(2)
                w = hgt = None
                for _ in range(120):
                    marker = source.read(1)
                    if not marker:
                        break
                    if marker != b"\xff":
                        continue
                    marker = source.read(1)
                    while marker == b"\xff":
                        marker = source.read(1)
                    if marker in (b"\xd8", b"\xd9", b"\x00"):
                        continue
                    length_bytes = source.read(2)
                    if len(length_bytes) != 2:
                        break
                    length = int.from_bytes(length_bytes, "big")
                    if length < 2:
                        break
                    if marker and marker[0] in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
                        data = source.read(5)
                        if len(data) == 5:
                            hgt, w = struct.unpack(">HH", data[1:5])
                        break
                    source.seek(length - 2, 1)
                if w is None:
                    return None, None
            else:
                return None, None
            if 0 < w <= 100000 and 0 < hgt <= 100000:
                return w, hgt
    except (OSError, ValueError, struct.error):
        pass
    return None, None


def valid_origin():
    """Reject explicit cross-origin browser mutation attempts."""
    origin = request.headers.get("Origin")
    if not origin:
        return True
    from urllib.parse import urlsplit
    try:
        parsed = urlsplit(origin)
        return (parsed.scheme in ("http", "https")
                and parsed.hostname in ("localhost", "127.0.0.1", "::1")
                and parsed.netloc.lower() == request.host.lower())
    except ValueError:
        return False


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
          width INTEGER, height INTEGER,
          UNIQUE(project_id, path))""")
        existing = {row[1] for row in conn.execute("PRAGMA table_info(dataset_images)")}
        for column in ("width", "height", "quality_sha256", "quality_flag", "quality_scanned_at",
                       "quality_dhash", "quality_blur_score", "quality_possible_blur"):
            if column not in existing:
                conn.execute(f"ALTER TABLE dataset_images ADD COLUMN {column} " + ("INTEGER" if column in ("width", "height", "quality_possible_blur")
                    else "REAL" if column == "quality_blur_score" else "TEXT"))
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

    dataset_quality.register(app, db, project_exists, local, valid_origin)

    @app.route("/api/workspace/datasets/<project_id>", methods=["GET", "POST"])
    def datasets(project_id):
        if not local():
            return jsonify(error="Manage datasets on the launcher PC"), 403
        if not project_exists(project_id):
            return jsonify(error="Active project not found"), 404
        if request.method != "GET" and not valid_origin():
            return jsonify(error="Cross-origin changes are not allowed"), 403
        if request.method == "GET":
            query = request.args.get("search", "").strip().lower()
            if len(query) > 120:
                return jsonify(error="Search too long"), 400
            review = request.args.get("review", "all")
            sort = request.args.get("sort", "name")
            quality_filter = request.args.get("quality", "all")
            if (review not in REVIEWS | {"all"} or sort not in ("name", "size", "resolution")
                    or quality_filter not in ("all", "exact", "near", "blur", "low_resolution", "unanalyzed")):
                return jsonify(error="Invalid filter"), 400
            order = {"name": "name COLLATE NOCASE, id", "size": "bytes DESC, name COLLATE NOCASE, id",
                     "resolution": "(COALESCE(width,0)*COALESCE(height,0)) DESC, name COLLATE NOCASE, id"}[sort]
            with closing(db()) as conn:
                rows = [dict(r) for r in conn.execute(
                    "SELECT id,name,bytes,review,path,width,height,quality_sha256,quality_flag,quality_scanned_at, "
                    "quality_dhash,quality_blur_score,quality_possible_blur FROM dataset_images "
                    "WHERE project_id=? ORDER BY " + order + " LIMIT ?",
                    (project_id, MAX_IMAGES))]
            counts = {}
            for r in rows:
                if r["quality_sha256"]:
                    counts[r["quality_sha256"]] = counts.get(r["quality_sha256"], 0) + 1
            near_ids = set()
            eligible = [r for r in rows if r["quality_dhash"] and r["quality_sha256"]]
            for i, a in enumerate(eligible):
                for b in eligible[i + 1:]:
                    if a["quality_sha256"] == b["quality_sha256"]:
                        continue
                    if not a["width"] or not a["height"] or not b["width"] or not b["height"]:
                        continue
                    if abs(a["width"] * b["height"] - b["width"] * a["height"]) * 100 > 3 * b["width"] * a["height"]:
                        continue
                    if near_match(a["quality_dhash"], b["quality_dhash"]):
                        near_ids.update((a["id"], b["id"]))
            def matches_quality(r):
                if quality_filter == "all":
                    return True
                if quality_filter == "exact":
                    return bool(r["quality_sha256"] and counts[r["quality_sha256"]] > 1)
                if quality_filter == "near":
                    return r["id"] in near_ids
                if quality_filter == "blur":
                    return bool(r["quality_possible_blur"])
                if quality_filter == "low_resolution":
                    return r["quality_flag"] == "low_resolution"
                return not r["quality_scanned_at"]
            return jsonify(images=[
                {"id": r["id"], "name": r["name"], "bytes": r["bytes"],
                 "review": r["review"], "width": r["width"], "height": r["height"],
                 "missing": not Path(r["path"]).is_file(),
                 "quality": r["quality_flag"], "analyzed": bool(r["quality_scanned_at"]),
                 "duplicate": bool(r["quality_sha256"] and counts[r["quality_sha256"]] > 1),
                 "near_duplicate": r["id"] in near_ids,
                 "possible_blur": bool(r["quality_possible_blur"]),
                 "blur_score": r["quality_blur_score"]}
                for r in rows if query in r["name"].lower() and (review == "all" or r["review"] == review)
                and matches_quality(r)])
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
                    width, height = dimensions(p)
                    files.append((uuid.uuid4().hex, project_id, str(p.resolve()),
                                  p.name, stat.st_size, width, height))
            with closing(db()) as conn, conn:
                before = conn.total_changes
                conn.executemany("INSERT OR IGNORE INTO dataset_images(id,project_id,path,name,bytes,width,height) VALUES (?,?,?,?,?,?,?)",
                                 files)
                added = conn.total_changes - before
            return jsonify(imported=added, scanned=len(files), note="Indexed by reference; originals unchanged")
        except (OSError, sqlite3.Error, ValueError):
            return jsonify(error="Could not index the selected folder"), 400

    @app.post("/api/workspace/datasets/<project_id>/batch")
    def dataset_batch(project_id):
        if not local() or not valid_origin():
            return jsonify(error="Manage datasets on the launcher PC"), 403
        if not project_exists(project_id):
            return jsonify(error="Active project not found"), 404
        if request.mimetype != "application/json" or not 0 < (request.content_length or 0) <= 8192:
            return jsonify(error="Invalid request"), 400
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify(error="Invalid batch"), 400
        action, ids, review = body.get("action"), body.get("ids"), body.get("review")
        if action not in ("review", "remove") or not isinstance(ids, list) or not 0 < len(ids) <= 200:
            return jsonify(error="Invalid batch"), 400
        if any(not isinstance(i, str) or len(i) != 32 or any(c not in "0123456789abcdef" for c in i) for i in ids):
            return jsonify(error="Invalid image ids"), 400
        if action == "review" and review not in REVIEWS:
            return jsonify(error="Invalid review state"), 400
        ids = list(dict.fromkeys(ids))
        with closing(db()) as conn, conn:
            before = conn.total_changes
            for image_id in ids:
                if action == "remove":
                    conn.execute("DELETE FROM dataset_images WHERE project_id=? AND id=?", (project_id, image_id))
                else:
                    conn.execute("UPDATE dataset_images SET review=? WHERE project_id=? AND id=?",
                                 (review, project_id, image_id))
            count = conn.total_changes - before
        return jsonify(updated=count, note="Original images unchanged")

    @app.route("/api/workspace/datasets/<project_id>/<image_id>", methods=["GET", "DELETE"])
    def dataset_image(project_id, image_id):
        if not local():
            return jsonify(error="Manage datasets on the launcher PC"), 403
        if not project_exists(project_id):
            return jsonify(error="Active project not found"), 404
        if request.method == "DELETE" and not valid_origin():
            return jsonify(error="Cross-origin changes are not allowed"), 403
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
