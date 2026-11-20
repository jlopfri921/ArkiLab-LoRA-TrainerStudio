"""OrkiLab project metadata. No trainer files are changed by this module."""
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def timestamp():
    return datetime.now(timezone.utc).isoformat()


class ProjectStore:
    def __init__(self, db):
        self.db = Path(db)

    @contextmanager
    def connect(self):
        self.db.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                conn.execute("""CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, engine TEXT NOT NULL,
                    category TEXT NOT NULL, dataset TEXT NOT NULL DEFAULT '',
                    notes TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL, archived INTEGER NOT NULL DEFAULT 0
                )""")
                yield conn
        finally:
            conn.close()

    def list(self, archived=False):
        with self.connect() as c:
            return [dict(r) for r in c.execute(
                "SELECT * FROM projects WHERE archived=? ORDER BY updated_at DESC, id",
                (int(archived),))]

    def create(self, payload, engines):
        if not isinstance(payload, dict):
            raise ValueError("Expected an object")
        fields = {}
        for key, limit in (("name", 120), ("engine", 80), ("category", 30),
                           ("dataset", 1024), ("notes", 4000)):
            value = payload.get(key, "")
            if not isinstance(value, str) or len(value) > limit:
                raise ValueError("Invalid " + key)
            fields[key] = value.strip()
        if not fields["name"]:
            raise ValueError("Project name is required")
        if fields["engine"] not in engines:
            raise ValueError("Unknown training engine")
        if fields["category"] not in ("image", "video", "audio", "multimodal"):
            raise ValueError("Invalid project category")
        now = timestamp()
        row = dict(fields, id=uuid.uuid4().hex, created_at=now, updated_at=now, archived=0)
        with self.connect() as c:
            c.execute("""INSERT INTO projects
                (id,name,engine,category,dataset,notes,created_at,updated_at,archived)
                VALUES (:id,:name,:engine,:category,:dataset,:notes,:created_at,:updated_at,:archived)""", row)
        return row

    def archive(self, project_id, archived=True):
        with self.connect() as c:
            cur = c.execute("UPDATE projects SET archived=?, updated_at=? WHERE id=?",
                            (int(archived), timestamp(), project_id))
            return cur.rowcount == 1
